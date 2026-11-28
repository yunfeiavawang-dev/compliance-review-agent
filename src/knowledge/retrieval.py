"""RAG retrieval for the compliance knowledge base."""

import chromadb
from src.config import AppConfig
from src.models import get_embedding_function


class ComplianceKnowledgeBase:
    """Retrieve relevant compliance knowledge from the vector store."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.client = chromadb.PersistentClient(path=config.chroma.persist_dir)
        self.embedding_fn = get_embedding_function(config)
        self.collection = self.client.get_or_create_collection(
            name=config.chroma.collection_name,
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )

    def query(self, question: str, n_results: int = 5, where: dict = None) -> list[dict]:
        """Query the knowledge base and return relevant chunks with sources."""
        kwargs = {
            "query_texts": [question],
            "n_results": min(n_results, self.collection.count()),
        }
        if where:
            kwargs["where"] = where

        results = self.collection.query(**kwargs)

        retrieved = []
        for i in range(len(results["ids"][0])):
            metadata = results["metadatas"][0][i]
            retrieved.append({
                "text": results["documents"][0][i],
                "source": metadata.get("title", metadata.get("source_file", "unknown")),
                "document_id": metadata.get("document_id", "unknown"),
                "version": metadata.get("version", "unknown"),
                "section": metadata.get("section", ""),
                "relevance_score": 1 - results["distances"][0][i],
            })

        return retrieved

    def query_by_topic(self, topic: str, n_results: int = 3) -> list[dict]:
        """Query for a specific compliance topic."""
        return self.query(topic, n_results=n_results)

    _STEP_QUERIES = {
        "intake": "document completeness check requirements for KYC onboarding submission",
        "identity_screening": "sanctions screening PEP watchlist verification procedures",
        "risk_assessment": "customer risk rating scoring methodology matrix factors",
        "standard_review": "standard due diligence CDD procedures requirements",
        "enhanced_due_diligence": "enhanced due diligence EDD requirements source of wealth verification",
        "human_review": "review decision approval escalation procedures",
        "decision": "KYC decision approve reject escalation criteria",
    }

    _STEP_BOOST_KEYWORDS: dict[str, list[str]] = {
        "intake": ["document", "completeness", "submission", "onboarding", "verification"],
        "identity_screening": ["sanctions", "pep", "screening", "watchlist", "adverse media"],
        "risk_assessment": ["risk", "rating", "score", "matrix", "factor"],
        "standard_review": ["due diligence", "cdd", "standard", "review", "procedures"],
        "enhanced_due_diligence": ["edd", "enhanced", "source of wealth", "source of funds", "beneficial ownership"],
        "human_review": ["approval", "escalation", "decision", "override"],
        "decision": ["decision", "approve", "reject", "escalation", "criteria"],
    }

    def select_context(
        self,
        question: str,
        step_name: str,
        n_results: int = 5,
        relevance_threshold: float = 0.3,
        max_chars: int = 3000,
    ) -> list[dict]:
        """Explicit context selection with relevance gating, step-aware boosting, and budget cap."""
        candidates = self.query(question, n_results=n_results)

        # Relevance gate
        candidates = [c for c in candidates if c.get("relevance_score", 0) >= relevance_threshold]

        # Step-aware boost
        boost_keywords = self._STEP_BOOST_KEYWORDS.get(step_name, [])
        for c in candidates:
            section = (c.get("section") or "").lower()
            if any(kw in section for kw in boost_keywords):
                c["relevance_score"] = c.get("relevance_score", 0) + 0.1

        candidates.sort(key=lambda c: c.get("relevance_score", 0), reverse=True)

        # Budget cap — keep full chunks, stop when total exceeds max_chars
        selected = []
        total_chars = 0
        for c in candidates:
            chunk_len = len(c.get("text", ""))
            if total_chars + chunk_len > max_chars and selected:
                break
            selected.append(c)
            total_chars += chunk_len

        return selected

    def get_policy_for_step(self, step_name: str, context: str = "", n_results: int = 3) -> list[dict]:
        """Retrieve policies relevant to a specific review step."""
        query_text = self._STEP_QUERIES.get(step_name, step_name)
        if context:
            query_text = f"{query_text}. Context: {context}"

        return self.select_context(query_text, step_name, n_results=n_results)

    def format_sources_for_prompt(self, results: list[dict], max_chars: int = 3000) -> str:
        """Format retrieved results as a context block for LLM prompts."""
        if not results:
            return "No relevant compliance policies found."

        output = []
        total_chars = 0

        for r in results:
            source_line = f"[Source: {r['source']} v{r['version']} — {r['section']}]"
            block = f"{source_line}\n{r['text']}"

            if total_chars + len(block) > max_chars:
                break

            output.append(block)
            total_chars += len(block)

        return "\n\n---\n\n".join(output)

    def count(self) -> int:
        return self.collection.count()
