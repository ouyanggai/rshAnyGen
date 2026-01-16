---
name: text_summary
title: 文本摘要
description: 对长文本进行摘要提取
category: text_processing
version: 1.0.0
execution_type: function
---

# 文本摘要

对长文本进行智能摘要，提取关键信息和核心观点。

## Use when

- 需要总结长文档
- 需要提取文章要点
- 需要生成会议纪要摘要
- 需要压缩大量文本

## Do not use when

- 文本已经很短
- 需要保留所有细节

## Parameters

- `text` (string, required): 待摘要的文本内容
- `max_length` (integer, optional): 摘要最大长度（默认: 200）
- `style` (string, optional): 摘要风格（默认: "concise"，可选: "bullet", "detailed"）

## Examples

```
User: "帮我总结这篇文章"
-> text_summary(text="文章内容...", max_length=200, style="concise")

User: "提取要点"
-> text_summary(text="文档内容...", style="bullet")
```

## Returns

```json
{
  "summary": "摘要内容",
  "original_length": 1000,
  "summary_length": 150,
  "compression_ratio": 0.15,
  "style": "concise"
}
```
