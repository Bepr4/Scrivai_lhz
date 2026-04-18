#!/usr/bin/env python3
"""Example 01: AuditorPES 审核单文档

演示:用 AuditorPES 对一份设备运维巡视记录做对照审核(checkpoints.json 指定要点)。

运行(需已配 .env 并激活 scrivai 环境):

    conda run -n scrivai python examples/01_audit_single_doc.py

预期输出:
    === AuditorPES 审核结果 (status=completed) ===
      CP001 合格: ...
      CP002 合格: ...
      CP003 合格: ...
    总结: {'total': 3, '合格': 3, ...}

依赖环境变量(可经 .env):
    ANTHROPIC_BASE_URL, ANTHROPIC_AUTH_TOKEN
    SCRIVAI_DEFAULT_MODEL    (可选,默认 glm-5.1)
    SCRIVAI_DEFAULT_PROVIDER (可选,默认 glm)
"""

from __future__ import annotations

import asyncio
import os
import shutil
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel

from scrivai import (
    AuditorPES,
    ModelConfig,
    WorkspaceSpec,
    build_workspace_manager,
    load_pes_config,
)

load_dotenv()


class Finding(BaseModel):
    checkpoint_id: str
    verdict: str
    evidence: list[dict[str, Any]] = []
    reasoning: str = ""


class AuditOutput(BaseModel):
    findings: list[Finding]
    summary: dict[str, int] = {}


def _require_env() -> None:
    if not os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        sys.exit("[ERROR] 未设置 ANTHROPIC_AUTH_TOKEN,请配置 .env(见 README)")


async def main() -> None:
    _require_env()
    repo_root = Path(__file__).resolve().parents[1]
    data_dir = repo_root / "examples" / "data"

    # 1. 构造 workspace(隔离目录 + skill 快照)
    ws_mgr = build_workspace_manager(
        workspaces_root="/tmp/scrivai-examples/ws",
        archives_root="/tmp/scrivai-examples/archives",
    )
    workspace = ws_mgr.create(
        WorkspaceSpec(
            run_id="example-01-audit",
            project_root=repo_root,
            force=True,
        )
    )

    # 2. 把业务数据预置到 workspace.data_dir(AuditorPES 契约要求)
    shutil.copy(data_dir / "checkpoints.json", workspace.data_dir / "checkpoints.json")
    shutil.copy(data_dir / "maintenance_report.md", workspace.data_dir / "document.md")

    # 3. 加载 AuditorPES config + model
    config = load_pes_config(repo_root / "scrivai" / "agents" / "auditor.yaml")
    model = ModelConfig(
        model=os.environ.get("SCRIVAI_DEFAULT_MODEL", "glm-5.1"),
        provider=os.environ.get("SCRIVAI_DEFAULT_PROVIDER", "glm"),
    )

    # 4. 构造 PES 并跑
    pes = AuditorPES(
        config=config,
        model=model,
        workspace=workspace,
        runtime_context={
            "output_schema": AuditOutput,
            "evidence_required": False,
        },
    )
    task_prompt = (
        "请对 data/document.md 按 data/checkpoints.json 中的 3 条要点做对照审核。"
        "为每条 checkpoint 产出一个 working/findings/<cp_id>.json,"
        "verdict 从 {合格,不合格,不适用,需要澄清} 中选一。"
        "重要:写入所有 JSON 文件(plan.json / findings/*.json / output.json)时"
        '必须经 Bash 调 `python -c \'import json; json.dump(obj, open(p,"w"),'
        " ensure_ascii=False, indent=2)'`,不要手写 JSON 字符串(避免中文标点导致"
        "非法 JSON)。"
    )
    run = await pes.run(task_prompt)

    # 5. 输出结果
    print(f"\n=== AuditorPES 审核结果 (status={run.status}) ===\n")
    if run.status != "completed":
        print(f"[FAIL] {run.error}")
        sys.exit(1)
    output = AuditOutput.model_validate(run.final_output)
    for f in output.findings:
        print(f"  {f.checkpoint_id} {f.verdict}: {f.reasoning[:80]}")
    print(f"\n总结: {output.summary}")
    print(f"\nWorkspace 目录(含 working/output/logs 可 inspect): {workspace.root_dir}")


if __name__ == "__main__":
    asyncio.run(main())
