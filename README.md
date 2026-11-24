# KYC Compliance Review Agent

An AI-powered agentic compliance review system for customer onboarding (KYC) at a simulated APAC financial institution. Built with **LangGraph** for workflow orchestration, **RAG** for compliance knowledge retrieval, and a **three-layer data architecture** (Database + Knowledge Base + Memory).

## Quick Start

### Prerequisites

- **Python 3.10+** (required by LangGraph)
- An **OpenAI API key** (recommended) or Volcano Engine Ark API key

### Setup (from fresh clone)

```bash
git clone https://github.com/yunfeiavawang-dev/compliance-review-agent.git
cd compliance-review-agent
```

```bash
python3 -m venv .venv && source .venv/bin/activate
```

```bash
pip install -e .
```

```bash
cp .env.template .env
```

Edit `.env` and set your API key:

```bash
# For OpenAI (recommended):
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here
EMBEDDING_PROVIDER=local

# For Ark (Doubao):
# LLM_PROVIDER=ark
# ARK_API_KEY=your-ark-key
# EMBEDDING_PROVIDER=local
```

### Initialize Data

```bash
python3 -c "from src.database.seed import seed_all; seed_all()"
```

```bash
python3 -c "from src.config import load_config; from src.knowledge.ingestion import ingest_documents; ingest_documents(load_config())"
```

### Run

```bash
streamlit run app.py
```

The app opens at `http://localhost:8501`. Select a case from the Review Queue and click **Start Review**.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                 Streamlit Dashboard UI                │
│  Review Queue │ Case Detail (3-col) │ Audit Timeline │
├─────────────────────────────────────────────────────┤
│              LangGraph Workflow Engine                │
│  intake → screening → risk → CDD/EDD → human → end  │
├──────────┬──────────────────┬────────────────────────┤
│ Database │  Knowledge Base  │       Memory           │
│ (SQLite) │ (ChromaDB + RAG) │ (Session + Policy Log) │
└──────────┴──────────────────┴────────────────────────┘
```

**Core design:** macro-structure via graph (deterministic process), micro-autonomy via LLM (reasoning within each step). See [DESIGN.md](DESIGN.md) for the full system design document.

## Node Design Patterns

| Node | Pattern | Description |
|------|---------|-------------|
| Intake | Rule-based + LLM fallback | Deterministic checks first; LLM only for edge cases |
| Screening | Single LLM call | Simulated sanctions/PEP/adverse media screening |
| Risk Assessment | Single LLM call | 5-factor scoring matrix (1-3 per factor) |
| Standard Review (CDD) | ReAct loop (max 4 rounds) | Autonomous investigation with 5 tools |
| Enhanced Due Diligence | ReAct loop (max 5 rounds) | Deeper investigation for high-risk cases |
| Human Review | Checkpoint interrupt | Workflow pauses for analyst decision |
| Decision | Single LLM call | Final summary with policy citations |

## Project Structure

```
compliance-review-agent/
├── app.py                      # Streamlit dashboard (Review Queue + Case Detail)
├── DESIGN.md                   # System design document (architecture, decisions, roadmap)
├── EXPLANATION.md              # Written explanation (use case, metrics, trade-offs)
├── src/
│   ├── config.py               # Configuration and provider abstraction
│   ├── models.py               # LLM and embedding provider wrappers
│   ├── graph/
│   │   ├── state.py            # ReviewState (TypedDict) with append-only audit trail
│   │   ├── nodes.py            # Node implementations (rules, LLM, ReAct)
│   │   ├── edges.py            # Conditional routing (all deterministic)
│   │   ├── workflow.py         # Graph assembly and compilation
│   │   └── resume.py           # Request-info loop resume logic
│   ├── knowledge/
│   │   ├── documents/          # Synthetic compliance policies (5 MD files)
│   │   │   └── case_reviews/   # Retrospective case review documents (RAG)
│   │   ├── ingestion.py        # Document chunking → ChromaDB ingestion
│   │   └── retrieval.py        # RAG retrieval with source citations
│   ├── memory/
│   │   ├── short_term.py       # Per-review session memory
│   │   └── long_term.py        # Policy version tracking (intentionally thin)
│   ├── database/
│   │   ├── schema.py           # SQLite schema (customers, reviews, audit_log, ...)
│   │   ├── crud.py             # Database operations
│   │   └── seed.py             # Synthetic data seeding
│   └── prompts/
│       └── templates.py        # Prompt templates per workflow node
├── data/
│   └── customers/              # Synthetic test cases (JSON)
│       ├── clean_case.json     # Low-risk individual — expected: approve
│       ├── edge_incomplete.json # BVI corporate, missing docs — expected: request more info
│       ├── edge_high_risk.json # Russian national, sanctions match — expected: escalate
│       ├── medium_risk_individual.json  # Medium-risk cross-border individual
│       ├── pep_declared.json   # Declared PEP with legitimate background
│       ├── expired_documents.json # Valid case but documents near expiry
│       └── corporate_clean.json # Clean corporate onboarding
└── tests/
    └── test_request_info_loop.py
```

## Test Cases

| Case | Customer | Type | Expected Path | Outcome |
|------|----------|------|---------------|---------|
| KYC-2024-001 | Chen Wei Lin | Individual | Full pipeline → Standard Review | Approve |
| KYC-2024-002 | Golden Dragon Trading | Corporate | Intake blocked (missing board resolution) | Request info |
| KYC-2024-003 | Mikhail Petrov | Individual | Full pipeline → EDD (sanctions + PEP match) | Escalate |
| KYC-2024-004 | Tanaka Yuki | Individual | Full pipeline → Standard Review | Approve |
| KYC-2024-005 | Dato' Ahmad | Individual | Full pipeline → Standard Review (declared PEP) | Approve with conditions |
| KYC-2024-006 | Sarah Chen | Individual | Conditional intake → Standard Review | Approve |
| KYC-2024-007 | TechBridge Solutions | Corporate | Full pipeline → Standard Review | Approve |

## LLM Provider Configuration

| Variable | Options | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `openai`, `ark` | LLM for chat completions |
| `EMBEDDING_PROVIDER` | `local`, `openai` | Embedding model (`local` = BAAI/bge-small-zh-v1.5, free) |
| `OPENAI_API_KEY` | — | Required if `LLM_PROVIDER=openai` |
| `ARK_API_KEY` | — | Required if `LLM_PROVIDER=ark` |

**Recommended for demo:** `LLM_PROVIDER=openai` with `gpt-4o-mini` and `EMBEDDING_PROVIDER=local`.

## Key Design Decisions

1. **LangGraph over autonomous agent** — Compliance needs auditable, deterministic process flow
2. **Rule-based + LLM hybrid** — Fast deterministic checks + LLM judgment for edge cases
3. **ReAct in CDD/EDD** — Multi-turn investigation produces richer audit trails
4. **RAG with citations** — Every AI conclusion traced to policy document + version + section
5. **Thin long-term memory** — Knowledge reuse via retrospective docs in RAG, not opaque memory
6. **Provider abstraction** — `.env` switch between Ark (BytePlus) and OpenAI, zero code changes

See [EXPLANATION.md](EXPLANATION.md) for detailed rationale and trade-offs.

## Synthetic Data

All data is synthetic. Pacific Rim Financial Group (PRFG) is fictional. Customer profiles, policies, and cases are fabricated for demonstration purposes only. No real customer data, regulated policies, or proprietary materials are used.
