---
name: knowledge_query
title: 内部知识库查询
description: 从内部知识库检索相关文档
category: knowledge
version: 1.0.0
execution_type: function
---

# 内部知识库查询

从用户的内部知识库检索相关文档、技术文档等。

## Use when

- 用户询问关于公司内部文档
- 用户查询技术规范
- 用户询问历史项目信息
- 需要从内部知识库获取专业信息

## Do not use when

- 用户询问一般性知识
- 用户询问与内部知识库无关的内容
- 需要实时网络搜索

## Parameters

- `query` (string, required): 查询内容，用于检索相关文档
- `top_k` (integer, optional): 返回结果数量（默认: 5, 最大: 10）

## Examples

```
User: "我们的 API 认证机制是什么？"
-> knowledge_query(query="API 认证机制", top_k=3)

User: "项目中使用的数据结构"
-> knowledge_query(query="数据结构 设计", top_k=5)
```

## Returns

```json
{
  "results": [
    {
      "doc_id": "doc-123",
      "title": "文档标题",
      "content": "文档内容片段",
      "score": 0.95,
      "metadata": {}
    }
  ],
  "total": 5,
  "query": "查询内容"
}
```
