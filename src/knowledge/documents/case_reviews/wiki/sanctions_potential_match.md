# Wiki: Sanctions Fuzzy Match

**Document ID:** WIKI-SANC-001
**Version:** 1.0
**Last Updated:** 2024-12-06
**Owner:** Compliance Operations
**Classification:** Internal — Compliance Staff Only

---

## Policy References

- **PRO-SAN-001 §3.1** — Name matching uses fuzzy algorithms; a match score alone does not confirm identity.
- **PRO-SAN-001 §3.3** — Match scoring: 95-100% = strong match, 80-94% = potential match, <80% = weak match.
- **PRO-SAN-001 §5.1** — Confirmed or strong match (95%+): freeze account activity, escalate to MLRO within 24 hours.
- **PRO-SAN-001 §5.2** — Potential match (80-94%): enhanced verification required using secondary identifiers (DOB, nationality, address). Must resolve within 48 hours or treat as confirmed.
- **CDD Guidelines §5.1** — Screening must cross-reference at least two independent data points beyond the name.
- **CDD Guidelines §5.2** — When match score is 80-94%, compare DOB, nationality, passport number, and known aliases before clearing.
- **AML Handbook §6.1** — Prohibited activities include processing transactions for sanctioned individuals; penalties include criminal liability.
- **RETRO-2024-W48 §3.3** — Name transliteration variants cause false positives. A name-only fuzzy match must NOT be cleared without a second identifying attribute, and the attribute used must be recorded.

## Decision Pattern

### Match Score Triage

| Score Range | Classification | Required Action | Timeline |
|------------|---------------|-----------------|----------|
| 95-100% | Strong match | Freeze activity; escalate to MLRO | Immediate (24h) |
| 80-94% | Potential match | Enhanced verification with secondary identifiers | 48 hours to resolve |
| 70-79% | Weak match | Document comparison; clear if secondary attributes diverge | 5 business days |
| <70% | Noise | Log and dismiss with reason | Same day |

### Secondary Identifier Comparison Protocol

When resolving a potential match, compare ALL available secondary identifiers:

1. **Date of birth** — Exact match required. Same year but different day/month → inconclusive (do not clear on DOB alone)
2. **Nationality** — Same nationality is necessary but not sufficient for confirmation
3. **Aliases / transliterations** — Check all known aliases; Cyrillic-Latin transliteration creates common false positives (e.g., Petrov/Pietrov, Mikhail/Michail/Mikail)
4. **Address / country of residence** — Different country of residence is a strong differentiator
5. **Occupation / role** — Compare against the designated reason on the sanctions list

A match is dismissed when **at least two** secondary identifiers clearly diverge from the listed individual. Record which identifiers were compared and the conclusion.

## Case Examples

### Example 1: Russian National — Potential Match (82%), Escalated

- **Profile:** Russian business owner (KYC-2024-003 pattern), name matched EU sanctions list at 82% confidence. Same DOB year (1972), same nationality (Russian).
- **AI Decision:** Escalate to compliance committee — multiple compounding risk factors
- **Human Decision:** Escalate — could not dismiss match within 48 hours
- **Key Findings:**
  - Listed individual: DOB 1972-03-22; customer DOB: 1972-07-14 — same year, different month
  - Both Russian nationals — nationality match is inconclusive
  - Customer in petrochemical business; listed individual designated for energy sector association
  - Adverse media regarding Dubai property investigation added further concern
- **Lesson:** When DOB year matches and the customer's business sector aligns with the sanctioned individual's designation reason, the match cannot be dismissed on DOB divergence alone. Escalation was correct.

### Example 2: Transliteration False Positive — Cleared

- **Profile:** Individual with common name returning transliteration variant match at 85%
- **AI Decision:** Request enhanced verification
- **Human Decision:** Clear — DOB (10 years apart) and nationality (different countries) both diverged
- **Key Findings:** Per RETRO-2024-W48 §3.3, the match was caused by Cyrillic-Latin transliteration of a common surname
- **Lesson:** When both DOB and nationality clearly diverge, the match can be dismissed. Record the two divergent identifiers in the review notes.

### Example 3: Common Name Match — Cleared After Verification

- **Profile:** East Asian individual with common name matching a PEP database entry at 78%
- **AI Decision:** Flag for verification
- **Human Decision:** Clear — different date of birth (15 years apart), different country of residence
- **Lesson:** Common names in certain regions produce high volumes of weak matches. The 70-79% range should be cleared efficiently but always with documented secondary-identifier comparison.

## Common Pitfalls

- :x: Clearing a potential match based on name spelling differences alone (transliterations can produce multiple valid spellings)
- :x: Treating same DOB year with different day/month as sufficient to dismiss
- :x: Failing to record which secondary identifiers were used to clear a match
- :x: Exceeding the 48-hour resolution window without escalation
- :white_check_mark: Comparing at least two secondary identifiers and documenting the comparison
- :white_check_mark: Escalating when the customer's business sector matches the sanctions designation reason
- :white_check_mark: Logging the full transliteration analysis when common-name matches occur
