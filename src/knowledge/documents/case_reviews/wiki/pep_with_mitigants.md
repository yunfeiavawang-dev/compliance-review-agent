# Wiki: PEP with Mitigating Factors

**Document ID:** WIKI-PEP-001
**Version:** 1.0
**Last Updated:** 2024-12-06
**Owner:** Compliance Operations
**Classification:** Internal — Compliance Staff Only

---

## Policy References

- **CDD Guidelines §6.1** — Scoring methodology: PEP status automatically sets customer_type risk factor to 3 (high).
- **CDD Guidelines §6.2** — Override rules: PEP status triggers automatic risk rating override to HIGH regardless of other factor scores.
- **CDD Guidelines §7.1** — EDD required for all high-risk customers: source of wealth documentation and source of funds evidence. Self-declaration alone is insufficient.
- **CDD Guidelines §7.3** — Senior management approval required for PEP accounts before onboarding.
- **Risk Rating Matrix §3.2** — Automatic overrides: confirmed PEP → HIGH risk rating, regardless of composite score.
- **Risk Rating Matrix §3.3** — Analyst override: risk rating can only be upgraded (never downgraded) by analysts. Downgrade requires compliance officer approval.
- **PRO-SAN-001 §5.3** — PEP identification: domestic PEPs require EDD; foreign PEPs require EDD + senior management approval.

## Decision Pattern

### PEP Classification and Cooling-Off Assessment

| Factor | Favor Approval w/ Conditions | Favor Escalation |
|--------|------------------------------|-------------------|
| Time since leaving office | 3+ years (past cooling-off) | < 3 years or still in office |
| Sanctions screening | Clear on all lists | Any potential or confirmed match |
| Adverse media | Clear — no corruption/fraud allegations | Findings related to corruption, fraud, or financial crime |
| Source of wealth | Documented with audited financials or verifiable business records | Self-declaration only, or unverifiable |
| Business-politics nexus | Business predates political career | Business started during or after political tenure |
| Transparency | PEP status self-declared | PEP status discovered during screening (not declared) |

### Decision Rules for Retired PEPs

1. **Approve with conditions** when ALL of:
   - Left office 3+ years ago
   - Sanctions screening clear
   - Adverse media clear
   - Source of wealth supported by independent evidence (audited financials, company records)
   - Conditions: enhanced monitoring, annual PEP status review, transaction thresholds

2. **Escalate** when ANY of:
   - Sanctions match (potential or confirmed)
   - Adverse media findings related to financial crime
   - Source of wealth cannot be independently verified
   - Business activities appear connected to political role

## Case Examples

### Example 1: Retired Deputy Minister — Approved with Conditions

- **Profile:** Malaysian former Deputy Minister of Trade (KYC-2024-005 pattern), retired 6+ years, chairman of family conglomerate (est. 1992, predates political career by 18 years)
- **AI Decision:** Approve with conditions — strong mitigants identified
- **Human Decision:** Approve with conditions: enhanced monitoring, annual PEP review, SoF verification for transactions > MYR 500,000
- **Key Findings:**
  - PEP status self-declared — demonstrates transparency
  - Sanctions clear on all lists; adverse media clear
  - Source of wealth documented: audited financials (Ibrahim Holdings), company annual report, property title deeds
  - Family business established 1992, political career started 2010 — business predates politics by 18 years
  - Risk score: 12/15 (high) — driven entirely by PEP status
- **Lesson:** A retired PEP with clean screening, documented wealth from a pre-existing family business, and transparent self-declaration meets the threshold for conditional approval. Escalation would be overly conservative and wastes compliance committee bandwidth.

### Example 2: Recently Retired Official — Escalated

- **Profile:** Former government advisor, left office 18 months ago, source of wealth is self-declaration only
- **AI Decision:** Escalate — within cooling-off period and unverified wealth
- **Human Decision:** Agreed — escalated to compliance committee
- **Key Findings:** Cooling-off period not elapsed; no independent wealth verification available
- **Lesson:** The cooling-off period and wealth documentation requirements are conjunctive — both must be met for conditional approval.

### Example 3: PEP Not Declared — Discovered During Screening

- **Profile:** Customer did not declare PEP status; screening revealed former advisory role in regional government
- **AI Decision:** Escalate — undisclosed PEP status is a transparency red flag
- **Human Decision:** Escalate — non-disclosure adds concern regardless of other mitigants
- **Lesson:** Failure to declare PEP status is an independent risk factor. Even if all other mitigants are strong, the non-disclosure raises questions about the customer's transparency and must be addressed before any approval.

## Common Pitfalls

- :x: Automatically escalating every PEP regardless of mitigants (wastes committee capacity; delays legitimate customers)
- :x: Approving a PEP based solely on clean screening without verifying source of wealth
- :x: Accepting self-declaration as sufficient source of wealth documentation for a PEP
- :x: Ignoring the business-politics timeline (did business start before or during political career?)
- :white_check_mark: Checking all six mitigant factors before deciding between conditional approval and escalation
- :white_check_mark: Setting specific, measurable conditions (transaction thresholds, review frequency)
- :white_check_mark: Requiring senior management sign-off per CDD Guidelines §7.3
