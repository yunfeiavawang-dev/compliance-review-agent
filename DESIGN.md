# System Design Document

**Project:** AI Agentic Compliance Review System
**Institution:** Pacific Rim Financial Group (PRFG) — simulated APAC financial institution
**Author:** Yunfei Wang
**Date:** 2026-11-25

---

## 1. Executive Summary

This system automates KYC (Know Your Customer) compliance review for customer onboarding at a simulated APAC bank. It combines **deterministic workflow orchestration** (LangGraph) with **LLM-powered reasoning** at each review step, plus **RAG-based policy retrieval** so every AI conclusion cites the specific compliance document, section, and version that supports it.

The core design principle: **macro-structure via graph, micro-autonomy via LLM**. The graph guarantees every case follows the mandated review sequence (intake → screening → risk assessment → due diligence → human approval → decision). Within each step, the LLM reasons freely — including multi-turn ReAct investigation in CDD/EDD — but cannot skip steps or alter the process.

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| LangGraph over autonomous agent | Compliance requires auditable, deterministic process flow; "the graph IS the audit trail" |
| Rule-based + LLM hybrid at intake | 90%+ cases resolved by rules in <1ms; LLM handles judgment calls on ambiguous submissions |
| ReAct loops in CDD/EDD | These nodes require non-structured investigation; ReAct produces richer audit traces than single-shot prompts |
| RAG with source citations | Every policy-based conclusion traced to document + version + section |
| Thin long-term memory | Compliance requires all knowledge to be auditable; experience reuse via retrospective docs in RAG, not opaque memory |
| Human-in-the-loop via checkpoint interrupt | LangGraph native `interrupt_before` ensures human approval cannot be bypassed |

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Streamlit Dashboard UI                       │
│  Review Queue │ Case Detail (3-col) │ Decision Panel │ Timeline  │
├─────────────────────────────────────────────────────────────────┤
│                   LangGraph Workflow Engine                       │
│  ┌────────┐   ┌───────────┐   ┌──────┐   ┌─────┐   ┌────────┐ │
│  │ Intake │──▶│ Screening │──▶│ Risk │──▶│ CDD │──▶│ Human  │ │
│  │(Rules+ │   │  (LLM)    │   │(LLM) │   │(Re- │   │Review  │ │
│  │  LLM)  │   └───────────┘   └──────┘   │Act) │   │(Inter- │ │
│  └────────┘                        │      └─────┘   │ rupt)  │ │
│       │                            │high             └────────┘ │
│       │blocked              ┌──────┴──────┐              │      │
│       ▼                     │EDD Doc Gate │              ▼      │
│  ┌──────────┐               │(Rules)      │        ┌──────────┐ │
│  │ Request  │◄──────────────┤             │        │ Decision │ │
│  │  Info    │               └─────────────┘        │  (LLM)   │ │
│  └──────────┘                     │                └──────────┘ │
│       │                     ┌─────▼─────┐                       │
│       ▼                     │   EDD     │                       │
│  ┌──────────┐               │  (ReAct)  │                       │
│  │  Await   │               └───────────┘                       │
│  │  Info    │                                                    │
│  └──────────┘                                                    │
├──────────┬──────────────────────┬────────────────────────────────┤
│ Database │   Knowledge Base     │          Memory                │
│ (SQLite) │ (ChromaDB + RAG)    │  (Short-term + Policy Log)     │
│          │                      │                                │
│ Customer │ 5 policy documents   │ SessionMemory (per-case)       │
│ profiles,│ + case review docs   │ PolicyVersionLog (audit)       │
│ reviews, │                      │                                │
│ audit log│ bge-small-zh-v1.5    │ LangGraph State (TypedDict)    │
│          │ 800/200 chunking     │                                │
└──────────┴──────────────────────┴────────────────────────────────┘
         │                │                      │
         ▼                ▼                      ▼
  ┌─────────────────────────────────────────────────────┐
  │              LLM Provider (Configurable)             │
  │  Ark (Doubao)  ◄──── .env switch ────►  OpenAI      │
  │  doubao-seed-evolving                   gpt-4o-mini  │
  └─────────────────────────────────────────────────────┘
```

### 2.1 Three-Layer Data Architecture

| Layer | Technology | Purpose | Access Pattern |
|-------|-----------|---------|----------------|
| **Structured Data** | SQLite | Customer profiles, review records, risk assessments, audit log, screening results | Exact queries (`WHERE case_id = ...`), transactional writes, relational joins |
| **Knowledge Base** | ChromaDB + RAG | Compliance policies (KYC, AML, CDD, sanctions, risk matrix) + retrospective case reviews | Semantic search (cosine similarity), source-cited retrieval |
| **Memory** | Python dict (short-term) + SQLite (policy version log) | Per-case session state; policy version tracking for audit reproducibility | Fast read/write (session), append-only log (policy versions) |

**Why three layers:** Structured data needs exact CRUD; knowledge needs semantic search; agent state needs fast session-scoped access. A single database cannot serve all three patterns.

---

## 3. LangGraph Workflow

### 3.1 Graph Structure

```
                                 ┌─────────────────────────────┐
                                 │        Entry Point           │
                                 └──────────┬──────────────────┘
                                            ▼
                                      ┌──────────┐
                                      │  intake   │
                                      └────┬─────┘
                                           │
                              ┌────────────┼────────────┐
                              │ blocked    │ complete/   │
                              ▼            │ conditional │
                       ┌──────────┐        ▼             │
                       │request_  │  ┌───────────────┐   │
                       │  info    │  │  identity_    │   │
                       └────┬─────┘  │  screening    │   │
                            │        └───────┬───────┘   │
                            │                │           │
                            │    ┌───────────┤           │
                            │    │confirmed  │ other     │
                            │    │  match    ▼           │
                            │    │   ┌──────────────┐    │
                            │    │   │risk_         │    │
                            │    │   │assessment    │    │
                            │    │   └──────┬───────┘    │
                            │    │          │            │
                            │    │   ┌──────┴──────┐     │
                            │    │   │high    low/ │     │
                            │    │   │        med  │     │
                            │    │   ▼             ▼     │
                            │    │  ┌────────┐ ┌────────┐│
                            │    │  │edd_doc │ │standard││
                            │    │  │_check  │ │_review ││
                            │    │  └───┬────┘ │(ReAct) ││
                            │    │      │      └───┬────┘│
                            │    │      ▼          │     │
                            │    │  ┌────────┐     │     │
                            │    │  │  edd   │     │     │
                            │    │  │(ReAct) │     │     │
                            │    │  └───┬────┘     │     │
                            │    │      │          │     │
                            │    │      └─────┬────┘     │
                            │    │            ▼          │
                            │    │     ┌────────────┐    │
                            │    │     │human_review│    │
                            │    │     │(interrupt) │    │
                            │    │     └─────┬──────┘    │
                            │    │           │           │
                            │    │           ▼           │
                            │    │     ┌──────────┐      │
                            │    │     │ decision │──────►END
                            │    │     └──────────┘
                            │    │
                            ▼    ▼
                       ┌──────────┐
                       │await_info│ (interrupt_before)
                       └──────┬───┘
                              │ resumes at requesting node
                              └──────► (intake | screening |
                                        edd_doc_check | edd |
                                        standard_review)
```

### 3.2 Conditional Edges (all deterministic)

| Edge Function | Input | Routing Logic |
|---------------|-------|---------------|
| `route_after_intake` | `intake_status` | `blocked` → request_info; `conditional`/`complete` → screening |
| `route_after_screening` | `sanctions_result` | `confirmed_match` → request_info; else → risk_assessment |
| `route_after_risk_assessment` | `risk_rating` | `high` → edd_document_check; else → standard_review |
| `route_after_edd_document_check` | `edd_missing_docs` + red flags | Missing docs + no red flag → request_info; else → EDD |
| `route_after_review` | `decision` | `request_more_info` → request_info; else → human_review |
| `route_after_human_review` | `human_decision` | `request_more_info` → request_info; else → decision |
| `route_after_request_info` | `info_round_exceeded` | Exceeded → human_review (escalate); else → await_info |
| `route_after_await_info` | `info_request_stage` | Returns to the node that requested info |

### 3.3 State Schema

`ReviewState(TypedDict)` — shared state flowing through all nodes. Key fields:

- **Case identification:** `case_id`, `review_id`, `customer_id`
- **Intake:** `intake_status` (blocked/conditional/complete), `critical_missing`, `non_critical_missing`
- **Screening:** `sanctions_result`, `pep_result`, `adverse_media_result`
- **Risk:** `risk_scores` (5-factor dict), `risk_total`, `risk_rating`, `due_diligence_level`
- **Decision:** `decision`, `decision_rationale`, `ai_confidence` (0.0–1.0)
- **Human:** `human_decision`, `human_notes`, `ai_human_agreement` (bool)
- **Workflow control:** `current_step`, `info_request_stage`, `info_request_round`, `info_round_exceeded`
- **Audit trail:** `Annotated[list[dict], operator.add]` — append-only reducer; nodes return only new entries, framework concatenates

### 3.4 Human-in-the-Loop

```python
graph.compile(
    checkpointer=MemorySaver(),
    interrupt_before=["human_review", "await_info"],
)
```

Two interrupt points:
1. **human_review:** Workflow pauses before human review. Streamlit renders the AI recommendation + evidence + policy citations. Compliance analyst submits decision via `app.update_state(config, {"human_decision": ..., "human_notes": ...}, as_node="human_review")`, then `app.stream(None, config)` resumes.
2. **await_info:** Workflow pauses before await_info node. RM provides supplemental documents. Submission is updated, then graph resumes at the node that requested the info (not intake), reusing earlier results.

---

## 4. Node Design Patterns

Each node uses the most appropriate pattern for its task:

| Node | Pattern | Why |
|------|---------|-----|
| `intake` | **Rule-based + LLM fallback** | Deterministic checks (field presence, expiry dates, UBO disclosure) cover 90%+ cases; LLM only for edge cases |
| `screening` | **Single LLM call** | In production: external API; prototype simulates with LLM classification of provided screening data |
| `risk_assessment` | **Single LLM call** | Structured scoring matrix (5 factors × 1-3 points) + code-based adjustments (conditional intake +1) |
| `standard_review` | **ReAct loop (max 4 rounds)** | Non-structured CDD investigation; LLM autonomously picks tools to gather evidence |
| `edd` | **ReAct loop (max 5 rounds)** | Deeper EDD investigation; more rounds for complex cases |
| `edd_document_check` | **Deterministic gate (no LLM)** | Check SoW/SoF evidence; pure rules, no judgment needed |
| `human_review` | **Passthrough** | Empty node; exists for `interrupt_before` |
| `decision` | **Single LLM call** | Summary generation from established facts |
| `request_info` | **Pure code** | Collects info requests from state; tracks round count |
| `await_info` | **Pure code** | Passthrough after graph resume; refreshes EDD doc list |

### 4.1 Intake: Rule-Based + LLM Fallback

```
Phase 1 (Rules, <1ms):
  ├── Check photo ID existence (category A for individuals)
  ├── Check corporate critical docs (certificate of incorporation, board resolution)
  ├── Verify document expiry dates
  ├── Check UBO disclosure (≥25% ownership without ID → edge case)
  ├── Check declarations signed
  └── Classify: critical_missing / non_critical_missing / edge_cases

Phase 2 (LLM, only if edge_cases or doc_issues exist):
  └── Send edge cases + policy context to LLM for judgment
      └── LLM may reclassify documents between critical/non-critical

Final classification:
  ├── critical_missing not empty → "blocked" (hard stop)
  ├── non_critical_missing not empty → "conditional" (proceed with risk +1)
  └── all empty → "complete" (proceed normally)
```

### 4.2 CDD/EDD: ReAct Loop

The ReAct loop implements Thought → Action → Observation cycles within a graph node:

```
System prompt (compliance review context)
   │
   ▼
Round 1: LLM picks a tool
   ├── search_policy("CDD requirements for individual savings account")
   │   └── Observation: [KYC Policy v2.1 — Section 4.2] "Standard CDD requires..."
   │
Round 2: LLM picks another tool
   ├── check_document("national_id")
   │   └── Observation: {"type": "national_id", "verified": true, "expiry": "2030-01-14"}
   │
Round 3: LLM picks another tool
   ├── assess_risk_factor("geography")
   │   └── Observation: {"score": 1, "justification": "Singapore — low risk jurisdiction"}
   │
Round 4: LLM concludes
   └── final_answer({"recommendation": "approve", "rationale": "...", "confidence": 0.92})
```

**5 ReAct Tools:**

| Tool | Function | Data Source |
|------|----------|-------------|
| `search_policy` | Query compliance knowledge base | ChromaDB RAG |
| `check_document` | Inspect a specific submitted document | State (submission) |
| `assess_risk_factor` | Deep-dive into a risk factor | State (risk_scores) |
| `search_precedent` | Search past case review notes | ChromaDB RAG (case_reviews collection) |
| `final_answer` | Conclude the investigation | — (terminates loop) |

**Audit benefit:** Each ReAct round is recorded in `audit_trail` with the tool called, the query, and an observation preview. This produces a richer investigation record than a single-shot prompt.

---

## 5. RAG Pipeline

### 5.1 Document Ingestion

```
Markdown policy docs (5 files + case reviews)
        │
        ▼
  parse_document_metadata()     ← Extract: document_id, version, effective_date, owner
        │
        ▼
  chunk_document()              ← Section-boundary splitting (## headers)
  (800 chars / 200 overlap)       Respects semantic boundaries; long sections get sub-chunks
        │
        ▼
  bge-small-zh-v1.5             ← Local embedding model (512-dim, bilingual CN/EN)
        │
        ▼
  ChromaDB (cosine similarity)  ← Persistent vector store (.chroma/)
                                   Metadata: document_id, version, section, title
```

### 5.2 Retrieval with Source Citations

```python
# Each node retrieves relevant policy before calling LLM
policy_results = self.kb.get_policy_for_step("intake")
# Returns: [{text, source, document_id, version, section, relevance_score}]

policy_context = self.kb.format_sources_for_prompt(policy_results)
# Formatted as: [Source: KYC Policy v2.1 — Section 3.1]\n{text}
```

Every LLM response includes `sources_cited` traced back to the specific document, version, and section. The dashboard renders these as clickable footnotes.

### 5.3 Knowledge Documents

| Document | ID | Coverage |
|----------|----|----------|
| KYC Policy | PRFG-KYC-001 | Customer identification, document requirements by type, verification procedures |
| AML Handbook | PRFG-AML-001 | Anti-money laundering obligations, SAR reporting, typologies |
| CDD Guidelines | PRFG-CDD-001 | Standard/Enhanced due diligence procedures, SoW/SoF requirements |
| Risk Rating Matrix | PRFG-RRM-001 | 5-factor scoring (1-3), thresholds, automatic overrides |
| Sanctions Screening | PRFG-SCR-001 | Screening procedures, match confidence levels, escalation timelines |
| Case Reviews (weekly) | — | Retrospective analysis of past cases; serves as "experience" via RAG |

---

## 6. Memory Architecture

### 6.1 Design Decision: Intentionally Thin Long-Term Memory

An earlier iteration stored free-form "experience" and "precedent" entries in a long-term memory table. This was **deliberately removed** because:

1. **Auditability:** Free-form memory entries are hard to trace to a human-reviewed source
2. **Correctability:** If the AI "remembers" wrong, correcting it requires finding and deleting specific rows — no review process
3. **Compliance fit:** Regulators expect knowledge to be managed through documented, versioned, reviewable processes

**Replacement:** Knowledge reuse goes through **retrospective case review documents → RAG ingestion**. These documents are human-readable, reviewable, versioned, and retrieved through the same cited path as policy text.

### 6.2 What Remains

| Component | Scope | Storage | Purpose |
|-----------|-------|---------|---------|
| `SessionMemory` | Per-case | Python dict (in-memory) | Conversation context, intermediate findings, pending questions |
| `LangGraph State` | Per-case | MemorySaver (in-memory checkpoint) | Full workflow state; survives `interrupt_before` pause |
| `PolicyVersionLog` | Cross-case | SQLite table | Records which policy version was active for each case; audit metadata only, never injected into prompts |

### 6.3 Knowledge Reuse Path

```
Compliance officer conducts post-case review
        │
        ▼
Writes retrospective document (case_reviews/*.md)
        │
        ▼
Document ingested into ChromaDB via same pipeline as policies
        │
        ▼
Future cases retrieve relevant precedents via search_precedent tool
        │
        ▼
All retrievals carry source citations (auditable, correctable)
```

---

## 7. Request-Info Loop

The only cycle in the graph. Handles the real-world scenario where cases need supplemental information.

### 7.1 Mechanism

1. Any node can trigger `request_info` by setting `decision = "request_more_info"`
2. `request_info_node` records **who** requested info (`info_request_stage`) and **which round** (`info_request_round`)
3. Graph pauses at `await_info` (`interrupt_before`)
4. RM provides supplemental documents; submission is updated via `update_state`
5. Graph resumes at the **requesting node** (not intake), reusing earlier results

### 7.2 Resume Routing

| Requesting Stage | Resumes At |
|-----------------|------------|
| `intake` | intake (re-check documents) |
| `identity_screening` | identity_screening |
| `edd_document_check` | edd_document_check (re-check EDD docs) |
| `enhanced_due_diligence` | enhanced_due_diligence |
| `standard_review` | standard_review |
| `human_review` | The review node (EDD or standard), not human_review itself |

### 7.3 Loop Protection

- Maximum `MAX_INFO_REQUEST_ROUNDS = 3`
- After 3 rounds: case goes directly to `human_review` with `decision = "escalate"` recommendation
- Prevents infinite loops from unresponsive submissions

### 7.4 EDD Document Gate

Before EDD, a deterministic gate checks for mandatory EDD evidence (source of wealth documentation, source of funds evidence). Three outcomes:

| Scenario | Action |
|----------|--------|
| All EDD docs present | Proceed to EDD |
| Docs missing + screening red flag (potential/confirmed sanctions or PEP) | **Proceed to EDD anyway** — gaps carried as conditions; never delay an escalation |
| Docs missing + no red flag | Request info first (avoid spending EDD effort on incomplete cases) |

---

## 8. Dashboard UI

### 8.1 Layout

Three-column Case Detail view:

| Left Column | Center Column | Right Column |
|-------------|---------------|--------------|
| Customer information | AI reasoning with SOP footnotes | Persistent decision panel |
| Documents submitted | ReAct investigation trace | Human decision controls |
| Account details | Risk scorecard | Agreement tracking |
| Screening results | | AI confidence indicator |

### 8.2 Key UI Patterns

- **Review Queue** as landing page (all 3 cases with status badges)
- **AI Recommendation ≠ Human Decision** — clearly separated UI sections
- **Policy source traceability** — clickable footnotes linking AI conclusions to specific policy sections
- **Visual Audit Timeline** — colored dots showing completed/current/pending steps
- **Conditional intake warning banner** — alerts when non-critical docs are missing
- **Agreement Rate tracking** — AI recommendation vs human decision matching

---

## 9. LLM Provider Configuration

### 9.1 Provider Abstraction

```python
# .env controls everything — zero code changes to switch
LLM_PROVIDER=openai          # or "ark"
EMBEDDING_PROVIDER=local     # or "openai"
```

| Provider | Model | Use Case |
|----------|-------|----------|
| **Ark** (Doubao) | doubao-seed-evolving | BytePlus ecosystem; cost/latency optimized for APAC |
| **OpenAI** | gpt-4o-mini | Development fallback; reliable structured output |
| **Local** (bge-small-zh-v1.5) | BAAI/bge-small-zh-v1.5 | Embeddings; zero-cost, offline, bilingual |

### 9.2 Model Wrapper

All LLM calls go through `src/models.py::chat_completion()`, a single function that wraps the OpenAI-compatible API. This enables:
- Uniform interface regardless of provider
- Single point for adding tracing/logging
- Easy swap to any OpenAI-compatible API (including Ark, which uses the same protocol)

---

## 10. Non-Functional Considerations

### 10.1 Auditability

| Requirement | Implementation |
|-------------|---------------|
| What checks were performed | `audit_trail` (append-only, reducer-protected) records every node action |
| Why a path was taken | Conditional edges are deterministic code; routing reproducible from state |
| What policies were consulted | `sources_cited` per node with document_id + version + section |
| Who approved | `interrupt_before` + `human_decision` + `human_notes` in state |
| Can it be reproduced | Checkpoint saves full state snapshot; same input + same policy version → same path |

### 10.2 Security & PII

- **All data is synthetic** — no real customer information
- `.env` with API keys excluded from git (`.gitignore`)
- LLM provider receives full submission JSON in prompts — in production, this is a cross-border data consideration (Ark API is in Beijing)
- No PII in URLs or query parameters
- No external service receives customer data beyond the LLM API

### 10.3 Persistence (Current vs Production)

| Aspect | Current (Prototype) | Production Recommendation |
|--------|--------------------|-----------------------------|
| Checkpointer | `MemorySaver` (in-memory, lost on restart) | `SqliteSaver` → `PostgresSaver` |
| Audit log | State-only (`audit_trail` list) | Append-only database table with retention policy |
| LLM tracing | None | Self-hosted Langfuse or custom `llm_calls` table |
| Thread ID | `case_id` (conflicts on re-review) | `case_id:run_number` |

### 10.4 Known Limitations

1. **MemorySaver is volatile** — cases in progress are lost on restart; `interrupt_before` cases (waiting for human review or supplemental info) cannot survive server restart
2. **search_precedent tool** calls `collection_filter` parameter not supported by ChromaDB `query()` — will fall back gracefully but precedent search is effectively regular knowledge search
3. **Decision vocabulary mismatch** — EDD prompt allows `approve_with_conditions` but database schema only accepts `approve/reject/request_more_info/escalate`
4. **Source-of-wealth/funds data** not fully threaded through all nodes that need it
5. **`expected_outcome` in test JSON** lives alongside input data — label leakage risk in LLM prompts
6. **No real sanctions/PEP API** — screening relies on pre-populated flags in test data or LLM simulation

---

## 11. Production Roadmap

### Phase 1: Prototype Hardening (Current Sprint)

- [x] Rule-based intake with LLM fallback
- [x] ReAct loops in CDD/EDD
- [x] Dashboard UI with review queue and audit timeline
- [x] 3 test cases covering happy path, blocked, and high-risk scenarios
- [ ] Persistent checkpointer (SqliteSaver)
- [ ] Audit trail written to database
- [ ] LLM call tracing

### Phase 2: Production Readiness

- Replace `MemorySaver` with `PostgresSaver`
- Integrate real sanctions/PEP screening APIs (Dow Jones, Refinitiv, ComplyAdvantage)
- Add PII masking layer before LLM calls
- Implement RBAC for analyst/officer/admin roles
- Add LLM tracing (self-hosted Langfuse) with PII redaction
- Thread ID scheme: `case_id:run_number`
- Align database schema enums with LLM output vocabulary

### Phase 3: Scale & Governance

- Multi-language support (EN / 繁中 / 简中 / Malay / Thai) for APAC coverage
- Evaluation framework with 20+ benchmark cases (see Eval Design Document)
- Automated regression testing on prompt/model changes
- Policy version change detection and re-review triggers
- Cross-case analytics dashboard for compliance managers
- Model validation framework per MAS AI Risk Management Guidelines
