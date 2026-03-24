#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))
from cors import check_cors_or_exit, cors_headers
import response as _resp_mod
from db import DB_PATH, init_db
from auth import login_user, AuthError

origin = check_cors_or_exit()
_cors_hdrs = cors_headers(origin)
_orig_output = _resp_mod._output
def _patched_output(status_code, body, extra_headers=None):
    _orig_output(status_code, body, _cors_hdrs + (extra_headers or []))
_resp_mod._output = _patched_output

from response import ok, error

init_db(DB_PATH)

method = os.environ.get("REQUEST_METHOD", "GET").upper()

if method == "OPTIONS":
    print("Status: 204 No Content")
    for h in _cors_hdrs:
        print(h)
    print()
    sys.exit(0)

if method != "POST":
    error("Method not allowed", 405)
    sys.exit(0)

content_length = int(os.environ.get("CONTENT_LENGTH", 0) or 0)
body = {}
if content_length > 0:
    raw = sys.stdin.buffer.read(content_length)
    body = json.loads(raw) if raw else {}

login_id = body.get("login_id", "")
password = body.get("password", "")
ip = os.environ.get("REMOTE_ADDR", "")

try:
    result = login_user(DB_PATH, login_id, password, ip)
    ok({
        "session_token": result["session_token"],
        "user_id": result["user_id"],
        "display_name": result["display_name"],
        "role": result["role"],
    })
except AuthError as e:
    error(e.message, e.status_code)
except Exception:
    error("Internal server error", 500)
