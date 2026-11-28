# Wiki: Grounds for Rejection — When and How to Reject

**Document ID:** WIKI-REJECT-001  
**Version:** 1.0  
**Last Updated:** 2024-11-15  
**Owner:** Compliance Review Team

---

## Policy References

- POL-KYC-001 §2.3 (Document Verification), §3.4 (Rejection Criteria)
- CDD Guidelines §4.1 (Identity Establishment Failure), §8.1 (Grounds for Declining)
- AML Handbook §6.2 (SAR Referral on Rejection)
- HKMA AML Guideline §6.2 (Document Integrity)
- MAS Notice 626 §2.2 (Identification and Verification)

## Decision Pattern: Mandatory Rejection Triggers

| Trigger | Policy Basis | Action |
|---------|-------------|--------|
| Cannot verify identity | CDD §4.1, MAS 626 §2.2 | Reject + consider STR |
| Document forgery suspected | POL-KYC-001 §2.3, HKMA §6.2 | Reject + mandatory STR referral |
| Confirmed sanctions match | PRO-SAN-001 §5.2 | Reject + freeze + report to MAS |
| Customer refuses to provide information | CDD §4.1 | Reject + consider STR |
| Beneficial owner cannot be identified | MAS 626 §2.3 | Reject — must not establish relationship |
| Funds suspected to relate to ML/TF | AML §6.1 | Reject + mandatory STR |

## Case Examples

### Example 1: Document Fraud — Passport MRZ Failure
**Pattern**: Individual applicant with passport that fails MRZ checksum verification. Manual inspection reveals lamination irregularities.

**Decision**: REJECT. Per POL-KYC-001 §2.3, if identity documents show signs of tampering or forgery, the relationship must not proceed. No further CDD is required — document fraud alone is sufficient grounds. Must be referred to MLRO for SAR filing per AML §6.2.

**Key principle**: Document fraud is an absolute rejection ground. Do not attempt to "work around" it by requesting alternative documents.

### Example 2: Confirmed Sanctions Match
**Pattern**: Customer name, date of birth, and nationality match a designated person on the OFAC SDN or EU consolidated list. Secondary identifiers (passport number, address) also match.

**Decision**: REJECT immediately + freeze any existing assets + report to regulator. Per PRO-SAN-001 §5.2, a confirmed match must be escalated within 24 hours. The compliance officer must file a report with MAS/HKMA and freeze all related accounts.

**Key principle**: Sanctions matches are non-negotiable. No amount of mitigants can override a confirmed sanctions designation.

### Example 3: Inability to Establish Identity
**Pattern**: Customer provides documents but they cannot be independently verified. Photo ID quality is poor, issuing authority cannot be contacted, or document is from a jurisdiction with no verification channels.

**Decision**: REJECT per CDD §4.1 — if the bank cannot satisfactorily establish the customer's identity, the business relationship must not proceed. Consider whether the difficulty in verification itself is suspicious (STR consideration).

## Common Pitfalls

1. **Do not substitute documents**: If a passport is suspected fraudulent, do not accept a driver's license as an alternative — the fraud suspicion taints the entire application
2. **Do not delay rejection for further investigation**: Document fraud triggers immediate rejection; investigation for SAR purposes happens afterward, not instead
3. **Distinguish reject from escalate**: Rejection means the relationship will NOT proceed. Escalation means senior decision-makers will decide. If the trigger is in the mandatory rejection table above, it is a reject, not an escalation
4. **Always consider STR**: Every rejection should be evaluated for STR filing. Mandatory STR triggers: document forgery, confirmed sanctions, suspected ML/TF funds
