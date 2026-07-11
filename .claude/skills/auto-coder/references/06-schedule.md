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