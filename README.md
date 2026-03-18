# Scrivai

可配置的通用文档生成与审核框架。

## 概述

面向横向项目中反复出现的两类需求：
- **审核**：基于规章制度/标准，逐要点审核文档合规性，输出审核报告
- **生成**：基于用户输入 + 历史案例库，按固定章节模板生成长文档，保证全文连贯

## 架构

```
SDK / API / CLI
      │
  编排层 (Orchestrator)
      │
  ┌───┴───┐
生成引擎  审核引擎
  └───┬───┘
   知识库 (qmd)
```

详见 `docs/architecture.md`。

## 快速开始

```python
import scrivai

project = scrivai.Project("scrivai-project.yaml")

# 审核
report = project.audit(document="doc.md")

# 生成
doc = project.generate(inputs={...})

# 生成 + 自审
doc = project.generate_and_review(inputs={...})
```

## 开发

```bash
conda activate scrivai
pytest tests/ -v
```
