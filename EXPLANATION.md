# Written Explanation

**Project:** AI Agentic Compliance Review System
**Author:** Yunfei Wang
**Date:** 2026-11-25

---

## 1. Use Case

### The Problem

KYC (Know Your Customer) compliance review at APAC financial institutions is a manual, document-heavy process. When a new customer applies to open an account, compliance analysts must:

1. Check that all required identification documents are present and valid
2. Screen the customer against sanctions lists, PEP databases, and adverse media
3. Assess risk across multiple dimensions (geography, customer type, product, transaction patterns, source of funds)
4. Conduct standard or enhanced due diligence depending on risk level
5. Make an approve/reject/escalate decision with full policy justification

This process typically takes **2-5 days per case** for standard reviews, **5-15 days for enhanced due diligence**, and suffers from:

- **Inconsistency:** Different analysts apply policies differently. The same customer reviewed by 5 analysts may receive 3 different risk ratings.
- **Incomplete first submissions:** 40% of submissions are missing documents, discovered only after days of review. The customer-RM-analyst communication loop adds more days.
- **Analyst bottleneck:** Experienced compliance analysts spend most of their time on routine checks rather than judgment-intensive cases.
- **Audit gaps:** Manual review makes it difficult to prove that every required check was performed and every policy was consulted.

### Why AI Agentic Compliance Review

The system automates the structured, policy-driven parts of KYC review while keeping human judgment at the decision point. It is not a chatbot — it is an **AI-powered review pipeline** that:

- Performs document completeness checks in milliseconds (rule-based, deterministic)
- Conducts multi-turn investigation for due diligence (ReAct loop with policy retrieval)
- Presents findings with full policy citations for human review
- Guarantees every case follows the mandated process (graph-enforced)
- Records a complete audit trail automatically

The compliance analyst's role shifts from "doing the checks" to "reviewing the AI's judgment" — a force multiplier, not a replacement.

---

## 2. Metrics

### Primary Metrics

| Metric | Current (Manual) | Target (AI-Assisted) | How Measured |
|--------|-----------------|---------------------|--------------|
| **First-Pass Document Completeness** | ~60% | 85%+ | % of submissions that pass intake without request-for-info |
| **Average Review Turnaround** | 3-5 days (CDD), 5-15 days (EDD) | <1 day (CDD), 2-3 days (EDD) | Submission timestamp to decision timestamp |
| **Risk Rating Consistency** | ~70% agreement rate across analysts | ≥95% run-to-run agreement (100% once factor scoring is fully rule-based) | Agreement rate: % of repeated runs / independent reviews that yield the same risk level |
| **Policy Citation Coverage** | Partial (analyst memory) | 100% | % of conclusions with traceable policy references |
| **Audit Trail Completeness** | Variable | 100% | % of review steps with documented action, evidence, and policy basis |

### How the System Improves Each Metric

**First-Pass Completeness (60% → 85%):** The intake node provides instant feedback on missing documents with a clear classification (critical = blocked, non-critical = proceed with risk flag). This cuts the feedback loop from days to seconds. The remaining 15% represents documents the submitter physically doesn't have yet (e.g., ACRA registration in progress).

**Review Turnaround (days → hours):** AI performs document checks, screening simulation, risk scoring, and due diligence investigation automatically. The human reviewer receives a complete package (AI recommendation + evidence + policy citations) rather than starting from scratch.

**Risk Rating Consistency (70% → ≥95%):** The rating step is deterministic: fixed score thresholds (total ≥12 → high, ≥8 → medium), +1 for a conditional intake, and a forced upgrade to high on any screening red flag. The remaining variability comes from the per-factor scores, which the LLM still assigns from the submission (temperature 0.3 reduces but does not eliminate run-to-run variation). In the current 7-case evaluation the risk level matched the expected rating in 5/7 cases. Reaching 100% requires moving factor scoring to a rule-based risk matrix, with the LLM only extracting the factors. The AI recommendation is tracked against the human decision (`ai_human_agreement`) to measure alignment over time.

**Policy Citation & Audit Completeness:** Structural guarantees from the architecture — not aspirational goals. The graph enforces step completion; RAG provides cited policy context; the append-only audit trail records every action.

### Secondary Metrics (Operational)

| Metric | Purpose |
|--------|---------|
| **AI-Human Agreement Rate** | Tracks how often the AI recommendation matches the human decision; a leading indicator for calibration |
| **AI Confidence Score** | 0.0–1.0 per case; low-confidence cases may need priority human attention |
| **Request-Info Round Count** | Cases averaging >1 round suggest submission quality issues upstream |
| **ReAct Tool Usage** | Which tools CDD/EDD nodes use most; indicates what policy areas are most referenced |

---

## 3. Key Design Decisions

### 3.1 LangGraph (Agentic Workflow) over Autonomous Agent

**Decision:** Use a directed graph with deterministic edges and LLM-powered nodes, not a fully autonomous agent loop.

**Rationale:** Compliance review follows a mandated process. The graph encodes this process — every case must go through intake, screening, risk assessment, appropriate due diligence, and human approval. An autonomous agent (like a ReAct loop deciding its own next step) could skip checks, reorder steps, or loop indefinitely.

**The graph IS the audit trail:** A regulator asking "did you screen this customer?" gets a definitive answer — the graph structure makes it impossible to skip screening. With an autonomous agent, the answer would be "it probably did, based on our prompt."

**Trade-off:** Less flexible than a fully autonomous agent. If a new compliance process emerges that doesn't fit the existing graph, the graph must be updated (a code change). But in regulated industries, this is a feature — process changes should be deliberate, reviewed, and versioned, not emergent from prompt engineering.

### 3.2 Rule-Based + LLM Hybrid at Intake

**Decision:** Deterministic rules first, LLM only for edge cases.

**Rationale:** "Does the submission include a passport?" is a yes/no question. Using an LLM for this is wasteful and introduces unnecessary non-determinism. The rule engine handles 90%+ of cases in <1ms. The LLM is called only when the rules detect ambiguity (e.g., a document type that doesn't clearly map to a category, a UBO structure that might or might not require additional disclosure).

**Trade-off:** Maintaining two code paths (rules + LLM). But the rule path is simple, testable, and fast — worth the small additional complexity.

### 3.3 ReAct Loops in CDD/EDD

**Decision:** CDD and EDD nodes use multi-turn ReAct (Thought → Action → Observation) loops instead of single-shot LLM calls.

**Rationale:** Due diligence is an investigation, not a classification. A good compliance analyst doesn't just read the case once — they check a policy, then look at a specific document, then check another policy, then search for precedents. ReAct replicates this workflow:

- **Richer audit trail:** Each round records what was searched, what was found, and what the agent thought about it.
- **On-demand retrieval:** Only fetches policy sections as needed, rather than stuffing the entire policy into the prompt.
- **Bounded:** Max 4 rounds (CDD) or 5 rounds (EDD), with forced conclusion at the limit.

**Trade-off:** More LLM calls per case (cost + latency). For a prototype, acceptable. In production, monitor and tune max rounds.

### 3.4 Thin Long-Term Memory (Retrospective Docs over Memory)

**Decision:** No free-form "agent experience" storage. Knowledge reuse goes through human-written retrospective documents ingested into RAG.

**Rationale:** An earlier design stored "experience" (edge-case learnings, observed patterns, confidence scores) in a memory table and recalled them into prompts. This was removed because:

1. Memory entries are hard to audit — who wrote them? Are they correct? When did they become stale?
2. If the AI "learns" something wrong, it propagates to all future cases
3. Compliance knowledge must be managed through documented, reviewable, versioned processes

The replacement — retrospective documents written by compliance officers, ingested into the same RAG pipeline as policies — is auditable, correctable, and fits the existing "lessons learned" practice in compliance teams.

**Trade-off:** No automatic learning. But in compliance, that's the right trade-off — knowledge changes should be deliberate and human-reviewed.

### 3.5 Resume-at-Requesting-Node for Request-Info

**Decision:** When supplemental information is provided, the graph resumes at the node that requested it, not at intake.

**Rationale:** If EDD requested source-of-wealth documentation, there's no need to re-run intake, screening, or risk assessment. Those results are still valid. Resuming at the requesting node reuses earlier work and avoids duplicate audit entries.

**Trade-off:** More complex routing logic. But the alternative — re-running the entire pipeline — wastes time, money, and produces confusing duplicate entries in the audit trail.

---

## 4. Trade-offs

| Area | What We Chose | What We Gave Up | Why |
|------|--------------|-----------------|-----|
| **Workflow control** | Graph-enforced process | Full agent autonomy | Auditability and predictability over flexibility |
| **Intake design** | Rules + LLM | Pure LLM | Speed and determinism for clear-cut checks |
| **CDD/EDD** | ReAct multi-turn | Single-shot prompt | Investigation depth and audit richness |
| **Memory** | RAG-based knowledge reuse | Automatic learning | Human oversight over convenience |
| **Persistence** | In-memory (prototype) | Durable persistence | Demo speed over production resilience |
| **Screening** | LLM simulation | Real APIs | Prototype scope; real APIs need vendor contracts |
| **Provider** | OpenAI + Ark (config switch) | Single provider | Flexibility for demo (OpenAI) + BytePlus ecosystem alignment (Ark) |

---

## 5. Known Limitations

### 5.1 Prototype Limitations

1. **Volatile state:** `MemorySaver` is in-memory. Cases in progress (waiting for human review or supplemental info) are lost on server restart. Production requires `SqliteSaver` or `PostgresSaver`.

2. **No real screening APIs:** Sanctions, PEP, and adverse media screening are simulated. The screening node either uses pre-populated flags from test data or asks the LLM to simulate screening based on customer information. Production requires integration with providers like Dow Jones, Refinitiv, or ComplyAdvantage.

3. **Label leakage in test data:** `expected_outcome` is in the same JSON file as input data, which is sent to the LLM via `submission_json` in the intake prompt. The LLM may see the expected answer. For proper evaluation, inputs and labels must be separated.

4. **Limited test coverage:** 3 test cases cover the main paths but cannot provide statistical confidence. The Eval Design Document proposes 20+ benchmark cases with pairwise coverage of risk dimensions.

### 5.2 Architecture Limitations

1. **Static graph:** The workflow handles the KYC process as currently defined. A novel compliance process (e.g., cryptocurrency-specific KYC) would require graph modification — a code change, not a configuration change.

2. **No cross-case learning:** The system does not automatically improve from past cases. All knowledge improvements require human review → document authoring → RAG ingestion. This is intentional (see Design Decision 3.4) but means the system won't self-optimize.

3. **LLM dependency for judgment calls:** ReAct loops in CDD/EDD depend on LLM quality. A weaker model may produce less thorough investigations or miss relevant policy sections. Model selection matters significantly for review quality.

4. **Single-language prompts:** Current prompts are English-only. APAC compliance documents may be in local languages; supporting multilingual policy retrieval requires extending the RAG pipeline.

### 5.3 Data and Integration Limitations

1. **Synthetic data only:** All customer profiles, policies, and cases are fabricated. Real-world policies would be significantly more complex and nuanced.

2. **PII masking not on the LLM path:** `src/auth/pii.py` masks names, passport / NRIC / HKID numbers, dates of birth, emails and phone numbers, and is used in the dashboard and the audit log. The graph nodes still send unmasked customer data to the LLM API. Production must mask before every LLM call, especially with cross-border LLM providers (Ark API in Beijing, OpenAI API in the US).

3. **RBAC is a skeleton:** `src/auth/rbac.py` defines four roles (analyst, senior analyst, compliance officer, admin), granular permissions and a risk-level approval check that the dashboard enforces when a decision is submitted. The current user is a hard-coded mock: there is no login or SSO, and no maker-checker rule (submitter ≠ approver) yet. Production would populate the user from the bank's identity provider (SAML / OIDC).

---

## 6. Open Questions

1. **Model selection for production:** Is `gpt-4o-mini` sufficient for CDD/EDD quality, or does the investigation depth require a larger model (GPT-4o, Claude)? This needs systematic evaluation with the benchmark cases.

2. **Confidence calibration:** The AI confidence score (0.0–1.0) is currently self-reported by the LLM. How well is it calibrated? Does 0.8 confidence actually correspond to 80% agreement with human decisions? Needs empirical validation.

3. **Regulatory acceptance:** Would APAC regulators (MAS, HKMA) accept an AI-assisted review as meeting KYC obligations? The system is designed for it (audit trail, human approval, policy citations), but regulatory stance on AI in compliance is evolving.

4. **Scaling economics:** ReAct loops in EDD use 5-10 LLM calls per case. At scale (thousands of cases/month), is this cost-effective compared to analyst time? What's the break-even point?

5. **Policy version management:** When a policy is updated, how should in-flight cases be handled? Should they continue under the old policy or restart under the new one? The `policy_version_log` tracks versions but doesn't trigger re-reviews.

6. **Integration with existing bank systems:** How does this system connect to the bank's core banking system, document management system, and existing compliance tools? The prototype is standalone; production integration is a significant engineering effort.
