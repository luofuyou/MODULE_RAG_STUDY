我想写一份完整的开发规范文档(DEV_SPEC) ,用于指导一个Python项目的全部开发流程。请帮我生成一个大致的框架和初步内容。 项目是什么 我要做一个模块化的 RAG （Retrieval-Augmented Generation） 系统，同时把它包装成一个 MCP Server (Model Context Protocol) ,这样 GitHub Copilot, Claude Desktop等 Al 助手可以直接调用我的知识库进行问答。 通信方式使用 Stdio Transport（本地子进程模式），不做 HTTP 部署。 项目定位与特色 这个项目不仅是一个功能完备的系统，更重要的是它是一个面向学习和面试求职的实战项目："教是最好的学"——我会边做边录视频教学，所以架构设计要清晰、易于讲解 配套有技术文档、代码示范和视频讲解 每个模块会整理面试高频题和简历撰写建议 开箱即用但同时支持深度扩展，可以作为简历项目 我已有的技术方向（需要体现在文档中） 
1. RAG策略: 智能分块（语义感知，不是简单定长切分）+ 上下文增强（元数据、图片描述注入 chunk）混合检索： BM25 （稀疏） + Dense Embedding （稠密) ，用 RRF 融合精排重排：支持 Cross-Encoder 和 LLM Rerank，两段式（粗排→精排）
2. 全链路可插拔架构: LLM、 Embedding、 Reranker、 VectorStore、 Splitter、 Evaluator 都要能通过配置切换 工厂模式+抽象基类 + 配置驱动(settings.yaml) 首批实现: Azure OpenAI、 OpenAI、 Ollama, DeepSeek (LLM) ; Chroma (向量库) ;LangChain RecursiveCharacterTextSplitter (切分) 
3. 多模态:采用Image-to-Text策略(Vision LLM生成图片描述,缝进chunk文本) ,不用 CLIP 多模态向量 
4. 可观测性： 全链路 Trace (Ingestion 链路 + Query 链路) ，用结构化 JSON Lines 日志Streamlit 本地 Dashboard，不依赖 LangSmith 等外部平台 Dashboard要有多个页面:系统总览、数据浏览、Ingestion管理、追踪查看、评估面板等 
5. 评估体系:可插拔评估框架,支持Ragas和自定义指标(hit_rate、MRR 等) 
6. MCP 集成:用Python官方 MCP SDK,暴露 tools (query_knowledge_hub list_collections, get_document_summary 等) 
7. 数据摄取: PDF→Markdown (用MarkItDown)→分块→LLM增强(重写、元数据注入、图片描述)→双路Embedding →Chroma Upsert,支持 SHA256增量跳过

文档结构要求 

请按以下结构来组织这份 DEV_SPEC: 
1. 项目概述:设计理念、项目定位 
2. 核心特点：每个亮点的简要说明 
3.技术选型: RAG核心流水线设计(Ingestion Pipeline, Retrieval Pipeline,要详细) MCP 服务设计 可插拔架构设计（接口定义、配置管理） 可观测性与 Dashboard 设计 多模态图片处理设计 
4. 测试方案: TDD理念,分层测试(单元/集成/E2E) , RAG质量评估 
5. 系统架构与模块设计： 整体架构图(ASCII art) 完整的目录结构树 模块职责说明表 数据流说明（Ingestion Flow、 Query Flow) 配置驱动设计示例 
6. 项目排期： 按阶段划分（A→I），每阶段有明确目的 每个子任务要有：修改文件列表、实现的类/函数、验收标准、测试方法 约 1 小时一个可验收增量 包含进度跟踪表

其他要求 

语言：中文 技术栈: Python,不使用LlamaIndex/LangChain框架(仅使用LangChain的splitter) 向量库先只实现 Chroma，架构上预留扩展 本地优先,轻量级，零外部服务依赖(SQLite做持久化) 测试框架用 pytest