# Wiki: Expired / Near-Expiry Documents

**Document ID:** WIKI-EXPDOC-001
**Version:** 1.0
**Last Updated:** 2024-12-06
**Owner:** Compliance Operations
**Classification:** Internal — Compliance Staff Only

---

## Policy References

- **POL-KYC-001 §3.1** — Individual customers must provide a valid Category A photo ID (passport, national ID, or driver's license). "Valid" means not expired at the date of submission.
- **POL-KYC-001 §3.1** — Category B proof of address must be dated within 3 months of submission.
- **CDD Guidelines §3.3** — Incomplete submissions: a missing critical document blocks the review; a missing non-critical document allows conditional processing with risk score +1.
- **RETRO-2024-W48 §3.1** — An expired proof of address is a documentation failure, not a risk-rating trade-off. Do not offset against a low risk score.

## Decision Pattern

### Document Validity Assessment

| Scenario | Classification | Action |
|----------|---------------|--------|
| Category A ID expired at submission | Critical missing | Block intake; request renewed document |
| Category A ID valid but expires within 30 days | Doc issue (non-critical) | Conditional approval; note to request renewal |
| Category A ID valid but expires within 90 days | Doc issue (flag only) | Proceed normally; flag for follow-up at renewal |
| Category B proof of address > 3 months old | Critical missing (per POL-KYC-001 §3.1) | Block; request fresh document |
| Category C tax document missing | Non-critical | Conditional processing; risk +1 |

### Key Rule

An approaching-expiry document that is still valid at submission date is NOT a critical deficiency. The intake node should flag it as a `doc_issue` and append a monitoring condition, but must not classify it as `critical_missing`.

## Case Examples

### Example 1: Near-Expiry Passport — Approved Conditionally

- **Profile:** Singaporean financial analyst (KYC-2024-006 pattern), passport expiring in ~7 weeks
- **AI Decision:** Approve (standard CDD) — passport valid at submission, flagged as doc_issue
- **Human Decision:** Approve with condition: "Request updated passport upon renewal before 2024-11-19"
- **Key Finding:** Missing Category C (tax document) triggered conditional intake with risk +1, but overall risk remained low (score 6/15)
- **Lesson:** Near-expiry is a monitoring item, not a blocking deficiency. The condition ensures the file stays compliant post-approval.

### Example 2: Expired Proof of Address — Blocked

- **Profile:** Individual customer submitted utility bill dated 4 months prior to application
- **AI Decision:** Request more info — flagged utility bill as expired per 3-month rule
- **Human Decision:** Agreed — returned to customer for fresh utility bill
- **Key Finding:** Two analysts initially wanted to approve with a "minor gap" note; compliance officer intervened
- **Lesson:** Per RETRO-2024-W48 §3.1, an expired proof of address is a documentation failure that must be remedied, not traded off against a low risk score.

### Example 3: Corporate Documents Near Expiry

- **Profile:** Corporate customer with audited financial statements 11 months old at submission (12-month limit per POL-KYC-001 §3.2)
- **AI Decision:** Approve — financials within the 12-month window
- **Human Decision:** Approve with note: "Flag for updated financials at next annual review"
- **Lesson:** Documents within policy limits but approaching expiry should trigger a proactive follow-up condition.

## Common Pitfalls

- :x: Treating a near-expiry (but valid) passport as a critical deficiency and blocking the case
- :x: Accepting an expired proof of address because the customer is low-risk
- :x: Failing to add a monitoring condition for documents expiring within 90 days
- :white_check_mark: Flagging near-expiry as a `doc_issue`, proceeding with conditional approval, and setting a renewal reminder
- :white_check_mark: Blocking intake only when the document is actually expired at submission date
