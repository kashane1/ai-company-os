# worker-outreach

The cold outreach operations lane for deployed local-SMB demos.

## Owns

- refreshing the outreach client-status ledger
- drafting and organizing operator-ready outreach artifacts
- logging manual touches when supplied by the operator
- reconciling replies through a future approved CRM/inbox adapter

## Does not own

- sending cold email
- sending SMS/texts
- sending Instagram or Facebook DMs
- bypassing opt-out or suppression rules
- owning CRM deliverability or inbox state

## Entrypoint

[main.py](main.py) claims `outreach` tasks from the control plane. Lane-specific
logic lives in [outreach/](outreach/).

## Manual-send boundary

Outbound contact is human-gated. The worker fails closed for task types such as
`OUTREACH_SEND_EMAIL`, `OUTREACH_SEND_SMS`, `OUTREACH_SEND_INSTAGRAM_DM`, and
`OUTREACH_SEND_FACEBOOK_DM`.

## Operator list

The durable client status list lives at:

- `state/prospects/outreach-lane/client-status.md`
- `state/prospects/outreach-lane/client-status.json`
- `state/prospects/outreach-lane/touches.jsonl`
