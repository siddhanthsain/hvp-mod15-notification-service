# MOD-15 — Notification Service Architecture

## Role in HVP
MOD-15 is the async notification backbone. It decouples claim event producers
(MOD-04, MOD-05, MOD-06) from recipient notification logic.

## Data Flow
MOD-04/05/06  →  POST /notify  →  Dispatcher

↓

ChannelStore (who to notify)

↓

TemplateEngine (what to say)

↓

Provider (SMS/Email/In-app)

↓

DeliveryTracker (audit trail)

## Channels
- SMS → Patient (Twilio in prod, MockProvider in dev)
- EMAIL → Hospital Coordinator, Adjudicator (AWS SES in prod)
- IN_APP → Hospital Coordinator, Adjudicator
- WHATSAPP → Future (not yet wired)

## Port: 8015
## Called by: MOD-04, MOD-05, MOD-06
