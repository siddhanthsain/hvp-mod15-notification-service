# MOD-15 — HVP Notification Service

Multi-channel notification service for the Health Value Platform.
Port 8015 | Called by MOD-04 (claim events), MOD-05 (patient alerts), MOD-06 (adjudicator assignments).

## Components

| Component | Status | Tests | Description |
|-----------|--------|-------|-------------|
| C01 Channel Store | ✅ Done | 28 | SMS, Email, WhatsApp, In-app per recipient |
| C02 Template Engine | ✅ Done | 29 | Message templates per event type per channel |
| C03 Notification Dispatcher | ✅ Done | 24 | Event → recipient → channel → provider |
| C04 Delivery Tracker | ✅ Done | 27 | PENDING/DELIVERED/FAILED/DEAD with retries |
| C05 Notification API | ✅ Done | 25 | POST /notify — primary endpoint |

**Total: 133 tests | Coverage ≥ 88%**

## How it works
MOD-04 fires claim.approved

↓

POST /api/v1/notifications/notify

↓

Dispatcher looks up hospital_coordinator_id + patient_abha

↓

ChannelStore → coordinator gets EMAIL+IN_APP, patient gets SMS

↓

TemplateEngine renders message per channel

↓

MockProvider records send (swap with Twilio/SES in prod)

↓

DeliveryTracker records DLV-XXXXXXXX per send

↓

Response: { dispatched_count: 3, delivered: 3, notification_ids: [...] }

## API Endpoints

| Endpoint | Method | Called by | Description |
|----------|--------|-----------|-------------|
| /api/v1/notifications/notify | POST | MOD-04/05/06 | Primary notify endpoint |
| /api/v1/notifications/claim/{claim_id} | GET | MOD-05/06 | All notifications for a claim |
| /api/v1/notifications/stats | GET | Dashboard | Delivery stats |
| /api/v1/notifications/channels | POST/GET | Setup | Configure recipient channels |
| /api/v1/notifications/templates | GET/POST | Setup | Template management |
| /api/v1/notifications/templates/render | POST | Debug | Render a template |
| /api/v1/notifications/deliveries | GET | Ops | List all deliveries |
| /api/v1/notifications/deliveries/stats | GET | Ops | Delivery stats |

## Default Channel Assignments

| Recipient Type | Channels |
|----------------|----------|
| HOSPITAL_COORDINATOR | EMAIL + IN_APP |
| PATIENT | SMS |
| INSURER_ADJUDICATOR | IN_APP + EMAIL |
| INSURER_ADMIN | EMAIL + IN_APP |

## Running

```bash
source .venv/bin/activate
uvicorn hvp_mod15_notification_service.main:app --port 8015 --app-dir src
```

## Testing

```bash
pytest tests/unit/ -q --cov=hvp_mod15_notification_service
```
