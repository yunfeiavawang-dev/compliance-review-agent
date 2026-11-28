# Wiki: Unusual Transaction Patterns and ML/TF Typologies

**Document ID:** WIKI-TXNPAT-001  
**Version:** 1.0  
**Last Updated:** 2024-11-15  
**Owner:** Compliance Review Team

---

## Policy References

- AML Handbook §3.1 (ML Typologies), §3.4 (Trade-Based ML), §4.1 (Transaction Monitoring)
- CDD Guidelines §7.2 (Ongoing Monitoring Triggers)
- MAS Notice 626 §4.1 (Transaction Monitoring)
- HKMA AML Guideline §7.1 (Transaction Monitoring)
- REG-FATF-RBA §4 (Trade-Based Money Laundering)

## Decision Pattern: Risk Assessment for Transaction Profiles

When assessing a customer's expected transaction profile at onboarding, the following patterns should raise the risk score:

| Pattern | Risk Indicator | Score Impact |
|---------|---------------|-------------|
| Expected deposits ≈ expected withdrawals (>90% ratio) | Pass-through / layering | +1 to transaction risk |
| Expected volume inconsistent with business size/age | Structuring risk | +1 to transaction risk |
| Multiple high-risk jurisdictions in transaction countries | Geographic layering | +1 per FATF grey/black list country |
| Cash-intensive initial deposit | No banking trail | +1 to source of funds risk |
| Sudden increase from prior relationship pattern | Behavior change | Trigger periodic review |

## Typology 1: Layering Through Multiple Accounts

**Pattern**: Customer opens accounts in multiple jurisdictions, moves funds rapidly between them (often within 24-48 hours), with each transfer slightly below reporting thresholds. The economic rationale for the transfers is unclear.

**Red flags at onboarding**:
- Multiple accounts requested across jurisdictions simultaneously
- Expected transaction patterns showing high volume relative to stated income
- Declared purpose vague ("investment" or "business transfers")
- Expected withdrawals nearly equal to deposits (pass-through)

**Assessment approach**: Compare expected transaction volume against declared income and business type. If monthly deposits exceed 3x monthly declared income without documented business rationale, flag for enhanced monitoring or escalation.

## Typology 2: Trade-Based Money Laundering (TBML)

**Pattern**: Customer uses trade transactions to move value across borders. Goods may be over-invoiced, under-invoiced, multiply invoiced, or fictitious. Common in import/export businesses, particularly in consumer electronics, textiles, and commodities.

**Red flags at onboarding**:
- Newly established trading company with disproportionate expected volume
- Trade corridors through free trade zones (Jebel Ali, RAK, Labuan)
- Transaction countries include FATF-listed jurisdictions
- Goods are easily mis-valued (electronics, precious metals, luxury goods)
- No audited financials despite claimed high revenue

**Assessment approach**: For trading companies less than 2 years old, verify trade license, request sample invoices and shipping documentation, compare expected volume against industry benchmarks. If the company has no audited financials and expects monthly transactions exceeding $200K, apply EDD regardless of other risk factors.

## Typology 3: Structuring (Smurfing)

**Pattern**: Customer or related parties make multiple deposits or transfers just below reporting thresholds to avoid triggering currency transaction reports.

**Red flags at onboarding**:
- Multiple accounts requested for "different purposes" with similar expected volumes
- Expected deposits cluster around reporting thresholds ($10,000 USD or local equivalent)
- Customer asks about reporting thresholds during onboarding
- Related parties applying simultaneously with similar profiles

**Assessment approach**: Structuring suspicion at onboarding is rare but can be indicated by the transaction profile. If expected deposits show a suspicious pattern, note for transaction monitoring setup.

## Typology 4: Shell Company Layering

**Pattern**: Customer is a legal entity with minimal operational substance, used primarily to hold or move funds. The beneficial ownership is obscured through nominee directors, bearer shares, or multi-layered holding structures.

**Red flags at onboarding**:
- Company has no employees, no physical office, or minimal web presence
- Registered in a jurisdiction known for opaque corporate structures (BVI, Cayman, Seychelles, Panama)
- Nominee directors or corporate directors
- Beneficial ownership chain passes through 3+ entities
- Declared business activity is vague ("consulting", "investments", "holding")
- No audited financials despite several years of operation

**Assessment approach**: For companies with any 3 of the above indicators, apply EDD and require a face-to-face meeting with the beneficial owner. If beneficial ownership cannot be traced to a natural person, decline the relationship per MAS 626 §2.3.

## Decision Guidance for Onboarding

When evaluating a customer's declared transaction profile:

1. **Compare volume to profile**: Monthly deposits should be consistent with declared annual income / business revenue. Ratio > 3x without documented rationale = flag
2. **Assess geographic risk**: Each FATF grey-list country in the transaction set adds risk. Black-list countries trigger automatic EDD
3. **Check for pass-through indicators**: If expected withdrawals are >80% of expected deposits, investigate the economic rationale
4. **Evaluate business age**: Companies < 2 years old with expected monthly transactions > $100K require additional business verification
5. **Consider product risk**: Private banking, trade finance, and correspondent banking are inherently higher risk than standard retail products

## Common Pitfalls

1. **Do not reject on transaction profile alone**: High transaction volumes are not inherently suspicious — they may be consistent with the customer's business. The question is whether the profile is consistent with verified information
2. **Do not apply rigid thresholds**: ML risk is assessed holistically, not by any single metric
3. **Document your assessment reasoning**: Whether you flag or clear a transaction pattern, record why — the rationale matters for regulatory examination
