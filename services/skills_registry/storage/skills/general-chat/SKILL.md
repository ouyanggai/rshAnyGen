---
name: general_chat
title: 通用对话
description: 处理通用对话场景
category: chat
version: 1.0.0
execution_type: function
---

# 通用对话

处理无法通过搜索或知识库查询解决的通用对话场景。

## Use when

- 其他技能无法处理
- 用户进行日常对话
- 闲聊或问候
- 需要调用通用 LLM 能力

## Do not use when

- 有专门的技能可以处理该请求
- 需要从外部获取信息

## Parameters

- `message` (string, required): 对话内容

## Examples

```
User: "你好"
-> general_chat(message="你好")

User: "今天天气怎么样？"
-> general_chat(message="今天天气怎么样？")
```

## Returns

```json
{
  "reply": "回复内容",
  "model": "模型名称",
  "tokens_used": 100
}
```
