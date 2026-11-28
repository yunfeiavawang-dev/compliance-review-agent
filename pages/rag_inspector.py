"""RAG Inspector — standalone page for exploring the compliance knowledge base.

Launch:  streamlit run pages/rag_inspector.py
Or access via the multi-page app sidebar when running the main app.
"""

import sys
from pathlib import Path

import streamlit as st

# Allow imports from project root when run standalone
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import load_config
from src.knowledge.retrieval import ComplianceKnowledgeBase
from src.models import get_llm_client, chat_completion

# --- Page Config ---
st.set_page_config(
    page_title="RAG Inspector",
    page_icon="🔎",
    layout="wide",
)

st.markdown("""
<style>
  .chunk-card {
      background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 8px;
      padding: 14px 16px; margin-bottom: 10px;
  }
  .chunk-score {
      display: inline-block; padding: 2px 8px; border-radius: 10px;
      font-size: 12px; font-weight: 600;
  }
  .score-high { background: #d4edda; color: #155724; }
  .score-mid  { background: #fff3cd; color: #856404; }
  .score-low  { background: #f8d7da; color: #721c24; }
  .meta-tag {
      display: inline-block; background: #e9ecef; padding: 1px 7px;
      border-radius: 4px; font-size: 11px; color: #495057; margin-right: 4px;
  }
  .doc-row {
      display: flex; align-items: center; gap: 10px; padding: 8px 0;
      border-bottom: 1px solid #f0f1f2; font-size: 13px;
  }
</style>
""", unsafe_allow_html=True)


# --- Init ---
@st.cache_resource
def _config():
    return load_config()

@st.cache_resource
def _kb():
    return ComplianceKnowledgeBase(_config())


config = _config()
kb = _kb()


# --- Header ---
st.title("🔎 RAG Inspector")
st.caption("Browse ingested documents, test retrieval queries, and compare RAG-grounded answers against the LLM alone.")

# --- Metrics row ---
all_meta = kb.collection.get(include=["metadatas"])["metadatas"]
doc_index: dict[str, dict] = {}
for m in all_meta:
    did = m.get("document_id", m.get("source_file", "unknown"))
    if did not in doc_index:
        doc_index[did] = {
            "title": m.get("title", did),
            "version": m.get("version", "?"),
            "chunks": 0,
            "source": m.get("source_file", ""),
        }
    doc_index[did]["chunks"] += 1

col_m1, col_m2, col_m3 = st.columns(3)
col_m1.metric("Documents", len(doc_index))
col_m2.metric("Total Chunks", len(all_meta))
col_m3.metric("Embedding Model", config.embedding.provider)

st.divider()

# --- Tabs ---
tab_query, tab_docs, tab_compare = st.tabs(
    ["🔍 Query Playground", "📄 Document Index", "⚖️ RAG vs LLM"]
)


# ═══════════════════════════════════════════════
# TAB 1: Query Playground
# ═══════════════════════════════════════════════
with tab_query:
    st.subheader("Query the Knowledge Base")
    query = st.text_input(
        "Enter a compliance question or keyword:",
        placeholder="e.g. What is the PEP cooling-off period?",
        key="rag_query",
    )
    col_n, col_t = st.columns([1, 2])
    with col_n:
        n_results = st.slider("Results to retrieve", 1, 10, 5, key="n_results")
    with col_t:
        threshold = st.slider("Min relevance score", 0.0, 1.0, 0.0, 0.05, key="threshold")

    if query:
        results = kb.query(query, n_results=n_results)
        if threshold > 0:
            results = [r for r in results if r["relevance_score"] >= threshold]

        if not results:
            st.info("No results above the relevance threshold.")
        else:
            st.markdown(f"**{len(results)} chunks retrieved**")
            for i, r in enumerate(results):
                score = r["relevance_score"]
                score_cls = "score-high" if score >= 0.5 else ("score-mid" if score >= 0.3 else "score-low")
                with st.expander(
                    f"[{score:.3f}]  {r['source']} — {r['section']}",
                    expanded=(i == 0),
                ):
                    st.markdown(
                        f'<span class="chunk-score {score_cls}">{score:.3f}</span> '
                        f'<span class="meta-tag">doc: {r["document_id"]}</span>'
                        f'<span class="meta-tag">v{r["version"]}</span>'
                        f'<span class="meta-tag">{r["section"]}</span>',
                        unsafe_allow_html=True,
                    )
                    st.text(r["text"])


# ═══════════════════════════════════════════════
# TAB 2: Document Index
# ═══════════════════════════════════════════════
with tab_docs:
    st.subheader("Ingested Documents")
    st.caption("All policy documents currently in the vector store.")

    search_filter = st.text_input("Filter by title or ID:", key="doc_filter")

    for did, info in sorted(doc_index.items(), key=lambda x: x[1]["title"]):
        title = info["title"]
        if search_filter and search_filter.lower() not in title.lower() and search_filter.lower() not in did.lower():
            continue
        st.markdown(
            f'<div class="doc-row">'
            f'<span style="font-weight:600;min-width:220px;">{title}</span>'
            f'<span class="meta-tag">{did}</span>'
            f'<span class="meta-tag">v{info["version"]}</span>'
            f'<span class="meta-tag">{info["chunks"]} chunks</span>'
            f'<span style="font-size:11px;color:#8f959e;">{info["source"]}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.divider()
    st.caption(f"{len(doc_index)} documents · {len(all_meta)} chunks total")


# ═══════════════════════════════════════════════
# TAB 3: RAG vs LLM comparison
# ═══════════════════════════════════════════════
with tab_compare:
    st.subheader("RAG-Grounded Answer vs Raw LLM")
    st.caption(
        "Ask the same question to both: (1) the LLM with retrieved policy sources, "
        "and (2) the LLM alone. Compare to see how grounding improves accuracy."
    )

    cmp_query = st.text_input(
        "Question:",
        placeholder="e.g. When must EDD be applied for PEP customers?",
        key="cmp_query",
    )
    cmp_n = st.slider("Sources to retrieve", 1, 8, 3, key="cmp_n")

    if cmp_query and st.button("Compare", type="primary", key="cmp_go"):
        results = kb.query(cmp_query, n_results=cmp_n)

        sources_text = "\n\n---\n\n".join(
            f"[Source: {r['source']} v{r['version']} — {r['section']}]\n{r['text']}"
            for r in results
        )

        rag_messages = [
            {
                "role": "system",
                "content": (
                    "Answer using ONLY the provided policy sources. "
                    "Cite the source for each claim using [Source: ...] notation."
                ),
            },
            {"role": "user", "content": f"Sources:\n{sources_text}\n\nQuestion: {cmp_query}"},
        ]

        raw_messages = [
            {
                "role": "system",
                "content": "Answer the following compliance question to the best of your knowledge.",
            },
            {"role": "user", "content": cmp_query},
        ]

        col_rag, col_raw = st.columns(2)

        with col_rag:
            st.markdown("#### 📚 With RAG Sources")
            try:
                client = get_llm_client(config)
                answer = chat_completion(client, config.llm.model, rag_messages, max_tokens=1024)
                st.markdown(answer)
            except Exception as e:
                st.error(f"LLM error: {e}")

            with st.expander("Retrieved sources"):
                for r in results:
                    st.markdown(
                        f'<span class="meta-tag">[{r["relevance_score"]:.2f}]</span>'
                        f'<span class="meta-tag">{r["source"]} v{r["version"]}</span>'
                        f' {r["section"]}',
                        unsafe_allow_html=True,
                    )
                    st.text(r["text"][:300])
                    st.divider()

        with col_raw:
            st.markdown("#### 🧠 Raw LLM (no sources)")
            try:
                client = get_llm_client(config)
                answer_raw = chat_completion(client, config.llm.model, raw_messages, max_tokens=1024)
                st.markdown(answer_raw)
            except Exception as e:
                st.error(f"LLM error: {e}")
