"""Private immutable file storage. Storage keys never come from upload filenames."""

import hashlib
import os
import re
from pathlib import Path
from uuid import uuid4

from flask import current_app
from PIL import Image
from werkzeug.exceptions import Forbidden
from werkzeug.utils import secure_filename

from authentic_dynamics.extensions import db
from authentic_dynamics.hub import models as m

from .core import audit, get_record, membership


class StorageService:
    def __init__(self, root=None):
        self.root = Path(root or current_app.config['HUB_UPLOAD_DIR']).resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)

    def path(self, key):
        if not re.fullmatch(r'[a-f0-9]{32}', key):
            raise ValueError('Invalid storage key.')
        path = self.root / key
        if path.is_symlink():
            raise ValueError('Storage symlinks are not allowed.')
        return path

    def save(self, stream):
        key = uuid4().hex
        path = self.path(key)
        digest, size = hashlib.sha256(), 0
        try:
            with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'wb') as target:
                while chunk := stream.read(65536):
                    size += len(chunk)
                    if size > current_app.config['HUB_UPLOAD_MAX_BYTES']:
                        raise ValueError('Document exceeds the upload limit.')
                    digest.update(chunk)
                    target.write(chunk)
                target.flush()
                os.fsync(target.fileno())
            if not size:
                raise ValueError('Empty documents are not supported.')
            return key, digest.hexdigest(), size
        except Exception:
            path.unlink(missing_ok=True)
            raise

    def open(self, key):
        return self.path(key).open('rb')

    def delete(self, key):
        if db.session.scalar(db.select(m.DocumentVersion.id).where(m.DocumentVersion.storage_key == key)):
            raise ValueError('Referenced document versions are retained.')
        self.path(key).unlink(missing_ok=True)


def validate_format(path, filename):
    extension = Path(filename).suffix.lower()
    if extension == '.pdf':
        with path.open('rb') as stream:
            if not stream.read(8).startswith(b'%PDF-'):
                raise ValueError('File is not a PDF.')
        return 'application/pdf'
    if extension in {'.png', '.jpg', '.jpeg'}:
        with Image.open(path) as picture:
            if picture.format != ('PNG' if extension == '.png' else 'JPEG'):
                raise ValueError('Image format does not match its extension.')
            picture.verify()
        return 'image/png' if extension == '.png' else 'image/jpeg'
    if extension in {'.txt', '.csv'}:
        content = path.read_text(encoding='utf-8')
        if '\x00' in content:
            raise ValueError('Binary content is not a text document.')
        return 'text/plain' if extension == '.txt' else 'text/csv'
    raise ValueError('Use PDF, PNG, JPEG, UTF-8 TXT, or CSV files.')


def may_read(document, workspace_id, actor_id):
    member = membership(workspace_id, actor_id)
    if document.workspace_id != workspace_id or (
        document.confidential and member.role not in {'owner', 'admin'}
    ):
        raise Forbidden()


def upload(document_id, file, workspace_id, actor_id):
    membership(workspace_id, actor_id, write=True)
    document = get_record('documents', document_id, workspace_id)
    may_read(document, workspace_id, actor_id)
    storage = StorageService()
    key, digest, size = storage.save(file.stream)
    try:
        filename = secure_filename(file.filename or '')[:250]
        mime = validate_format(storage.path(key), filename)
        version_number = db.session.scalar(db.select(db.func.coalesce(
            db.func.max(m.DocumentVersion.version_number), 0)).where(
            m.DocumentVersion.document_id == document.id)) + 1
        version = m.DocumentVersion(workspace_id=workspace_id, document_id=document.id,
            version_number=version_number, storage_key=key, sha256=digest, size_bytes=size,
            mime_type=mime, original_name=filename, uploaded_by=actor_id)
        db.session.add(version)
        db.session.flush()
        document.current_version_id = version.id
        audit(workspace_id, actor_id, 'upload_version', version)
        db.session.commit()
        return version
    except Exception:
        db.session.rollback()
        storage.delete(key)
        raise
