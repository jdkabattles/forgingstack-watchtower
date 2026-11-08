# ForgingStack Watchtower — skill for agents

Use this tool when an agent is expected to keep checking in and the
caller wants to hear about it the moment it goes quiet.

## When to use it

- A long-running agent, worker, or scheduled job that should report
  in on a schedule — register a watch, hand the agent its check-in
  key, and let Watchtower listen.
- When silence itself is the signal: a stuck worker, a crashed
  agent, a job that stopped without saying so.

## When NOT to use it

- To check whether an action was allowed. That is Mandate Check's
  job, not this one. Watchtower watches liveness only: it never
  judges what the agent did, only whether it is still there.
- For an agent that has no way to check in. Without check-ins there
  is nothing to watch — the first silence alerts immediately.

## How to call it (MCP)

Tool: `create_watch`
Arguments: `agent_id`, `interval_seconds` (30 to 2,592,000),
`grace_seconds` (0 to 86,400), `notify_email`.
Costs 1 credit. Returns the watch plus a check-in key, shown once —
save it and give it to the watched agent.

Tool: `check_in`
Arguments: `watch_id`, `checkin_key`. Free, no API key needed.
A check-in after an alert or overdue period returns a recovery
receipt.

Tool: `get_watch`
Arguments: `watch_id`. Returns the watch status — `healthy`,
`overdue`, `alerted`, or `snoozed` — plus `next_expected_checkin`,
`alert_deadline`, and the last 20 events.

## How to read the result

- `status: "healthy"` → the agent checked in on schedule.
- `status: "overdue"` → quiet past its interval, still inside grace.
- `status: "alerted"` → quiet past interval plus grace; an alert
  email was sent and an alert receipt was issued (1 credit).
- `status: "snoozed"` → alerts silenced until `snoozed_until`.
- One watch per agent per owner. A second watch for the same agent
  is rejected with the existing watch id — delete it first to
  register a different one.

## Status

Live, v0.1.2. API: https://forgingstack-watchtower.jkbattles.workers.dev
Signup: POST /v1/signup with an email returns an API key once and
100 starter credits; email verification is required before the key
can register watches. Credit packs: $10 for 1,000 credits via
POST /v1/billing/checkout.
