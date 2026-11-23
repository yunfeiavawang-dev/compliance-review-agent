"""LLM and embedding provider abstraction."""

from openai import OpenAI
from src.config import AppConfig


def get_llm_client(config: AppConfig) -> OpenAI:
    """Return an OpenAI-compatible client for the configured LLM provider."""
    return OpenAI(
        api_key=config.llm.api_key,
        base_url=config.llm.base_url,
        timeout=60.0,
    )


def chat_completion(client: OpenAI, model: str, messages: list[dict], temperature: float = 0.3, max_tokens: int = 4096) -> str:
    """Run a chat completion and return the assistant message content."""
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content


_embedding_model = None


def get_embedding_function(config: AppConfig):
    """Return an embedding function compatible with ChromaDB."""
    if config.embedding.provider == "local":
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
        return SentenceTransformerEmbeddingFunction(
            model_name=config.embedding.model_name,
        )
    else:
        from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
        return OpenAIEmbeddingFunction(
            api_key=config.llm.api_key,
            model_name=config.embedding.model_name,
        )


def embed_text(config: AppConfig, texts: list[str]) -> list[list[float]]:
    """Embed a list of texts using the configured embedding provider."""
    global _embedding_model
    if config.embedding.provider == "local":
        if _embedding_model is None:
            from sentence_transformers import SentenceTransformer
            _embedding_model = SentenceTransformer(config.embedding.model_name)
        return _embedding_model.encode(texts).tolist()
    else:
        client = get_llm_client(config)
        response = client.embeddings.create(
            model=config.embedding.model_name,
            input=texts,
        )
        return [item.embedding for item in response.data]
