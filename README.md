# KYC Compliance Review Agent

An AI-powered agentic compliance review system for customer onboarding (KYC) at a simulated APAC financial institution. Built with **LangGraph** for workflow orchestration, **RAG** for compliance knowledge retrieval, and a **3-layer data architecture** (Database + Knowledge Base + Memory).

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                  Streamlit Demo UI                    │
├─────────────────────────────────────────────────────┤
│              LangGraph Workflow Engine                │
│  intake → screening → risk assessment → review →     │
│  human-in-the-loop → decision                        │
├──────────┬──────────────────┬────────────────────────┤
│ Database │  Knowledge Base  │       Memory           │
│ (SQLite) │ (ChromaDB + RAG) │ (Short-term + Long)    │
│ Customer │ Compliance       │ Session state,          │
│ profiles,│ policies,        │ cross-review            │
│ reviews, │ regulations,     │ patterns,               │
│ decisions│ handbooks        │ analyst prefs            │
└──────────┴──────────────────┴────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.9+
- An OpenAI API key (or Volcano Engine Ark API key)

### Setup

```bash
# Clone the repository
git clone https://github.com/yunfeiavawang-dev/compliance-review-agent.git
cd compliance-review-agent

# Install dependencies
pip install langgraph langchain langchain-openai langchain-community chromadb sentence-transformers streamlit python-dotenv openai pydantic

# Configure environment
cp .env.template .env
# Edit .env with your API keys
```

### Initialize Data

```bash
# Seed the database with synthetic customer data
python -c "import sys; sys.path.insert(0, '.'); from src.database.seed import seed_all; seed_all()"

# Ingest compliance documents into ChromaDB
python -c "import sys; sys.path.insert(0, '.'); from src.config import load_config; from src.knowledge.ingestion import ingest_documents; ingest_documents(load_config())"
```

### Run the Demo

```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`. Select a sample case from the sidebar and click "Start Review".

## LLM Provider Configuration

The system supports multiple LLM providers via the `.env` file:

| Variable | Options | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `openai`, `ark` | LLM provider for chat completions |
| `EMBEDDING_PROVIDER` | `local`, `openai` | Embedding provider (local uses BAAI/bge-small-zh-v1.5) |

**Recommended:** Use `LLM_PROVIDER=openai` with `gpt-4o-mini` for reliable results. Ark (doubao-seed-evolving) is also supported but requires network access to `ark.cn-beijing.volces.com`.

## Project Structure

```
compliance-review-agent/
├── app.py                      # Streamlit demo application
├── src/
│   ├── config.py               # Configuration and provider abstraction
│   ├── models.py               # LLM and embedding provider wrappers
│   ├── graph/
│   │   ├── state.py            # LangGraph state schema (TypedDict)
│   │   ├── nodes.py            # Graph node implementations
│   │   ├── edges.py            # Conditional routing logic
│   │   └── workflow.py         # Graph assembly and compilation
│   ├── knowledge/
│   │   ├── documents/          # Synthetic compliance policy documents
│   │   │   ├── kyc_policy.md
│   │   │   ├── aml_handbook.md
│   │   │   ├── cdd_guidelines.md
│   │   │   ├── sanctions_screening.md
│   │   │   └── risk_rating_matrix.md
│   │   ├── ingestion.py        # Document chunking and ChromaDB ingestion
│   │   └── retrieval.py        # RAG retrieval with source citations
│   ├── memory/
│   │   ├── short_term.py       # Per-review session memory
│   │   └── long_term.py        # Cross-review accumulated experience
│   ├── database/
│   │   ├── schema.py           # SQLite schema definition
│   │   ├── crud.py             # Database operations
│   │   └── seed.py             # Synthetic data seeding
│   └── prompts/
│       └── templates.py        # Prompt templates per workflow node
├── data/
│   └── customers/              # Synthetic test cases
│       ├── clean_case.json     # Standard low-risk individual
│       ├── edge_incomplete.json # Corporate with missing documents
│       └── edge_high_risk.json # Individual with sanctions/PEP flags
└── tests/
```

## Test Cases

| Case | Customer | Type | Expected Path | Expected Outcome |
|------|----------|------|---------------|-----------------|
| KYC-2024-001 | Chen Wei Lin | Individual | Intake → Screening → Risk(Low) → Standard Review → Approve | Approve |
| KYC-2024-002 | Golden Dragon Trading | Corporate | Intake → Request More Info | Request more info (missing docs) |
| KYC-2024-003 | Mikhail Petrov | Individual | Intake → Screening → Risk(High) → EDD → Request More Info | Escalate / Request more info |

## Key Design Decisions

- **LangGraph** for workflow orchestration: stateful directed graph with conditional branching, human-in-the-loop via checkpoint interrupts
- **3-layer data architecture**: structured data in SQLite, unstructured knowledge in ChromaDB/RAG, agent experience in memory
- **RAG with source citations**: every policy-based conclusion traced back to specific document, version, and section
- **Provider abstraction**: config-based switching between Ark and OpenAI without code changes

## Synthetic Data

All data is synthetic. The institution "Pacific Rim Financial Group" (PRFG) is fictional. Customer profiles, policies, and cases are fabricated for demonstration purposes only.
