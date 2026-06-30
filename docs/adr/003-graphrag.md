# ADR-003: GraphRAG 知识图谱 + 降级策略

## 状态

已采纳（2026 年 2 月）

## 背景

问答系统需要从知识库检索钱币相关信息。纯关键词检索（SQLite LIKE）召回率低，需要语义+结构化的检索方案。

## 决策

采用 **微软 GraphRAG（Global + Local 双模式）+ SQLite 关键词兜底** 三级降级架构。

## 理由

1. **GraphRAG Global Search**：利用知识图谱的社区结构，回答宏观问题（"清朝钱币有哪些特点？"）
2. **GraphRAG Local Search**：基于 ChromaDB 向量检索，精确定位具体实体
3. **SQLite LIKE 兜底**：当 GraphRAG 不可用时（依赖缺失、API 异常），自动降级到关键词检索
4. **LLM 最终兜底**：数据库也搜不到时，由 LLM 基于自身知识回答

## 查询流程

```
用户提问
    │
    ├─→ GraphRAG Local (ChromaDB + LLM)    [首选]
    │   └─→ 失败 → 关键词检索 (SQLite LIKE)
    │
    ├─→ GraphRAG Global (社区摘要 + LLM)   [备选]
    │   └─→ 失败 → 关键词检索
    │
    └─→ 联网搜索 (Tavily + LLM)            [可选]
        └─→ 失败 → 关键词检索
            └─→ 失败 → LLM 直接回答
```

## 代价

- 依赖 `langchain_graphrag` 包（与 Python 3.13 有兼容问题）
- Neo4j 可选但启动开销较大
- ChromaDB 嵌入调用硅基流动 API（有网络依赖）

## 备选方案

| 方案 | 优点 | 缺点 |
|------|------|------|
| **纯 RAG (LangChain)** | 简单直接 | 无图结构，回答缺乏全局视角 |
| **Neo4j Cypher** | 强大的图查询 | 需要写复杂的 Cypher 语句 |
| **Elasticsearch** | 全文搜索成熟 | 运维重，无图语义 |
