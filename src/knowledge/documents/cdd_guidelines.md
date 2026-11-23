# Customer Due Diligence (CDD) Guidelines

**Document ID:** GDL-CDD-001  
**Version:** 1.8  
**Effective Date:** 2024-02-01  
**Last Reviewed:** 2024-05-30  
**Owner:** Head of KYC Operations  
**Classification:** Internal – Compliance Staff Only

---

## 1. Purpose

These guidelines provide step-by-step procedures for conducting Customer Due Diligence during the onboarding process at Pacific Rim Financial Group (PRFG). They supplement the KYC Policy (POL-KYC-001) with operational detail.

## 2. CDD Workflow Overview

```
Submission Received
    → Document Completeness Check
    → Identity Verification
    → Sanctions/PEP Screening
    → Risk Assessment
    → [Low/Medium Risk] → Standard Review → Decision
    → [High Risk] → Enhanced Due Diligence → Senior Approval → Decision
    → Decision: Approve / Reject / Request More Information
```

## 3. Step 1: Document Completeness Check

### 3.1 Individual Applications

Verify the submission contains:
- [ ] Completed application form with all mandatory fields
- [ ] At least two ID documents from different categories (see KYC Policy Section 3.1)
- [ ] All documents are legible copies or certified originals
- [ ] Documents are not expired (IDs must have >3 months validity remaining)
- [ ] Address proof is dated within the required timeframe
- [ ] Signed customer declaration and consent form

### 3.2 Corporate Applications

Verify the submission contains:
- [ ] All items from the individual checklist for each authorized signatory
- [ ] Certificate of incorporation/registration
- [ ] Memorandum and articles of association (or equivalent)
- [ ] Board resolution for account opening
- [ ] Beneficial ownership declaration
- [ ] Latest audited financial statements
- [ ] Business license (if applicable)

### 3.3 Handling Incomplete Submissions

If documentation is incomplete:
1. Send a standardized "Information Request" notification to the submitter specifying exactly which documents are missing
2. Set a 10-business-day deadline for response
3. If no response after first follow-up (day 5), send a reminder
4. If still incomplete after 10 business days, the application is marked as "Expired - Incomplete" and must be resubmitted
5. Document all communication in the case file

## 4. Step 2: Identity Verification

### 4.1 Document Authentication

For each identification document, verify:
- Document appears genuine (no signs of alteration or forgery)
- Photo matches the applicant (for in-person or video verification)
- Document number format matches the issuing country's standard
- Expiry date is valid (minimum 3 months remaining)
- Issuing authority is recognized

### 4.2 Cross-Reference Checks

- Name and date of birth are consistent across all submitted documents
- Address matches between proof of address and application form
- For corporate customers: signatory names match the board resolution

### 4.3 Electronic Verification

When available, supplement document verification with:
- Government database verification (national ID systems)
- Credit bureau data matching
- Utility company address verification
- Corporate registry verification for business entities

## 5. Step 3: Sanctions and PEP Screening

### 5.1 Screening Procedure

1. Screen the customer name (and all known aliases) against all mandatory sanctions lists
2. Screen against PEP databases (domestic and international)
3. Screen against adverse media databases
4. For corporate customers, also screen: all beneficial owners, directors, and authorized signatories
5. Record all screening results including "no match" results

### 5.2 Interpreting Screening Results

**True Positive (Confirmed Match):**
- Stop the onboarding process immediately
- Escalate to the Compliance Officer
- Do not inform the applicant of the reason
- File a SAR if appropriate

**Potential Match (Requires Investigation):**
- Gather additional information to confirm or dismiss
- Compare date of birth, nationality, address, and other identifying details
- Document your analysis and conclusion
- If unable to dismiss with confidence, escalate

**False Positive (Dismissed):**
- Document the reason for dismissal (e.g., different date of birth, different nationality)
- Retain the documentation in the case file
- Proceed with onboarding

## 6. Step 4: Risk Assessment

### 6.1 Scoring Methodology

Apply the risk factor matrix from KYC Policy Section 4.1. Score each factor on a 1-3 scale:

| Score | Level | Description |
|-------|-------|-------------|
| 1 | Low | No elevated risk indicators |
| 2 | Medium | Some risk indicators but mitigating factors present |
| 3 | High | Clear risk indicators, enhanced measures required |

**Overall Risk Score = Sum of all factor scores**

| Total Score | Risk Rating | Due Diligence Level |
|-------------|-------------|---------------------|
| 5-8 | Low | Standard CDD |
| 9-12 | Medium | Standard CDD with enhanced monitoring |
| 13-15 | High | Enhanced Due Diligence (EDD) |

### 6.2 Override Rules

- Any single factor scored at 3 AND total score ≥ 10 → automatically High Risk
- PEP status → automatically High Risk regardless of total score
- Sanctions list match → Stop (do not assign rating, escalate immediately)
- Analyst may upgrade (never downgrade) the risk rating with documented justification

## 7. Step 5: Enhanced Due Diligence (EDD)

EDD is required when the customer is rated High Risk. In addition to standard CDD:

### 7.1 Additional Information Required

- Detailed source of wealth documentation (employment records, business financials, asset records)
- Detailed source of funds for the initial deposit and expected transactions
- Purpose of the account and expected transaction patterns with specific amounts
- References from other financial institutions
- For PEPs: nature and duration of the public position, any known connections to the jurisdiction's government

### 7.2 Enhanced Verification

- Independent verification of source of wealth through third-party sources
- Adverse media search using multiple databases and open-source intelligence
- Review of court records and regulatory enforcement actions
- For corporate customers: verification of corporate structure through registry filings

### 7.3 Senior Management Approval

The following must be documented and approved by a Senior Compliance Manager (or above):
- Summary of all CDD and EDD findings
- Risk assessment with specific risk factors identified
- Rationale for why the relationship should proceed (or be declined)
- Proposed ongoing monitoring measures
- Recommended review frequency

## 8. Step 6: Decision

### 8.1 Approve

Requirements:
- All documentation is complete and verified
- Screening results are clear (or potential matches dismissed with documentation)
- Risk rating is assigned and appropriate due diligence level completed
- For High Risk: senior management approval obtained

### 8.2 Reject

Grounds for rejection:
- Confirmed sanctions list match
- Unable to verify identity to required standard
- Customer refuses to provide required documentation
- Adverse information that cannot be mitigated
- Unacceptable risk level as determined by compliance review

Rejection notification must not reveal specific compliance concerns. Use standard language: "We are unable to proceed with your application at this time."

### 8.3 Request More Information

When additional information is needed:
- Be specific about what is required and why (without revealing internal risk concerns)
- Set a clear deadline (10 business days)
- Track the request and follow up if not received
- After two unsuccessful requests, escalate to Team Lead for a decision

## 9. Quality Assurance

### 9.1 Peer Review

- 100% of High Risk decisions must be peer-reviewed before finalization
- Random sampling of 20% of Low and Medium Risk decisions for quality review
- Monthly quality reports produced by the QA team

### 9.2 Common Errors

Based on recent QA findings, pay attention to:
- Failing to screen all beneficial owners (not just the primary applicant)
- Accepting expired identification documents
- Not documenting the reason for dismissing screening matches
- Applying incorrect risk rating methodology
- Insufficient documentation of EDD findings
