"""KnowledgeHub 配置模型 — 基于 Pydantic 的类型安全配置。

所有配置项都有默认值和类型校验，通过 settings.yaml 加载。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field


# ====== 子配置模型 ======


class ProviderConfig(BaseModel):
    """通用 Provider 配置（LLM / Embedding / VectorStore / Splitter 共用）。"""

    provider: str = "openai"
    params: dict[str, Any] = Field(default_factory=dict)


class LLMConfig(ProviderConfig):
    """LLM 配置。"""

    provider: str = "openai"
    params: dict[str, Any] = Field(default_factory=lambda: {
        "model": "gpt-4o-mini",
        "temperature": 0.0,
        "max_tokens": 4096,
    })


class EmbeddingConfig(ProviderConfig):
    """Embedding 配置。"""

    provider: str = "openai"
    params: dict[str, Any] = Field(default_factory=lambda: {
        "model": "text-embedding-3-small",
    })


class VectorStoreConfig(ProviderConfig):
    """VectorStore 配置。"""

    provider: str = "chroma"
    params: dict[str, Any] = Field(default_factory=lambda: {
        "persist_path": "./data/vector_db",
        "collection_name": "default",
    })


class SplitterConfig(ProviderConfig):
    """Splitter 配置。"""

    provider: str = "langchain_recursive"
    params: dict[str, Any] = Field(default_factory=lambda: {
        "chunk_size": 1000,
        "chunk_overlap": 200,
        "separators": ["\n## ", "\n### ", "\n\n", "\n", " "],
    })


class RerankerStageConfig(BaseModel):
    """重排阶段配置（coarse / fine）。"""

    provider: str = "none"
    params: dict[str, Any] = Field(default_factory=dict)


class RerankerConfig(BaseModel):
    """Reranker 配置。"""

    coarse: RerankerStageConfig = Field(default_factory=RerankerStageConfig)
    fine: RerankerStageConfig = Field(default_factory=RerankerStageConfig)


class BM25RetrievalConfig(BaseModel):
    """BM25 检索配置。"""

    enabled: bool = True
    top_k: int = 20


class DenseRetrievalConfig(BaseModel):
    """Dense 检索配置。"""

    top_k: int = 20


class FusionConfig(BaseModel):
    """RRF 融合配置。"""

    method: str = "rrf"  # rrf | weighted
    k: int = 60
    top_n: int = 15


class RetrievalConfig(BaseModel):
    """检索配置。"""

    bm25: BM25RetrievalConfig = Field(default_factory=BM25RetrievalConfig)
    dense: DenseRetrievalConfig = Field(default_factory=DenseRetrievalConfig)
    fusion: FusionConfig = Field(default_factory=FusionConfig)
    final_top_k: int = 5
    query_rewrite: bool = False


class ImageProcessingConfig(BaseModel):
    """图片处理配置。"""

    enabled: bool = True
    max_images_per_doc: int = 50


class EnhancementConfig(BaseModel):
    """Chunk 增强配置。"""

    enabled: bool = True
    rewrite: bool = False
    inject_metadata: bool = True
    inject_image_desc: bool = True


class IngestionConfig(BaseModel):
    """摄取配置。"""

    watch_dir: str = "./data/raw"
    image_processing: ImageProcessingConfig = Field(default_factory=ImageProcessingConfig)
    enhancement: EnhancementConfig = Field(default_factory=EnhancementConfig)


class MCPConfig(BaseModel):
    """MCP 配置。"""

    server_name: str = "knowledge-hub"
    server_version: str = "1.0.0"


class ObservabilityConfig(BaseModel):
    """可观测性配置。"""

    log_level: str = "INFO"
    log_dir: str = "./logs"
    trace_enabled: bool = True
    dashboard_port: int = 8501


class StorageConfig(BaseModel):
    """存储配置。"""

    sqlite_path: str = "./data/knowledge_hub.db"
    bm25_index_path: str = "./data/bm25_index"


class EvaluationConfig(BaseModel):
    """评估配置。"""

    framework: str = "custom"  # custom | ragas
    metrics: list[str] = Field(default_factory=lambda: ["hit_rate", "mrr", "context_precision"])
    eval_dataset_path: str = "./data/eval/eval_dataset.json"


# ====== 主配置模型 ======


class Settings(BaseModel):
    """KnowledgeHub 主配置。

    通过 `Settings.from_yaml("settings.yaml")` 加载。
    """

    llm: LLMConfig = Field(default_factory=LLMConfig)
    vision_llm: LLMConfig = Field(default_factory=LLMConfig)
    rerank_llm: LLMConfig = Field(default_factory=LLMConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    reranker: RerankerConfig = Field(default_factory=RerankerConfig)
    vectorstore: VectorStoreConfig = Field(default_factory=VectorStoreConfig)
    splitter: SplitterConfig = Field(default_factory=SplitterConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    ingestion: IngestionConfig = Field(default_factory=IngestionConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    evaluation: EvaluationConfig = Field(default_factory=EvaluationConfig)

    @classmethod
    def from_yaml(cls, path: str = "settings.yaml") -> "Settings":
        """从 YAML 文件加载配置，自动展开 ${ENV_VAR} 环境变量引用。

        Args:
            path: YAML 配置文件路径。

        Returns:
            Settings 实例。

        Raises:
            FileNotFoundError: 配置文件不存在。
            pydantic.ValidationError: 配置校验失败。
        """
        import os
        import yaml

        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        if raw is None:
            raw = {}

        # 递归展开 ${ENV_VAR}
        expanded = cls._expand_env(raw)
        return cls(**expanded)

    @staticmethod
    def _expand_env(obj: Any) -> Any:
        """递归展开对象中的 ${ENV_VAR} 环境变量引用。

        Args:
            obj: 任意嵌套的字典/列表/字符串。

        Returns:
            展开后的对象。
        """
        import os

        if isinstance(obj, str):
            if obj.startswith("${") and obj.endswith("}"):
                env_key = obj[2:-1]
                return os.environ.get(env_key, "")
            return obj
        elif isinstance(obj, dict):
            return {k: Settings._expand_env(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [Settings._expand_env(v) for v in obj]
        return obj
