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
