# Wiki: False Positive Resolution — Sanctions and PEP Screening

**Document ID:** WIKI-FALSEPOS-001  
**Version:** 1.0  
**Last Updated:** 2024-11-15  
**Owner:** Compliance Review Team

---

## Policy References

- PRO-SAN-001 §3.1 (Match Categorization), §3.3 (Resolution Procedures), §5.1 (Potential Match Handling)
- CDD Guidelines §5.1 (Screening Process), §5.2 (Match Investigation)
- MAS Notice 626 §7.2 (Match Handling)
- HKMA AML Guideline §4.2 (PEP Identification)

## Decision Pattern: False Positive Determination

A screening hit is a **false positive** when the flagged individual is demonstrably NOT the same person as the listed/designated individual. Resolution must be evidence-based, not assumption-based.

| Confidence Level | Match Score | Required Evidence to Dismiss | Approver |
|-----------------|-------------|-----------------------------|---------| 
| Exact match (95-100%) | Name + DOB + nationality | Multiple secondary identifiers must DIFFER (passport number, photo, address). Cannot dismiss on name alone | Compliance Officer |
| Strong match (80-94%) | Name + partial DOB or nationality | At least 2 differentiating factors (different passport number, different middle name, different photo, different city of birth) | Senior Analyst |
| Partial match (70-79%) | Name only or name + nationality | One clear differentiating factor sufficient (different DOB, different nationality, different gender) | Analyst |
| Weak match (<70%) | Partial name | Auto-dismiss with documented rationale | System / Analyst |

## Secondary Identifiers for Resolution

When resolving a potential match, compare these secondary identifiers:
1. **Date of birth** — exact match vs. partial (same year vs. different year)
2. **Passport/ID number** — the strongest differentiator; a different passport number from the listed person is strong evidence of false positive
3. **Place of birth** — city-level comparison
4. **Physical description/photo** — if available on the list entry
5. **Known associates** — do the customer's declared associates overlap with the listed person's known network?
6. **Address history** — has the customer ever resided at addresses associated with the listed person?
7. **Occupation/employer** — consistency with the listed person's known activities

## Case Examples

### Example 1: Common Name — Different Person
**Scenario**: Customer "Ahmed Ali Hassan" (Egyptian, DOB 1990-03-15) triggers a 76% match against "Ahmed Hassan Ali" (Sudanese, DOB 1975-08-22) on the UN sanctions list.

**Resolution**: FALSE POSITIVE. Different name ordering, different nationality, different DOB (15-year gap), different country of birth. Document: "Match dismissed — different individual. Name ordering reversed, nationality differs (Egyptian vs. Sudanese), DOB differs by 15 years. No overlapping secondary identifiers."

**Approver**: Analyst (partial match, clear differentiation).

### Example 2: Same Name and Nationality — Different DOB
**Scenario**: Customer "Mikhail Petrov" (Russian, DOB 1972-07-14) triggers an 82% match against "Mikhail Vladimirovich Petrov" (Russian, DOB 1972-03-22) on the EU sanctions list.

**Resolution**: CANNOT DISMISS as false positive. Same nationality, same birth year, patronymic not provided by customer. Must escalate — per PRO-SAN-001 §5.1, when the match cannot be dismissed within 48 hours using available secondary identifiers, treat as a potential true match and escalate to Compliance Committee. Request additional information from customer: patronymic, place of birth, passport number for comparison.

**Key principle**: A common name in the same nationality with a close DOB is NOT sufficient to dismiss. The burden of proof is on the bank to demonstrate it is a different person.

### Example 3: PEP Match — Former Official, Confirmed Different Person
**Scenario**: Customer "Park Min-jun" (South Korean, businessman) triggers a PEP match against "Park Min-jun" (South Korean, former Vice Minister of Finance, 2008-2014).

**Resolution**: Customer provides passport number, place of birth (Busan), and company registration documents. PEP database entry shows the former Vice Minister was born in Seoul and holds a different passport number. FALSE POSITIVE for the PEP match. Document the resolution with specific identifier comparisons.

**Note**: Even after dismissing the PEP match, the customer's overall risk profile must still be assessed normally. A dismissed PEP match does not automatically mean low risk.

## Common Pitfalls

1. **Never dismiss on name spelling alone**: "Mohammed" vs. "Muhammad" is not a differentiating factor — these are transliteration variants
2. **Year-of-birth match is high risk**: If the year of birth matches, the bar for dismissal is higher even if the exact date differs — could be a data entry error on the list
3. **Document every dismissal**: The resolution rationale must be recorded in the audit trail with specific identifier comparisons
4. **Partial matches still need investigation**: A 72% match cannot be auto-dismissed if the customer shares nationality and approximate age with the listed person
5. **Customer self-declaration is not evidence**: The customer saying "that's not me" is not sufficient to dismiss a match — independent verification is required
