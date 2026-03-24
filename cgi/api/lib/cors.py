"""CORS handling for CGI responses."""
import os

ALLOWED_ORIGINS = {
    "https://garyohosu.github.io",
    "http://localhost",
    "http://127.0.0.1",
}


def get_origin():
    """Return the Origin header from the current request."""
    return os.environ.get("HTTP_ORIGIN", "")


def is_allowed_origin(origin: str) -> bool:
    """Return True if origin is in the allowed list."""
    if not origin:
        return False
    # Allow localhost/127.0.0.1 with any port for local dev
    for allowed in ALLOWED_ORIGINS:
        if origin == allowed:
            return True
        if allowed in ("http://localhost", "http://127.0.0.1"):
            if origin.startswith(allowed + ":") or origin == allowed:
                return True
    return False


def cors_headers(origin: str) -> list:
    """Return CORS response headers for an allowed origin."""
    return [
        f"Access-Control-Allow-Origin: {origin}",
        "Access-Control-Allow-Credentials: true",
        "Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers: Authorization, Content-Type",
    ]


def check_cors_or_exit():
    """
    Check CORS Origin. If missing or not allowed, print 403 and exit.
    Returns the allowed origin string if OK.
    """
    import sys
    import json

    origin = get_origin()
    if not is_allowed_origin(origin):
        print("Status: 403 Forbidden")
        print("Content-Type: application/json; charset=utf-8")
        print()
        print(json.dumps({"status": "error", "message": "Forbidden", "errors": []}))
        sys.exit(0)
    return origin
