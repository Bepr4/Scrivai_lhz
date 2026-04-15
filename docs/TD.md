# Scrivai 任务分解（Task Document）

> **版本**: v3（2026-04-15）
> **v2→v3 变更**：T0.2 统一 pydantic 集中在 `scrivai/models/`；T0.3 改为快照+锁实现；新增 T0.8b（available-tools skill）、T1.0（`build_qmd_client_from_config`）；EvolutionConfig 对齐 EvoSkill 真实 API。**无外部 contracts 依赖**：Scrivai 自包含，qmd 类型经 `from qmd import ...` 用并 re-export。

**依据**: `design.md` + `/home/iomgaa/Projects/GOVDOC_PROGRAM_PLAN.md`
**开发分支**: `feat/v3-p0-cleanup`

---

## 里程碑总览

| 里程碑 | 交付 | 集成点 |
|---|---|---|
| M0（Week 1-2） | 契约冻结 + WorkspaceManager + MockAgentSession + scrivai-cli 骨架 + 通用 skill 草稿 + 契约测试全绿 | I0：用 MockAgentSession 跑通 PES 三阶段 |
| M1（Week 3-5） | 真实 AgentSession（Claude SDK）+ 真实 Library 接 qmd + IO 完整 + 通用 skill 完善 | I1：用真 SDK 跑通小 fixture 端到端 |
| M2（Week 6-7） | EvoSkill 集成 + 并发 + 真实负载验证 | I2：EvoSkill 在 fixture 上跑出至少一个候选分支 |
| M3（Week 8） | PyPI 0.1.0 + 清干旧代码 | I3：旧符号 `git grep` 零结果 |

---

## M0: 契约冻结 + Workspace + Mock（Week 1-2）

### T0.1 重写 `scrivai/__init__.py` 为新 public API
- **DoD**:
  - 仅导出 §4 的符号：`AgentSession, AgentProfile, PhaseConfig, ModelConfig, WorkspaceManager, WorkspaceSpec, WorkspaceHandle, PhaseResult, AgentRunResult, build_agent_session, build_workspace_manager, RuleLibrary, CaseLibrary, TemplateLibrary, LibraryEntry, build_libraries, docx_to_markdown, doc_to_markdown, pdf_to_markdown, DocxRenderer`
  - 旧符号全部不再出现：`LLMClient, LLMConfig, LLMMessage, LLMResponse, LLMUsage, PromptTemplate, FewShotTemplate, OutputParser, PydanticOutputParser, JsonOutputParser, RetryingParser, ExtractChain, AuditChain, GenerateChain, Project, ProjectConfig, KnowledgeStore, AuditEngine, AuditResult, GenerationEngine, GenerationContext, SearchResult, MockLLMClient`
- **依赖**: 无
- **优先级**: P0
- **契约测试挂钩**: `tests/contract/test_public_api.py::test_import_surface`
- **估时**: 0.5d

### T0.2 `scrivai.models` — pydantic + Protocol 集中（v3 调整）
- **DoD**:
  - `scrivai/models/agent.py`: `ModelConfig, PhaseConfig, AgentProfile, PhaseResult, AgentRunResult, AgentSession`（Protocol）
  - `scrivai/models/workspace.py`: `WorkspaceSpec, WorkspaceSnapshot, WorkspaceHandle, WorkspaceManager`（Protocol）
  - `scrivai/models/knowledge.py`: `LibraryEntry, Library`
  - `scrivai/models/evolution.py`: `Evaluator, EvolutionConfig, EvolutionRun`
  - `scrivai/__init__.py` 顶层暴露所有 pydantic + Protocol + 工厂；同时 **re-export qmd 类型**：`from qmd import ChunkRef, SearchResult, CollectionInfo` 转发
  - mypy 通过
- **依赖**: T0.1
- **优先级**: P0
- **契约测试挂钩**: `tests/contract/test_models.py`、`tests/contract/test_reexport.py`（验证 `scrivai.ChunkRef is qmd.ChunkRef`）
- **估时**: 1d

### T0.3 `WorkspaceManager` 真实实现（v3：快照 + 锁）
- **DoD**:
  - 按 design.md §5.2 新版伪代码实现：
    - `shutil.copytree(symlinks=False)` 做内容快照（**不再** symlink）
    - `fcntl` 文件锁防并发撞 run_id
    - `WorkspaceSpec.force` 字段：默认 reject，True 覆盖
    - `WorkspaceSnapshot`（git hash）写入 `meta.json`
    - `archive(success=True)` 打包**完整可复现集**：`snapshot/.claude` + `snapshot/data` + `output` + `logs` + `meta.json`
    - `archive(success=False)` 写 `.failed` 标记
    - `cleanup_old` 同时清 archives 和 failed workspace
  - 契约测试：
    - `test_concurrent_create_rejected`（两进程同时 create 同 run_id）
    - `test_force_recreate`
    - `test_snapshot_preserves_skills`（源修改后 workspace 不变）
    - `test_archive_portability`（归档拷到 `/tmp` 解压能读 meta.json + snapshot）
    - design.md §4.5 不变量 1-4
  - Linux/macOS（Windows 后续）
- **依赖**: T0.2
- **优先级**: P0
- **契约测试挂钩**: `tests/contract/test_workspace.py`
- **估时**: 2d（v3 扩大 +0.5d）

### T0.4 `MockAgentSession`（`scrivai.testing.mock_agent`）
- **DoD**:
  - 接收预录 trajectory 列表（list of `AgentRunResult`），按调用顺序返回
  - 支持按 `task_prompt` 关键词选择不同 trajectory
  - 不依赖 claude-agent-sdk 包
  - 用于 Scrivai 自己 + GovDoc 单测
- **依赖**: T0.2
- **优先级**: P0
- **契约测试挂钩**: `tests/contract/test_mock_agent.py`
- **估时**: 0.5d

### T0.5 `scrivai.knowledge` — Library 三兄弟
- **DoD**:
  - `LibraryEntry, Library, RuleLibrary, CaseLibrary, TemplateLibrary` pydantic + Protocol
  - 实现：构造时 `qmd.create_collection("rules"/"cases"/"templates")` 若不存在
  - `add/get/list/delete/search` 闭环
  - 元数据完全持久化在 qmd chunk metadata（不维护内存）
  - `build_libraries(qmd_client)` 工厂
- **依赖**: T0.1, qmd T0.4
- **优先级**: P0
- **契约测试挂钩**: `tests/contract/test_libraries.py`
- **估时**: 1.5d

### T0.6 `scrivai.io` — 工具骨架
- **DoD**:
  - `docx_to_markdown / doc_to_markdown / pdf_to_markdown` 函数签名就位
  - docx → md 用 pandoc 子进程（实现）
  - doc → md 用 LibreOffice → pandoc（实现）
  - PDF → md 走 docling（不可用时抛 NotImplementedError）
  - `DocxRenderer` 基于 docxtpl；`list_placeholders` 用正则
- **依赖**: T0.1
- **优先级**: P0
- **估时**: 1.5d

### T0.7 `scrivai-cli` 入口 + JSON 输出子命令
- **DoD**:
  - `scrivai/cli/__main__.py`：argparse 路由 `library / io / workspace` 三个 group
  - 所有命令：JSON stdout、error JSON stderr、退出码、env 回退（`SCRIVAI_PROJECT_ROOT, QMD_DB_PATH, SCRIVAI_WORKSPACE_ROOT, SCRIVAI_ARCHIVES_ROOT`）
  - `pyproject.toml` 注册 `scrivai-cli` entry point
  - **CLI 输出 JSON 与对应 Python API `model_dump(mode="json")` 严格一致**
  - 命令冷启动 P50 < 300ms
- **依赖**: T0.5, T0.6, T0.3
- **优先级**: P0
- **契约测试挂钩**: `tests/contract/test_cli.py`
- **估时**: 1.5d

### T0.8 通用 Skill 草稿（`Scrivai/skills/`）
- **DoD**:
  - `skills/search-knowledge/SKILL.md`、`skills/inspect-document/SKILL.md`、`skills/render-output/SKILL.md`
  - 每份按 design.md §4.6 标准格式（YAML frontmatter + Markdown body）
  - 明确列出对应 CLI 命令的调用方式 / 输出 JSON 结构 / Tips
  - 通过 mock workspace 验证 SKILL.md **经快照复制**到 `working/.claude/skills/`（v3：不再 symlink）
- **依赖**: T0.3, T0.7
- **优先级**: P0
- **估时**: 1d

### T0.8b available-tools skill（v3 新增）
- **DoD**:
  - `Scrivai/skills/available-tools/SKILL.md` 枚举 `scrivai-cli` + `qmd` 每个子命令
  - 每命令含：参数列表、输出 JSON shape 示例、典型错误
  - 通用 agent profile（`auditor.yaml` 等）的 `skills_required` 默认含 `available-tools`
- **依赖**: T0.7、T0.8
- **优先级**: P0
- **估时**: 0.5d

### T0.9 通用 Agent Profile 草稿（`Scrivai/agents/`）
- **DoD**:
  - `agents/extractor.yaml`、`agents/auditor.yaml`、`agents/generator.yaml`
  - 每份含 plan/execute/summarize 三 phase 配置
  - YAML 加载（`load_agent_profile`）通过；schema 校验通过
- **依赖**: T0.2, T0.8
- **优先级**: P0
- **估时**: 0.5d

### T0.10 PESRunner 骨架（用 MockAgentSession）
- **DoD**:
  - `agent/runner.py` 实现 PES 三阶段串接（design §5.1 伪代码的"上层"）
  - 用 MockAgentSession 跑通：plan → execute → summarize 顺序、context 拼接、PhaseResult 收集、错误中断
  - 写 phase 日志到 workspace.logs_dir
- **依赖**: T0.2, T0.4
- **优先级**: P0
- **契约测试挂钩**: `tests/contract/test_pes_runner.py`
- **估时**: 1.5d

### T0.11 契约测试 pytest plugin（`scrivai.testing.contract`）
- **DoD**:
  - 提供 fixtures：`scrivai_workspace_manager`, `scrivai_qmd_client`, `scrivai_libraries`
  - 套件覆盖 design.md §4.5 全部不变量
  - 可被 GovDoc 复用：`pytest --pyargs scrivai.testing.contract`
- **依赖**: T0.3-T0.10
- **优先级**: P0
- **估时**: 1d

### T0.12 跑通 qmd 契约测试（双向验证）
- **DoD**: Scrivai venv 里 `pytest --pyargs qmd.testing.contract` 全绿
- **依赖**: qmd T0.5
- **优先级**: P0
- **估时**: 0.2d

**M0 DoD 汇总**: T0.1-T0.12；契约测试在 MockAgentSession + FakeQmd 下全绿；I0 通过。

---

## M1: 真实 AgentSession + 真实集成（Week 3-5）

### T1.0 `build_qmd_client_from_config` 工厂（v3 新增）
- **DoD**:
  - `scrivai/__init__.py` 暴露 `build_qmd_client_from_config(db_path)`
  - 内部封装 `import qmd; qmd.connect(db_path)`
  - 返回对象满足 `QmdClient` Protocol（contracts）
  - 契约测试：业务层仅通过此函数获取 qmd client
- **依赖**: T0.5
- **优先级**: P0
- **估时**: 0.2d

### T1.1 接通 Claude Agent SDK
- **DoD**:
  - `_AgentSession.run` 真实实现 design §5.1
  - 用 `query()`（无状态）调 SDK；逐 phase 顺序跑
  - 解析 `AssistantMessage / UserMessage / ResultMessage`，提取 `text / turns / usage`
  - 异常捕获 → `PhaseResult.error`
  - `cwd = workspace.working_dir`；env 注入 `SCRIVAI_PROJECT_ROOT, QMD_DB_PATH, GOVDOC_RUN_ID`
  - `setting_sources=["project"]`；`mcp_servers={}`
- **依赖**: T0.2, T0.3
- **优先级**: P0
- **估时**: 2d

### T1.2 多供应商（Claude / GLM / MiniMax）适配
- **DoD**:
  - `ModelConfig` 的 `model + base_url + api_key` 正确传给 SDK
  - 至少跑通 claude-sonnet-4-6 + glm-5.1 各一次小 query
  - 输出格式差异在 contract test 中标注（不阻断）
- **依赖**: T1.1
- **优先级**: P0
- **估时**: 1d

### T1.3 PES context 传递 + phase log 持久化
- **DoD**:
  - plan.text 拼到 execute 的 system_prompt
  - execute.text 拼到 summarize 的 system_prompt
  - 每个 phase 完成时 dump trajectory 到 `workspace.logs_dir / f"{phase}.json"`
  - meta.json 增补 phase 进度
- **依赖**: T1.1
- **优先级**: P0
- **估时**: 1d

### T1.4 Library 真实对接 qmd
- **DoD**:
  - `build_libraries(qmd_client)` 接受真 `QmdClient`
  - `add` 触发真实分块 + embedding（透传到 qmd）
  - `search` 通过 `qmd.hybrid_search`
  - `get/list/delete` 通过 metadata filters
- **依赖**: T0.5, qmd T1.x
- **优先级**: P0
- **估时**: 1d

### T1.5 IO 工具完善
- **DoD**:
  - pandoc 处理表格/公式/图片替代文本边缘情况
  - `docx_to_markdown` 对 fixture `tender_small.docx` 产出合理 md
  - `DocxRenderer` 渲染 fixture `workpaper_template.docx`（含循环、表格、页眉页脚）
- **依赖**: T0.6
- **优先级**: P0
- **估时**: 2d

### T1.6 通用 Skill 内容打磨
- **DoD**:
  - `search-knowledge/SKILL.md`：补充 5 个真实查询示例 + 错误处理
  - `inspect-document/SKILL.md`：详述如何从 chunk_id 反向定位原文段落
  - `render-output/SKILL.md`：详述 docxtpl 上下文 schema 约定
- **依赖**: T0.8
- **优先级**: P0
- **估时**: 1d

### T1.7 真实 LLM 跑 fixture
- **DoD**:
  - 用 `Scrivai/agents/auditor.yaml` + 真实 SDK + fixture `tender_small.md` + `checkpoints_golden.json` 端到端跑一次
  - PhaseResult 三段都有 text/turns/usage
  - workspace 归档到 archives_root
  - **此测试不阻断 CI（需 API key），但本地必须能跑**
- **依赖**: T1.1-T1.6
- **优先级**: P0
- **估时**: 1.5d

**M1 DoD**: I1 通过；契约测试在真实 SDK + 真实 qmd 下全绿；fixture 端到端可跑。

---

## M2: EvoSkill + 并发 + 稳定性（Week 6-7）

### T2.1 `scrivai.evolution` 数据模型
- **DoD**:
  - `EvolutionConfig, EvolutionRun, Evaluator` Protocol pydantic
  - 字节级匹配 design.md §4.8
- **依赖**: M1
- **优先级**: P0
- **估时**: 0.5d

### T2.2 Base run + trajectory 收集
- **DoD**:
  - `evolution/runner.py::run_base_pass` 跑 eval_dataset 全部任务，收集 trajectory + score
- **依赖**: T2.1
- **优先级**: P0
- **估时**: 1d

### T2.3 Proposer + Generator
- **DoD**:
  - `proposer.py`：用 proposer_model 分析失败 trajectory，产出 N 条 SKILL.md 修改提议
  - `generator.py`：把每条提议生成具体 SKILL.md diff，git commit 到分支 `evo/<timestamp>-<idx>`
  - 不写 main 分支
- **依赖**: T2.1
- **优先级**: P0
- **估时**: 2d

### T2.4 Frontier
- **DoD**:
  - 在每个候选分支跑 evaluator → 打分
  - 留 top-N 分支
  - 输出 `EvolutionRun` 含 `promoted_branch`（最高分超过 base 时）
- **依赖**: T2.3
- **优先级**: P0
- **估时**: 1.5d

### T2.5 EvoSkill 在 fixture 上跑通
- **DoD**:
  - 用 `checkpoints_golden.json` 作为 eval_dataset
  - 业务层提供 `Evaluator`（IoU 评分）
  - 至少跑出 1 个候选分支；若分数高于 base，给出 `promoted_branch` 名
- **依赖**: T2.4
- **优先级**: P0
- **估时**: 1d

### T2.6 并发 + 大文档压测
- **DoD**:
  - PES 内 execute 阶段允许 agent 自己并发跑 tool（SDK 默认）
  - 100 页文书 + 30 checkpoint 端到端 ≤ 10 分钟
  - 失败率 ≤ 5%
- **依赖**: M1
- **优先级**: P0
- **估时**: 1.5d

### T2.7 日志与可观察性（loguru）
- **DoD**:
  - phase 启动/结束打 usage
  - 失败时记录原 prompt 前 200 字 + 错误堆栈
  - workspace meta.json 累积 phase 进度
- **依赖**: M1
- **优先级**: P1
- **估时**: 0.5d

---

## M3: 打包发布（Week 8）

### T3.1 删旧代码
- **DoD**:
  - 旧目录整体删除：`scrivai/audit/`、`scrivai/generation/`、`scrivai/project.py`、`scrivai/llm.py`（旧版）、`scrivai/knowledge/store.py`（旧版）
  - 新结构（`scrivai/agent/ scrivai/cli/ scrivai/knowledge/ scrivai/io/ scrivai/evolution/ scrivai/testing/`）
  - **验收脚本**（design.md §7）零结果
- **依赖**: M2
- **优先级**: P0
- **估时**: 1d

### T3.2 pyproject 0.1.0 + 依赖锁定
- **DoD**:
  - 版本 0.1.0
  - 依赖：`claude-agent-sdk>=X`、`qmd>=0.1.0`、`pydantic>=2`、`pyyaml`、`docxtpl`、`pandoc-cli`（系统依赖）
  - CHANGELOG 标"完全重写：切换为 Claude Agent SDK 范式"
- **依赖**: T3.1
- **优先级**: P0
- **估时**: 0.3d

### T3.3 README + 示例
- **DoD**:
  - README 反映新定位（"Claude Agent 编排框架"）
  - `examples/` 提供独立 demo：自包含 agent + skill + 跑一次审核（不依赖 GovDoc）
- **依赖**: T3.1
- **优先级**: P1
- **估时**: 1d

### T3.4 私有 PyPI 发布（可选）
- **依赖**: T3.2
- **优先级**: P1
- **估时**: 0.3d

---

## Deprecation Target（M3 验收清单）

`Scrivai/scrivai/` 源码 **零出现** 以下符号：

```
LLMClient, LLMConfig, LLMMessage, LLMResponse, LLMUsage,
PromptTemplate, FewShotTemplate,
OutputParser, PydanticOutputParser, JsonOutputParser, RetryingParser,
ExtractChain, AuditChain, GenerateChain,
ExtractInput, ExtractOutput, ExtractedItem,
AuditInput, AuditOutput, AuditFinding, Checkpoint,
GenerateInput, GenerateOutput, SectionSpec, GeneratedSection,
Project, ProjectConfig, KnowledgeStore, AuditEngine, AuditResult,
GenerationEngine, GenerationContext,
SearchResult,    # 由 qmd 提供
MockLLMClient
```

验收脚本（CI）：

```bash
cd /home/iomgaa/Projects/Scrivai
bad=""
for sym in LLMClient LLMConfig LLMMessage LLMResponse LLMUsage \
           PromptTemplate FewShotTemplate OutputParser PydanticOutputParser \
           JsonOutputParser RetryingParser ExtractChain AuditChain GenerateChain \
           Project ProjectConfig KnowledgeStore AuditEngine AuditResult \
           GenerationEngine GenerationContext MockLLMClient; do
  if git grep -q "\\b$sym\\b" -- 'scrivai/**/*.py'; then
    bad="$bad $sym"
  fi
done
[ -z "$bad" ] && echo "OK" || { echo "FAIL:$bad"; exit 1; }

# 业务术语洁净
grep -rE "招标|政府采购|审核点|底稿|投标人" scrivai/ && echo "FAIL: business terms leaked" && exit 1
echo "All clean."
```

---

## 跨项目集成任务

| 任务 | 集成点 | 说明 |
|---|---|---|
| 消费 qmd 的 `FakeQmdClient` 跑契约 | I0 | M0 必须 |
| 暴露 `MockAgentSession + TempWorkspaceManager + scrivai.testing.contract` 给 GovDoc | I0 | GovDoc 单测必需 |
| Library 固定 collection 名（"rules"/"cases"/"templates"） | I0 | 写入契约 |
| 与 qmd 协商批量 add API | I1→I2 | 走 PLAN §8 流程 |
| EvoSkill 评测集格式与 GovDoc 对齐 | I2 | 业务层产 dataset，Scrivai 消费 |

---

## 风险 & 纠偏

| 风险 | 缓解 |
|---|---|
| Claude Agent SDK 版本演进破坏 API | 锁定 minor 版本；M0 末跑 SDK smoke test 校验 |
| 兼容供应商（GLM/MiniMax）实际行为偏差大 | M1 双跑校验；prompt 中明确"以 JSON 格式回复"等约束 |
| Workspace symlink 在某些文件系统失败（NFS、Docker bind mount） | M1 在 docker-compose 环境跑一次完整 fixture |
| EvoSkill Proposer 提议过多无关 / 低质量修改 | Generator 限制 N（默认 5）；Evaluator 严格筛 |
| PES 三阶段过度拆分导致某些短任务低效 | 对小任务可设 plan max_turns=2，降低开销 |
| 业务术语漏入 Scrivai | pre-commit hook + CI grep |

---

## 日常节奏

- 每天 commit 前：`ruff check . --fix && ruff format . && pytest tests/unit/ tests/contract/`
- 每周五：偏移自检（`GOVDOC_PROGRAM_PLAN.md §11`）
- M0/M1/M2/M3 末：在 `INTEGRATION_ISSUES.md` 汇报
