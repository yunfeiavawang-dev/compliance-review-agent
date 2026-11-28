# KYC Agent — Rubric Evaluation Report

**Date**: 2026-11-26 12:30
**LLM**: ark/doubao-seed-evolving
**Cases**: 7

## Aggregate Scores

| Metric | Value |
|--------|-------|
| Accuracy (decision acceptable) | 86% (6/7) |
| Risk Rating Match | 5/7 |
| DD Level Match | 7/7 |
| Total Tokens | 291,601 |
| Total Cost (USD) | $0.1620 |
| Avg Latency per Case | 616.9s |
| Avg Experience Score | 5.3/7.0 |

## Per-Case Results

| Case | Customer | Decision | Expected | Risk | DD | Exp Score | Tokens | Latency |
|------|----------|----------|----------|------|----|-----------|--------|---------|
| KYC-2024-001 | Chen Wei Lin | approve Y | approve | N | Y | 4.5 | 43,597 | 698s |
| KYC-2024-007 | TechBridge Solutio | approve Y | approve | N | Y | 6.0 | 40,752 | 527s |
| KYC-2024-006 | Sarah Chen Mei Lin | approve Y | approve | Y | Y | 5.5 | 37,708 | 574s |
| KYC-2024-004 | Tanaka Yuki | approve Y | approve | Y | Y | 5.5 | 29,530 | 470s |
| KYC-2024-005 | Dato' Ahmad bin Ib | approve_with_conditions Y | approve_with_conditions | Y | Y | 5.5 | 43,768 | 648s |
| KYC-2024-002 | Golden Dragon Trad | escalate **N** | request_more_information | Y | Y | 4.5 | 46,785 | 753s |
| KYC-2024-003 | Mikhail Petrov | escalate Y | escalate_to_compliance_committee | Y | Y | 5.5 | 49,461 | 647s |

## Experience Detail

### KYC-2024-001 — Chen Wei Lin
- Clarity: 4/5
- Jargon: 3/5 (found: CDD, KYC, PEP)
- References: Yes
- Next Steps: No
- **Total: 4.5/7.0**

### KYC-2024-007 — TechBridge Solutions Pte Ltd
- Clarity: 4/5
- Jargon: 4/5 (found: KYC, PEP)
- References: Yes
- Next Steps: Yes
- **Total: 6.0/7.0**

### KYC-2024-006 — Sarah Chen Mei Ling
- Clarity: 4/5
- Jargon: 3/5 (found: CDD, KYC, PEP)
- References: Yes
- Next Steps: Yes
- **Total: 5.5/7.0**

### KYC-2024-004 — Tanaka Yuki
- Clarity: 4/5
- Jargon: 3/5 (found: CDD, KYC, PEP)
- References: Yes
- Next Steps: Yes
- **Total: 5.5/7.0**

### KYC-2024-005 — Dato' Ahmad bin Ibrahim
- Clarity: 4/5
- Jargon: 3/5 (found: EDD, KYC, PEP, SAR)
- References: Yes
- Next Steps: Yes
- **Total: 5.5/7.0**

### KYC-2024-002 — Golden Dragon Trading Co. Ltd
- Clarity: 4/5
- Jargon: 3/5 (found: CDD, KYC, PEP)
- References: Yes
- Next Steps: No
- **Total: 4.5/7.0**

### KYC-2024-003 — Mikhail Petrov
- Clarity: 4/5
- Jargon: 3/5 (found: CDD, EDD, KYC, PEP)
- References: Yes
- Next Steps: Yes
- **Total: 5.5/7.0**

## Node Latency Breakdown

| Case | ? | await_info | decision | edd_document_check | enhanced_due_diligence | identity_screening | intake | request_info | risk_assessment | standard_review | Total |
|------| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| KYC-2024-001 | 0s | 0s | 162s | 0s | 0s | 213s | 192s | 0s | 131s | 0s | 698s |
| KYC-2024-007 | 0s | 0s | 124s | 0s | 0s | 161s | 115s | 0s | 127s | 0s | 527s |
| KYC-2024-006 | 74s | 0s | 168s | 0s | 0s | 98s | 91s | 0s | 143s | 0s | 574s |
| KYC-2024-004 | 0s | 0s | 124s | 0s | 0s | 81s | 126s | 0s | 139s | 0s | 470s |
| KYC-2024-005 | 0s | 0s | 159s | 234s | 0s | 141s | 114s | 0s | 0s | 0s | 648s |
| KYC-2024-002 | 132s | 140s | 185s | 0s | 0s | 296s | 0s | 0s | 0s | 0s | 753s |
| KYC-2024-003 | 0s | 0s | 154s | 217s | 0s | 143s | 133s | 0s | 0s | 0s | 647s |
