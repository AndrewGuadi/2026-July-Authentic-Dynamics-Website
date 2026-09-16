"""Defaults shared by development and production; secrets come from deployment."""


class Config:
    DEBUG = False
    TESTING = False
    SECRET_KEY = None
    MAX_CONTENT_LENGTH = 1024 * 1024
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = "Lax"
