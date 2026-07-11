    # RAG-MCP 开发规范文档 (DEV_SPEC)

> **项目代号**: KnowledgeHub  
> **版本**: v1.0  
> **最后更新**: 2024-12-20  
> **文档状态**: 评审中

---

## 目录

1. [项目概述](#1-项目概述)
2. [核心特点](#2-核心特点)
3. [技术选型与设计](#3-技术选型与设计)
4. [测试方案](#4-测试方案)
5. [系统架构与模块设计](#5-系统架构与模块设计)
6. [项目排期](#6-项目排期)

---

## 1. 项目概述

### 1.1 设计理念

| 维度 | 理念 |
|------|------|
| **教是最好的学** | 边做边录视频教学，架构清晰、易于讲解，每个模块配套技术文档与代码示范 |
| **可插拔优先** | 所有核心组件（LLM、Embedding、Reranker、VectorStore、Splitter、Evaluator）通过配置切换，不硬编码任何厂商 |
| **本地优先** | 零外部服务依赖（SQLite 做持久化），开箱即用，同时支持深度扩展 |
| **面试驱动** | 每个模块整理面试高频题和简历撰写建议，项目本身作为简历核心项目 |
| **可观测** | 全链路 Trace + 本地 Dashboard，让 RAG 黑盒透明化 |

### 1.2 项目定位

KnowledgeHub 是一个**模块化的 RAG 系统**，同时包装为 **MCP Server（Model Context Protocol）**，使得 GitHub Copilot、Claude Desktop 等 AI 助手可以通过 Stdio Transport 直接调用本地知识库进行问答。

**一句话定位**: "一个为学习而设计、为面试而打磨、为生产而预留的本地 RAG + MCP 知识库系统。"

### 1.3 技术约束

| 约束项 | 说明 |
|--------|------|
| 语言 | Python 3.11+ |
| 框架限制 | **不使用 LlamaIndex / LangChain 框架**（仅允许使用 LangChain 的 `RecursiveCharacterTextSplitter`） |
| 向量库 | 首批仅实现 Chroma，架构层预留 Milvus / Qdrant 扩展接口 |
| 持久化 | SQLite（元数据、Trace、评估结果），零外部数据库 |
| 通信方式 | MCP Stdio Transport（本地子进程），不做 HTTP 部署 |
| 测试框架 | pytest + pytest-asyncio |

---

## 2. 核心特点

### 2.1 智能分块 + 上下文增强

- **语义感知分块**: 在 LangChain `RecursiveCharacterTextSplitter` 基础上，叠加 Markdown 标题层级感知、代码块完整性保护
- **上下文注入**: 每个 chunk 自动注入文档元数据（来源、页码、章节路径）、图片描述文本
- **LLM 增强**: 可选的 chunk 重写/摘要，提升检索召回率

### 2.2 混合检索 + 两段式重排

```
Query
  ├─ BM25 (稀疏) → Top-K₁ ─┐
  ├─ Dense (稠密) → Top-K₁ ─┤
  │                          ├─ RRF 融合 → Top-K₂
  │                          │     │
  │                          │     ├─ Cross-Encoder 粗排 → Top-K₃
  │                          │     │     │
  │                          │     │     └─ LLM 精排 → Final Top-K
  │                          │     │
```

- **融合策略**: RRF（Reciprocal Rank Fusion），参数 k=60
- **粗排**: Cross-Encoder（如 BAAI/bge-reranker-base）
- **精排**: LLM Rerank（让 LLM 对候选 chunk 打分/排序）

### 2.3 全链路可插拔架构

- **六大可插拔组件**: LLM、Embedding、Reranker、VectorStore、Splitter、Evaluator
- **设计模式**: 抽象基类（ABC） + 工厂模式 + 配置驱动（`settings.yaml`）
- **首批实现**:
  - LLM: Azure OpenAI、OpenAI、Ollama、DeepSeek
  - Embedding: OpenAI text-embedding-3-small、Ollama
  - Reranker: Cross-Encoder（HuggingFace）、LLM Rerank
  - VectorStore: Chroma
  - Splitter: LangChain RecursiveCharacterTextSplitter
  - Evaluator: Ragas + 自定义指标

### 2.4 多模态 Image-to-Text

- **策略**: Vision LLM 生成图片描述 → 缝进 chunk 文本
- **不使用**: CLIP 多模态向量（避免复杂的多模态索引）
- **流程**: PDF 提取图片 → Vision LLM 生成描述 → 描述注入最近 chunk

### 2.5 全链路可观测性

- **结构化日志**: JSON Lines 格式，记录 Ingestion 链路 + Query 链路全量 Trace
- **本地 Dashboard**: Streamlit 多页面应用，零外部平台依赖（不依赖 LangSmith）
- **Dashboard 页面**: 系统总览、数据浏览、Ingestion 管理、追踪查看、评估面板

### 2.6 可插拔评估体系

- **框架**: 支持 Ragas（faithfulness、answer_relevancy 等）
- **自定义指标**: hit_rate、MRR、context_precision、context_recall
- **离线评估**: 构建评估数据集 → 批量跑测 → 生成报告

### 2.7 MCP 集成

- **SDK**: Python 官方 MCP SDK（`mcp` 包）
- **Transport**: Stdio（本地子进程模式）
- **暴露 Tools**: `query_knowledge_hub`、`list_collections`、`get_document_summary`、`ingest_document` 等

### 2.8 增量摄取

- **SHA256 指纹**: 文件级别去重，已摄入文件自动跳过
- **SQLite 记录**: 文件路径、SHA256、摄取时间、chunk 数量、状态

---

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

## 4. 测试方案

### 4.1 TDD 理念

**Red → Green → Refactor**

```
写测试（失败） → 写实现（通过） → 重构（保持通过）
```

- 每个 ~1 小时增量开发前，先写测试用例
- 测试覆盖核心逻辑，不追求 100% 覆盖率
- 测试本身也是文档，体现设计意图

### 4.2 分层测试架构

```
┌─────────────────────────────────────────────────┐
│                    E2E Tests                     │  ← 端到端：完整 Ingestion→Query 流程
│              (tests/e2e/)                        │     依赖: Chroma + LLM（mock 或真实）
├─────────────────────────────────────────────────┤
│              Integration Tests                   │  ← 集成：模块间协作
│           (tests/integration/)                   │     依赖: SQLite + Chroma（本地）
├─────────────────────────────────────────────────┤
│                  Unit Tests                      │  ← 单元：单个类/函数
│              (tests/unit/)                       │     依赖: 无（全部 mock）
└─────────────────────────────────────────────────┘

测试比例:  Unit 70% | Integration 20% | E2E 10%
```

### 4.3 测试目录结构

```
tests/
├── conftest.py                          # 公共 fixtures
├── unit/
│   ├── __init__.py
│   ├── test_rrf_fusion.py               # RRF 融合算法
│   ├── test_chunk_metadata.py            # Chunk 数据结构
│   ├── test_checksum.py                  # SHA256 去重
│   ├── test_config_loader.py             # 配置加载
│   ├── test_llm_factory.py               # LLM 工厂
│   ├── test_embedding_factory.py         # Embedding 工厂
│   ├── test_reranker_factory.py          # Reranker 工厂
│   ├── test_bm25_retriever.py            # BM25 检索
│   ├── test_cross_encoder_reranker.py    # Cross-Encoder 重排
│   ├── test_chunker.py                   # 语义分块
│   ├── test_context_injector.py          # 上下文注入
│   ├── test_image_processor.py           # 图片处理
│   ├── test_trace_logger.py              # Trace 日志
│   ├── test_evaluator_metrics.py         # 评估指标
│   └── test_mcp_tools.py                 # MCP 工具（mock）
├── integration/
│   ├── __init__.py
│   ├── test_chroma_store.py              # Chroma 读写
│   ├── test_sqlite_store.py              # SQLite 持久化
│   ├── test_ingestion_pipeline.py        # 完整摄取流程
│   ├── test_retrieval_pipeline.py        # 完整检索流程
│   └── test_bm25_persistence.py          # BM25 索引持久化
└── e2e/
    ├── __init__.py
    ├── test_full_rag_flow.py             # Ingestion→Query 全流程
    ├── test_mcp_server.py                # MCP Stdio 通信
    └── test_incremental_ingestion.py     # 增量摄取
```

### 4.4 测试策略详解

#### 4.4.1 单元测试

```python
# tests/unit/test_rrf_fusion.py
import pytest
from knowledge_hub.retrieval.fusion import rrf_fusion
from knowledge_hub.core.models import Chunk, RetrievalResult, ChunkMetadata

@pytest.fixture
def sample_chunks():
    return [
        Chunk(chunk_id="c1", content="chunk1", enhanced_content="chunk1",
              metadata=ChunkMetadata(source_file="doc.pdf", source_type="pdf",
              doc_title="Doc", page_number=1, section_path="", chunk_index=0,
              total_chunks=3, sha256="abc", image_descriptions=[], created_at=""),
              tokens=10),
        Chunk(chunk_id="c2", content="chunk2", enhanced_content="chunk2",
              metadata=ChunkMetadata(source_file="doc.pdf", source_type="pdf",
              doc_title="Doc", page_number=1, section_path="", chunk_index=1,
              total_chunks=3, sha256="abc", image_descriptions=[], created_at=""),
              tokens=10),
    ]

def test_rrf_fusion_basic(sample_chunks):
    """RRF 融合：两个检索器都返回相同 chunk，分数应更高"""
    bm25_results = [
        RetrievalResult(chunk=sample_chunks[0], score=0.9, retrieval_method="bm25", rank=1),
        RetrievalResult(chunk=sample_chunks[1], score=0.7, retrieval_method="bm25", rank=2),
    ]
    dense_results = [
        RetrievalResult(chunk=sample_chunks[1], score=0.95, retrieval_method="dense", rank=1),
        RetrievalResult(chunk=sample_chunks[0], score=0.8, retrieval_method="dense", rank=2),
    ]

    fused = rrf_fusion(bm25_results, dense_results, k=60, top_n=2)

    assert len(fused) == 2
    # c1 在 BM25 rank=1, Dense rank=2 → score = 1/61 + 1/62
    # c2 在 BM25 rank=2, Dense rank=1 → score = 1/62 + 1/61
    # 应该近似相等，但 c1 略高（更小的 rank sum）
    assert fused[0].score >= fused[1].score

def test_rrf_fusion_empty_inputs():
    """RRF 融合：空输入返回空列表"""
    assert rrf_fusion([], []) == []

def test_rrf_fusion_single_source(sample_chunks):
    """RRF 融合：只有一个检索器有结果"""
    bm25_results = [
        RetrievalResult(chunk=sample_chunks[0], score=0.9, retrieval_method="bm25", rank=1),
    ]
    fused = rrf_fusion(bm25_results, [], k=60, top_n=5)
    assert len(fused) == 1
    assert fused[0].chunk.chunk_id == "c1"
```

#### 4.4.2 集成测试

```python
# tests/integration/test_chroma_store.py
import pytest
import tempfile
import os
from knowledge_hub.providers.vectorstore.chroma_store import ChromaStore

@pytest.fixture
async def chroma_store():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = ChromaStore(persist_path=tmpdir, collection_name="test")
        await store.init()
        yield store
        await store.cleanup()

@pytest.mark.asyncio
async def test_chroma_upsert_and_query(chroma_store):
    """测试 Chroma 向量写入和检索"""
    chunks = [
        {"chunk_id": "c1", "content": "hello world",
         "embedding": [0.1] * 1536, "metadata": {"source": "test"}},
        {"chunk_id": "c2", "content": "foo bar",
         "embedding": [0.2] * 1536, "metadata": {"source": "test"}},
    ]

    count = await chroma_store.upsert("test", chunks)
    assert count == 2

    results = await chroma_store.query("test", [0.1] * 1536, top_k=1)
    assert len(results) == 1
    assert results[0]["chunk_id"] == "c1"
```

#### 4.4.3 E2E 测试

```python
# tests/e2e/test_full_rag_flow.py
import pytest
import tempfile
from pathlib import Path

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_full_ingest_and_query_flow(test_app):
    """端到端：摄取一个 Markdown 文件 → 查询 → 验证回答"""
    # 1. 准备测试文档
    with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False) as f:
        f.write("# RAG 简介\n\nRAG 是检索增强生成的缩写...")
        md_path = f.name

    # 2. 摄取
    result = await test_app.ingestion_pipeline.run(md_path)
    assert result.status == "success"
    assert result.chunk_count > 0

    # 3. 查询
    response = await test_app.retrieval_pipeline.query("RAG 是什么？")
    assert "检索增强生成" in response.answer
    assert len(response.contexts) > 0

    # 4. 验证 Trace
    assert response.trace.trace_id is not None
    assert len(response.trace.steps) > 5  # 至少经过 5 个步骤
```

### 4.5 RAG 质量评估

#### 4.5.1 评估指标

| 指标 | 类型 | 公式 | 说明 |
|------|------|------|------|
| **hit_rate** | 检索 | `命中查询数 / 总查询数` | Top-K 中是否包含正确文档 |
| **MRR** | 检索 | `mean(1/rank_of_first_hit)` | 第一个命中结果的倒数排名 |
| **context_precision** | 检索 | `相关chunk数 / 返回chunk总数` | 上下文精确率 |
| **context_recall** | 检索 | `召回的相关chunk数 / 总相关chunk数` | 上下文召回率 |
| **faithfulness** | 生成 | `答案中可被上下文支持的说法数 / 总说法数` | 忠实度（Ragas） |
| **answer_relevancy** | 生成 | LLM 评分 | 答案相关性（Ragas） |

#### 4.5.2 评估数据集格式

```json
// data/eval/eval_dataset.json
{
  "version": "1.0",
  "dataset": [
    {
      "query_id": "q001",
      "query": "什么是 RAG？",
      "ground_truth_doc_ids": ["doc_001"],
      "ground_truth_answer": "RAG 是检索增强生成...",
      "expected_chunks": ["chunk_001", "chunk_002"]
    },
    {
      "query_id": "q002",
      "query": "BM25 和 Dense 检索有什么区别？",
      "ground_truth_doc_ids": ["doc_002"],
      "ground_truth_answer": "BM25 是基于词频的稀疏检索...",
      "expected_chunks": ["chunk_010"]
    }
  ]
}
```

#### 4.5.3 评估执行

```python
# src/knowledge_hub/evaluation/evaluator.py
class EvaluationRunner:
    def __init__(self, settings: Settings):
        self.retrieval_pipeline = RetrievalPipeline(settings)
        self.metrics = {
            "hit_rate": HitRateMetric(),
            "mrr": MRRMetric(),
            "context_precision": ContextPrecisionMetric(),
        }
        if settings.evaluation.framework == "ragas":
            self.metrics["faithfulness"] = RagasFaithfulness()

    async def run(self, dataset_path: str) -> EvaluationReport:
        dataset = self._load_dataset(dataset_path)
        results = []

        for item in dataset:
            response = await self.retrieval_pipeline.query(item["query"])
            for name, metric in self.metrics.items():
                score = metric.compute(
                    query=item["query"],
                    response=response,
                    ground_truth=item,
                )
                results.append({
                    "query_id": item["query_id"],
                    "metric": name,
                    "score": score,
                })

        return EvaluationReport(results=results)
```

### 4.6 pytest 配置

```ini
# pyproject.toml [tool.pytest.ini_options]
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
asyncio_mode = "auto"
markers = [
    "unit: 单元测试",
    "integration: 集成测试（需要本地存储）",
    "e2e: 端到端测试（需要完整环境）",
    "slow: 耗时较长的测试",
    "requires_llm: 需要 LLM API key 的测试",
]
addopts = [
    "-v",
    "--tb=short",
    "--strict-markers",
    "-m", "not requires_llm",  # 默认跳过需要 API key 的测试
]
```

---

## 5. 系统架构与模块设计

### 5.1 整体架构图

```
╔═══════════════════════════════════════════════════════════════════════════╗
║                          KnowledgeHub 系统架构                             ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║  ┌─────────────────────────────────────────────────────────────────┐      ║
║  │                      客户端层 (Clients)                           │      ║
║  │   ┌──────────┐   ┌──────────┐   ┌──────────────┐              │      ║
║  │   │ Claude   │   │ GitHub   │   │  直接 CLI    │              │      ║
║  │   │ Desktop  │   │ Copilot  │   │              │              │      ║
║  │   └────┬─────┘   └────┬─────┘   └──────┬───────┘              │      ║
║  └────────┼──────────────┼─────────────────┼──────────────────────┘      ║
║           │              │                 │                               ║
║           │    MCP Stdio Transport        │                               ║
║           │     (JSON-RPC over stdio)     │                               ║
║           │              │                 │                               ║
║  ┌────────▼──────────────▼─────────────────▼──────────────────────┐      ║
║  │                    MCP Server 层                                 │      ║
║  │  ┌────────────────────────────────────────────────────────┐   │      ║
║  │  │  Tools Registry    │  Resources Registry               │   │      ║
║  │  │  · query_knowledge  │  · knowledgehub://collections    │   │      ║
║  │  │  · list_collections  │  · knowledgehub://documents/{}  │   │      ║
║  │  │  · ingest_document   │  · knowledgehub://stats/overview│   │      ║
║  │  │  · delete_document   │                                  │   │      ║
║  │  │  · get_trace         │                                  │   │      ║
║  │  └────────────────────────────────────────────────────────┘   │      ║
║  └────────────────────────┬───────────────────────────────────────┘      ║
║                           │                                                ║
║  ┌────────────────────────▼───────────────────────────────────────┐      ║
║  │                    核心服务层                                     │      ║
║  │                                                                  │      ║
║  │  ┌──────────────────────┐   ┌──────────────────────┐           │      ║
║  │  │  Ingestion Pipeline  │   │  Retrieval Pipeline   │           │      ║
║  │  │                      │   │                      │           │      ║
║  │  │  · File Discovery    │   │  · Query Rewrite     │           │      ║
║  │  │  · SHA256 Check      │   │  · BM25 Retrieve    │           │      ║
║  │  │  · Load (MarkItDown) │   │  · Dense Retrieve   │           │      ║
║  │  │  · Image Extract     │   │  · RRF Fusion       │           │      ║
║  │  │  · Image Description │   │  · Coarse Rerank    │           │      ║
║  │  │  · Semantic Chunk    │   │  · Fine Rerank      │           │      ║
║  │  │  · Context Inject    │   │  · Context Assembly │           │      ║
║  │  │  · LLM Enhance       │   │  · LLM Generation   │           │      ║
║  │  │  · Dual Embed        │   │                      │           │      ║
║  │  │  · Chroma Upsert     │   │                      │           │      ║
║  │  │  · BM25 Index Build  │   │                      │           │      ║
║  │  └──────────────────────┘   └──────────────────────┘           │      ║
║  └────────────────────────────────────────────────────────────────┘      ║
║                           │                                                ║
║  ┌────────────────────────▼───────────────────────────────────────┐      ║
║  │              可插拔组件层 (Pluggable Components)                   │      ║
║  │                                                                  │      ║
║  │  ┌─────────┐ ┌─────────┐ ┌──────────┐ ┌──────────┐            │      ║
║  │  │  LLM    │ │Embedding│ │ Reranker │ │VectorStore│            │      ║
║  │  │ Factory │ │ Factory │ │ Factory  │ │ Factory  │            │      ║
║  │  ├─────────┤ ├─────────┤ ├──────────┤ ├──────────┤            │      ║
║  │  │ OpenAI  │ │ OpenAI  │ │Cross-Enc │ │ Chroma   │            │      ║
║  │  │ Azure   │ │ Ollama  │ │LLM Rerank│ │ (预留:   │            │      ║
║  │  │ Ollama  │ │         │ │          │ │ Milvus)  │            │      ║
║  │  │ DeepSeek│ │         │ │          │ │ Qdrant)  │            │      ║
║  │  └─────────┘ └─────────┘ └──────────┘ └──────────┘            │      ║
║  │  ┌─────────┐ ┌─────────┐                                     │      ║
║  │  │Splitter │ │Evaluator│                                     │      ║
║  │  │ Factory │ │ Factory │                                     │      ║
║  │  ├─────────┤ ├─────────┤                                     │      ║
║  │  │LangChain│ │ Custom  │                                     │      ║
║  │  │Recursive│ │ Ragas   │                                     │      ║
║  │  └─────────┘ └─────────┘                                     │      ║
║  └────────────────────────────────────────────────────────────────┘      ║
║                           │                                                ║
║  ┌────────────────────────▼───────────────────────────────────────┐      ║
║  │                    存储与可观测层                                 │      ║
║  │                                                                  │      ║
║  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │      ║
║  │  │ Chroma   │  │ SQLite   │  │ BM25     │  │ JSONL    │       │      ║
║  │  │ (Vector) │  │ (Meta +  │  │ Index    │  │ Trace    │       │      ║
║  │  │          │  │  Trace)  │  │ (Persist)│  │ Logs     │       │      ║
║  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │      ║
║  │                                                                  │      ║
║  │  ┌──────────────────────────────────────────────────────┐      │      ║
║  │  │              Streamlit Dashboard                      │      │      ║
║  │  │  · 系统总览  · 数据浏览  · Ingestion管理              │      │      ║
║  │  │  · 追踪查看  · 评估面板                                │      │      ║
║  │  └──────────────────────────────────────────────────────┘      │      ║
║  └────────────────────────────────────────────────────────────────┘      ║
║                           │                                                ║
║  ┌────────────────────────▼───────────────────────────────────────┐      ║
║  │                  配置层 (settings.yaml)                          │      ║
║  │  · LLM / Embedding / Reranker / VectorStore / Splitter 配置     │      ║
║  │  · Retrieval 参数 (top_k, fusion_k, rerank 参数)                 │      ║
║  │  · Ingestion 参数 (image_processing, enhancement)               │      ║
║  │  · Observability 参数 (log_level, trace_enabled)                │      ║
║  └────────────────────────────────────────────────────────────────┘      ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

### 5.2 完整目录结构树

```
knowledge-hub/
├── README.md                               # 项目说明
├── DEV_SPEC.md                             # 本文档（开发规范）
├── settings.yaml                           # 主配置文件
├── settings.example.yaml                   # 配置模板
├── pyproject.toml                          # Python 项目配置
├── requirements.txt                        # 依赖列表
├── requirements-dev.txt                    # 开发依赖
├── Makefile                                # 常用命令
├── .env.example                            # 环境变量模板
├── .gitignore
│
├── src/
│   └── knowledge_hub/
│       ├── __init__.py
│       ├── __version__.py
│       ├── main.py                         # 项目入口（MCP Server 启动）
│       │
│       ├── config/                         # 配置管理
│       │   ├── __init__.py
│       │   ├── settings.py                 # Pydantic Settings 模型
│       │   └── loader.py                   # YAML 加载 + 环境变量展开
│       │
│       ├── core/                           # 核心抽象（ABC）
│       │   ├── __init__.py
│       │   ├── models.py                   # 数据模型（Chunk, RetrievalResult 等）
│       │   ├── base_llm.py                 # BaseLLM ABC
│       │   ├── base_embedding.py           # BaseEmbedding ABC
│       │   ├── base_reranker.py            # BaseReranker ABC
│       │   ├── base_vectorstore.py         # BaseVectorStore ABC
│       │   ├── base_splitter.py            # BaseSplitter ABC
│       │   └── base_evaluator.py           # BaseEvaluator ABC
│       │
│       ├── factories/                      # 工厂模式
│       │   ├── __init__.py
│       │   ├── llm_factory.py              # LLMFactory
│       │   ├── embedding_factory.py        # EmbeddingFactory
│       │   ├── reranker_factory.py         # RerankerFactory
│       │   ├── vectorstore_factory.py      # VectorStoreFactory
│       │   ├── splitter_factory.py         # SplitterFactory
│       │   └── evaluator_factory.py        # EvaluatorFactory
│       │
│       ├── providers/                      # 具体实现
│       │   ├── __init__.py
│       │   ├── llm/
│       │   │   ├── __init__.py
│       │   │   ├── openai_llm.py           # OpenAI LLM
│       │   │   ├── azure_llm.py            # Azure OpenAI LLM
│       │   │   ├── ollama_llm.py           # Ollama LLM
│       │   │   └── deepseek_llm.py         # DeepSeek LLM
│       │   ├── embedding/
│       │   │   ├── __init__.py
│       │   │   ├── openai_embedding.py     # OpenAI Embedding
│       │   │   └── ollama_embedding.py     # Ollama Embedding
│       │   ├── reranker/
│       │   │   ├── __init__.py
│       │   │   ├── cross_encoder_reranker.py  # Cross-Encoder 重排
│       │   │   └── llm_reranker.py            # LLM 重排
│       │   ├── vectorstore/
│       │   │   ├── __init__.py
│       │   │   └── chroma_store.py         # Chroma 向量库实现
│       │   ├── splitter/
│       │   │   ├── __init__.py
│       │   │   └── langchain_splitter.py   # LangChain RecursiveSplitter 封装
│       │   └── loader/
│       │       ├── __init__.py
│       │       └── markitdown_loader.py     # PDF→Markdown 加载器
│       │
│       ├── ingestion/                      # 数据摄取流水线
│       │   ├── __init__.py
│       │   ├── discovery.py                # 文件发现
│       │   ├── checksum.py                 # SHA256 去重
│       │   ├── chunker.py                  # 语义分块
│       │   ├── context_injector.py         # 上下文注入（metadata + 图片描述）
│       │   ├── enhancer.py                 # LLM 增强（可选重写）
│       │   ├── image_processor.py          # Image-to-Text 处理
│       │   ├── embedder.py                 # 双路 Embedding
│       │   └── pipeline.py                 # Ingestion 编排器
│       │
│       ├── retrieval/                      # 检索流水线
│       │   ├── __init__.py
│       │   ├── bm25_retriever.py           # BM25 稀疏检索
│       │   ├── dense_retriever.py          # Dense 稠密检索
│       │   ├── fusion.py                   # RRF 融合
│       │   ├── reranker.py                 # 两段式重排编排
│       │   ├── context_assembler.py        # 上下文组装
│       │   ├── query_rewriter.py           # 查询改写（可选）
│       │   └── pipeline.py                 # Retrieval 编排器
│       │
│       ├── mcp/                            # MCP Server
│       │   ├── __init__.py
│       │   ├── server.py                   # MCP Server 初始化
│       │   ├── tools.py                    # MCP Tools 定义与处理
│       │   └── resources.py                # MCP Resources 定义与处理
│       │
│       ├── evaluation/                     # 评估框架
│       │   ├── __init__.py
│       │   ├── metrics/
│       │   │   ├── __init__.py
│       │   │   ├── hit_rate.py             # Hit Rate
│       │   │   ├── mrr.py                  # MRR
│       │   │   ├── context_precision.py    # Context Precision
│       │   │   └── context_recall.py       # Context Recall
│       │   ├── ragas_evaluator.py          # Ragas 集成
│       │   ├── evaluator.py                # 评估运行器
│       │   └── report.py                   # 评估报告生成
│       │
│       ├── observability/                  # 可观测性
│       │   ├── __init__.py
│       │   ├── logger.py                   # 结构化 JSONL 日志
│       │   ├── tracer.py                   # 全链路 Tracer
│       │   └── trace_store.py              # Trace 持久化（SQLite）
│       │
│       ├── dashboard/                      # Streamlit Dashboard
│       │   ├── __init__.py
│       │   ├── app.py                      # Dashboard 入口
│       │   ├── pages/
│       │   │   ├── __init__.py
│       │   │   ├── overview.py             # 系统总览
│       │   │   ├── data_browser.py         # 数据浏览
│       │   │   ├── ingestion_mgr.py        # Ingestion 管理
│       │   │   ├── trace_viewer.py         # 追踪查看
│       │   │   └── eval_panel.py           # 评估面板
│       │   └── components/
│       │       ├── __init__.py
│       │       ├── charts.py               # 图表组件
│       │       └── tables.py               # 表格组件
│       │
│       ├── storage/                        # 存储层
│       │   ├── __init__.py
│       │   ├── sqlite_store.py             # SQLite 元数据存储
│       │   ├── bm25_index.py               # BM25 索引持久化
│       │   └── image_cache.py              # 图片描述缓存
│       │
│       └── utils/
│           ├── __init__.py
│           ├── hash.py                     # SHA256 工具
│           ├── text.py                     # 文本处理工具
│           └── time.py                     # 时间工具
│
├── tests/                                  # 测试（见 4.3 节）
│   ├── conftest.py
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── data/                                   # 数据目录
│   ├── raw/                               # 原始文件（PDF/MD/TXT）
│   ├── processed/                          # 处理后的 Markdown
│   ├── vector_db/                          # Chroma 持久化
│   ├── bm25_index/                         # BM25 索引持久化
│   ├── eval/                               # 评估数据集
│   │   └── eval_dataset.json
│   └── knowledge_hub.db                    # SQLite 数据库
│
├── logs/                                   # 日志目录
│   ├── ingestion.jsonl                     # 摄取 Trace
│   └── query.jsonl                         # 查询 Trace
│
├── docs/                                   # 文档目录
│   ├── architecture/                       # 架构文档
│   ├── interview/                          # 面试题集
│   │   ├── rag_basics.md
│   │   ├── hybrid_retrieval.md
│   │   ├── mcp_protocol.md
│   │   └── ...
│   ├── resume/                             # 简历撰写建议
│   │   └── project_description.md
│   └── api/                                # API 文档
│
├── scripts/                                # 脚本
│   ├── run_mcp.sh                          # 启动 MCP Server
│   ├── run_dashboard.sh                    # 启动 Dashboard
│   ├── run_eval.sh                         # 运行评估
│   └── ingest_dir.sh                       # 批量摄取目录
│
└── .github/                                # CI/CD（可选）
    └── workflows/
        └── ci.yml
```

### 5.3 模块职责说明表

| 模块 | 路径 | 职责 | 对外接口 | 依赖 |
|------|------|------|----------|------|
| **Config** | `config/` | 加载和验证 settings.yaml，环境变量展开 | `Settings.from_yaml()` | pydantic, yaml |
| **Core ABCs** | `core/` | 定义所有可插拔组件的抽象基类和数据模型 | `BaseLLM`, `BaseEmbedding`, ... | abc, dataclasses |
| **Factories** | `factories/` | 根据配置创建具体组件实例 | `LLMFactory.create(config)` | core, providers |
| **LLM Providers** | `providers/llm/` | 各厂商 LLM 的具体实现 | `complete()`, `stream_complete()` | openai SDK |
| **Embedding Providers** | `providers/embedding/` | 各厂商 Embedding 实现 | `embed()`, `embed_batch()` | openai SDK |
| **Reranker Providers** | `providers/reranker/` | Cross-Encoder 和 LLM 重排 | `rerank(query, docs, top_k)` | sentence-transformers |
| **VectorStore Provider** | `providers/vectorstore/` | Chroma 向量库封装 | `upsert()`, `query()`, `delete()` | chromadb |
| **Splitter Provider** | `providers/splitter/` | 文本切分 | `split(text, metadata)` | langchain splitter |
| **Loader Provider** | `providers/loader/` | PDF→Markdown 加载 | `load(file_path)` | markitdown |
| **Ingestion Pipeline** | `ingestion/` | 编排完整摄取流程 | `pipeline.run(file_path)` | 所有 providers |
| **Retrieval Pipeline** | `retrieval/` | 编排完整检索流程 | `pipeline.query(query)` | providers, fusion |
| **BM25 Retriever** | `retrieval/bm25_retriever.py` | BM25 稀疏检索 | `retrieve(query, top_k)` | rank_bm25 |
| **Fusion** | `retrieval/fusion.py` | RRF 融合算法 | `rrf_fusion(list1, list2)` | 无 |
| **MCP Server** | `mcp/` | MCP 协议通信，暴露 Tools/Resources | `server.run()` | mcp SDK |
| **Evaluation** | `evaluation/` | RAG 质量评估 | `evaluator.run(dataset)` | retrieval pipeline |
| **Observability** | `observability/` | 全链路 Trace 和结构化日志 | `Tracer.start_trace()` | structlog, sqlite |
| **Dashboard** | `dashboard/` | Streamlit 可视化 | `streamlit run app.py` | streamlit |
| **Storage** | `storage/` | SQLite 元数据 + BM25 索引持久化 | `SQLiteStore`, `BM25Index` | sqlite3, pickle |
| **Utils** | `utils/` | 通用工具函数 | `hash_file()`, `normalize_text()` | hashlib |

### 5.4 数据流说明

#### 5.4.1 Ingestion Flow（数据摄取流）

```
用户放置文件到 data/raw/
         │
         ▼
┌──────────────────────────────────────────────────────────────────┐
│ 1. FileDiscovery.scan("data/raw/")                                │
│    → ["data/raw/doc1.pdf", "data/raw/doc2.md", ...]              │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│ 2. for file_path in files:                                       │
│      sha256 = ChecksumCompute.compute(file_path)                 │
│      if SQLiteStore.exists(sha256):                              │
│          log("skip: already ingested")                           │
│          continue                                                │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│ 3. markdown, images = MarkItDownLoader.load(file_path)           │
│    → markdown: "# Title\n\n正文..."                              │
│    → images: [{"path": "img/fig1.png", "page": 2}, ...]         │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│ 4. if images and image_processing.enabled:                       │
│      for img in images:                                          │
│          img_sha = hash(img.path)                                │
│          if ImageCache.exists(img_sha):                          │
│              desc = ImageCache.get(img_sha)                      │
│          else:                                                   │
│              desc = await VisionLLM.describe(img.path)           │
│              ImageCache.set(img_sha, desc)                       │
│          img["description"] = desc                               │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│ 5. chunks = SemanticChunker.split(markdown, metadata)            │
│    → [Chunk(chunk_id="c1", content="...", ...), ...]            │
│    切分时感知 Markdown 标题层级，保护代码块完整性                   │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│ 6. chunks = ContextInjector.inject(chunks, images, metadata)     │
│    → 每个 chunk 的 enhanced_content 加入:                         │
│      "[来源: doc1.pdf | 页码: 2 | 章节: 第一章 > 1.2 安装]\n"    │
│      "[图片描述: 这是一个架构图，展示了...]\n"                     │
│      原始 chunk 内容                                              │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│ 7. if enhancement.rewrite:                                       │
│      chunks = await LLMEnhancer.rewrite(chunks)                  │
│      → LLM 重写 chunk 提升检索质量（可选）                         │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│ 8. for chunk in chunks:                                          │
│      dense_emb = await EmbeddingProvider.embed(chunk.enhanced)   │
│      chunk.embedding = dense_emb                                 │
│    → 所有 chunk 获得 Dense Embedding                              │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│ 9. ChromaStore.upsert(collection, chunks)                        │
│    → 向量 + metadata 写入 Chroma                                  │
│    BM25IndexBuilder.build(chunks)                                │
│    → 构建 BM25 倒排索引并持久化                                    │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│ 10. SQLiteStore.record({                                         │
│       file_path, sha256, chunk_count,                            │
│       status: "success", ingested_at: now()                      │
│     })                                                           │
│    TraceLogger.flush(trace_id)                                   │
│    → 元数据写入 SQLite，Trace 刷盘                                │
└──────────────────────────────────────────────────────────────────┘
```

#### 5.4.2 Query Flow（查询流）

```
用户通过 MCP Client 发送查询
         │
         ▼
┌──────────────────────────────────────────────────────────────────┐
│ 1. MCP Server 接收 tool_call: query_knowledge_hub(query="...")   │
│    → 调用 RetrievalPipeline.query(query)                         │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│ 2. trace = Tracer.start_trace("query", query)                    │
│    → 生成 trace_id，开始记录                                       │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│ 3. if retrieval.query_rewrite:                                   │
│      queries = await QueryRewriter.rewrite(query)                │
│      → 生成扩展查询列表                                            │
│    else:                                                         │
│      queries = [query]                                           │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│ 4. 并行执行:                                                      │
│    ┌─────────────────────────┐  ┌──────────────────────────┐    │
│    │ BM25Retrieve            │  │ DenseRetrieve             │    │
│    │   for q in queries:     │  │   emb = Embedding.embed(q)│    │
│    │     results = BM25Index │  │   results = ChromaStore   │    │
│    │       .search(q, top_k) │  │     .query(emb, top_k)    │    │
│    │   → Top-20              │  │   → Top-20                │    │
│    └───────────┬─────────────┘  └────────────┬─────────────┘    │
│                │                              │                   │
│                └──────────┬───────────────────┘                   │
│                           ▼                                       │
│              trace.log("bm25", results)                           │
│              trace.log("dense", results)                          │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│ 5. fused = RRFFusion.fusion(                                     │
│      bm25_results, dense_results,                                │
│      k=60, top_n=15                                              │
│    )                                                             │
│    → 合并去重，按 RRF 分数排序，取 Top-15                          │
│    trace.log("fusion", fused)                                    │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│ 6. if reranker.coarse.provider != "none":                        │
│      coarse = await CrossEncoderReranker.rerank(                 │
│        query, [c.content for c in fused], top_k=10               │
│      )                                                            │
│      → Cross-Encoder 粗排，取 Top-10                              │
│      trace.log("rerank.coarse", coarse)                          │
│    else:                                                         │
│      coarse = fused[:10]                                         │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│ 7. if reranker.fine.provider != "none":                          │
│      fine = await LLMReranker.rerank(                            │
│        query, coarse, top_k=5                                    │
│      )                                                            │
│      → LLM 对每个 chunk 打分，取 Top-5                            │
│      trace.log("rerank.fine", fine)                              │
│    else:                                                         │
│      fine = coarse[:5]                                           │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│ 8. context = ContextAssembler.assemble(                           │
│      fine, format="numbered_with_citations"                      │
│    )                                                              │
│    → "[1] (doc1.pdf, p.2) chunk content...\n"                    │
│      "[2] (doc2.md, §1.2) chunk content...\n"                    │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│ 9. prompt = build_prompt(query, context)                         │
│    answer = await LLM.complete(prompt)                           │
│    → LLM 基于上下文生成回答                                       │
│    trace.log("generate", answer)                                 │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│ 10. response = RetrievalResponse(                                │
│       query=query, answer=answer,                                │
│       contexts=fine, trace=trace.end(),                          │
│       latency_ms=elapsed                                         │
│     )                                                            │
│     → 封装响应，包含 Trace                                        │
│     → 返回给 MCP Server → 返回给 Client                           │
└──────────────────────────────────────────────────────────────────┘
```

### 5.5 配置驱动设计示例

#### 5.5.1 组件初始化流程

```python
# src/knowledge_hub/main.py
from knowledge_hub.config.settings import Settings
from knowledge_hub.factories.llm_factory import LLMFactory
from knowledge_hub.factories.embedding_factory import EmbeddingFactory
from knowledge_hub.factories.reranker_factory import RerankerFactory
from knowledge_hub.factories.vectorstore_factory import VectorStoreFactory
from knowledge_hub.factories.splitter_factory import SplitterFactory
from knowledge_hub.ingestion.pipeline import IngestionPipeline
from knowledge_hub.retrieval.pipeline import RetrievalPipeline
from knowledge_hub.mcp.server import MCPServer

class KnowledgeHub:
    def __init__(self, config_path: str = "settings.yaml"):
        self.settings = Settings.from_yaml(config_path)
        self._init_components()

    def _init_components(self):
        s = self.settings

        # 通过工厂创建所有可插拔组件
        self.llm = LLMFactory.create(s.llm.model_dump())
        self.vision_llm = LLMFactory.create(s.vision_llm.model_dump())
        self.rerank_llm = LLMFactory.create(s.rerank_llm.model_dump())
        self.embedding = EmbeddingFactory.create(s.embedding.model_dump())
        self.coarse_reranker = RerankerFactory.create(s.reranker.coarse)
        self.fine_reranker = RerankerFactory.create(s.reranker.fine)
        self.vectorstore = VectorStoreFactory.create(s.vectorstore.model_dump())
        self.splitter = SplitterFactory.create(s.splitter.model_dump())

        # 组装 Pipeline
        self.ingestion_pipeline = IngestionPipeline(
            splitter=self.splitter,
            embedding=self.embedding,
            vectorstore=self.vectorstore,
            vision_llm=self.vision_llm,
            settings=s.ingestion,
        )
        self.retrieval_pipeline = RetrievalPipeline(
            embedding=self.embedding,
            vectorstore=self.vectorstore,
            llm=self.llm,
            coarse_reranker=self.coarse_reranker,
            fine_reranker=self.fine_reranker,
            settings=s.retrieval,
        )

    async def run_mcp_server(self):
        server = MCPServer(
            ingestion_pipeline=self.ingestion_pipeline,
            retrieval_pipeline=self.retrieval_pipeline,
            settings=self.settings.mcp,
        )
        await server.run()

if __name__ == "__main__":
    import asyncio
    hub = KnowledgeHub()
    asyncio.run(hub.run_mcp_server())
```

#### 5.5.2 运行时切换配置示例

```python
# 通过环境变量切换配置文件
# 开发环境: settings.dev.yaml (使用 Ollama)
# 生产环境: settings.prod.yaml (使用 Azure OpenAI)

import os
config_file = os.getenv("KH_CONFIG", "settings.yaml")
hub = KnowledgeHub(config_path=config_file)
```

---

## 6. 项目排期

### 6.1 阶段总览

| 阶段 | 名称 | 目的 | 预估时长 | 子任务数 |
|------|------|------|----------|----------|
| **A** | 项目引导与配置系统 | 搭建项目骨架、配置加载、CI 基础 | 3h | 3 |
| **B** | 核心抽象与工厂模式 | 定义所有 ABC、工厂、数据模型 | 4h | 4 |
| **C** | Provider 实现（LLM + Embedding + Splitter） | 实现首批 LLM、Embedding、Splitter | 5h | 5 |
| **D** | Ingestion Pipeline | 完整数据摄取流水线 | 6h | 6 |
| **E** | Retrieval Pipeline | 完整检索流水线 | 5h | 5 |
| **F** | MCP Server 集成 | MCP Tools/Resources + Stdio 通信 | 4h | 4 |
| **G** | 可观测性 + Trace | 结构化日志、全链路追踪、SQLite 存储 | 3h | 3 |
| **H** | 评估框架 | 自定义指标 + Ragas 集成 | 3h | 3 |
| **I** | Streamlit Dashboard | 多页面 Dashboard | 5h | 5 |
| | **总计** | | **38h** | **38** |

### 6.2 进度跟踪表

| 阶段 | 子任务 | 状态 | 完成日期 | 备注 |
|------|--------|------|----------|------|
| A | A1: 项目初始化与依赖管理 | ✅ 已完成 | 2026-07-11 | |
| A | A2: 配置系统（YAML + Pydantic） | ✅ 已完成 | 2026-07-11 | 
| A | A3: SQLite 存储基础 | ⬜ 未开始 | | |
| B | B1: 核心数据模型定义 | ⬜ 未开始 | | |
| B | B2: 六大抽象基类（ABC） | ⬜ 未开始 | | |
| B | B3: 工厂模式实现 | ⬜ 未开始 | | |
| B | B4: KnowledgeHub 编排器 | ⬜ 未开始 | | |
| C | C1: OpenAI LLM Provider | ⬜ 未开始 | | |
| C | C2: Azure/Ollama/DeepSeek LLM | ⬜ 未开始 | | |
| C | C3: OpenAI/Ollama Embedding | ⬜ 未开始 | | |
| C | C4: LangChain Splitter 封装 | ⬜ 未开始 | | |
| C | C5: MarkItDown Loader | ⬜ 未开始 | | |
| D | D1: 文件发现 + SHA256 去重 | ⬜ 未开始 | | |
| D | D2: 语义分块 + 上下文注入 | ⬜ 未开始 | | |
| D | D3: Image-to-Text 处理 | ⬜ 未开始 | | |
| D | D4: LLM 增强（可选重写） | ⬜ 未开始 | | |
| D | D5: 双路 Embedding + Chroma Upsert | ⬜ 未开始 | | |
| D | D6: Ingestion Pipeline 编排 | ⬜ 未开始 | | |
| E | E1: BM25 检索器 | ⬜ 未开始 | | |
| E | E2: Dense 检索器 | ⬜ 未开始 | | |
| E | E3: RRF 融合 | ⬜ 未开始 | | |
| E | E4: 两段式重排 | ⬜ 未开始 | | |
| E | E5: Retrieval Pipeline 编排 | ⬜ 未开始 | | |
| F | F1: MCP Tools 定义 | ⬜ 未开始 | | |
| F2: MCP Resources 定义 | ⬜ 未开始 | | | |
| F | F3: Tool 处理逻辑 | ⬜ 未开始 | | |
| F | F4: MCP Server Stdio 启动 | ⬜ 未开始 | | |
| G | G1: 结构化 JSONL 日志 | ⬜ 未开始 | | |
| G | G2: 全链路 Tracer | ⬜ 未开始 | | |
| G | G3: Trace SQLite 存储 | ⬜ 未开始 | | |
| H | H1: 自定义评估指标 | ⬜ 未开始 | | |
| H | H2: 评估运行器 | ⬜ 未开始 | | |
| H | H3: Ragas 集成 | ⬜ 未开始 | | |
| I | I1: Dashboard 骨架 + 系统总览 | ⬜ 未开始 | | |
| I | I2: 数据浏览页面 | ⬜ 未开始 | | |
| I | I3: Ingestion 管理页面 | ⬜ 未开始 | | |
| I | I4: 追踪查看页面 | ⬜ 未开始 | | |
| I | I5: 评估面板页面 | ⬜ 未开始 | | |

> **状态标记**: ⬜ 未开始 | 🔵 进行中 | ✅ 已完成 | ⚠️ 阻塞

---

### 6.3 详细排期（阶段 A → I）

---

#### 阶段 A: 项目引导与配置系统（3h）

**目的**: 搭建项目骨架，配置系统可用，SQLite 存储基础就绪。

---

**A1: 项目初始化与依赖管理**（1h）

| 项目 | 内容 |
|------|------|
| **修改文件** | `pyproject.toml`, `requirements.txt`, `requirements-dev.txt`, `.gitignore`, `.env.example`, `README.md`, `Makefile` |
| **实现内容** | 项目目录结构创建、依赖声明、Makefile 常用命令（test/lint/run）、.gitignore 配置 |
| **验收标准** | `make install` 可安装所有依赖；`make test` 可运行空测试套件并返回 0 |
| **测试方法** | `pytest --co` 无报错；`python -c "import knowledge_hub"` 无报错 |

```makefile
# Makefile 核心内容
.PHONY: install test lint run-mcp run-dashboard

install:
	pip install -e ".[dev]"

test:
	pytest tests/ -v

lint:
	ruff check src/ tests/

run-mcp:
	python -m knowledge_hub.main

run-dashboard:
	streamlit run src/knowledge_hub/dashboard/app.py
```

---

**A2: 配置系统（YAML + Pydantic）**（1h）

| 项目 | 内容 |
|------|------|
| **修改文件** | `settings.yaml`, `settings.example.yaml`, `src/knowledge_hub/config/__init__.py`, `src/knowledge_hub/config/settings.py`, `src/knowledge_hub/config/loader.py`, `tests/unit/test_config_loader.py` |
| **实现类/函数** | `Settings`（Pydantic BaseModel）, `Settings.from_yaml()`, `Settings._expand_env()`, 各子配置模型（`LLMConfig`, `EmbeddingConfig` 等） |
| **验收标准** | `Settings.from_yaml("settings.yaml")` 正确加载所有配置；环境变量 `${VAR}` 正确展开；缺失必填字段抛出 `ValidationError` |
| **测试方法** | `pytest tests/unit/test_config_loader.py -v` |

```python
# tests/unit/test_config_loader.py 核心测试
def test_load_settings_from_yaml():
    settings = Settings.from_yaml("settings.example.yaml")
    assert settings.llm.provider == "openai"
    assert settings.retrieval.fusion.k == 60

def test_env_var_expansion(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
    settings = Settings.from_yaml("settings.example.yaml")
    assert settings.llm.params["api_key"] == "sk-test-123"

def test_missing_required_field_raises():
    with pytest.raises(ValidationError):
        Settings(llm={})  # 缺少 provider
```

---

**A3: SQLite 存储基础**（1h）

| 项目 | 内容 |
|------|------|
| **修改文件** | `src/knowledge_hub/storage/__init__.py`, `src/knowledge_hub/storage/sqlite_store.py`, `tests/integration/test_sqlite_store.py` |
| **实现类/函数** | `SQLiteStore`（init, execute, query, close）, 建表 SQL（documents, chunks, traces, image_cache, eval_results） |
| **验收标准** | `SQLiteStore.init()` 创建所有表；CRUD 操作正常；数据库文件创建在 `data/knowledge_hub.db` |
| **测试方法** | `pytest tests/integration/test_sqlite_store.py -v` |

**SQLite 表结构**:

```sql
-- 文档记录表
CREATE TABLE IF NOT EXISTS documents (
    doc_id TEXT PRIMARY KEY,
    file_path TEXT NOT NULL,
    sha256 TEXT UNIQUE NOT NULL,
    doc_title TEXT,
    source_type TEXT,
    chunk_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Chunk 记录表
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL,
    content TEXT,
    enhanced_content TEXT,
    chunk_index INTEGER,
    page_number INTEGER,
    section_path TEXT,
    FOREIGN KEY (doc_id) REFERENCES documents(doc_id)
);

-- Trace 记录表
CREATE TABLE IF NOT EXISTS traces (
    trace_id TEXT PRIMARY KEY,
    trace_type TEXT NOT NULL,  -- 'ingestion' | 'query'
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    duration_ms INTEGER,
    status TEXT,
    data_json TEXT  -- 完整 trace JSON
);

-- 图片描述缓存表
CREATE TABLE IF NOT EXISTS image_cache (
    image_sha256 TEXT PRIMARY KEY,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 评估结果表
CREATE TABLE IF NOT EXISTS eval_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    eval_run_id TEXT,
    query_id TEXT,
    metric_name TEXT,
    score REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

#### 阶段 B: 核心抽象与工厂模式（4h）

**目的**: 定义所有可插拔组件的抽象基类和数据模型，工厂模式可创建组件。

---

**B1: 核心数据模型定义**（1h）

| 项目 | 内容 |
|------|------|
| **修改文件** | `src/knowledge_hub/core/__init__.py`, `src/knowledge_hub/core/models.py`, `tests/unit/test_models.py` |
| **实现类/函数** | `Chunk`, `ChunkMetadata`, `RetrievalResult`, `RetrievalResponse`, `RetrievalTrace`, `IngestionResult`, `DocumentInfo` |
| **验收标准** | 数据模型可正确序列化/反序列化；类型注解完整；`from_dict()` / `to_dict()` 正确 |
| **测试方法** | `pytest tests/unit/test_models.py -v` |

---

**B2: 六大抽象基类（ABC）**（1h）

| 项目 | 内容 |
|------|------|
| **修改文件** | `src/knowledge_hub/core/base_llm.py`, `base_embedding.py`, `base_reranker.py`, `base_vectorstore.py`, `base_splitter.py`, `base_evaluator.py`, `tests/unit/test_abc_compliance.py` |
| **实现类/函数** | `BaseLLM`, `BaseEmbedding`, `BaseReranker`, `BaseVectorStore`, `BaseSplitter`, `BaseEvaluator`（均含抽象方法定义） |
| **验收标准** | 每个 ABC 不能直接实例化（抛出 `TypeError`）；子类未实现抽象方法时抛出 `TypeError` |
| **测试方法** | `pytest tests/unit/test_abc_compliance.py -v` |

```python
# tests/unit/test_abc_compliance.py
import pytest
from knowledge_hub.core.base_llm import BaseLLM

def test_cannot_instantiate_abc():
    with pytest.raises(TypeError):
        BaseLLM()

def test_subclass_must_implement_abstract():
    class IncompleteLLM(BaseLLM):
        pass
    with pytest.raises(TypeError):
        IncompleteLLM()
```

---

**B3: 工厂模式实现**（1h）

| 项目 | 内容 |
|------|------|
| **修改文件** | `src/knowledge_hub/factories/__init__.py`, `llm_factory.py`, `embedding_factory.py`, `reranker_factory.py`, `vectorstore_factory.py`, `splitter_factory.py`, `evaluator_factory.py`, `tests/unit/test_factories.py` |
| **实现类/函数** | `LLMFactory.create()`, `EmbeddingFactory.create()`, `RerankerFactory.create()`, `VectorStoreFactory.create()`, `SplitterFactory.create()`, `EvaluatorFactory.create()`（均含 `_registry` 字典和 `register()` 方法） |
| **验收标准** | `create({"provider": "openai", ...})` 返回正确实例；未知 provider 抛出 `ValueError`；`register()` 可注册自定义实现 |
| **测试方法** | `pytest tests/unit/test_factories.py -v` |

---

**B4: KnowledgeHub 编排器骨架**（1h）

| 项目 | 内容 |
|------|------|
| **修改文件** | `src/knowledge_hub/__init__.py`, `src/knowledge_hub/main.py`, `tests/unit/test_knowledge_hub_init.py` |
| **实现类/函数** | `KnowledgeHub.__init__()`, `KnowledgeHub._init_components()`（此时 providers 尚未实现，用 mock 验证编排逻辑） |
| **验收标准** | 给定 settings.yaml，`KnowledgeHub` 能通过工厂创建所有组件引用（此时用 mock provider）；组件引用类型正确 |
| **测试方法** | `pytest tests/unit/test_knowledge_hub_init.py -v` |

---

#### 阶段 C: Provider 实现（5h）

**目的**: 实现首批 LLM、Embedding、Splitter、Loader 具体实现。

---

**C1: OpenAI LLM Provider**（1h）

| 项目 | 内容 |
|------|------|
| **修改文件** | `src/knowledge_hub/providers/llm/__init__.py`, `openai_llm.py`, `tests/unit/test_openai_llm.py` |
| **实现类/函数** | `OpenAILLM(BaseLLM)`：`__init__(model, api_key, temperature, max_tokens)`, `complete()`, `stream_complete()`, `model_name` |
| **验收标准** | `complete()` 返回字符串；支持 system/user/assistant 消息；`stream_complete()` 生成器逐 token 返回；API key 从参数或环境变量获取 |
| **测试方法** | `pytest tests/unit/test_openai_llm.py -v`（mock openai client） |

```python
# tests/unit/test_openai_llm.py
@pytest.mark.asyncio
async def test_openai_llm_complete(mock_openai_client):
    llm = OpenAILLM(model="gpt-4o-mini", api_key="sk-test")
    result = await llm.complete([{"role": "user", "content": "hello"}])
    assert isinstance(result, str)
    mock_openai_client.chat.completions.create.assert_called_once()
```

---

**C2: Azure / Ollama / DeepSeek LLM**（1h）

| 项目 | 内容 |
|------|------|
| **修改文件** | `azure_llm.py`, `ollama_llm.py`, `deepseek_llm.py`, `tests/unit/test_azure_llm.py`, `test_ollama_llm.py`, `test_deepseek_llm.py` |
| **实现类/函数** | `AzureOpenAILLM`, `OllamaLLM`, `DeepSeekLLM`（均继承 `BaseLLM`） |
| **验收标准** | Azure 使用 `AzureOpenAI` client；Ollama 使用 `base_url` 调用本地模型；DeepSeek 使用 `base_url="https://api.deepseek.com"` |
| **测试方法** | `pytest tests/unit/test_azure_llm.py tests/unit/test_ollama_llm.py tests/unit/test_deepseek_llm.py -v` |

---

**C3: OpenAI / Ollama Embedding**（1h）

| 项目 | 内容 |
|------|------|
| **修改文件** | `src/knowledge_hub/providers/embedding/__init__.py`, `openai_embedding.py`, `ollama_embedding.py`, `tests/unit/test_openai_embedding.py`, `test_ollama_embedding.py` |
| **实现类/函数** | `OpenAIEmbedding(BaseEmbedding)`：`embed()`, `embed_batch()`, `dimension`；`OllamaEmbedding(BaseEmbedding)` |
| **验收标准** | `embed("hello")` 返回 `list[float]`，长度 == `dimension`；`embed_batch()` 批量返回；维度属性正确 |
| **测试方法** | `pytest tests/unit/test_openai_embedding.py -v`（mock） |

---

**C4: LangChain Splitter 封装**（1h）

| 项目 | 内容 |
|------|------|
| **修改文件** | `src/knowledge_hub/providers/splitter/__init__.py`, `langchain_splitter.py`, `tests/unit/test_langchain_splitter.py` |
| **实现类/函数** | `LangChainRecursiveSplitter(BaseSplitter)`：`split(text, metadata) -> list[Chunk]`；内部使用 `RecursiveCharacterTextSplitter` |
| **验收标准** | 切分结果 `len(chunks) > 0`；每个 chunk `content` 非空；`chunk_index` 连续；`chunk_size` 和 `chunk_overlap` 配置生效 |
| **测试方法** | `pytest tests/unit/test_langchain_splitter.py -v` |

---

**C5: MarkItDown Loader**（1h）

| 项目 | 内容 |
|------|------|
| **修改文件** | `src/knowledge_hub/providers/loader/__init__.py`, `markitdown_loader.py`, `tests/unit/test_markitdown_loader.py`, `tests/fixtures/sample.pdf`, `tests/fixtures/sample.md` |
| **实现类/函数** | `MarkItDownLoader`：`load(file_path) -> tuple[str, list[dict]]`（返回 markdown + 图片信息） |
| **验收标准** | PDF 输入 → Markdown 字符串；MD 输入 → 原文；图片引用提取到列表；不支持的格式抛出 `ValueError` |
| **测试方法** | `pytest tests/unit/test_markitdown_loader.py -v` |

---

#### 阶段 D: Ingestion Pipeline（6h）

**目的**: 完整的数据摄取流水线可用，支持 PDF→Markdown→分块→增强→双路 Embedding→存储。

---

**D1: 文件发现 + SHA256 去重**（1h）

| 项目 | 内容 |
|------|------|
| **修改文件** | `src/knowledge_hub/ingestion/discovery.py`, `src/knowledge_hub/utils/hash.py`, `src/knowledge_hub/ingestion/checksum.py`, `tests/unit/test_discovery.py`, `tests/unit/test_checksum.py` |
| **实现类/函数** | `FileDiscovery.scan(dir) -> list[str]`；`compute_sha256(file_path) -> str`；`ChecksumChecker.should_skip(sha256) -> bool`（查 SQLite） |
| **验收标准** | 递归扫描 `data/raw/`；返回 `.pdf`, `.md`, `.txt` 文件；SHA256 一致性；重复文件跳过 |
| **测试方法** | `pytest tests/unit/test_discovery.py tests/unit/test_checksum.py -v` |

---

**D2: 语义分块 + 上下文注入**（1h）

| 项目 | 内容 |
|------|------|
| **修改文件** | `src/knowledge_hub/ingestion/chunker.py`, `context_injector.py`, `tests/unit/test_chunker.py`, `tests/unit/test_context_injector.py` |
| **实现类/函数** | `SemanticChunker`：封装 LangChain Splitter + Markdown header 感知；`ContextInjector.inject(chunks, images, metadata) -> list[Chunk]` |
| **验收标准** | Markdown 标题切分生效；代码块不被截断；元数据前缀注入；图片描述注入到最近 chunk |
| **测试方法** | `pytest tests/unit/test_chunker.py tests/unit/test_context_injector.py -v` |

---

**D3: Image-to-Text 处理**（1h）

| 项目 | 内容 |
|------|------|
| **修改文件** | `src/knowledge_hub/ingestion/image_processor.py`, `src/knowledge_hub/storage/image_cache.py`, `tests/unit/test_image_processor.py` |
| **实现类/函数** | `ImageProcessor.process(images) -> dict[str, str]`；`ImageCache.get/set/exists()`（SQLite） |
| **验收标准** | Vision LLM 生成图片描述；缓存命中跳过 LLM 调用；返回 `{image_id: description}` 字典 |
| **测试方法** | `pytest tests/unit/test_image_processor.py -v`（mock Vision LLM） |

---

**D4: LLM 增强（可选重写）**（1h）

| 项目 | 内容 |
|------|------|
| **修改文件** | `src/knowledge_hub/ingestion/enhancer.py`, `tests/unit/test_enhancer.py` |
| **实现类/函数** | `LLMEnhancer.rewrite(chunks) -> list[Chunk]`；`LLMEnhancer.summarize(chunks) -> list[Chunk]` |
| **验收标准** | rewrite 后 content 改变但语义保持；enhancement.rewrite=false 时跳过；空 chunk 列表返回空 |
| **测试方法** | `pytest tests/unit/test_enhancer.py -v`（mock LLM） |

---

**D5: 双路 Embedding + Chroma Upsert**（1h）

| 项目 | 内容 |
|------|------|
| **修改文件** | `src/knowledge_hub/ingestion/embedder.py`, `src/knowledge_hub/providers/vectorstore/chroma_store.py`, `src/knowledge_hub/storage/bm25_index.py`, `tests/integration/test_chroma_store.py`, `tests/integration/test_bm25_index.py` |
| **实现类/函数** | `DualEmbedder.embed(chunks) -> list[Chunk]`（Dense embedding）；`ChromaStore(BaseVectorStore)`：`upsert()`, `query()`, `delete()`；`BM25Index`：`build()`, `search()`, `persist()`, `load()` |
| **验收标准** | Chroma 写入后可查回；BM25 索引持久化后重启可加载；批量 embedding 正确 |
| **测试方法** | `pytest tests/integration/test_chroma_store.py tests/integration/test_bm25_index.py -v` |

---

**D6: Ingestion Pipeline 编排**（1h）

| 项目 | 内容 |
|------|------|
| **修改文件** | `src/knowledge_hub/ingestion/pipeline.py`, `tests/integration/test_ingestion_pipeline.py` |
| **实现类/函数** | `IngestionPipeline.run(file_path) -> IngestionResult`；编排 D1→D5 所有步骤 |
| **验收标准** | 给定 PDF/MD 文件，完整摄取流程执行成功；SQLite 记录写入；重复文件跳过；Trace 日志生成 |
| **测试方法** | `pytest tests/integration/test_ingestion_pipeline.py -v` |

---

#### 阶段 E: Retrieval Pipeline（5h）

**目的**: 完整检索流水线可用，支持混合检索 + RRF + 两段式重排。

---

**E1: BM25 检索器**（1h）

| 项目 | 内容 |
|------|------|
| **修改文件** | `src/knowledge_hub/retrieval/bm25_retriever.py`, `tests/unit/test_bm25_retriever.py` |
| **实现类/函数** | `BM25Retriever.retrieve(query, top_k) -> list[RetrievalResult]`；从持久化 BM25 索引查询 |
| **验收标准** | 查询返回 Top-K 结果；分数按 BM25 分数降序；空索引返回空列表 |
| **测试方法** | `pytest tests/unit/test_bm25_retriever.py -v` |

---

**E2: Dense 检索器**（1h）

| 项目 | 内容 |
|------|------|
| **修改文件** | `src/knowledge_hub/retrieval/dense_retriever.py`, `tests/unit/test_dense_retriever.py` |
| **实现类/函数** | `DenseRetriever.retrieve(query, top_k) -> list[RetrievalResult]`；Embedding → Chroma 查询 |
| **验收标准** | 查询返回 Top-K 结果；分数按 cosine similarity 降序 |
| **测试方法** | `pytest tests/unit/test_dense_retriever.py -v`（mock Chroma） |

---

**E3: RRF 融合**（1h）

| 项目 | 内容 |
|------|------|
| **修改文件** | `src/knowledge_hub/retrieval/fusion.py`, `tests/unit/test_rrf_fusion.py` |
| **实现类/函数** | `rrf_fusion(bm25_results, dense_results, k, top_n) -> list[RetrievalResult]` |
| **验收标准** | 融合后去重；分数 = Σ 1/(k + rank)；按分数降序取 Top-N；空输入返回空 |
| **测试方法** | `pytest tests/unit/test_rrf_fusion.py -v` |

---

**E4: 两段式重排**（1h）

| 项目 | 内容 |
|------|------|
| **修改文件** | `src/knowledge_hub/providers/reranker/cross_encoder_reranker.py`, `llm_reranker.py`, `src/knowledge_hub/retrieval/reranker.py`, `tests/unit/test_cross_encoder_reranker.py`, `tests/unit/test_llm_reranker.py` |
| **实现类/函数** | `CrossEncoderReranker(BaseReranker)`：`rerank(query, docs, top_k)`；`LLMReranker(BaseReranker)`：`rerank(query, docs, top_k)`；`RerankerOrchestrator.rerank(fused_results) -> list[RetrievalResult]` |
| **验收标准** | Cross-Encoder 输出按分数降序；LLM Rerank 输出按分数降序；coarse→fine 两段式串联 |
| **测试方法** | `pytest tests/unit/test_cross_encoder_reranker.py tests/unit/test_llm_reranker.py -v` |

---

**E5: Retrieval Pipeline 编排**（1h）

| 项目 | 内容 |
|------|------|
| **修改文件** | `src/knowledge_hub/retrieval/pipeline.py`, `src/knowledge_hub/retrieval/context_assembler.py`, `src/knowledge_hub/retrieval/query_rewriter.py`, `tests/integration/test_retrieval_pipeline.py` |
| **实现类/函数** | `RetrievalPipeline.query(query) -> RetrievalResponse`；`ContextAssembler.assemble(results) -> str`；`QueryRewriter.rewrite(query) -> list[str]` |
| **验收标准** | 完整检索流程执行成功；返回 answer + contexts + trace；LLM 生成回答包含上下文信息 |
| **测试方法** | `pytest tests/integration/test_retrieval_pipeline.py -v` |

---

#### 阶段 F: MCP Server 集成（4h）

**目的**: MCP Server 通过 Stdio 通信，Claude Desktop 可调用。

---

**F1: MCP Tools 定义**（1h）

| 项目 | 内容 |
|------|------|
| **修改文件** | `src/knowledge_hub/mcp/tools.py`, `tests/unit/test_mcp_tools.py` |
| **实现类/函数** | `TOOL_DEFINITIONS: list[Tool]`；`handle_tool_call(name, arguments) -> Any` |
| **验收标准** | 8 个 Tool 定义完整（name, description, inputSchema）；`handle_tool_call` 路由正确；未知 tool 抛出 `ValueError` |
| **测试方法** | `pytest tests/unit/test_mcp_tools.py -v`（mock pipeline） |

---

**F2: MCP Resources 定义**（1h）

| 项目 | 内容 |
|------|------|
| **修改文件** | `src/knowledge_hub/mcp/resources.py`, `tests/unit/test_mcp_resources.py` |
| **实现类/函数** | `RESOURCE_DEFINITIONS: list[Resource]`；`handle_resource_read(uri) -> str` |
| **验收标准** | 4 个 Resource URI 模式定义；`handle_resource_read` 解析 URI 并返回 JSON；无效 URI 抛出错误 |
| **测试方法** | `pytest tests/unit/test_mcp_resources.py -v` |

---

**F3: Tool 处理逻辑**（1h）

| 项目 | 内容 |
|------|------|
| **修改文件** | `src/knowledge_hub/mcp/tools.py`（补充实现）, `tests/integration/test_mcp_tool_handlers.py` |
| **实现类/函数** | `handle_query_knowledge_hub()`, `handle_list_collections()`, `handle_ingest_document()`, `handle_delete_document()`, `handle_get_document_summary()`, `handle_list_documents()`, `handle_get_collection_stats()`, `handle_get_retrieval_trace()` |
| **验收标准** | 每个 tool handler 正确调用对应 pipeline 方法；返回格式符合 MCP 规范；错误处理返回 error message |
| **测试方法** | `pytest tests/integration/test_mcp_tool_handlers.py -v` |

---

**F4: MCP Server Stdio 启动**（1h）

| 项目 | 内容 |
|------|------|
| **修改文件** | `src/knowledge_hub/mcp/server.py`, `src/knowledge_hub/main.py`, `tests/e2e/test_mcp_server.py`, `scripts/run_mcp.sh` |
| **实现类/函数** | `MCPServer.run()`；`main()` 入口 |
| **验收标准** | `python -m knowledge_hub.main` 启动后等待 stdin；输入 MCP initialize 请求返回正确响应；list_tools 返回所有 tool 定义 |
| **测试方法** | `pytest tests/e2e/test_mcp_server.py -v`（子进程模拟 Stdio 通信） |

**Claude Desktop 配置示例**:

```json
// ~/Library/Application Support/Claude/claude_desktop_config.json
{
  "mcpServers": {
    "knowledge-hub": {
      "command": "python",
      "args": ["-m", "knowledge_hub.main"],
      "cwd": "/path/to/knowledge-hub"
    }
  }
}
```

---

#### 阶段 G: 可观测性 + Trace（3h）

**目的**: 全链路 Trace 可记录、可查询、可持久化。

---

**G1: 结构化 JSONL 日志**（1h）

| 项目 | 内容 |
|------|------|
| **修改文件** | `src/knowledge_hub/observability/logger.py`, `tests/unit/test_logger.py` |
| **实现类/函数** | `StructuredLogger.log(event, trace_id, data, duration_ms)`；输出到 `logs/ingestion.jsonl` / `logs/query.jsonl` |
| **验收标准** | 每行一个 JSON 对象；包含 trace_id, event, timestamp, data, duration_ms；文件追加写入 |
| **测试方法** | `pytest tests/unit/test_logger.py -v` |

---

**G2: 全链路 Tracer**（1h）

| 项目 | 内容 |
|------|------|
| **修改文件** | `src/knowledge_hub/observability/tracer.py`, `tests/unit/test_tracer.py` |
| **实现类/函数** | `Tracer.start_trace(trace_type, data) -> trace_id`；`Tracer.log_step(event, data, duration_ms)`；`Tracer.end_trace() -> Trace` |
| **验收标准** | 每个 trace 有唯一 ID；step 按时间顺序记录；`end_trace()` 返回完整 `RetrievalTrace` 对象 |
| **测试方法** | `pytest tests/unit/test_tracer.py -v` |

---

**G3: Trace SQLite 存储**（1h）

| 项目 | 内容 |
|------|------|
| **修改文件** | `src/knowledge_hub/observability/trace_store.py`, `tests/integration/test_trace_store.py` |
| **实现类/函数** | `TraceStore.save(trace)`；`TraceStore.get_by_id(trace_id) -> Trace`；`TraceStore.list_recent(limit) -> list[Trace]` |
| **验收标准** | Trace 写入 SQLite 可查回；按 trace_id 查询返回完整 trace；list_recent 返回最近 N 条 |
| **测试方法** | `pytest tests/integration/test_trace_store.py -v` |

---

#### 阶段 H: 评估框架（3h）

**目的**: 可运行评估，生成指标报告。

---

**H1: 自定义评估指标**（1h）

| 项目 | 内容 |
|------|------|
| **修改文件** | `src/knowledge_hub/evaluation/metrics/hit_rate.py`, `mrr.py`, `context_precision.py`, `context_recall.py`, `tests/unit/test_evaluator_metrics.py` |
| **实现类/函数** | `HitRateMetric.compute(query, response, ground_truth) -> float`；`MRRMetric.compute()`；`ContextPrecisionMetric.compute()`；`ContextRecallMetric.compute()` |
| **验收标准** | hit_rate: 命中=1.0，未命中=0.0；MRR: 第一个命中排名的倒数；precision/recall 计算正确 |
| **测试方法** | `pytest tests/unit/test_evaluator_metrics.py -v` |

---

**H2: 评估运行器**（1h）

| 项目 | 内容 |
|------|------|
| **修改文件** | `src/knowledge_hub/evaluation/evaluator.py`, `report.py`, `data/eval/eval_dataset.json`, `tests/integration/test_evaluator.py` |
| **实现类/函数** | `EvaluationRunner.run(dataset_path) -> EvaluationReport`；`EvaluationReport.summary() -> dict`；`EvaluationReport.to_dataframe()` |
| **验收标准** | 评估数据集正确加载；批量运行查询并计算指标；报告包含每个 query 的每个 metric 分数 |
| **测试方法** | `pytest tests/integration/test_evaluator.py -v`（mock LLM） |

---

**H3: Ragas 集成**（1h）

| 项目 | 内容 |
|------|------|
| **修改文件** | `src/knowledge_hub/evaluation/ragas_evaluator.py`, `tests/unit/test_ragas_evaluator.py` |
| **实现类/函数** | `RagasEvaluator.evaluate(queries, responses, contexts) -> dict`；集成 faithfulness, answer_relevancy |
| **验收标准** | Ragas 指标正确计算；framework=ragas 时使用 Ragas；framework=custom 时使用自定义指标 |
| **测试方法** | `pytest tests/unit/test_ragas_evaluator.py -v`（mock Ragas） |

---

#### 阶段 I: Streamlit Dashboard（5h）

**目的**: 多页面 Dashboard 可视化系统状态和 Trace。

---

**I1: Dashboard 骨架 + 系统总览**（1h）

| 项目 | 内容 |
|------|------|
| **修改文件** | `src/knowledge_hub/dashboard/app.py`, `pages/overview.py`, `components/charts.py`, `components/tables.py`, `scripts/run_dashboard.sh` |
| **实现类/函数** | `app.py`：侧边栏导航 + 页面路由；`overview.render()`：collection 数量、总 chunk 数、总文档数、存储大小、最近摄取/查询记录 |
| **验收标准** | `streamlit run app.py` 启动成功；系统总览页面显示正确统计数据；侧边栏导航可切换页面 |
| **测试方法** | 手动验证 + `streamlit run src/knowledge_hub/dashboard/app.py` |

---

**I2: 数据浏览页面**（1h）

| 项目 | 内容 |
|------|------|
| **修改文件** | `pages/data_browser.py` |
| **实现类/函数** | `data_browser.render()`：collection 下拉框 → 文档列表 → chunk 详情；支持全文搜索、高亮 |
| **验收标准** | 三级浏览（collection→document→chunk）；搜索功能可用；chunk 内容高亮显示 |
| **测试方法** | 手动验证 |

---

**I3: Ingestion 管理页面**（1h）

| 项目 | 内容 |
|------|------|
| **修改文件** | `pages/ingestion_mgr.py` |
| **实现类/函数** | `ingestion_mgr.render()`：文件上传、触发摄取、进度显示、历史记录、删除文档 |
| **验收标准** | 上传文件触发摄取；显示摄取进度和结果；历史记录可查看；删除文档功能可用 |
| **测试方法** | 手动验证 |

---

**I4: 追踪查看页面**（1h）

| 项目 | 内容 |
|------|------|
| **修改文件** | `pages/trace_viewer.py` |
| **实现类/函数** | `trace_viewer.render()`：按 trace_id 查看；可视化各步骤耗时（条形图）；查看 BM25/Dense/Rerank 分数变化 |
| **验收标准** | Trace 列表可分页浏览；点击 trace_id 查看详情；步骤耗时可视化；分数变化折线图 |
| **测试方法** | 手动验证 |

---

**I5: 评估面板页面**（1h）

| 项目 | 内容 |
|------|------|
| **修改文件** | `pages/eval_panel.py` |
| **实现类/函数** | `eval_panel.render()`：运行评估、查看历史结果、指标趋势图、配置对比 |
| **验收标准** | 点击按钮触发评估运行；评估结果以表格展示；指标趋势折线图；不同配置评估结果对比 |
| **测试方法** | 手动验证 |

---

### 6.4 关键里程碑

| 里程碑 | 完成阶段 | 交付物 | 演示能力 |
|--------|----------|--------|----------|
| **M1: 配置与抽象就绪** | A + B | 可运行的配置系统 + 所有 ABC + 工厂 | `Settings.from_yaml()` 加载配置；工厂创建 mock 组件 |
| **M2: Provider 可用** | C | 所有 LLM/Embedding/Splitter/Loader 实现 | 切换 settings.yaml 切换 LLM 提供商 |
| **M3: Ingestion 可用** | D | 完整摄取流水线 | PDF→Chunk→Chroma 全流程 |
| **M4: Retrieval 可用** | E | 完整检索流水线 | 混合检索 + RRF + 两段式重排 |
| **M5: MCP 可用** | F | MCP Server Stdio 通信 | Claude Desktop 调用知识库问答 |
| **M6: 可观测** | G | 全链路 Trace | JSONL 日志 + SQLite 查询 |
| **M7: 可评估** | H | 评估框架 | 运行评估生成报告 |
| **M8: 可视化** | I | Streamlit Dashboard | 5 页面 Dashboard 完整可用 |

---

### 6.5 面试与简历配套（贯穿全程）

每个阶段完成后，同步产出：

| 阶段 | 面试题 | 简历要点 |
|------|--------|----------|
| A-B | "如何设计可插拔架构？" "ABC vs Protocol 的取舍？" | "基于工厂模式+ABC+配置驱动的可插拔架构" |
| C | "OpenAI/Ollama/DeepSeek 接口差异？" "如何统一异步 LLM 调用？" | "统一 4 种 LLM 提供商的异步调用层" |
| D | "RAG 数据摄取有哪些坑？" "如何做增量摄取？" "图片描述如何注入 chunk？" | "支持 SHA256 增量摄取、Vision LLM 图片描述注入的 Ingestion Pipeline" |
| E | "BM25 vs Dense 各自优劣？" "RRF 融合原理？" "两段式重排为什么？" | "BM25+Dense 混合检索，RRF 融合，Cross-Encoder+LLM 两段式重排" |
| F | "MCP 协议是什么？" "Stdio vs HTTP 的取舍？" | "基于 MCP 协议的 AI 助手知识库集成，支持 Claude Desktop/Copilot" |
| G | "RAG 系统如何做可观测？" "Trace 数据结构怎么设计？" | "全链路 Trace + JSONL 结构化日志 + SQLite 持久化" |
| H | "RAG 评估有哪些指标？" "hit_rate vs MRR 区别？" | "可插拔评估框架，支持 Ragas + 自定义指标" |
| I | "如何做 RAG 系统的监控面板？" | "Streamlit 多页面 Dashboard，零外部平台依赖" |

---

## 附录

### A. 面试高频题索引

| 主题 | 文档路径 | 关联阶段 |
|------|----------|----------|
| RAG 基础 | `docs/interview/rag_basics.md` | D, E |
| 混合检索 | `docs/interview/hybrid_retrieval.md` | E |
| RRF 融合 | `docs/interview/rrf_fusion.md` | E |
| 重排策略 | `docs/interview/reranking.md` | E |
| 可插拔架构 | `docs/interview/pluggable_architecture.md` | B |
| MCP 协议 | `docs/interview/mcp_protocol.md` | F |
| RAG 评估 | `docs/interview/rag_evaluation.md` | H |
| 多模态处理 | `docs/interview/multimodal_rag.md` | D |
| 可观测性 | `docs/interview/observability.md` | G |

### B. 简历项目描述模板

```
项目名称：KnowledgeHub — 模块化 RAG + MCP 知识库系统
技术栈：Python 3.11, asyncio, Chroma, BM25, MCP SDK, Streamlit, SQLite, pytest

项目描述：
设计并实现了一个模块化的 RAG（检索增强生成）系统，通过 MCP 协议
（Model Context Protocol）将本地知识库暴露给 Claude Desktop、GitHub Copilot
等 AI 助手，实现基于 Stdio 的本地子进程通信。

核心贡献：
• 设计全链路可插拔架构（工厂模式 + ABC + 配置驱动），LLM、Embedding、
  Reranker、VectorStore、Splitter、Evaluator 六大组件均通过 settings.yaml
  配置切换，首批实现 4 种 LLM 提供商（OpenAI/Azure/Ollama/DeepSeek）
• 实现 BM25 + Dense Embedding 混合检索，使用 RRF 算法融合排序，
  叠加 Cross-Encoder + LLM 两段式重排，检索准确率提升 XX%
• 采用 Vision LLM Image-to-Text 策略处理多模态内容，将图片描述注入
  chunk 文本，无需 CLIP 多模态向量索引
• 构建全链路 Trace 可观测体系（JSONL 结构化日志 + SQLite 持久化），
  配合 Streamlit 多页面 Dashboard 实现零外部平台依赖的本地监控
• 实现可插拔评估框架（Ragas + 自定义 hit_rate/MRR 指标），支持
  批量评估和配置对比
• 基于 TDD 开发，单元/集成/E2E 三层测试，覆盖核心链路
```

### C. 开发环境要求

| 工具 | 版本 | 用途 |
|------|------|------|
| Python | 3.11+ | 运行时 |
| uv / pip | latest | 包管理 |
| pytest | 8.0+ | 测试 |
| ruff | latest | lint + format |
| make | any | 任务运行 |
| ChromaDB | 0.5+ | 向量库 |
| Ollama | latest（可选） | 本地 LLM |
| Claude Desktop | latest（可选） | MCP Client 测试 |

### D. 常用开发命令

```bash
# 安装
make install

# 测试
make test                           # 全部测试
pytest tests/unit/ -v               # 仅单元测试
pytest tests/integration/ -v        # 仅集成测试
pytest -m "not slow" -v             # 跳过慢测试

# 运行
make run-mcp                        # 启动 MCP Server
make run-dashboard                  # 启动 Dashboard

# 摄取
python -m knowledge_hub.scripts.ingest data/raw/

# 评估
python -m knowledge_hub.scripts.eval data/eval/eval_dataset.json

# 代码质量
make lint
```

---

> **文档结束**  
> 本文档随项目开发持续更新，每个阶段完成后回顾并修订相关章节。  
> 最新版本请查看 Git 仓库 `DEV_SPEC.md`。