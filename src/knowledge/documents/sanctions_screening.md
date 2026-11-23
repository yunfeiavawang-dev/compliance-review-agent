# Sanctions and Watchlist Screening Procedures

**Document ID:** PRO-SAN-001  
**Version:** 2.1  
**Effective Date:** 2024-04-01  
**Last Reviewed:** 2024-08-10  
**Owner:** Sanctions Compliance Team Lead  
**Classification:** Internal – Compliance Staff Only

---

## 1. Purpose

This document provides detailed procedures for conducting sanctions and watchlist screening during customer onboarding and ongoing monitoring at Pacific Rim Financial Group (PRFG).

## 2. Screening Databases

### 2.1 Mandatory Lists

| List | Publisher | Update Frequency | Priority |
|------|-----------|-----------------|----------|
| UN Security Council Consolidated List | United Nations | Real-time | Critical |
| OFAC SDN List | US Treasury | Weekly + ad-hoc | Critical |
| OFAC Consolidated Non-SDN List | US Treasury | Weekly | High |
| EU Consolidated Financial Sanctions | European Union | Daily | High |
| Local Regulatory Authority List | Monetary Authority | Monthly | High |
| PRFG Internal Watchlist | PRFG Compliance | Real-time | High |

### 2.2 Supplementary Databases

| Database | Purpose | Coverage |
|----------|---------|----------|
| World-Check (Refinitiv) | PEP and adverse media | Global |
| Dow Jones Risk & Compliance | Sanctions, PEP, adverse media | Global |
| Local Credit Bureau | Financial history | Domestic |
| Company Registry | Corporate verification | Domestic and regional |

## 3. Screening Methodology

### 3.1 Name Matching

The screening system uses a multi-algorithm approach:
- **Exact match:** Direct string comparison
- **Fuzzy match:** Levenshtein distance with minimum 85% similarity threshold
- **Phonetic match:** Soundex and Metaphone algorithms for name variations
- **Transliteration match:** Cross-script name matching (e.g., Chinese characters to Pinyin, Arabic to Latin)

### 3.2 Data Points for Screening

For each customer or related party, screen the following:
- Full legal name (all parts)
- Known aliases and former names
- Date of birth
- Nationality / country of citizenship
- Country of residence
- National identification number (where available)
- For entities: registration number, country of incorporation

### 3.3 Match Scoring

| Score Range | Classification | Action |
|-------------|---------------|--------|
| 95-100% | Strong Match | Immediate escalation, block transaction |
| 80-94% | Potential Match | Manual review within 4 hours |
| 60-79% | Weak Match | Review within 24 hours, likely dismiss |
| Below 60% | No Match | Auto-clear, log result |

## 4. Screening Workflow

### 4.1 Initial Screening (Onboarding)

1. Submit customer data to screening system
2. System returns matches with confidence scores
3. For each match above 60%:
   a. Compare all available data points between the customer and the listed entity
   b. Check for distinguishing information (date of birth, nationality, address)
   c. If match can be clearly dismissed → Document reason and proceed
   d. If match cannot be dismissed → Escalate per Section 5

### 4.2 Ongoing Screening

- **Daily batch screening:** All active customers re-screened when list updates arrive
- **Event-triggered screening:** When customer data is updated
- **Transaction screening:** Real-time for wire transfers above threshold

### 4.3 Negative News / Adverse Media Screening

Conduct adverse media checks for:
- All High Risk customers
- All PEPs and their associates
- All corporate customers with complex ownership structures

Search terms should include: customer name, known aliases, company name, plus keywords such as: fraud, money laundering, corruption, bribery, sanctions evasion, tax evasion, terrorist financing, criminal, indictment, prosecution, regulatory action.

## 5. Escalation Procedures

### 5.1 Confirmed or Strong Match (95-100%)

| Step | Action | Timeline | Responsible |
|------|--------|----------|-------------|
| 1 | Block the application/transaction | Immediately | Screening analyst |
| 2 | Notify Compliance Officer | Within 1 hour | Screening analyst |
| 3 | Compile full match report | Within 4 hours | Screening analyst |
| 4 | Compliance Officer reviews and confirms | Within 8 hours | Compliance Officer |
| 5 | File regulatory report if confirmed | Within 24 hours | MLRO |
| 6 | Notify senior management | Within 24 hours | Compliance Officer |

### 5.2 Potential Match (80-94%)

1. Gather additional identifying information from the customer or public sources
2. Compare at least 3 independent data points beyond name
3. Document analysis in the case file
4. If dismissed: record specific distinguishing factors used
5. If unable to dismiss within 48 hours: treat as confirmed and follow 5.1

### 5.3 PEP Identification

When a customer is identified as a PEP:
1. This does NOT automatically mean the customer should be rejected
2. Automatically classify as High Risk
3. Apply Enhanced Due Diligence procedures
4. Obtain Senior Management approval
5. Implement enhanced ongoing monitoring
6. Review at least annually

**PEP Categories:**
- Heads of state, government ministers, senior politicians
- Senior military officials
- Senior judicial officials
- Senior executives of state-owned enterprises
- Senior officials of international organizations
- Family members and close associates of the above

## 6. Sanctions List Countries and Jurisdictions

### 6.1 Comprehensively Sanctioned Countries (as of latest update)

Transactions involving these jurisdictions require MLRO approval regardless of amount:
- North Korea (DPRK)
- Iran
- Syria
- Cuba
- Crimea, Donetsk, Luhansk regions

### 6.2 High-Risk Jurisdictions (FATF Grey List)

Enhanced due diligence required for all customers with connections to these jurisdictions. The list is updated regularly — refer to the latest FATF publication.

### 6.3 Jurisdiction Risk Assessment

PRFG maintains an internal jurisdiction risk rating that considers:
- FATF assessment ratings
- Transparency International Corruption Perception Index
- Basel AML Index
- Bilateral sanctions and trade restrictions
- Correspondent banking relationships in the jurisdiction

## 7. Record Keeping

For each screening event, retain:
- Date and time of screening
- Screening system used and version
- Lists screened against
- Full results including all matches above 60%
- Analysis and disposition of each match
- Identity of the analyst who performed the review
- Approval chain for escalated matches

Records retention: minimum 7 years from the date of screening.

## 8. Quality Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Screening completion rate | 100% of onboarding | Monthly audit |
| Mean time to resolve potential matches | < 24 hours | Weekly report |
| False positive rate | < 5% of all alerts | Monthly analysis |
| Escalation timeliness | 100% within SLA | Weekly report |
| Documentation completeness | 100% of dispositions documented | Quarterly QA |
