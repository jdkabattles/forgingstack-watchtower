"""MCP wrapper client for ForgingStack Watchtower, v0.1.0.

An agent-native service must be usable by agents, not just by humans
with curl. MCP is the standard interface agents already speak, so the
wrapper exposes the same live REST API as MCP tools, with no duplicated
logic: every tool call goes through the REST API, so metering and
receipts stay in one place. The service itself is private; this file
is only a client.

Protocol: JSON-RPC 2.0 over stdio, no new dependencies (stdlib only).
Supported methods: initialize, ping, tools/list, tools/call.
Notifications (no id, e.g. notifications/initialized) get no response.

Environment:
  FORGINGSTACK_API_BASE  default https://forgingstack-watchtower.jkbattles.workers.dev
  FORGINGSTACK_API_KEY   required for all tools except check_in;
                         sign up via POST /v1/signup (key shown once)

Run:  python -m app.mcp_server
"""

import json
import os
import sys
import urllib.error
import urllib.request

BASE = os.environ.get(
    "FORGINGSTACK_API_BASE",
    "https://forgingstack-watchtower.jkbattles.workers.dev",
)
API_KEY = os.environ.get("FORGINGSTACK_API_KEY", "")

TOOLS = [
    {
        "name": "create_watch",
        "description": "Register a liveness watch on an agent. The agent "
        "must check in at least every interval_seconds (plus grace); if "
        "it goes quiet past that, Watchtower emails an alert and issues "
        "a hash-chained receipt. Costs 1 credit. Returns the watch plus "
        "a check-in key, shown once — save it: the agent checks in with "
        "it, and it cannot be shown again.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_id": {"type": "string"},
                "interval_seconds": {"type": "integer"},
                "grace_seconds": {"type": "integer"},
                "notify_email": {"type": "string"},
            },
            "required": [
                "agent_id", "interval_seconds", "grace_seconds",
                "notify_email",
            ],
        },
    },
    {
        "name": "check_in",
        "description": "Check in for a watch. Free. Needs only watch_id "
        "and the check-in key from watch registration — no API key. "
        "A check-in after an alert or overdue period returns a "
        "recovery receipt.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "watch_id": {"type": "integer"},
                "checkin_key": {"type": "string"},
            },
            "required": ["watch_id", "checkin_key"],
        },
    },
    {
        "name": "get_watch",
        "description": "Fetch a watch by id, with its current status "
        "(healthy, overdue, alerted, snoozed) and its last 20 events.",
        "inputSchema": {
            "type": "object",
            "properties": {"watch_id": {"type": "integer"}},
            "required": ["watch_id"],
        },
    },
    {
        "name": "get_credits",
        "description": "Remaining credit balance for the configured API key.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_receipt",
        "description": "Fetch a past Watchtower receipt by id. Receipts "
        "are hash-chained: each receipt's hash covers the previous "
        "receipt's hash, so tampering breaks the chain.",
        "inputSchema": {
            "type": "object",
            "properties": {"receipt_id": {"type": "integer"}},
            "required": ["receipt_id"],
        },
    },
]


def _http(method, path, body=None):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode() if body is not None else None,
        method=method,
    )
    # The check-in endpoint needs no API key; the rest do. Send the key
    # only when one is configured, so check_in works keyless.
    if API_KEY:
        req.add_header("X-API-Key", API_KEY)
    req.add_header("Content-Type", "application/json")
    # A User-Agent is required: the default Python urllib agent is
    # rejected (Cloudflare 1010) through some egress paths.
    req.add_header("User-Agent", "ForgingStack-Watchtower/0.1.0")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode() or "{}")
        except Exception:
            return e.code, {"detail": "api error"}


def _text(payload, is_error=False):
    return {
        "content": [{"type": "text", "text": json.dumps(payload)}],
        "isError": is_error,
    }


def handle(msg):
    method = msg.get("method")
    params = msg.get("params") or {}
    if method == "initialize":
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "forgingstack-watchtower", "version": "0.1.0"},
        }
    if method == "ping":
        return {}
    if method == "tools/list":
        return {"tools": TOOLS}
    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments") or {}
        if name == "create_watch":
            body = {k: args[k] for k in
                    ("agent_id", "interval_seconds", "grace_seconds",
                     "notify_email")}
            status, data = _http("POST", "/v1/watches", body)
            return _text(data, is_error=status >= 400)
        if name == "check_in":
            body = {k: args[k] for k in ("watch_id", "checkin_key")}
            status, data = _http("POST", "/v1/checkin", body)
            return _text(data, is_error=status >= 400)
        if name == "get_watch":
            status, data = _http(
                "GET", f"/v1/watches/{args['watch_id']}"
            )
            return _text(data, is_error=status >= 400)
        if name == "get_credits":
            status, data = _http("GET", "/v1/credits")
            return _text(data, is_error=status >= 400)
        if name == "get_receipt":
            status, data = _http(
                "GET", f"/v1/receipts/{args['receipt_id']}"
            )
            return _text(data, is_error=status >= 400)
        raise ValueError(f"unknown tool: {name}")
    raise ValueError(f"unknown method: {method}")


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        # Notifications carry no id and get no response.
        if "id" not in msg:
            continue
        try:
            result = handle(msg)
            out = {"jsonrpc": "2.0", "id": msg["id"], "result": result}
        except Exception as exc:  # noqa: BLE001 - MCP error surface
            out = {
                "jsonrpc": "2.0", "id": msg["id"],
                "error": {"code": -32603, "message": str(exc)},
            }
        sys.stdout.write(json.dumps(out) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
