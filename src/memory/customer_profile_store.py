"""Customer behavior profile store — read + write bank profile data.

In production this would query the bank's CRM / core banking system.
For the demo it reads/writes mock JSON profiles keyed by case_id.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional


class CustomerProfileStore:
    """Store for customer long-term behavior profiles.

    Demo: loads from and writes to JSON files in ``profiles_dir``.
    Production: would call bank CRM / core-system API, or query
    Volcengine PostgreSQL / Redis.
    """

    def __init__(self, profiles_dir: str = "data/customer_profiles"):
        self.profiles_dir = Path(profiles_dir)
        self._cache: dict[str, Optional[dict]] = {}

    def get_profile(self, case_id: str) -> Optional[dict]:
        """Fetch the customer's bank-wide behavior profile.

        Returns ``None`` for new customers with no prior bank relationship.
        """
        if case_id in self._cache:
            return self._cache[case_id]

        profile_path = self.profiles_dir / f"{case_id}_profile.json"
        if profile_path.exists():
            with open(profile_path) as f:
                profile = json.load(f)
            self._cache[case_id] = profile
            return profile

        self._cache[case_id] = None
        return None

    def write_case_summary(
        self,
        case_id: str,
        customer_id: str,
        summary: dict[str, Any],
    ) -> None:
        """Append a case review summary to the customer's profile.

        If no profile exists yet (new customer), creates a minimal one.
        The ``review_history`` list accumulates summaries across reviews,
        giving future reviews context on how this customer has been
        assessed before.
        """
        profile = self.get_profile(case_id)
        if profile is None:
            profile = {
                "customer_id": customer_id,
                "review_history": [],
            }

        if "review_history" not in profile:
            profile["review_history"] = []
        profile["review_history"].append(summary)

        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        profile_path = self.profiles_dir / f"{case_id}_profile.json"
        with open(profile_path, "w") as f:
            json.dump(profile, f, indent=2, default=str)

        self._cache[case_id] = profile

    def format_for_prompt(self, profile: Optional[dict]) -> str:
        """Format the profile into LLM-readable context text."""
        if profile is None:
            return (
                "【Customer Profile】No prior bank relationship found — this is a NEW customer. "
                "All assessments must rely entirely on the current submission materials."
            )

        ts = profile.get("transaction_summary", {})
        ch = profile.get("compliance_history", {})

        lines = [
            "【Customer Profile — Bank Internal Behavioral Data】",
            f"Relationship tenure: {profile.get('relationship_tenure_years', 'N/A')} years "
            f"(since {profile.get('relationship_start', 'N/A')})",
            f"Customer segment: {profile.get('customer_segment', 'N/A')}",
            f"Products held: {', '.join(profile.get('products_held', []))}",
            "",
            "Transaction behavior (last 12 months):",
            f"  Avg monthly inflow: ${ts.get('avg_monthly_inflow', 0):,.0f}",
            f"  Avg monthly outflow: ${ts.get('avg_monthly_outflow', 0):,.0f}",
            f"  Max single transaction: ${ts.get('max_single_transaction', 0):,.0f}",
            f"  Cross-border tx ratio: {ts.get('cross_border_tx_pct', 0):.0%}",
            f"  Primary counterparty countries: {', '.join(ts.get('primary_counterparty_countries', []))}",
            f"  Cash deposit frequency: {ts.get('cash_deposit_frequency', 'N/A')}",
            f"  Transaction monitoring alerts (12m): {ts.get('unusual_pattern_flags', 0)}",
        ]

        events = profile.get("risk_events", [])
        if events:
            lines.append(f"\nHistorical risk events ({len(events)}):")
            for e in events:
                lines.append(
                    f"  [{e.get('date', '?')}] {e.get('event_type', '?')}: "
                    f"{e.get('description', '')} → {e.get('outcome', '?')}"
                )
        else:
            lines.append("\nHistorical risk events: None")

        lines.extend([
            "",
            "Compliance history:",
            f"  Previous KYC reviews: {ch.get('previous_kyc_reviews', 0)}",
            f"  Last KYC: {ch.get('last_kyc_date', 'N/A')} → {ch.get('last_kyc_outcome', 'N/A')}",
            f"  Risk rating trajectory: {' → '.join(ch.get('risk_rating_trajectory', []))}",
            f"  SAR filed: {'Yes' if ch.get('sar_filed') else 'No'}",
            f"  Regulatory inquiries: {ch.get('regulatory_inquiries', 0)}",
        ])

        ext = profile.get("external_data", {})
        if ext:
            lines.extend([
                "",
                "Third-party data:",
                f"  Credit score: {ext.get('credit_score', 'N/A')}",
                f"  Other bank loans: {ext.get('other_bank_loans', 0)}",
                f"  Bankruptcy records: {'Yes' if ext.get('bankruptcy_records') else 'No'}",
                f"  Litigation records: {ext.get('litigation_records', 0)}",
            ])

        svc = profile.get("service_summary", {})
        if svc:
            lines.extend([
                "",
                "Service history:",
                f"  Total interactions: {svc.get('total_interactions', 0)}",
                f"  Complaints: {svc.get('complaints', 0)}",
                f"  Account freezes: {svc.get('account_freezes', 0)}",
            ])

        tags = profile.get("internal_tags", [])
        if tags:
            lines.append(f"\nInternal tags: {', '.join(tags)}")

        return "\n".join(lines)
