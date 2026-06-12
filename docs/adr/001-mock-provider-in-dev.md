# ADR-001 — Use MockProvider in Dev and Tests

## Status: Accepted

## Context
Real SMS/email providers (Twilio, SES) require credentials, cost money,
and are unreliable in unit tests.

## Decision
Use MockProvider (in-memory) for all dev and test runs.
ProviderRegistry.mock=True is the default.
Production swap: set mock=False and inject real provider per channel.

## Consequences
- Zero cost in dev and CI
- No real messages sent during development
- Production deployment requires provider credentials via env vars
