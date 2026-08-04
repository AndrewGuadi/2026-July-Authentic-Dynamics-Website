"""Authorization gate and scope validation.

Nothing in this framework runs until :meth:`ScopeValidator.require_authorization`
succeeds. Scope inputs are normalised, sanity-checked and recorded verbatim so
that the engagement record shows exactly what was collected and why.
"""
from __future__ import annotations

import getpass
import ipaddress
import platform
import re
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.config import AppConfig

DOMAIN_RE = re.compile(
    r"^(?=.{4,253}$)(?!-)(?:[A-Za-z0-9-]{1,63}(?<!-)\.)+[A-Za-z]{2,63}$"
)
USERNAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._\-]{1,63}$")
NAME_RE = re.compile(r"^[\w \.\'\-,&]{2,120}$", re.UNICODE)
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[A-Za-z]{2,63}$")
COUNTRY_RE = re.compile(r"^[A-Za-z]{2}$")

RESERVED_HOSTS = {"localhost", "local", "internal", "test", "invalid", "example.com"}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".heic", ".webp", ".gif", ".pdf"}


class ValidationError(ValueError):
    """Raised when the supplied scope cannot be accepted."""


class AuthorizationError(PermissionError):
    """Raised when the operator has not attested authorization."""


@dataclass(slots=True)
class Scope:
    """Immutable record of an authorized engagement scope."""

    full_name: str
    client_slug: str
    domain: Optional[str]
    username: Optional[str]
    email: Optional[str]
    birth_date: Optional[str]
    country: Optional[str]
    subject_type: str
    image_dir: Optional[str]
    image_count: int
    engagement_id: str
    authorized: bool
    authorized_at: str
    operator: str
    hostname: str
    platform: str
    targets: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialise the scope for ``scope.json`` and the report header."""
        return asdict(self)


def slugify(value: str) -> str:
    """Return a filesystem-safe slug for workspace naming."""
    slug = re.sub(r"[^A-Za-z0-9]+", "_", value.strip()).strip("_").lower()
    return slug or "client"


class ScopeValidator:
    """Validate CLI inputs before any collection begins."""

    def __init__(self, config: AppConfig) -> None:
        """Store config for image-extension and module awareness."""
        self.config = config

    # -- authorization ---------------------------------------------------
    @staticmethod
    def require_authorization(flag: str) -> None:
        """Abort unless the operator passed ``--authorized yes``.

        Args:
            flag: Raw value of the ``--authorized`` option.

        Raises:
            AuthorizationError: If the value is anything other than ``yes``.
        """
        if str(flag).strip().lower() != "yes":
            raise AuthorizationError(
                "explicit authorization attestation missing (received "
                f"'{flag}'). No collection was performed."
            )

    # -- field validation ------------------------------------------------
    @staticmethod
    def validate_full_name(value: str) -> str:
        """Validate the audit subject's name/brand."""
        name = " ".join(str(value).split())
        if not NAME_RE.match(name):
            raise ValidationError(f"invalid --full-name value: {value!r}")
        return name

    @staticmethod
    def validate_domain(value: str) -> str:
        """Validate a public, non-reserved domain name."""
        domain = str(value).strip().lower().rstrip(".")
        domain = re.sub(r"^https?://", "", domain).split("/")[0]
        if not DOMAIN_RE.match(domain):
            raise ValidationError(f"invalid --domain value: {value!r}")
        if domain in RESERVED_HOSTS or domain.split(".")[-1] in RESERVED_HOSTS:
            raise ValidationError(f"reserved / non-routable domain rejected: {domain}")
        try:
            ipaddress.ip_address(domain)
        except ValueError:
            return domain
        raise ValidationError("IP addresses are out of scope for passive domain enumeration")

    @staticmethod
    def validate_username(value: str) -> str:
        """Validate a handle used for public account enumeration."""
        username = str(value).strip().lstrip("@")
        if not USERNAME_RE.match(username):
            raise ValidationError(f"invalid --username value: {value!r}")
        return username

    @staticmethod
    def validate_email(value: str) -> str:
        """Validate and normalize an explicitly authorized email target."""
        email = str(value).strip().lower()
        if len(email) > 254 or not EMAIL_RE.match(email):
            raise ValidationError(f"invalid --email value: {value!r}")
        return email

    @staticmethod
    def validate_birth_date(value: str) -> str:
        """Validate a yente matching date in ISO YYYY or YYYY-MM-DD format."""
        raw = str(value).strip()
        if re.fullmatch(r"\d{4}", raw):
            year = int(raw)
            if 1900 <= year <= date.today().year:
                return raw
        try:
            parsed = date.fromisoformat(raw)
        except ValueError as exc:
            raise ValidationError("--birth-date must be YYYY or YYYY-MM-DD") from exc
        if parsed > date.today():
            raise ValidationError("--birth-date cannot be in the future")
        return parsed.isoformat()

    @staticmethod
    def validate_country(value: str) -> str:
        """Validate a two-letter country code used only as a matching attribute."""
        country = str(value).strip().lower()
        if not COUNTRY_RE.match(country):
            raise ValidationError("--country must be a two-letter country code")
        return country

    @staticmethod
    def validate_subject_type(value: str) -> str:
        """Map the operator-facing subject type to the supported yente schemas."""
        subject_type = str(value).strip().lower()
        if subject_type not in {"person", "organization", "company"}:
            raise ValidationError("--subject-type must be person, organization, or company")
        return subject_type

    def validate_image_dir(self, value: Path) -> tuple[str, int]:
        """Validate a directory of client-supplied images.

        Returns:
            Tuple of (resolved path, number of candidate image files).
        """
        path = Path(value).expanduser().resolve()
        if not path.exists():
            raise ValidationError(f"--image-dir does not exist: {path}")
        if not path.is_dir():
            raise ValidationError(f"--image-dir is not a directory: {path}")
        allowed = {
            str(ext).lower()
            for ext in self.config.options_for("exiftool").get("extensions", IMAGE_SUFFIXES)
        }
        count = sum(1 for p in path.rglob("*") if p.is_file() and p.suffix.lower() in allowed)
        if count == 0:
            raise ValidationError(f"no supported image files found under {path}")
        return str(path), count

    # -- assembly --------------------------------------------------------
    def build_scope(
        self,
        full_name: str,
        domain: Optional[str],
        username: Optional[str],
        email: Optional[str],
        birth_date: Optional[str],
        country: Optional[str],
        subject_type: str,
        image_dir: Optional[Path],
        engagement_id: Optional[str] = None,
    ) -> Scope:
        """Validate every input and return an immutable :class:`Scope`.

        Raises:
            ValidationError: If a field is invalid or the scope is empty.
        """
        name = self.validate_full_name(full_name)
        clean_domain = self.validate_domain(domain) if domain else None
        clean_username = self.validate_username(username) if username else None
        clean_email = self.validate_email(email) if email else None
        clean_birth_date = self.validate_birth_date(birth_date) if birth_date else None
        clean_country = self.validate_country(country) if country else None
        clean_subject_type = self.validate_subject_type(subject_type)
        image_path, image_count = (None, 0)
        if image_dir is not None:
            image_path, image_count = self.validate_image_dir(image_dir)

        identity_screening = bool(self.config.modules.get("yente", False))
        if not any([clean_domain, clean_username, clean_email, image_path, identity_screening]):
            raise ValidationError(
                "empty scope: supply --domain, --username, --email or --image-dir, "
                "or enable the yente identity-screening module"
            )

        now = datetime.now(timezone.utc)
        targets = [t for t in (clean_domain, clean_username, clean_email, image_path) if t]
        if identity_screening:
            targets.append(name)
        return Scope(
            full_name=name,
            client_slug=slugify(name),
            domain=clean_domain,
            username=clean_username,
            email=clean_email,
            birth_date=clean_birth_date,
            country=clean_country,
            subject_type=clean_subject_type,
            image_dir=image_path,
            image_count=image_count,
            engagement_id=engagement_id or f"RAF-{now.strftime('%Y%m%d-%H%M%S')}",
            authorized=True,
            authorized_at=now.isoformat(),
            operator=_safe_operator(),
            hostname=platform.node(),
            platform=f"{platform.system()} {platform.release()}",
            targets=targets,
        )


def _safe_operator() -> str:
    """Best-effort operator identity for the audit trail."""
    try:
        return getpass.getuser()
    except Exception:  # pragma: no cover - container/no-passwd environments
        return "unknown"
