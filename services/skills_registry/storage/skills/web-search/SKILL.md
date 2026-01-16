---
name: web_search
title: Web Search
description: Search the web for current information
category: search
version: 1.0.0
---

# Web Search

Search the web using your preferred search engine to find current information, news, and facts.

## Use when

- User asks for current events, news, or recent information
- User needs to verify facts or find up-to-date data
- User requests information that may have changed recently

## Do not use when

- The information is already in your training data
- User asks about general knowledge that doesn't require current data
- User explicitly says they don't need web search

## Parameters

- `query` (string, required): The search query
- `top_n` (integer, optional): Number of results (default: 5, max: 10)
