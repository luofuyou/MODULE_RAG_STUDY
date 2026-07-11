## 3. 技术选型与设计

### 3.1 技术栈总览

| 层级 | 技术选型 | 说明 |
|------|----------|------|
| 语言 | Python 3.11+ | async/await、类型注解、match-case |
| 异步框架 | asyncio | 全链路异步 |
| 配置管理 | Pydantic Settings + YAML | 类型安全的配置 |
| LLM 调用 | openai SDK（兼容 Azure/Ollama/DeepSeek） | 统一接口 |
| 向量库 | chromadb | 本地嵌入式 |
| 稀疏检索 | rank_bm25 | 纯 Python BM25 |
| 文档解析 | markitdown（微软） | PDF→Markdown |
| 图片处理 | Pillow + Vision LLM | Image-to-Text |
| 重排模型 | sentence-transformers | Cross-Encoder |
| 评估 | ragas + 自定义 | 双轨评估 |
| MCP | mcp Python SDK | 官方 SDK |
| Dashboard | Streamlit | 本地可视化 |
| 持久化 | SQLite（内置） | 元数据 + Trace |
| 测试 | pytest + pytest-asyncio | TDD |
| 日志 | structlog → JSONL | 结构化日志 |

### 3.2 RAG 核心流水线设计

#### 3.2.1 Ingestion Pipeline（数据摄取流水线）

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Ingestion Pipeline                            │
│                                                                      │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐       │
│  │ File     │───▶│ SHA256   │───▶│ Load     │───▶│ Image    │       │
│  │ Discovery│    │ Check    │    │ (MarkItDown)│  │ Extract  │       │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘       │
│       │               │                │               │            │
│    scan data/    skip if exists    PDF→Markdown   extract images    │
│                                                                      │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐       │
│  │ Image    │───▶│ Semantic │───▶│ LLM      │───▶│ Dual     │       │
│  │ Desc     │    │ Chunking │    │ Enhance  │    │ Embed    │       │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘       │
│       │               │                │               │            │
│  Vision LLM     RecursiveSplit +    metadata +    dense emb +       │
│  → description   markdown aware    image desc     BM25 token        │
│                                                                      │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                       │
│  │ Chroma   │───▶│ BM25     │───▶│ SQLite   │                       │
│  │ Upsert   │    │ Index    │    │ Record   │                       │
│  └──────────┘    └──────────┘    └──────────┘                       │
│       │               │                │                            │
│  store vectors   build inverted    record metadata,                │
│  + metadata      index (persist)   checksum, chunks                │
│                                                                      │
│  ┌──────────────────────────────────────────────┐                   │
│  │           Trace Logger (JSONL)                │                   │
│  └──────────────────────────────────────────────┘                   │
└─────────────────────────────────────────────────────────────────────┘
```

**详细步骤说明**:

| 步骤 | 组件 | 输入 | 输出 | 关键逻辑 |
|------|------|------|------|----------|
| 1 | FileDiscovery | `data/raw/` 目录 | 文件路径列表 | 递归扫描 `.pdf`, `.md`, `.txt` |
| 2 | ChecksumCheck | 文件路径 | `skip: bool` | SHA256 计算并查询 SQLite，命中则跳过 |
| 3 | Loader | 文件路径 | Markdown 文本 + 图片列表 | MarkItDown 解析 PDF；Markdown 直接读取 |
| 4 | ImageExtract | Markdown 文本 | 图片列表 | 提取 `![](image.png)` 引用 |
| 5 | ImageDescription | 图片列表 | `{image_id: description}` | Vision LLM 生成描述，缓存结果 |
| 6 | SemanticChunker | Markdown 文本 | `List[Chunk]` | RecursiveCharacterTextSplitter + Markdown header 感知 |
| 7 | ContextInjector | `List[Chunk]` + 图片描述 | `List[Chunk]`（增强后） | 注入 metadata、图片描述到最近 chunk |
| 8 | LLMEnhancer | `List[Chunk]` | `List[Chunk]`（增强后） | 可选：LLM 重写 chunk 提升检索质量 |
| 9 | DualEmbedder | `List[Chunk]` | `List[EmbeddingResult]` | Dense embedding + BM25 分词 |
| 10 | ChromaUpsert | `List[EmbeddingResult]` | `collection_size` | 向量 + metadata 写入 Chroma |
| 11 | BM25IndexBuilder | `List[Chunk]` | `index_size` | 构建 BM25 倒排索引并持久化 |
| 12 | SQLiteRecord | 摄取元数据 | `record_id` | 写入文件记录、chunk 统计 |
| 13 | TraceLogger | 全链路事件 | `logs/ingestion.jsonl` | 结构化 JSON 日志 |

**Chunk 数据结构**:

```python
@dataclass
class Chunk:
    chunk_id: str               # UUID
    content: str                # 原始文本
    enhanced_content: str       # 增强后文本（含图片描述、元数据前缀）
    metadata: ChunkMetadata     # 元数据
    tokens: int                 # token 数量

@dataclass
class ChunkMetadata:
    source_file: str            # 源文件路径
    source_type: str            # pdf / md / txt
    doc_title: str              # 文档标题
    page_number: int | None     # 页码（PDF）
    section_path: str           # 章节路径，如 "第一章 > 1.2 安装"
    chunk_index: int            # chunk 在文档中的序号
    total_chunks: int           # 文档总 chunk 数
    sha256: str                 # 源文件 SHA256
    image_descriptions: list[str]  # 关联图片描述列表
    created_at: str             # ISO 时间戳
```

#### 3.2.2 Retrieval Pipeline（检索流水线）

```
┌─────────────────────────────────────────────────────────────────────┐
│                       Retrieval Pipeline                             │
│                                                                      │
│                      ┌──────────┐                                    │
│                      │  Query   │                                    │
│                      │  Input   │                                    │
│                      └────┬─────┘                                    │
│                           │                                          │
│                    ┌──────▼──────┐                                   │
│                    │   Query     │                                   │
│                    │  Rewrite    │  (可选) LLM 改写查询扩展召回       │
│                    └──────┬──────┘                                   │
│                           │                                          │
│              ┌────────────┼────────────┐                             │
│              ▼            ▼            │                             │
│      ┌──────────┐  ┌──────────┐       │                             │
│      │  BM25    │  │  Dense   │       │                             │
│      │ Retrieve │  │ Retrieve │       │                             │
│      │ Top-K₁=20│  │ Top-K₁=20│       │                             │
│      └────┬─────┘  └────┬─────┘       │                             │
│           │             │             │                             │
│           └──────┬──────┘             │                             │
│                  ▼                    │                             │
│          ┌──────────────┐             │                             │
│          │  RRF Fusion  │             │                             │
│          │  → Top-K₂=15 │             │                             │
│          └──────┬───────┘             │                             │
│                 │                     │                             │
│          ┌──────▼───────┐             │                             │
│          │ Cross-Encoder│             │                             │
│          │ Coarse Rerank│             │                             │
│          │ → Top-K₃=10  │             │                             │
│          └──────┬───────┘             │                             │
│                 │                     │                             │
│          ┌──────▼───────┐             │                             │
│          │  LLM Rerank  │             │                             │
│          │  Fine Rerank │             │                             │
│          │ → Final K=5  │             │                             │
│          └──────┬───────┘             │                             │
│                 │                     │                             │
│          ┌──────▼───────┐             │                             │
│          │   Context    │             │                             │
│          │  Assembly    │  组装最终上下文                             │
│          └──────┬───────┘             │                             │
│                 │                     │                             │
│          ┌──────▼───────┐             │                             │
│          │   LLM        │             │                             │
│          │  Generation  │  生成最终回答                               │
│          └──────┬───────┘             │                             │
│                 │                     │                             │
│          ┌──────▼───────┐             │                             │
│          │   Response   │             │                             │
│          │   + Trace    │             │                             │
│          └──────────────┘             │                             │
└─────────────────────────────────────────────────────────────────────┘
```

**详细步骤说明**:

| 步骤 | 组件 | 输入 | 输出 | 关键逻辑 |
|------|------|------|------|----------|
| 1 | QueryInput | 用户 query | `Query` 对象 | 标准化、校验 |
| 2 | QueryRewrite | `Query` | `List[Query]` | 可选：LLM 生成同义/扩展查询 |
| 3a | BM25Retrieve | `Query` | `List[RetrievalResult]` (Top-20) | rank_bm25 库，从持久化索引查询 |
| 3b | DenseRetrieve | `Query` | `List[RetrievalResult]` (Top-20) | Chroma cosine similarity |
| 4 | RRFFusion | 两个列表 | `List[RetrievalResult]` (Top-15) | `score = Σ 1/(k + rank_i)`, k=60 |
| 5 | CrossEncoderRerank | `List[RetrievalResult]` | `List[RetrievalResult]` (Top-10) | sentence-transformers 模型 |
| 6 | LLMRerank | `List[RetrievalResult]` | `List[RetrievalResult]` (Top-5) | LLM 对每个 chunk 打分排序 |
| 7 | ContextAssembly | `List[RetrievalResult]` | `str` (上下文) | 拼接 chunk + 引用标注 |
| 8 | Generation | `str` + `Query` | `str` (回答) | LLM 生成 + 引用来源 |
| 9 | ResponsePackaging | 回答 + Trace | `Response` 对象 | 封装结果 + 全链路 Trace |

**RetrievalResult 数据结构**:

```python
@dataclass
class RetrievalResult:
    chunk: Chunk
    score: float
    retrieval_method: str      # "bm25" | "dense" | "fusion" | "rerank"
    rank: int

@dataclass
class RetrievalResponse:
    query: str
    answer: str
    contexts: list[RetrievalResult]
    trace: RetrievalTrace       # 全链路追踪
    latency_ms: float
```

#### 3.2.3 RRF 融合算法

```python
def rrf_fusion(
    bm25_results: list[RetrievalResult],
    dense_results: list[RetrievalResult],
    k: int = 60,
    top_n: int = 15,
) -> list[RetrievalResult]:
    """
    Reciprocal Rank Fusion
    score(doc) = Σ 1 / (k + rank_i(doc))
    """
    scores: dict[str, float] = {}
    chunk_map: dict[str, Chunk] = {}

    for rank, result in enumerate(bm25_results, start=1):
        cid = result.chunk.chunk_id
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
        chunk_map[cid] = result.chunk

    for rank, result in enumerate(dense_results, start=1):
        cid = result.chunk.chunk_id
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
        chunk_map[cid] = result.chunk

    sorted_ids = sorted(scores, key=lambda x: scores[x], reverse=True)[:top_n]
    return [
        RetrievalResult(
            chunk=chunk_map[cid],
            score=scores[cid],
            retrieval_method="fusion",
            rank=i + 1,
        )
        for i, cid in enumerate(sorted_ids)
    ]
```

### 3.3 MCP 服务设计

#### 3.3.1 MCP Server 架构

```
┌─────────────────────────────────────────────┐
│              MCP Server (Stdio)              │
│                                              │
│  ┌────────────┐  ┌────────────┐  ┌────────┐ │
│  │  Tools     │  │ Resources  │  │ Prompts│ │
│  │  Registry  │  │  Registry  │  │        │ │
│  └─────┬──────┘  └─────┬──────┘  └────────┘ │
│        │                │                     │
│  ┌─────▼────────────────▼─────────────────┐  │
│  │         KnowledgeHub Core               │  │
│  │  ┌──────────┐  ┌──────────────────┐   │  │
│  │  │Retrieval │  │   Ingestion      │   │  │
│  │  │Pipeline  │  │   Pipeline       │   │  │
│  │  └──────────┘  └──────────────────┘   │  │
│  │  ┌──────────┐  ┌──────────────────┐   │  │
│  │  │Vector    │  │   SQLite Store   │   │  │
│  │  │Store     │  │   (Metadata)     │   │  │
│  │  └──────────┘  └──────────────────┘   │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  Transport: Stdio (stdin/stdout JSON-RPC)    │
└──────────────────┬──────────────────────────┘
                   │
        ┌──────────┴──────────┐
        │  MCP Client         │
        │  (Claude Desktop /  │
        │   Copilot / etc.)   │
        └─────────────────────┘
```

#### 3.3.2 MCP Tools 定义

| Tool 名称 | 参数 | 返回值 | 说明 |
|-----------|------|--------|------|
| `query_knowledge_hub` | `query: str`, `collection: str = "default"`, `top_k: int = 5` | `{answer, contexts, trace_id}` | 核心问答接口 |
| `list_collections` | 无 | `list[str]` | 列出所有知识库 collection |
| `get_document_summary` | `doc_id: str` | `{title, summary, chunk_count, source}` | 获取文档摘要 |
| `ingest_document` | `file_path: str` | `{doc_id, chunk_count, status}` | 摄取单个文档 |
| `list_documents` | `collection: str = "default"`, `limit: int = 20` | `list[DocumentInfo]` | 列出已摄取文档 |
| `delete_document` | `doc_id: str` | `{success: bool}` | 删除文档及其向量 |
| `get_collection_stats` | `collection: str = "default"` | `{total_chunks, total_docs, size_mb}` | 获取 collection 统计 |
| `get_retrieval_trace` | `trace_id: str` | `{steps, latencies, scores}` | 获取某次检索的全链路 Trace |

#### 3.3.3 MCP Resources 定义

| Resource URI | 说明 |
|-------------|------|
| `knowledgehub://collections` | 所有 collection 列表 |
| `knowledgehub://documents/{collection}` | 某 collection 下所有文档 |
| `knowledgehub://document/{doc_id}/chunks` | 某文档的所有 chunk |
| `knowledgehub://stats/overview` | 系统总览统计 |

#### 3.3.4 MCP Server 初始化

```python
# src/knowledge_hub/mcp/server.py
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, Resource

from knowledge_hub.mcp.tools import TOOL_DEFINITIONS, handle_tool_call
from knowledge_hub.mcp.resources import RESOURCE_DEFINITIONS, handle_resource_read

server = Server("knowledge-hub")

@server.list_tools()
async def list_tools() -> list[Tool]:
    return TOOL_DEFINITIONS

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> Any:
    return await handle_tool_call(name, arguments)

@server.list_resources()
async def list_resources() -> list[Resource]:
    return RESOURCE_DEFINITIONS

@server.read_resource()
async def read_resource(uri: str) -> str:
    return await handle_resource_read(uri)

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### 3.4 可插拔架构设计

#### 3.4.1 抽象基类定义

```python
# src/knowledge_hub/core/base_llm.py
from abc import ABC, abstractmethod
from typing import Any

class BaseLLM(ABC):
    """LLM 抽象基类"""

    @abstractmethod
    async def complete(self, messages: list[dict], **kwargs) -> str:
        """对话补全"""
        ...

    @abstractmethod
    async def stream_complete(self, messages: list[dict], **kwargs):
        """流式补全"""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """模型名称"""
        ...


# src/knowledge_hub/core/base_embedding.py
class BaseEmbedding(ABC):
    """Embedding 抽象基类"""

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """单条文本 embedding"""
        ...

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量 embedding"""
        ...

    @property
    @abstractmethod
    def dimension(self) -> int:
        """向量维度"""
        ...


# src/knowledge_hub/core/base_reranker.py
class BaseReranker(ABC):
    """重排器抽象基类"""

    @abstractmethod
    async def rerank(
        self, query: str, documents: list[str], top_k: int
    ) -> list[tuple[int, float]]:
        """
        返回 [(original_index, score), ...] 按 score 降序
        """
        ...


# src/knowledge_hub/core/base_vectorstore.py
class BaseVectorStore(ABC):
    """向量存储抽象基类"""

    @abstractmethod
    async def upsert(self, collection: str, chunks: list[dict]) -> int:
        """插入/更新向量"""
        ...

    @abstractmethod
    async def query(
        self, collection: str, embedding: list[float], top_k: int
    ) -> list[dict]:
        """向量检索"""
        ...

    @abstractmethod
    async def delete(self, collection: str, doc_id: str) -> bool:
        """删除文档相关向量"""
        ...

    @abstractmethod
    async def list_collections(self) -> list[str]:
        """列出所有 collection"""
        ...


# src/knowledge_hub/core/base_splitter.py
class BaseSplitter(ABC):
    """文本切分器抽象基类"""

    @abstractmethod
    def split(self, text: str, metadata: dict | None = None) -> list[Chunk]:
        """切分文本"""
        ...


# src/knowledge_hub/core/base_evaluator.py
class BaseEvaluator(ABC):
    """评估器抽象基类"""

    @abstractmethod
    async def evaluate(
        self, queries: list[str], ground_truth: list[list[str]]
    ) -> dict[str, float]:
        """评估检索质量"""
        ...
```

#### 3.4.2 工厂模式

```python
# src/knowledge_hub/factories/llm_factory.py
from knowledge_hub.core.base_llm import BaseLLM
from knowledge_hub.providers.llm.openai_llm import OpenAILLM
from knowledge_hub.providers.llm.azure_llm import AzureOpenAILLM
from knowledge_hub.providers.llm.ollama_llm import OllamaLLM
from knowledge_hub.providers.llm.deepseek_llm import DeepSeekLLM

class LLMFactory:
    _registry: dict[str, type[BaseLLM]] = {
        "openai": OpenAILLM,
        "azure": AzureOpenAILLM,
        "ollama": OllamaLLM,
        "deepseek": DeepSeekLLM,
    }

    @classmethod
    def create(cls, config: dict) -> BaseLLM:
        provider = config["provider"]
        if provider not in cls._registry:
            raise ValueError(f"Unknown LLM provider: {provider}. "
                           f"Available: {list(cls._registry.keys())}")
        return cls._registry[provider](**config.get("params", {}))

    @classmethod
    def register(cls, name: str, llm_class: type[BaseLLM]):
        """注册自定义 LLM provider"""
        cls._registry[name] = llm_class
```

#### 3.4.3 配置驱动（settings.yaml）

```yaml
# settings.yaml
# ====== LLM 配置 ======
llm:
  provider: openai                    # openai | azure | ollama | deepseek
  params:
    model: gpt-4o-mini
    temperature: 0.0
    max_tokens: 4096
    api_key: ${OPENAI_API_KEY}       # 环境变量引用

# 用于 Image-to-Text 的 Vision LLM
vision_llm:
  provider: openai
  params:
    model: gpt-4o
    api_key: ${OPENAI_API_KEY}

# 用于 Query Rewrite / LLM Rerank 的 LLM
rerank_llm:
  provider: deepseek
  params:
    model: deepseek-chat
    api_key: ${DEEPSEEK_API_KEY}

# ====== Embedding 配置 ======
embedding:
  provider: openai                   # openai | ollama
  params:
    model: text-embedding-3-small
    api_key: ${OPENAI_API_KEY}

# ====== Reranker 配置 ======
reranker:
  coarse:
    provider: cross_encoder          # cross_encoder | none
    params:
      model_name: BAAI/bge-reranker-base
  fine:
    provider: llm                    # llm | none
    params:
      model: gpt-4o-mini

# ====== VectorStore 配置 ======
vectorstore:
  provider: chroma                   # chroma (预留: milvus, qdrant)
  params:
    persist_path: ./data/vector_db
    collection_name: default

# ====== Splitter 配置 ======
splitter:
  provider: langchain_recursive
  params:
    chunk_size: 1000
    chunk_overlap: 200
    separators:
      - "\n## "
      - "\n### "
      - "\n\n"
      - "\n"
      - " "

# ====== 检索配置 ======
retrieval:
  bm25:
    enabled: true
    top_k: 20
  dense:
    top_k: 20
  fusion:
    method: rrf                      # rrf | weighted
    k: 60
    top_n: 15
  final_top_k: 5
  query_rewrite: false

# ====== 摄取配置 ======
ingestion:
  watch_dir: ./data/raw
  image_processing:
    enabled: true
    max_images_per_doc: 50
  enhancement:
    enabled: true
    rewrite: false                   # 可选 LLM 重写 chunk
    inject_metadata: true
    inject_image_desc: true

# ====== MCP 配置 ======
mcp:
  server_name: knowledge-hub
  server_version: "1.0.0"

# ====== 可观测性配置 ======
observability:
  log_level: INFO
  log_dir: ./logs
  trace_enabled: true
  dashboard_port: 8501

# ====== 存储配置 ======
storage:
  sqlite_path: ./data/knowledge_hub.db
  bm25_index_path: ./data/bm25_index

# ====== 评估配置 ======
evaluation:
  framework: custom                  # custom | ragas
  metrics:
    - hit_rate
    - mrr
    - context_precision
  eval_dataset_path: ./data/eval/eval_dataset.json
```

#### 3.4.4 配置加载器

```python
# src/knowledge_hub/config/settings.py
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
import yaml
import os

class LLMConfig(BaseModel):
    provider: str
    params: dict = {}

class EmbeddingConfig(BaseModel):
    provider: str
    params: dict = {}

class VectorStoreConfig(BaseModel):
    provider: str
    params: dict = {}

class SplitterConfig(BaseModel):
    provider: str
    params: dict = {}

class RerankerConfig(BaseModel):
    coarse: dict = {}
    fine: dict = {}

class RetrievalConfig(BaseModel):
    bm25: dict = {}
    dense: dict = {}
    fusion: dict = {}
    final_top_k: int = 5
    query_rewrite: bool = False

class Settings(BaseSettings):
    llm: LLMConfig
    vision_llm: LLMConfig
    rerank_llm: LLMConfig
    embedding: EmbeddingConfig
    reranker: RerankerConfig
    vectorstore: VectorStoreConfig
    splitter: SplitterConfig
    retrieval: RetrievalConfig
    ingestion: dict
    mcp: dict
    observability: dict
    storage: dict
    evaluation: dict

    @classmethod
    def from_yaml(cls, path: str = "settings.yaml") -> "Settings":
        with open(path) as f:
            raw = yaml.safe_load(f)
        # 展开 ${ENV_VAR}
        raw = cls._expand_env(raw)
        return cls(**raw)

    @staticmethod
    def _expand_env(obj):
        if isinstance(obj, str):
            if obj.startswith("${") and obj.endswith("}"):
                env_key = obj[2:-1]
                return os.environ.get(env_key, "")
            return obj
        elif isinstance(obj, dict):
            return {k: cls._expand_env(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [cls._expand_env(v) for v in obj]
        return obj
```

### 3.5 可观测性与 Dashboard 设计

#### 3.5.1 全链路 Trace 设计

```
┌─────────────────────────────────────────────────┐
│              Trace 架构                           │
│                                                   │
│  ┌─────────────┐    ┌──────────────┐             │
│  │ Ingestion   │    │   Query      │             │
│  │ Trace       │    │   Trace      │             │
│  └──────┬──────┘    └──────┬───────┘             │
│         │                  │                      │
│         ▼                  ▼                      │
│  ┌──────────────────────────────────────┐        │
│  │    Structured Logger (JSONL)          │        │
│  │    logs/ingestion.jsonl               │        │
│  │    logs/query.jsonl                   │        │
│  └──────────────────┬───────────────────┘        │
│                     │                              │
│         ┌───────────▼───────────┐                │
│         │   SQLite Trace Store   │                │
│         │   (可查询索引)          │                │
│         └───────────┬───────────┘                │
│                     │                              │
│         ┌───────────▼───────────┐                │
│         │  Streamlit Dashboard   │                │
│         │  (可视化查看)           │                │
│         └───────────────────────┘                │
└─────────────────────────────────────────────────┘
```

**Trace 事件结构（JSONL）**:

```jsonl
{"trace_id":"abc123","event":"ingestion.start","timestamp":"2024-12-20T10:00:00Z","data":{"file":"doc.pdf"}}
{"trace_id":"abc123","event":"ingestion.checksum","timestamp":"2024-12-20T10:00:01Z","data":{"sha256":"...","skip":false},"duration_ms":12}
{"trace_id":"abc123","event":"ingestion.load","timestamp":"2024-12-20T10:00:03Z","data":{"pages":10,"images":5},"duration_ms":2100}
{"trace_id":"abc123","event":"ingestion.chunk","timestamp":"2024-12-20T10:00:04Z","data":{"chunk_count":25},"duration_ms":850}
{"trace_id":"abc123","event":"ingestion.embed","timestamp":"2024-12-20T10:00:06Z","data":{"chunks":25},"duration_ms":1800}
{"trace_id":"abc123","event":"ingestion.complete","timestamp":"2024-12-20T10:00:07Z","data":{"total_chunks":25},"duration_ms":6762}
```

```jsonl
{"trace_id":"def456","event":"query.start","timestamp":"2024-12-20T10:05:00Z","data":{"query":"什么是RAG？"}}
{"trace_id":"def456","event":"query.bm25","timestamp":"2024-12-20T10:05:00Z","data":{"top_k":20,"results":20},"duration_ms":15}
{"trace_id":"def456","event":"query.dense","timestamp":"2024-12-20T10:05:01Z","data":{"top_k":20,"results":20},"duration_ms":320}
{"trace_id":"def456","event":"query.fusion","timestamp":"2024-12-20T10:05:01Z","data":{"method":"rrf","merged":15},"duration_ms":2}
{"trace_id":"def456","event":"query.rerank.coarse","timestamp":"2024-12-20T10:05:02Z","data":{"input":15,"output":10},"duration_ms":450}
{"trace_id":"def456","event":"query.rerank.fine","timestamp":"2024-12-20T10:05:03Z","data":{"input":10,"output":5},"duration_ms":1200}
{"trace_id":"def456","event":"query.generate","timestamp":"2024-12-20T10:05:04Z","data":{"context_chunks":5},"duration_ms":1500}
{"trace_id":"def456","event":"query.complete","timestamp":"2024-12-20T10:05:04Z","data":{"total_latency_ms":3487},"duration_ms":3487}
```

#### 3.5.2 Streamlit Dashboard 设计

| 页面 | 功能 | 数据来源 |
|------|------|----------|
| **系统总览** | collection 数量、总 chunk 数、总文档数、存储大小、最近摄取记录、最近查询记录 | SQLite + Chroma |
| **数据浏览** | 按 collection → 文档 → chunk 三级浏览，支持搜索、高亮、过滤 | Chroma + SQLite |
| **Ingestion 管理** | 上传文件、触发摄取、查看摄取进度、查看历史记录、删除文档 | Ingestion Pipeline |
| **追踪查看** | 按 trace_id 查看 Ingestion/Query 全链路，可视化各步骤耗时和分数变化 | JSONL + SQLite |
| **评估面板** | 运行评估、查看历史评估结果、指标趋势图、对比不同配置的评估结果 | 评估框架 + SQLite |

**Dashboard 技术要点**:

```python
# src/knowledge_hub/dashboard/app.py
import streamlit as st

st.set_page_config(
    page_title="KnowledgeHub Dashboard",
    page_icon="📚",
    layout="wide",
)

# 侧边栏导航
page = st.sidebar.selectbox(
    "页面导航",
    ["系统总览", "数据浏览", "Ingestion管理", "追踪查看", "评估面板"],
)

if page == "系统总览":
    from knowledge_hub.dashboard.pages.overview import render
elif page == "数据浏览":
    from knowledge_hub.dashboard.pages.data_browser import render
elif page == "Ingestion管理":
    from knowledge_hub.dashboard.pages.ingestion_mgr import render
elif page == "追踪查看":
    from knowledge_hub.dashboard.pages.trace_viewer import render
elif page == "评估面板":
    from knowledge_hub.dashboard.pages.eval_panel import render

render()
```

### 3.6 多模态图片处理设计

```
┌──────────────────────────────────────────────────────────┐
│                Image-to-Text 处理流程                      │
│                                                           │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐            │
│  │ PDF/MD   │───▶│ Extract  │───▶│ Cache    │            │
│  │ Source   │    │ Images   │    │ Check    │            │
│  └──────────┘    └──────────┘    └──────────┘            │
│                       │               │                    │
│                  提取图片         SHA256 去重              │
│                                       │                    │
│                   ┌───────────────────▼────────────┐      │
│                   │   Vision LLM (gpt-4o)          │      │
│                   │   Prompt: "描述这张图片的内容..."  │      │
│                   └───────────────────┬────────────┘      │
│                                       │                    │
│                   ┌───────────────────▼────────────┐      │
│                   │   Image Description Cache      │      │
│                   │   (SQLite: image_sha256→desc)  │      │
│                   └───────────────────┬────────────┘      │
│                                       │                    │
│                   ┌───────────────────▼────────────┐      │
│                   │   Inject into nearest Chunk     │      │
│                   │   enhanced_content = chunk +    │      │
│                   │   "\n[图片描述: ...]"           │      │
│                   └────────────────────────────────┘      │
└──────────────────────────────────────────────────────────┘
```

**关键设计决策**:

| 决策 | 选择 | 理由 |
|------|------|------|
| 图片描述方式 | Vision LLM (gpt-4o) | 文本描述可被 BM25 + Dense 双路检索，无需多模态向量 |
| 不使用 CLIP | — | CLIP 多模态向量需额外向量索引，增加复杂度；文本描述更通用 |
| 图片描述缓存 | SQLite (image_sha256 → desc) | 相同图片不重复调用 LLM |
| 描述注入位置 | 最近 chunk 的 enhanced_content | 保持 chunk 内容连贯性 |

---
