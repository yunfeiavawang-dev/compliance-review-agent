"""Configuration loading and model provider abstraction."""

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class LLMConfig:
    provider: str = "ark"
    model: str = "doubao-seed-evolving"
    base_url: str = ""
    api_key: str = ""
    temperature: float = 0.3
    max_tokens: int = 4096


@dataclass
class EmbeddingConfig:
    provider: str = "local"
    model_name: str = "BAAI/bge-small-zh-v1.5"
    dimension: int = 512
    base_url: str = ""
    api_key: str = ""


@dataclass
class DatabaseConfig:
    path: str = "data/compliance.db"


@dataclass
class ChromaConfig:
    persist_dir: str = ".chroma"
    collection_name: str = "compliance_policies"


@dataclass
class AppConfig:
    llm: LLMConfig = field(default_factory=LLMConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    chroma: ChromaConfig = field(default_factory=ChromaConfig)


def load_config() -> AppConfig:
    llm_provider = os.getenv("LLM_PROVIDER", "ark")

    if llm_provider == "ark":
        llm = LLMConfig(
            provider="ark",
            model=os.getenv("ARK_MODEL", "doubao-seed-evolving"),
            base_url=os.getenv("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3"),
            api_key=os.getenv("ARK_API_KEY", ""),
            temperature=0.3,
        )
    else:
        llm = LLMConfig(
            provider="openai",
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            base_url="https://api.openai.com/v1",
            api_key=os.getenv("OPENAI_API_KEY", ""),
            temperature=0.3,
        )

    embedding_provider = os.getenv("EMBEDDING_PROVIDER", "local")
    if embedding_provider == "ark":
        embedding = EmbeddingConfig(
            provider="ark",
            model_name=os.getenv("ARK_EMBEDDING_ENDPOINT_ID", ""),
            dimension=2560,
            base_url=os.getenv("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3"),
            api_key=os.getenv("ARK_API_KEY", ""),
        )
    elif embedding_provider == "local":
        embedding = EmbeddingConfig(
            provider="local",
            model_name="BAAI/bge-small-zh-v1.5",
            dimension=512,
        )
    else:
        embedding = EmbeddingConfig(
            provider="openai",
            model_name=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
            dimension=1536,
            api_key=os.getenv("OPENAI_API_KEY", ""),
        )

    return AppConfig(llm=llm, embedding=embedding)
