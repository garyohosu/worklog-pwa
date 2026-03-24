#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, os, json
import urllib.parse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))
from cors import check_cors_or_exit, cors_headers
import response as _resp_mod
from db import DB_PATH, init_db
from auth import check_session, AuthError
from equipment import (
    list_equipment, search_equipment, get_by_qr,
    create_equipment, update_equipment, sync_pull_equipment,
    EquipmentError,
)

origin = check_cors_or_exit()
_cors_hdrs = cors_headers(origin)
_orig_output = _resp_mod._output
def _patched_output(status_code, body, extra_headers=None):
    _orig_output(status_code, body, _cors_hdrs + (extra_headers or []))
_resp_mod._output = _patched_output

from response import ok, created, error, conflict

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
        if action == "list":
            items = list_equipment(DB_PATH)
            ok({"items": items})

        elif action == "search":
            q = qs.get("q", [""])[0]
            items = search_equipment(DB_PATH, q)
            ok({"items": items})

        elif action == "by_qr":
            qr_value = qs.get("qr_value", [""])[0]
            item = get_by_qr(DB_PATH, qr_value)
            ok({"item": item})

        elif action == "sync_pull":
            since_token = qs.get("since_token", [None])[0]
            items, next_since_token = sync_pull_equipment(DB_PATH, since_token)
            ok({"items": items, "next_since_token": next_since_token})

        else:
            error("Unknown action", 400)

    elif method == "POST":
        item = create_equipment(DB_PATH, role, body)
        created({"item": item})

    elif method == "PUT":
        equipment_code = body.get("equipment_code", "")
        item = update_equipment(DB_PATH, equipment_code, role, body)
        ok({"item": item})

    else:
        error("Method not allowed", 405)

except EquipmentError as e:
    if e.status_code == 409:
        conflict(e.message)
    else:
        error(e.message, e.status_code)
except Exception:
    error("Internal server error", 500)
