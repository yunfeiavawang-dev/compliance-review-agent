# KYC Agent — Metrics Report

**LLM**: ark/doubao-seed-evolving
**Evaluation Date**: N/A
**Cases Evaluated**: 7

## 1. Token Consumption

| Case | Customer | Input Tokens | Output Tokens | Total |
|------|----------|-------------|--------------|-------|
| KYC-2024-001 | Chen Wei Lin | 12,596 | 31,001 | 43,597 |
| KYC-2024-007 | TechBridge Solutio | 13,679 | 27,073 | 40,752 |
| KYC-2024-006 | Sarah Chen Mei Lin | 10,889 | 26,819 | 37,708 |
| KYC-2024-004 | Tanaka Yuki | 6,469 | 23,061 | 29,530 |
| KYC-2024-005 | Dato' Ahmad bin Ib | 10,207 | 33,561 | 43,768 |
| KYC-2024-002 | Golden Dragon Trad | 8,738 | 38,047 | 46,785 |
| KYC-2024-003 | Mikhail Petrov | 14,709 | 34,752 | 49,461 |
| **Average** | | **11,041** | **30,616** | **41,657** |
| **Total (7 cases)** | | **77,287** | **214,314** | **291,601** |

## 2. Latency

### End-to-End per Case

| Case | Customer | Elapsed (s) |
|------|----------|-------------|
| KYC-2024-001 | Chen Wei Lin | 698.3s |
| KYC-2024-007 | TechBridge Solutio | 527.2s |
| KYC-2024-006 | Sarah Chen Mei Lin | 573.8s |
| KYC-2024-004 | Tanaka Yuki | 470.1s |
| KYC-2024-005 | Dato' Ahmad bin Ib | 648.3s |
| KYC-2024-002 | Golden Dragon Trad | 753.4s |
| KYC-2024-003 | Mikhail Petrov | 647.1s |
| **Average** | | **616.9s** |

### Per-Node Latency (seconds)

| Case | ? | await_info | decision | edd_document_check | enhanced_due_diligence | identity_screening | intake | request_info | risk_assessment | standard_review |
|------| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| KYC-2024-001 | 0 | 0 | 162 | 0 | 0 | 213 | 192 | 0 | 130 | 0 |
| KYC-2024-007 | 0 | 0 | 124 | 0 | 0 | 161 | 115 | 0 | 127 | 0 |
| KYC-2024-006 | 74 | 0 | 168 | 0 | 0 | 98 | 91 | 0 | 143 | 0 |
| KYC-2024-004 | 0 | 0 | 124 | 0 | 0 | 81 | 126 | 0 | 139 | 0 |
| KYC-2024-005 | 0 | 0 | 159 | 234 | 0 | 141 | 114 | 0 | 0 | 0 |
| KYC-2024-002 | 132 | 140 | 185 | 0 | 0 | 296 | 0 | 0 | 0 | 0 |
| KYC-2024-003 | 0 | 0 | 154 | 217 | 0 | 143 | 133 | 0 | 0 | 0 |
| **Avg** | 30 | 140 | 154 | 150 | 0 | 162 | 110 | 0 | 77 | 0 |

## 3. Cost Analysis

### Demo Run (7 cases, actual consumption)

- Input tokens: 77,287
- Output tokens: 214,314
- LLM cost: ¥1.1664 ($0.1620)
- **Total demo cost: $0.1620** (LLM only, no infra)

## Scaled Cost Projection (Volcengine Full Stack)

| Monthly Volume | LLM Cost (CNY) | LLM Cost (USD) | Infra (USD) | Total (USD) | Per Case |
|----------------|-----------------|----------------|-------------|-------------|----------|
| 500 cases | ¥83.31 | $11.57 | $268 | $279.57 | $0.5591 |
| 1,000 cases | ¥166.63 | $23.14 | $268 | $291.14 | $0.2911 |
| 5,000 cases | ¥833.14 | $115.71 | $268 | $383.71 | $0.0767 |

**Infrastructure breakdown:**

- ECS (2x ecs.g3i.xlarge): $180/mo
- VKE (Kubernetes): $0/mo
- TOS (Object Storage, 100GB): $3/mo
- RDS MySQL (basic): $45/mo
- Redis (1GB): $15/mo
- CDN (50GB): $5/mo
- CloudMonitor: $0/mo
- VPC + NAT Gateway: $20/mo
- **Subtotal**: $268/mo

*LLM: Doubao-seed-evolving @ ¥0.004/1K input + ¥0.004/1K output*

## 4. Accuracy

| Case | Customer | Decision (Actual) | Decision (Expected) | Match | Risk Match | DD Match |
|------|----------|-------------------|---------------------|-------|------------|----------|
| KYC-2024-001 | Chen Wei Lin | approve | approve | Y | **N** | Y |
| KYC-2024-007 | TechBridge Solutio | approve | approve | Y | **N** | Y |
| KYC-2024-006 | Sarah Chen Mei Lin | approve | approve | Y | Y | Y |
| KYC-2024-004 | Tanaka Yuki | approve | approve | Y | Y | Y |
| KYC-2024-005 | Dato' Ahmad bin Ib | approve_with_conditions | approve_with_conditions | Y | Y | Y |
| KYC-2024-002 | Golden Dragon Trad | escalate | request_more_information | **N** | Y | Y |
| KYC-2024-003 | Mikhail Petrov | escalate | escalate_to_compliance_committee | Y | Y | Y |

**Decision Accuracy**: 6/7 (86%)
**Risk Rating Match**: 5/7
**DD Level Match**: 7/7

## 5. Experience Scores

| Case | Clarity | Jargon | References | Next Steps | Total |
|------|---------|--------|------------|------------|-------|
| KYC-2024-001 | 4/5 | 3/5 | Y | N | 4.5/7.0 |
| KYC-2024-007 | 4/5 | 4/5 | Y | Y | 6.0/7.0 |
| KYC-2024-006 | 4/5 | 3/5 | Y | Y | 5.5/7.0 |
| KYC-2024-004 | 4/5 | 3/5 | Y | Y | 5.5/7.0 |
| KYC-2024-005 | 4/5 | 3/5 | Y | Y | 5.5/7.0 |
| KYC-2024-002 | 4/5 | 3/5 | Y | N | 4.5/7.0 |
| KYC-2024-003 | 4/5 | 3/5 | Y | Y | 5.5/7.0 |
| **Average** | | | | | **5.3/7.0** |
