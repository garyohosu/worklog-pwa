"""HTTP response helpers for CGI handlers."""
import json
import sys


def _output(status_code: int, body: dict, extra_headers: list = None):
    """Write CGI response to stdout."""
    status_map = {
        200: "200 OK",
        201: "201 Created",
        400: "400 Bad Request",
        401: "401 Unauthorized",
        403: "403 Forbidden",
        404: "404 Not Found",
        409: "409 Conflict",
        429: "429 Too Many Requests",
        500: "500 Internal Server Error",
    }
    status_text = status_map.get(status_code, f"{status_code}")
    print(f"Status: {status_text}")
    print("Content-Type: application/json; charset=utf-8")
    if extra_headers:
        for h in extra_headers:
            print(h)
    print()
    print(json.dumps(body, ensure_ascii=False))


def ok(data=None, message="", status_code=200):
    body = {"status": "ok", "message": message}
    if data is not None:
        body["data"] = data
    _output(status_code, body)


def created(data=None, message=""):
    ok(data=data, message=message, status_code=201)


def error(message: str, status_code: int = 400, errors: list = None):
    body = {"status": "error", "message": message, "errors": errors or []}
    _output(status_code, body)


def conflict(message: str, server_entity: dict = None):
    body = {
        "status": "error",
        "message": message,
        "data": {"server_entity": server_entity or {}},
        "errors": [],
    }
    _output(409, body)


def list_response(items: list, total: int, has_next: bool):
    ok(data={"items": items, "total": total, "has_next": has_next})
