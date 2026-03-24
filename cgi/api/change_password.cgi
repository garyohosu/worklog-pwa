#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))
from cors import check_cors_or_exit, cors_headers
import response as _resp_mod
from db import DB_PATH, init_db
from auth import check_session, change_password, AuthError

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

auth_header = os.environ.get("HTTP_AUTHORIZATION", "")
token = auth_header.replace("Bearer ", "").strip() if auth_header.startswith("Bearer ") else ""

content_length = int(os.environ.get("CONTENT_LENGTH", 0) or 0)
body = {}
if content_length > 0:
    raw = sys.stdin.buffer.read(content_length)
    body = json.loads(raw) if raw else {}

old_password = body.get("old_password", "")
new_password = body.get("new_password", "")

try:
    change_password(DB_PATH, token, old_password, new_password)
    ok()
except AuthError as e:
    error(e.message, e.status_code)
except Exception:
    error("Internal server error", 500)
