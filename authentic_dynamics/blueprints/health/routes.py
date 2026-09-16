from . import bp


@bp.get("/healthz")
def health():
    """Process liveness only; no external dependencies are configured yet."""
    return {"status": "ok"}, 200, {"Cache-Control": "no-store"}
