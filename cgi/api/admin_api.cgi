#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, os, json
import urllib.parse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))
from cors import check_cors_or_exit, cors_headers
import response as _resp_mod
from db import DB_PATH, init_db
from auth import check_session, reset_password as auth_reset_password, AuthError
from admin import list_users, get_dashboard, set_active, set_role, AdminError

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

auth_header = os.environ.get("HTTP_AUTHORIZATION", "")
token = auth_header.replace("Bearer ", "").strip() if auth_header.startswith("Bearer ") else ""

try:
    sess = check_session(DB_PATH, token)
except AuthError as e:
    error(e.message, e.status_code)
    sys.exit(0)

user_id = sess["user_id"]
role = sess["role"]

qs = urllib.parse.parse_qs(os.environ.get("QUERY_STRING", ""))
action = qs.get("action", [""])[0]

content_length = int(os.environ.get("CONTENT_LENGTH", 0) or 0)
body = {}
if content_length > 0:
    raw = sys.stdin.buffer.read(content_length)
    body = json.loads(raw) if raw else {}

try:
    if method == "GET":
        if action == "user_list":
            items = list_users(DB_PATH, role)
            ok({"items": items})

        elif action == "dashboard":
            data = get_dashboard(DB_PATH, role)
            ok({"data": data})

        else:
            error("Unknown action", 400)

    elif method == "POST":
        if action == "reset_password":
            login_id = body.get("login_id", "")
            if role != "admin":
                error("Forbidden", 403)
                sys.exit(0)
            temp_password = auth_reset_password(DB_PATH, login_id)
            ok({"temp_password": temp_password})

        else:
            error("Unknown action", 400)

    elif method == "PUT":
        if action == "set_active":
            target_user_id = body.get("target_user_id")
            is_active = body.get("is_active")
            set_active(DB_PATH, target_user_id, is_active, user_id, role)
            ok()

        elif action == "set_role":
            target_user_id = body.get("target_user_id")
            new_role = body.get("role", "")
            set_role(DB_PATH, target_user_id, new_role, user_id, role)
            ok()

        else:
            error("Unknown action", 400)

    else:
        error("Method not allowed", 405)

except AdminError as e:
    error(e.message, e.status_code)
except Exception:
    error("Internal server error", 500)
