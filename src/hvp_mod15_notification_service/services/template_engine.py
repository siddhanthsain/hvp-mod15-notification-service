# MOD15-C02 — Notification Template Engine
# One template per event_type per channel.
# Variables substituted at render time using str.format_map().

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


# Built-in templates for all HVP claim events
BUILTIN_TEMPLATES: list[dict] = [
    # ── Claim state changes (MOD-04 events) ─────────────────────────────────
    {
        "event_type": "claim.submitted",
        "channel":    "SMS",
        "subject":    None,
        "body":       "HVP: Claim {claim_id} submitted to {insurer_code}. Amount: Rs {claim_amount}. Track at HVP portal.",
    },
    {
        "event_type": "claim.submitted",
        "channel":    "EMAIL",
        "subject":    "Claim Submitted — {claim_id}",
        "body":       "Dear {actor_name},\n\nYour claim {claim_id} has been submitted to {insurer_code} for Rs {claim_amount}.\n\nExpected response: 3-7 working days.\n\nHVP Team",
    },
    {
        "event_type": "claim.submitted",
        "channel":    "IN_APP",
        "subject":    "Claim Submitted",
        "body":       "Claim {claim_id} submitted to {insurer_code}. Amount: Rs {claim_amount}.",
    },
    {
        "event_type": "claim.approved",
        "channel":    "SMS",
        "subject":    None,
        "body":       "HVP: APPROVED. Claim {claim_id} approved for Rs {approved_amount}. Disbursement in 3 working days.",
    },
    {
        "event_type": "claim.approved",
        "channel":    "EMAIL",
        "subject":    "Claim Approved — {claim_id}",
        "body":       "Dear {actor_name},\n\nClaim {claim_id} has been APPROVED.\nApproved amount: Rs {approved_amount}\nDisbursement: 3 working days\n\nHVP Team",
    },
    {
        "event_type": "claim.approved",
        "channel":    "IN_APP",
        "subject":    "Claim Approved ✓",
        "body":       "Claim {claim_id} approved for Rs {approved_amount}.",
    },
    {
        "event_type": "claim.rejected",
        "channel":    "SMS",
        "subject":    None,
        "body":       "HVP: REJECTED. Claim {claim_id} rejected. Reason: {rejection_reason}. Contact insurer for appeal.",
    },
    {
        "event_type": "claim.rejected",
        "channel":    "EMAIL",
        "subject":    "Claim Rejected — {claim_id}",
        "body":       "Dear {actor_name},\n\nClaim {claim_id} has been REJECTED.\nReason: {rejection_reason}\n\nFor appeal, contact {insurer_code} within 30 days.\n\nHVP Team",
    },
    {
        "event_type": "claim.rejected",
        "channel":    "IN_APP",
        "subject":    "Claim Rejected",
        "body":       "Claim {claim_id} rejected. Reason: {rejection_reason}",
    },
    {
        "event_type": "claim.queried",
        "channel":    "SMS",
        "subject":    None,
        "body":       "HVP: Insurer queried claim {claim_id}. Please submit documents within 7 days.",
    },
    {
        "event_type": "claim.queried",
        "channel":    "EMAIL",
        "subject":    "Documents Required — {claim_id}",
        "body":       "Dear {actor_name},\n\nInsurer has raised a query on claim {claim_id}.\nQuery: {query_text}\n\nPlease respond within 7 working days.\n\nHVP Team",
    },
    {
        "event_type": "claim.queried",
        "channel":    "IN_APP",
        "subject":    "Query on Claim",
        "body":       "Insurer queried claim {claim_id}: {query_text}",
    },
    # ── Adjudicator assignment (MOD-06 events) ────────────────────────────────
    {
        "event_type": "adjudicator.assigned",
        "channel":    "EMAIL",
        "subject":    "New Claim Assigned — {claim_id}",
        "body":       "Dear {actor_name},\n\nClaim {claim_id} (Rs {claim_amount}) from {hospital_code} has been assigned to you.\n\nLogin to HVP to review.\n\nHVP Team",
    },
    {
        "event_type": "adjudicator.assigned",
        "channel":    "IN_APP",
        "subject":    "New Claim",
        "body":       "Claim {claim_id} assigned to you. Hospital: {hospital_code}. Amount: Rs {claim_amount}.",
    },
    # ── Auth events (MOD-08) ──────────────────────────────────────────────────
    {
        "event_type": "auth.login_success",
        "channel":    "EMAIL",
        "subject":    "New Login to HVP",
        "body":       "Dear {actor_name},\n\nNew login detected at {timestamp_utc} from {ip_address}.\n\nIf this was not you, contact support immediately.\n\nHVP Team",
    },
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class TemplateEngine:
    def __init__(self) -> None:
        self._templates: dict[str, dict] = {}
        self._seed_builtin()

    def _seed_builtin(self) -> None:
        for t in BUILTIN_TEMPLATES:
            tpl_id = f"TPL-{uuid.uuid4().hex[:8].upper()}"
            self._templates[tpl_id] = {
                "template_id": tpl_id,
                "event_type":  t["event_type"],
                "channel":     t["channel"],
                "subject":     t.get("subject"),
                "body":        t["body"],
                "is_builtin":  True,
                "created_at":  _now(),
            }
        logger.info("Seeded %s built-in notification templates", len(BUILTIN_TEMPLATES))

    def get_template(self, event_type: str, channel: str) -> dict | None:
        """Get template for a specific event_type + channel combination."""
        for tpl in self._templates.values():
            if tpl["event_type"] == event_type and tpl["channel"] == channel:
                return tpl
        return None

    def render(self, event_type: str, channel: str, variables: dict) -> dict | None:
        """
        Render a template with variables.
        Missing variables are replaced with empty string (never raises KeyError).
        Returns dict with: subject, body, event_type, channel.
        Returns None if no template found.
        """
        tpl = self.get_template(event_type, channel)
        if not tpl:
            logger.warning("No template for event_type=%s channel=%s", event_type, channel)
            return None

        safe_vars = {k: str(v) if v is not None else "" for k, v in variables.items()}

        try:
            rendered_body    = tpl["body"].format_map(
                _SafeDict(safe_vars)
            )
            rendered_subject = (
                tpl["subject"].format_map(_SafeDict(safe_vars))
                if tpl.get("subject") else None
            )
        except Exception as exc:
            logger.error("Template render failed event=%s channel=%s: %s",
                         event_type, channel, exc)
            rendered_body    = tpl["body"]
            rendered_subject = tpl.get("subject")

        return {
            "event_type":  event_type,
            "channel":     channel,
            "subject":     rendered_subject,
            "body":        rendered_body,
            "template_id": tpl["template_id"],
        }

    def add_template(self, data: dict) -> dict:
        """Add a custom template. Cannot override built-in templates."""
        existing = self.get_template(data["event_type"], data["channel"])
        if existing and existing.get("is_builtin"):
            raise ValueError(
                f"Cannot override built-in template for {data['event_type']} / {data['channel']}"
            )
        tpl_id = f"TPL-{uuid.uuid4().hex[:8].upper()}"
        tpl    = {
            "template_id": tpl_id,
            "event_type":  data["event_type"],
            "channel":     data["channel"],
            "subject":     data.get("subject"),
            "body":        data["body"],
            "is_builtin":  False,
            "created_at":  _now(),
        }
        self._templates[tpl_id] = tpl
        return tpl

    def list_by_event_type(self, event_type: str) -> list[dict]:
        return [t for t in self._templates.values() if t["event_type"] == event_type]

    @property
    def total_templates(self) -> int:
        return len(self._templates)


class _SafeDict(dict):
    """dict subclass that returns '{key}' for missing keys instead of raising KeyError."""
    def __missing__(self, key: str) -> str:
        return f"{{{key}}}"
