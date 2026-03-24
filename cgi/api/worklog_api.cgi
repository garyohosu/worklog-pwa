#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, os, json
import urllib.parse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))
from cors import check_cors_or_exit, cors_headers
import response as _resp_mod
from db import DB_PATH, init_db
from auth import check_session, AuthError
from worklog import (
    get_worklogs, get_worklog_detail, create_worklog,
    update_worklog, delete_worklog, sync_push, sync_pull,
    WorkLogError,
)

origin = check_cors_or_exit()
_cors_hdrs = cors_headers(origin)
_orig_output = _resp_mod._output
def _patched_output(status_code, body, extra_headers=None):
    _orig_output(status_code, body, _cors_hdrs + (extra_headers or []))
_resp_mod._output = _patched_output

from response import ok, created, error, conflict, list_response

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
            include_deleted = qs.get("include_deleted", ["0"])[0] == "1"
            page = int(qs.get("page", ["1"])[0])
            page_size = int(qs.get("page_size", ["50"])[0])
            items, total, has_next = get_worklogs(DB_PATH, user_id, role, include_deleted, page, page_size)
            list_response(items, total, has_next)

        elif action == "detail":
            log_uuid = qs.get("log_uuid", [""])[0]
            item = get_worklog_detail(DB_PATH, log_uuid, user_id, role)
            ok({"item": item})

        elif action == "sync_pull":
            since_token = qs.get("since_token", [None])[0]
            items, next_since_token = sync_pull(DB_PATH, user_id, role, since_token)
            ok({"items": items, "next_since_token": next_since_token})

        else:
            error("Unknown action", 400)

    elif method == "POST":
        if action == "create":
            fields = dict(body)
            item = create_worklog(DB_PATH, user_id, fields)
            created({"item": item})

        elif action == "sync_push":
            items = body.get("items", [])
            results = sync_push(DB_PATH, items, user_id)
            ok({"results": results})

        else:
            error("Unknown action", 400)

    elif method == "PUT":
        if action == "update":
            log_uuid = body.get("log_uuid", "")
            base_revision = body.get("base_revision")
            fields = body.get("fields", {})
            item = update_worklog(DB_PATH, log_uuid, base_revision, fields, user_id, role)
            ok({"item": item})

        elif action == "status":
            log_uuid = body.get("log_uuid", "")
            base_revision = body.get("base_revision")
            status_val = body.get("status", "")
            item = update_worklog(DB_PATH, log_uuid, base_revision, {"status": status_val}, user_id, role)
            ok({"item": item})

        else:
            error("Unknown action", 400)

    elif method == "DELETE":
        if action == "delete":
            log_uuid = qs.get("log_uuid", [""])[0]
            delete_worklog(DB_PATH, log_uuid, user_id, role)
            ok()

        else:
            error("Unknown action", 400)

    else:
        error("Method not allowed", 405)

except WorkLogError as e:
    if e.status_code == 409:
        conflict(e.message, e.server_entity)
    else:
        error(e.message, e.status_code)
except Exception as e:
    error("Internal server error", 500)
