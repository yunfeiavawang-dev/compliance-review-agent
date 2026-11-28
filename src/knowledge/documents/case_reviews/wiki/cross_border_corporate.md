# Wiki: Cross-Border Corporate Structures

**Document ID:** WIKI-XBCORP-001
**Version:** 1.0
**Last Updated:** 2024-12-06
**Owner:** Compliance Operations
**Classification:** Internal — Compliance Staff Only

---

## Policy References

- **POL-KYC-001 §3.2** — Corporate customers require: certificate of incorporation, memorandum of association, board resolution, register of directors/shareholders, ID for authorized signatories, ID for beneficial owners (25%+), audited financials (within 12 months).
- **POL-KYC-001 §3.3** — Beneficial ownership threshold: 25% or significant control. If ownership cannot be determined, escalate to Compliance Review Committee.
- **CDD Guidelines §5.1** — Multi-jurisdiction screening: screen against sanctions lists of ALL countries where the entity operates.
- **CDD Guidelines §6.1** — Geography risk scoring: countries of incorporation, operation, and primary transaction counterparties all factor into geographic risk.
- **AML Handbook §3.1** — Customer behavior red flags include: complex ownership structures designed to obscure beneficial ownership; operations in high-risk jurisdictions without clear business rationale.
- **AML Handbook §3.4** — High-risk business types: shell companies, special purpose vehicles, nominee structures.
- **Risk Rating Matrix §2.2** — Geographic risk: Score 1 (FATF-compliant, no grey/black list); Score 2 (some high-risk indicators); Score 3 (sanctioned, grey-listed, or multiple high-risk jurisdictions).
- **RETRO-2024-W48 §3.2** — Nominee shareholders: when shareholding sits just below the 25% threshold and a nominee arrangement is indicated, request a beneficial-ownership declaration before applying the threshold.

## Decision Pattern

### Corporate Structure Assessment

| Factor | Low Concern | Medium Concern | High Concern |
|--------|------------|----------------|--------------|
| Jurisdiction | Single, FATF-compliant | 2-3 moderate-risk jurisdictions | Sanctioned / grey-listed / opacity |
| Ownership | Direct, transparent, all UBOs identified | Layered but traceable (2-3 levels) | Opaque, nominee structures, >3 levels |
| Business rationale | Clear commercial reason for structure | Structure somewhat complex for business type | No clear reason for multi-jurisdiction structure |
| Documentation | Full set including audited financials | Minor gaps (non-critical) | Missing critical documents or unverifiable |
| Transaction countries | Consistent with business operations | Some deviation from declared business | Significant unexplained geographic spread |

### Key Decision Rules

1. **Approve (standard CDD)** when:
   - All corporate documents complete per POL-KYC-001 §3.2
   - Ownership transparent with all UBOs identified
   - Transaction countries consistent with business operations
   - No adverse screening findings

2. **Approve with conditions** when:
   - Non-critical documents missing (conditional intake)
   - Multi-jurisdiction but clear business rationale
   - Conditions: enhanced transaction monitoring, periodic ownership review

3. **Request more info** when:
   - Beneficial ownership unclear or nominee structures detected
   - Audited financials older than 12 months
   - Transaction countries inconsistent with declared business

4. **Escalate** when:
   - Ownership cannot be determined to natural persons
   - Operations in comprehensively sanctioned countries (PRO-SAN-001 §6.1)
   - Shell company indicators per AML Handbook §3.4

## Case Examples

### Example 1: Singapore Tech Company — Approved (Clean)

- **Profile:** Singapore-incorporated IT consulting firm (KYC-2024-007 pattern), 2 Singaporean co-founders (60/40 split), both identified with NRIC, government contracts
- **AI Decision:** Approve — all documents complete, transparent ownership, clean screening
- **Human Decision:** Approve
- **Key Findings:**
  - All 5 required corporate documents provided and verified (certificate of incorporation, memorandum, board resolution, audited financials by KPMG, business license)
  - Both UBOs above 25% threshold, both identified with valid ID
  - Transaction countries (SG, MY, IN) consistent with regional IT consulting
  - Risk score: 6/15 (low)
- **Lesson:** Clean corporate structures with transparent ownership, complete documentation, and consistent transaction patterns should be processed efficiently through standard CDD.

### Example 2: Multi-Jurisdiction Trading Company — Approved with Conditions

- **Profile:** Corporate entity incorporated in Singapore with subsidiaries in Malaysia and Indonesia, trading in APAC markets
- **AI Decision:** Approve with conditions — multi-jurisdiction adds moderate geographic risk
- **Human Decision:** Approve with conditions: quarterly transaction country review, annual ownership verification
- **Key Findings:** Ownership traceable to two levels; all UBOs identified; business rationale for multi-jurisdiction structure clear (regional trading); audited financials provided
- **Lesson:** Multi-jurisdiction is not automatically high-risk when the business rationale is clear and ownership is transparent. Set monitoring conditions proportional to complexity.

### Example 3: Offshore Holding Company — Escalated

- **Profile:** BVI-incorporated holding company with subsidiaries in 4 jurisdictions, nominee directors, single UBO identified through 3 layers of holding entities
- **AI Decision:** Escalate — complex structure, nominee directors, opacity jurisdiction
- **Human Decision:** Escalate to compliance committee
- **Key Findings:** Nominee directors per AML Handbook §3.4; BVI is an opacity-risk jurisdiction; 3-layer ownership makes ongoing monitoring difficult; no clear business rationale for the structure complexity
- **Lesson:** When the structure complexity exceeds what the business requires, treat the complexity itself as a red flag. Per RETRO-2024-W48 §3.2, do not rely solely on the 25% threshold — look for nominee arrangements at any level.

## Common Pitfalls

- :x: Applying individual-customer CDD logic to corporate structures (corporate requires additional documents and ownership analysis)
- :x: Only screening the entity itself without screening authorized signatories and UBOs
- :x: Accepting the 25% threshold mechanically when nominee indicators are present
- :x: Treating multi-jurisdiction operations as automatically high-risk without assessing business rationale
- :white_check_mark: Screening all entities in the ownership chain, plus signatories and UBOs individually
- :white_check_mark: Verifying that transaction countries align with the declared business operations
- :white_check_mark: Setting monitoring conditions proportional to the structure's complexity
