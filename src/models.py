"""LLM and embedding provider abstraction."""

import os
import time
from openai import OpenAI, APITimeoutError, APIConnectionError
from src.config import AppConfig

# Ark (Volcengine) API must bypass the local proxy to reach China endpoints.
_no_proxy = os.environ.get("NO_PROXY", "")
if "volces.com" not in _no_proxy:
    os.environ["NO_PROXY"] = f"{_no_proxy},volces.com,.volces.com" if _no_proxy else "volces.com,.volces.com"


def get_llm_client(config: AppConfig) -> OpenAI:
    """Return an OpenAI-compatible client for the configured LLM provider."""
    return OpenAI(
        api_key=config.llm.api_key,
        base_url=config.llm.base_url,
        timeout=300.0,
    )


def chat_completion(client: OpenAI, model: str, messages: list[dict], temperature: float = 0.3, max_tokens: int = 4096) -> str:
    """Run a chat completion and return the assistant message content."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content
            usage = response.usage
            if usage and _token_callback:
                _token_callback(usage.prompt_tokens or 0, usage.completion_tokens or 0)
            return content
        except (APITimeoutError, APIConnectionError) as e:
            if attempt < max_retries - 1:
                wait = 5 * (attempt + 1)
                print(f"  [retry {attempt+1}/{max_retries}] {type(e).__name__}, waiting {wait}s...")
                time.sleep(wait)
            else:
                raise


_token_callback = None


def set_token_callback(callback):
    """Register a callback(input_tokens, output_tokens) for every LLM call."""
    global _token_callback
    _token_callback = callback


_embedding_model = None


def get_embedding_function(config: AppConfig):
    """Return an embedding function compatible with ChromaDB."""
    if config.embedding.provider == "local":
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
        return SentenceTransformerEmbeddingFunction(
            model_name=config.embedding.model_name,
        )
    elif config.embedding.provider == "ark":
        from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
        return OpenAIEmbeddingFunction(
            api_key=config.embedding.api_key,
            model_name=config.embedding.model_name,
            api_base=config.embedding.base_url,
        )
    else:
        from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
        return OpenAIEmbeddingFunction(
            api_key=config.embedding.api_key or config.llm.api_key,
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
    elif config.embedding.provider == "ark":
        client = OpenAI(
            api_key=config.embedding.api_key,
            base_url=config.embedding.base_url,
            timeout=120.0,
        )
        response = client.embeddings.create(
            model=config.embedding.model_name,
            input=texts,
        )
        return [item.embedding for item in response.data]
    else:
        client = get_llm_client(config)
        response = client.embeddings.create(
            model=config.embedding.model_name,
            input=texts,
        )
        return [item.embedding for item in response.data]
