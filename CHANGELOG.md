# Changelog — MOD-15 Notification Service

## [0.1.0] — 2026-06-12

### Added
- C01: Channel Store — SMS/Email/WhatsApp/In-app channel preferences per recipient
- C02: Template Engine — built-in templates for all HVP claim events
- C03: Notification Dispatcher — event → recipient → channel → provider
- C04: Delivery Tracker — PENDING/DELIVERED/FAILED/DEAD audit trail
- C05: Notification API — POST /notify primary endpoint
- MockProvider for dev/test (zero-cost, no real sends)
- 133 unit tests, ≥88% coverage
