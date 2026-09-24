"""Defaults shared by development and production; secrets come from deployment."""


class Config:
    DEBUG = False
    TESTING = False
    SECRET_KEY = None
    # Set in production to the single public hostname (without a scheme).
    CANONICAL_HOST = ""
    SQLALCHEMY_DATABASE_URI = "sqlite:///authentic_dynamics.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    VIDEO_SERVER_ENABLED = True
    VIDEO_MAX_BYTES = 128 * 1024 * 1024
    VIDEO_MAX_SECONDS = 180
    VIDEO_TIMEOUT_SECONDS = 300
    VIDEO_BROWSER_MAX_BYTES = 64 * 1024 * 1024
    VIDEO_BROWSER_MAX_SECONDS = 60
    SESSION_COOKIE_HTTPONLY = True
    # Local development runs over HTTP. Set AD_SESSION_COOKIE_SECURE=true behind HTTPS.
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_SAMESITE = "Lax"
