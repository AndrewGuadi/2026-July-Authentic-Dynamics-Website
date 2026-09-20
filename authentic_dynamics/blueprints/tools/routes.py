import io
from pathlib import Path

from flask import render_template, request, send_file
from werkzeug.utils import secure_filename

from . import bp
from .converters import MAX_FILE_BYTES, ConversionError, convert_csv, convert_json, convert_pdf

MIMETYPES = {
    "png": "image/png", "webp": "image/webp", "jpeg": "image/jpeg",
    "zip": "application/zip", "json": "application/json", "xml": "application/xml",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "tsv": "text/tab-separated-values",
    "csv": "text/csv",
}


@bp.after_request
def private_response(response):
    response.headers["Cache-Control"] = "no-store"
    return response


@bp.get("")
@bp.get("/")
def catalog():
    return render_template("tools/catalog.html", active_page="tools")


@bp.route("/pdf-to-image", methods=["GET", "POST"])
def pdf():
    return converter("pdf")


@bp.get("/local-ai")
def local_ai():
    return render_template("tools/local_ai.html", active_page="tools")


@bp.get("/list-cleaner")
def list_cleaner():
    return render_template("tools/list_cleaner.html", active_page="tools")


@bp.get("/free-invoice-maker")
def free_invoice_maker():
    return render_template("tools/free_invoice_maker.html", active_page="tools")


@bp.get("/qr-code-maker")
def qr_code_maker():
    return render_template("tools/qr_code_maker.html", active_page="tools")


@bp.route("/csv-converter", methods=["GET", "POST"])
def csv():
    return converter("csv")


@bp.route("/json-converter", methods=["GET", "POST"])
def json_converter():
    error = None
    if request.method == "POST":
        try:
            upload = request.files.get("file")
            content = request.form.get("json_text", "")
            stem = "converted"
            if upload and upload.filename:
                if content.strip():
                    raise ConversionError("Choose either a file or pasted JSON, then clear the other input.")
                if Path(upload.filename).suffix.lower() != ".json":
                    raise ConversionError("Choose a .json file.")
                data = upload.read(MAX_FILE_BYTES + 1)
                stem = Path(secure_filename(upload.filename)).stem[:100] or "converted"
            else:
                data = content.encode("utf-8")
                if len(data) > 400000:
                    raise ConversionError("Pasted JSON is limited to 400 KB. Upload a JSON file for larger data.")
            extension = request.form.get("format", "xlsx")
            result = convert_json(data, extension)
            return send_file(io.BytesIO(result), mimetype=MIMETYPES[extension],
                             as_attachment=True, download_name=f"{stem}.{extension}", max_age=0)
        except ConversionError as exc:
            error = str(exc)
            if request.accept_mimetypes.best == "application/json":
                return {"error": error}, 400
    return render_template("tools/json_converter.html", error=error,
                           values=request.form, active_page="tools"), 400 if error else 200


def converter(kind):
    error = None
    if request.method == "POST":
        try:
            upload = request.files.get("file")
            if not upload or not upload.filename:
                raise ConversionError("Choose a file to convert.")
            if Path(upload.filename).suffix.lower() != f".{kind}":
                raise ConversionError(f"Choose a .{kind} file.")
            data = upload.read(MAX_FILE_BYTES + 1)
            if not data or len(data) > MAX_FILE_BYTES:
                raise ConversionError("Choose a nonempty file no larger than 10 MiB.")
            extension = request.form.get("format", "")
            if kind == "pdf":
                dpi = request.form.get("dpi", "150")
                if dpi not in {"72", "150", "300"}:
                    raise ConversionError("Choose a supported resolution.")
                result, extension = convert_pdf(data, extension, int(dpi))
            else:
                result = convert_csv(data, extension, request.form.get("delimiter", ","),
                                     request.form.get("headers") == "on")
            stem = Path(secure_filename(upload.filename)).stem[:100] or "converted"
            return send_file(io.BytesIO(result), mimetype=MIMETYPES[extension],
                             as_attachment=True, download_name=f"{stem}.{extension}", max_age=0)
        except ConversionError as exc:
            error = str(exc)
            if request.accept_mimetypes.best == "application/json":
                return {"error": error}, 400
    return render_template("tools/converter.html", kind=kind, error=error,
                           values=request.form, active_page="tools"), 400 if error else 200
