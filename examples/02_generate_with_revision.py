#!/usr/bin/env python3
"""Example 02: GeneratorPES 用 docxtpl 模板生成文档

演示 3 件事:
  1. 运行时构造 docxtpl 模板(避免入库 .docx 二进制)
  2. GeneratorPES 填充占位符产出 output.json
  3. --render 开关追加 docx 渲染

运行(需已配 .env 并激活 scrivai 环境):

    conda run -n scrivai python examples/02_generate_with_revision.py            # 不渲染 docx
    conda run -n scrivai python examples/02_generate_with_revision.py --render   # 渲染 docx

产出:
    /tmp/scrivai-examples/ws/<run_id>/working/output.json
    /tmp/scrivai-examples/ws/<run_id>/output/final.docx(--render 时)

依赖环境变量(可经 .env):
    ANTHROPIC_BASE_URL, ANTHROPIC_AUTH_TOKEN
    SCRIVAI_DEFAULT_MODEL    (可选,默认 glm-5.1)
    SCRIVAI_DEFAULT_PROVIDER (可选,默认 glm)
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Any

# examples 不是 package(无 __init__.py),把 examples/ 加入 sys.path 后走相对模块路径
sys.path.insert(0, str(Path(__file__).resolve().parent))

from data.simple_template import build_template  # noqa: E402
from dotenv import load_dotenv  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from scrivai import (  # noqa: E402
    GeneratorPES,
    ModelConfig,
    WorkspaceSpec,
    build_workspace_manager,
    load_pes_config,
)

load_dotenv()


class Section(BaseModel):
    placeholder: str
    content: str = ""
    source_refs: list[dict[str, Any]] = []


class GeneratorOutput(BaseModel):
    context: dict[str, str] = {}
    sections: list[Section] = []


def _require_env() -> None:
    if not os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        sys.exit("[ERROR] 未设置 ANTHROPIC_AUTH_TOKEN,请配置 .env(见 README)")


async def main(render: bool) -> None:
    _require_env()
    repo_root = Path(__file__).resolve().parents[1]

    # 1. 运行时生成 docxtpl 模板(避免入库 .docx 二进制)
    template_path = Path("/tmp/scrivai-examples/simple_template.docx")
    build_template(template_path)

    # 2. 构造 workspace(隔离目录 + skill 快照)
    ws_mgr = build_workspace_manager(
        workspaces_root="/tmp/scrivai-examples/ws",
        archives_root="/tmp/scrivai-examples/archives",
    )
    workspace = ws_mgr.create(
        WorkspaceSpec(
            run_id=f"example-02-gen-{'render' if render else 'nodocx'}",
            project_root=repo_root,
            force=True,
        )
    )

    # 3. 加载 GeneratorPES config + model
    config = load_pes_config(repo_root / "scrivai" / "agents" / "generator.yaml")
    model = ModelConfig(
        model=os.environ.get("SCRIVAI_DEFAULT_MODEL", "glm-5.1"),
        provider=os.environ.get("SCRIVAI_DEFAULT_PROVIDER", "glm"),
    )

    # 4. 构造 PES 并跑
    pes = GeneratorPES(
        config=config,
        model=model,
        workspace=workspace,
        runtime_context={
            "template_path": template_path,
            "context_schema": GeneratorOutput,
            "auto_render": render,
        },
    )
    task_prompt = (
        "请基于以下工程输入填充 docxtpl 模板的 3 个占位符,产出工程概况章节。\n"
        "输入字段:\n"
        "  - project_name: 220kV 华阳变电站扩建工程\n"
        "  - project_location: 广东省广州市天河区\n"
        "  - project_scale: 新增主变 2 台,单台容量 180 MVA\n"
        "重要:写入所有 JSON 文件(plan.json / findings/*.json / output.json)时"
        '必须经 Bash 调 `python -c \'import json; json.dump(obj, open(p,"w"),'
        " ensure_ascii=False, indent=2)'`,不要手写 JSON 字符串(避免中文全角标点"
        "导致非法 JSON)。"
    )
    run = await pes.run(task_prompt)

    # 5. 输出结果
    print(f"\n=== GeneratorPES 生成结果 (status={run.status}) ===\n")
    if run.status != "completed":
        print(f"[FAIL] {run.error}")
        sys.exit(1)
    output = GeneratorOutput.model_validate(run.final_output)
    for s in output.sections:
        print(f"  {{{{ {s.placeholder} }}}} → {s.content[:80]}")
    if render:
        final_docx = workspace.output_dir / "final.docx"
        print(f"\ndocx 已渲染: {final_docx} ({final_docx.stat().st_size} bytes)")
    print(f"\nWorkspace 目录(含 working/output/logs 可 inspect): {workspace.root_dir}")


def _cli() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--render", action="store_true", help="开启 docxtpl auto_render")
    asyncio.run(main(ap.parse_args().render))


if __name__ == "__main__":
    _cli()
