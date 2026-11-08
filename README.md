# ForgingStack Watchtower

The agent that stops checking in IS the one you will hear about.

mcp-name: io.github.jdkabattles/forgingstack-watchtower

This is the **public client** for Watchtower. The service itself —
the liveness checks, the alert emails, the receipt chain, the key
store, and billing — runs on ForgingStack's private service and is
**not** in this repo. Copying this repo does not give you the service:
you still need an API key and credits, from signup below.

Live API: https://forgingstack-watchtower.jkbattles.workers.dev

## How it works

1. You register a watch on an agent: how often it should check in
   (`interval_seconds`, 30 to 2,592,000) plus extra quiet time allowed
   (`grace_seconds`, 0 to 86,400), and where the alert email goes.
   One watch per agent per owner. Registering a watch costs 1 credit
   and returns a check-in key, shown once.
2. The agent checks in with its watch id and check-in key. Check-ins
   are free and need no API key.
3. If the agent goes quiet past its interval plus grace, Watchtower
   emails an alert and issues a hash-chained receipt. Each alert
   costs the watch owner 1 credit; an owner at 0 credits is skipped
   and the watch stays overdue.
4. When the agent checks in again after an alert or overdue period,
   a recovery receipt is issued. You can also snooze a watch
   (1 to 1,440 minutes) to silence alerts for a while.

## Signup (v1)

```bash
curl -X POST https://forgingstack-watchtower.jkbattles.workers.dev/v1/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com"}'
```

Returns an API key **once** and 100 starter credits. Save the key
immediately — it is stored only as a hash and cannot be shown again.
Click the verification link in the signup email before the key can
register watches; until then, watch registration returns 403.

## Use it (MCP, stdio)

Set the key, then run the MCP server in this repo:

```bash
export FORGINGSTACK_API_KEY="your-key-here"
python -m app.mcp_server
```

Tools: `create_watch`, `check_in`, `get_watch`, `get_credits`,
`get_receipt`. See `SKILL.md` for when to use it and when not to.

## Price

1 credit to register a watch, 1 credit per alert, check-ins free.
100 starter credits on signup. Credit packs: $10 for 1,000 credits,
bought with `POST /v1/billing/checkout` — credits are added once the
payment is verified (usually within the hour).

## Files in this repo

- `app/mcp_server.py` — MCP wrapper client (stdio, stdlib only)
- `SKILL.md` — when to use it, how to read watch status
- `agent-card.json` — A2A-style discovery card
- `server.json` — MCP Registry metadata
- `pyproject.toml` — package metadata for the MCP client
