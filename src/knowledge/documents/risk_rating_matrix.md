# Customer Risk Rating Matrix and Classification Guide

**Document ID:** GDL-RRM-001  
**Version:** 1.5  
**Effective Date:** 2024-01-15  
**Last Reviewed:** 2024-06-01  
**Owner:** Chief Compliance Officer  
**Classification:** Internal – Compliance Staff Only

---

## 1. Purpose

This document provides the detailed risk scoring methodology used to assign customer risk ratings during KYC onboarding at Pacific Rim Financial Group (PRFG). It is to be used in conjunction with KYC Policy (POL-KYC-001) and CDD Guidelines (GDL-CDD-001).

## 2. Risk Factor Categories

Five risk categories are assessed for each customer. Each category receives a score from 1 (low risk) to 3 (high risk).

### 2.1 Customer Type Risk

| Score | Customer Type | Examples |
|-------|--------------|----------|
| 1 | Low Risk | Salaried employee (government/established company), retiree with pension, student with parental support |
| 2 | Medium Risk | Self-employed professional, small business owner (<5 years), freelancer, contractor |
| 3 | High Risk | PEP or PEP associate, trust/foundation/NPO, shell company, nominee arrangement, unregulated financial service provider |

**Special Rules:**
- All Politically Exposed Persons (PEPs) automatically score 3
- Non-profit organizations (NPOs) with international remittance activity automatically score 3
- Regulated financial institutions from low-risk jurisdictions may score 1

### 2.2 Geographic Risk

| Score | Geography | Description |
|-------|-----------|-------------|
| 1 | Low Risk | Domestic customers; customers from jurisdictions with FATF "compliant" or "largely compliant" ratings |
| 2 | Medium Risk | Customers from jurisdictions with FATF "partially compliant" ratings; customers with business ties to medium-risk regions |
| 3 | High Risk | Customers from FATF high-risk or non-cooperative jurisdictions; customers from comprehensively sanctioned countries; customers with significant business ties to high-risk regions |

**Assessment includes:**
- Customer's country of residence
- Customer's nationality/citizenship
- Countries where the customer conducts significant business
- For corporate customers: countries of incorporation, operation, and primary counterparties

### 2.3 Product/Service Risk

| Score | Product/Service | Examples |
|-------|----------------|----------|
| 1 | Low Risk | Basic savings account, term deposit, standard personal loan |
| 2 | Medium Risk | Business current account, trade finance, foreign currency account, commercial lending |
| 3 | High Risk | Private banking, correspondent banking, payable-through accounts, virtual asset services, wire transfer services |

### 2.4 Transaction Pattern Risk

| Score | Expected Activity | Indicators |
|-------|------------------|------------|
| 1 | Low Risk | Regular salary deposits, standard bill payments, modest savings; transaction volume consistent with declared income |
| 2 | Medium Risk | Regular business receipts and payments, occasional large transactions with clear purpose; some cross-border activity |
| 3 | High Risk | Frequent large cash transactions, high-value cross-border wires, rapid fund movements, expected activity inconsistent with business profile |

**Note:** This factor is assessed based on expected activity declared at onboarding. Actual transaction monitoring may trigger re-assessment.

### 2.5 Source of Funds Risk

| Score | Source of Funds | Examples |
|-------|----------------|----------|
| 1 | Low Risk | Employment income from established employer, pension, government benefits |
| 2 | Medium Risk | Business revenue with audited accounts, rental income, investment returns from regulated products |
| 3 | High Risk | Inheritance (especially cross-border or large), gifts from non-family, cryptocurrency proceeds, cash-intensive business revenue, funds from high-risk jurisdictions |

## 3. Composite Risk Scoring

### 3.1 Calculation

**Total Risk Score = Customer Type + Geography + Product/Service + Transaction Pattern + Source of Funds**

| Total Score | Risk Rating | Required Due Diligence | Review Cycle |
|-------------|-------------|----------------------|--------------|
| 5-8 | Low | Standard CDD | Every 3 years |
| 9-12 | Medium | Standard CDD + Enhanced Monitoring | Every 2 years |
| 13-15 | High | Enhanced Due Diligence (EDD) | Annually |

### 3.2 Automatic Overrides

The following conditions override the calculated risk score:

| Condition | Override To | Authority |
|-----------|-----------|-----------|
| PEP (or PEP family/associate) | High Risk | Automatic |
| Sanctions list match | STOP - Escalate | Automatic |
| Adverse media: financial crime | High Risk | Analyst + Supervisor |
| Complex ownership (>3 layers) | High Risk | Analyst + Supervisor |
| Customer from sanctioned country | STOP - Escalate | Automatic |
| Cash-intensive business + High Risk geography | High Risk | Automatic |

### 3.3 Analyst Override (Upgrade Only)

An analyst may upgrade a customer's risk rating above the calculated level when:
- Professional judgment identifies risk factors not captured by the matrix
- New information emerges during the review process
- The customer's overall profile raises concerns despite moderate individual scores

**An analyst may NEVER downgrade a risk rating.** Downgrades require Team Lead approval and documented justification.

## 4. Industry-Specific Risk Considerations

### 4.1 Retail Banking

- Focus on individual customer identification and verification
- Monitor for structuring (multiple transactions below reporting threshold)
- Pay attention to dormant accounts reactivated with large transactions

### 4.2 Commercial Banking

- Verify business purpose and expected transaction patterns
- Assess industry risk (Section 3.4 of AML Handbook)
- Identify and verify all beneficial owners meeting the 25% threshold
- Review corporate structure for complexity and transparency

### 4.3 Payment Services

- Higher inherent risk due to speed and volume of transactions
- Focus on transaction monitoring and velocity checks
- Enhanced screening for cross-border payment recipients
- Monitor for aggregation patterns suggesting structuring

## 5. Periodic Review Triggers

Beyond the standard review cycle, a risk reassessment must be performed when:

| Trigger | Timeline |
|---------|----------|
| Customer requests change to high-risk product | Before product change |
| Significant change in transaction pattern | Within 5 business days of detection |
| Adverse media alert | Within 2 business days |
| Customer relocation to higher-risk jurisdiction | Within 5 business days |
| Change in beneficial ownership | Within 10 business days |
| Sanctions list update affecting customer profile | Within 24 hours |
| Law enforcement inquiry about the customer | Immediately |
| SAR filed on the customer | Within 1 business day |

## 6. Documentation Requirements

For each risk assessment, the case file must contain:
- Completed risk scoring worksheet with scores and justification for each category
- Supporting evidence for each risk factor assessment
- Any override decisions with documented rationale
- Screening results (sanctions, PEP, adverse media)
- Analyst signature and date
- Supervisor review and approval (for High Risk or override cases)
- Recommended next review date
