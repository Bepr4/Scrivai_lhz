"""造 30 条 mock feedback 用于 M2 integration test。

幂等：每次清 feedback/phases/runs 表后重插。

用法::

    conda run -n scrivai python -m tests.fixtures.m2_evolution.seed_feedback --db /tmp/test.db
"""

from __future__ import annotations

import argparse
import random
import sqlite3
from pathlib import Path

from scrivai.trajectory.store import TrajectoryStore

# ---------------------------------------------------------------------------
# Mock 数据模板（变电站运维场景，中文）
# ---------------------------------------------------------------------------

_PES_FIXTURES: dict[str, list[dict]] = {
    "extractor": [
        {
            "question": "从《220kV 变电站运行维护规程》第 3 章抽取 5 条主要检查点",
            "draft": {"items": ["主变压器油位"]},
            "final": {
                "items": [
                    "主变压器油位（正常范围 20-40℃ 刻度区间）",
                    "断路器 SF6 气体压力（额定值 0.6 MPa，报警值 0.55 MPa）",
                    "接地电阻值（不超过 4 Ω）",
                    "继电保护定值核对（与定值单一致）",
                    "遥信状态确认（与监控系统一致）",
                ]
            },
        },
        {
            "question": "抽取《变电站运行维护规程》中的工具及仪器要求",
            "draft": {"items": ["万用表"]},
            "final": {
                "items": [
                    "数字万用表（精度 0.5 级以上）",
                    "红外测温仪（量程 -20℃ 至 350℃）",
                    "兆欧表（500V/1000V 可选）",
                    "接地电阻测试仪",
                    "SF6 气体检漏仪",
                ]
            },
        },
        {
            "question": "从巡视记录模板中提取必填字段清单",
            "draft": {"fields": ["日期", "值班员"]},
            "final": {
                "fields": [
                    "巡视日期",
                    "值班员工号及姓名",
                    "天气状况",
                    "设备运行方式",
                    "异常设备编号",
                    "缺陷等级（紧急/严重/一般）",
                    "处理措施及结果",
                ]
            },
        },
        {
            "question": "抽取 10kV 配电室安全规程中的作业前检查项",
            "draft": {"checks": ["挂警示牌"]},
            "final": {
                "checks": [
                    "确认停电范围并验电",
                    "装设接地线（编号记录）",
                    "挂'禁止合闸'警示牌",
                    "装设遮栏并悬挂标示牌",
                    "检查安全工器具试验合格证",
                ]
            },
        },
        {
            "question": "提取年度检修计划模板中的时间节点字段",
            "draft": {"fields": ["计划开始日期"]},
            "final": {
                "fields": [
                    "计划开始日期",
                    "计划完成日期",
                    "实际开始日期",
                    "实际完成日期",
                    "延期原因（如有）",
                    "验收日期",
                    "验收人工号",
                ]
            },
        },
    ],
    "auditor": [
        {
            "question": "对《220kV 主变压器检修报告》进行 10 条 checkpoint 审核",
            "draft": {
                "findings": [
                    {
                        "checkpoint_id": "cp-1",
                        "verdict": "pass",
                        "evidence": "油位正常",
                    }
                ]
            },
            "final": {
                "findings": [
                    {
                        "checkpoint_id": "cp-1",
                        "verdict": "pass",
                        "evidence": "主变油位指示正常（位于 20-40℃ 区间，见报告第 3.2 节图 3-1）",
                    },
                    {
                        "checkpoint_id": "cp-2",
                        "verdict": "fail",
                        "evidence": "文档未明确 SF6 断路器压力阈值，仅描述'压力正常'，缺乏数据支撑",
                    },
                    {
                        "checkpoint_id": "cp-3",
                        "verdict": "pass",
                        "evidence": "继电保护定值已与最新定值单（编号 DZ-2026-042）核对一致",
                    },
                    {
                        "checkpoint_id": "cp-4",
                        "verdict": "warning",
                        "evidence": "接地电阻测试值 3.8 Ω，临近上限 4 Ω，建议下次检修重点复测",
                    },
                ]
            },
        },
        {
            "question": "审核《35kV 线路巡视报告》格式与完整性",
            "draft": {
                "findings": [
                    {"checkpoint_id": "cp-1", "verdict": "pass", "evidence": "格式基本合规"}
                ]  # noqa: E501
            },
            "final": {
                "findings": [
                    {
                        "checkpoint_id": "cp-1",
                        "verdict": "fail",
                        "evidence": "巡视人员工号缺失，不符合《运维管理规定》第 5.3 条要求",
                    },
                    {
                        "checkpoint_id": "cp-2",
                        "verdict": "fail",
                        "evidence": "第 3 处导线弧垂未填写实测数据，仅填写'目测正常'",
                    },
                    {
                        "checkpoint_id": "cp-3",
                        "verdict": "pass",
                        "evidence": "杆塔编号与 GIS 系统一致，照片附件完整",
                    },
                ]
            },
        },
        {
            "question": "对年度设备台账进行数据一致性审核",
            "draft": {
                "findings": [{"checkpoint_id": "cp-1", "verdict": "pass", "evidence": "台账存在"}]
            },
            "final": {
                "findings": [
                    {
                        "checkpoint_id": "cp-1",
                        "verdict": "fail",
                        "evidence": "主变 1# 投运日期台账填写 2018-03-15，与出厂铭牌 2018-04-20 不符",  # noqa: E501
                    },
                    {
                        "checkpoint_id": "cp-2",
                        "verdict": "pass",
                        "evidence": "断路器额定电流参数与设备铭牌一致",
                    },
                ]
            },
        },
        {
            "question": "审核《防汛专项检查报告》执行标准符合性",
            "draft": {
                "findings": [
                    {"checkpoint_id": "cp-1", "verdict": "pass", "evidence": "防汛措施到位"}
                ]  # noqa: E501
            },
            "final": {
                "findings": [
                    {
                        "checkpoint_id": "cp-1",
                        "verdict": "pass",
                        "evidence": "防水挡板安装记录齐全，符合《防汛应急预案》附录 A 要求",
                    },
                    {
                        "checkpoint_id": "cp-2",
                        "verdict": "warning",
                        "evidence": "电缆沟积水抽排记录不连续，建议补充 6 月 15 日-20 日期间记录",
                    },
                ]
            },
        },
        {
            "question": "对《继电保护定值整定报告》进行技术符合性审核",
            "draft": {
                "findings": [
                    {"checkpoint_id": "cp-1", "verdict": "pass", "evidence": "定值单已签发"}
                ]  # noqa: E501
            },
            "final": {
                "findings": [
                    {
                        "checkpoint_id": "cp-1",
                        "verdict": "pass",
                        "evidence": "过流保护定值 Iset=600A，与系统短路电流计算结论一致（见附录 B）",  # noqa: E501
                    },
                    {
                        "checkpoint_id": "cp-2",
                        "verdict": "fail",
                        "evidence": "差动保护制动系数未填写，定值单第 4 页留空",
                    },
                    {
                        "checkpoint_id": "cp-3",
                        "verdict": "pass",
                        "evidence": "定值单已经调度中心审批，审批人签名及日期完整",
                    },
                ]
            },
        },
    ],
    "generator": [
        {
            "question": "生成《220kV 变电站年度技术监督工作底稿》(DOCX 格式)",
            "draft": {"content": "项目：变电站审计\n状态：已完成"},
            "final": {
                "content": (
                    "# XX 220kV 变电站技术监督工作底稿\n\n"
                    "## 1 项目基本信息\n"
                    "- 项目名称：XX 220kV 变电站年度技术监督\n"
                    "- 监督日期：2026-04-17\n"
                    "- 监督单位：XX 供电公司变电运检室\n"
                    "- 监督人员：张工（工号 10042）、李工（工号 10058）\n\n"
                    "## 2 监督范围\n"
                    "本次监督涵盖主变压器、断路器、互感器、继电保护装置及接地系统。\n\n"
                    "## 3 审核结论\n"
                    "| 检查项目 | 结论 | 备注 |\n"
                    "|---|---|---|\n"
                    "| 主变油位 | 合格 | 位于正常刻度区间 |\n"
                    "| SF6 压力 | 不合格 | 缺少实测数据 |\n"
                    "| 接地电阻 | 注意 | 临近上限，需持续关注 |\n\n"
                    "## 4 整改要求\n"
                    "1. 补充 SF6 断路器实测压力值，不得以定性描述代替定量数据。\n"
                    "2. 下次检修周期（2026-10）对接地电阻进行复测并记录。\n"
                )
            },
        },
        {
            "question": "生成设备缺陷处理通知单（A4 格式）",
            "draft": {"content": "通知单：SF6 压力不足"},
            "final": {
                "content": (
                    "# 设备缺陷处理通知单\n\n"
                    "- 通知单编号：QX-2026-0417-001\n"
                    "- 发现日期：2026-04-17\n"
                    "- 设备名称：220kV 1# 断路器（GW4-220/600）\n"
                    "- 缺陷描述：SF6 气体压力 0.53 MPa，低于报警值 0.55 MPa。\n"
                    "- 缺陷等级：严重\n"
                    "- 要求处理期限：24 小时内补气至额定压力 0.60 MPa\n"
                    "- 责任班组：变电运检一班\n"
                    "- 审核人：运检室主任（签名）\n"
                )
            },
        },
        {
            "question": "生成月度巡视汇总报告",
            "draft": {"content": "4 月巡视汇总：共 12 次，发现缺陷 2 处。"},
            "final": {
                "content": (
                    "# XX 变电站 2026 年 4 月巡视汇总报告\n\n"
                    "## 巡视统计\n"
                    "- 计划巡视次数：12 次\n"
                    "- 实际完成次数：12 次\n"
                    "- 完成率：100%\n\n"
                    "## 发现缺陷\n"
                    "| 序号 | 设备 | 缺陷描述 | 等级 | 状态 |\n"
                    "|---|---|---|---|---|\n"
                    "| 1 | 220kV 1# 断路器 | SF6 压力低 | 严重 | 已处理 |\n"
                    "| 2 | 10kV 3# 开关柜 | 柜门密封条老化 | 一般 | 计划处理 |\n\n"
                    "## 结论\n"
                    "本月设备整体运行正常，SF6 压力缺陷已于发现后 8 小时内完成补气处理。\n"
                )
            },
        },
        {
            "question": "生成继电保护动作分析报告",
            "draft": {"content": "2026-04-10 零序保护动作，线路跳闸。"},
            "final": {
                "content": (
                    "# 继电保护动作分析报告\n\n"
                    "- 动作时间：2026-04-10 03:22:14\n"
                    "- 动作装置：XX 220kV 线路零序电流保护（RCS-931A）\n"
                    "- 动作相别：A 相\n"
                    "- 故障测距：18.4 km（线路全长 42.6 km）\n\n"
                    "## 动作原因分析\n"
                    "经现场排查，故障点位于 18.2 km 处（与测距一致），"
                    "雷击导致绝缘子放电，造成 A 相接地故障。\n\n"
                    "## 处理结果\n"
                    "更换绝缘子 3 片，03:58 恢复送电，停电时长 36 分钟。\n"
                )
            },
        },
        {
            "question": "生成年度设备状态评价报告摘要",
            "draft": {"content": "设备整体状况良好。"},
            "final": {
                "content": (
                    "# XX 220kV 变电站 2025 年度设备状态评价报告（摘要）\n\n"
                    "## 评价结论\n"
                    "| 设备类别 | 评价等级 | 主要问题 |\n"
                    "|---|---|---|\n"
                    "| 主变压器 | 正常 | 无 |\n"
                    "| 断路器 | 注意 | 1# 断路器 SF6 压力偏低（已处理）|\n"
                    "| 互感器 | 正常 | 无 |\n"
                    "| 继电保护 | 正常 | 差动保护定值单待补全 |\n\n"
                    "## 下年度重点工作\n"
                    "1. 对 1# 断路器开展专项检修，更换密封垫。\n"
                    "2. 完善继电保护定值单归档管理。\n"
                    "3. 对服役超 15 年互感器进行状态评估。\n"
                )
            },
        },
    ],
}


def _clear_tables(db_path: Path) -> None:
    """按外键顺序清空所有相关表（幂等前提）。"""
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("DELETE FROM tool_calls")
        conn.execute("DELETE FROM turns")
        conn.execute("DELETE FROM feedback")
        conn.execute("DELETE FROM phases")
        conn.execute("DELETE FROM runs")
        conn.commit()
    finally:
        conn.close()


def _mk_mock_data(pes: str, idx: int, rng: random.Random) -> dict:
    """从模板中循环取数据，构造单条 mock 所需字段。"""
    fixtures = _PES_FIXTURES[pes]
    tpl = fixtures[idx % len(fixtures)]
    return {
        "run_id": f"mock-{pes}-{idx:02d}",
        "task_prompt": f"[{pes}] {tpl['question']} (rev {idx})",
        "input_summary": f"{tpl['question']} (样本 {idx})",
        "draft_output": dict(tpl["draft"]),
        "final_output": dict(tpl["final"]),
        "confidence": round(rng.uniform(0.75, 0.95), 2),
        "include_phases": idx < 3,  # 每 PES 前 3 条写入 phases
    }


def seed(db_path: Path) -> int:
    """清表后插入 30 条 mock feedback；返回实际插入数量。

    参数
    ----
    db_path:
        trajectory.db 文件路径，若不存在会自动创建。

    返回
    ----
    int
        成功插入的 feedback 条数（正常应为 30）。
    """
    # 先初始化 store（建表），再清表（保证幂等）
    store = TrajectoryStore(db_path=db_path)
    _clear_tables(db_path)
    rng = random.Random(42)
    count = 0

    for pes in ("extractor", "auditor", "generator"):
        for i in range(10):
            mock = _mk_mock_data(pes, i, rng)
            run_id = mock["run_id"]

            # --- 写入 runs 表 ---
            store.start_run(
                run_id=run_id,
                pes_name=pes,
                model_name="glm-5.1",
                provider="glm",
                sdk_version="0.1.3",
                skills_git_hash=None,
                agents_git_hash=None,
                skills_is_dirty=False,
                task_prompt=mock["task_prompt"],
                runtime_context={"mock": True, "seed_index": i},
            )

            # --- 可选写入 phases 表（前 3 条）---
            if mock["include_phases"]:
                for phase_order, phase_name in enumerate(("plan", "execute", "summarize")):
                    phase_id = store.record_phase_start(
                        run_id=run_id,
                        phase_name=phase_name,
                        phase_order=phase_order,
                        attempt_no=1,
                    )
                    store.record_phase_end(
                        phase_id=phase_id,
                        prompt=f"[{phase_name}] mock prompt — {run_id}",
                        response_text=f"[{phase_name}] mock response — {run_id}",
                        produced_files=[],
                        usage={"prompt_tokens": 100, "completion_tokens": 200},
                        error=None,
                        error_type=None,
                        is_retryable=None,
                    )

            # --- 结束 run ---
            store.finalize_run(
                run_id=run_id,
                status="completed",
                final_output=mock["draft_output"],
                workspace_archive_path=None,
                error=None,
                error_type=None,
            )

            # --- 写入 feedback 表 ---
            store.record_feedback(
                run_id=run_id,
                input_summary=mock["input_summary"],
                draft_output=mock["draft_output"],
                final_output=mock["final_output"],
                corrections=None,
                review_policy_version=None,
                source="human_expert",
                confidence=mock["confidence"],
                submitted_by=None,
            )

            count += 1

    return count


def main() -> int:
    """CLI 入口：解析 --db 参数并调用 seed()。"""
    parser = argparse.ArgumentParser(
        description="向 trajectory.db 注入 30 条 mock FeedbackRecord（M2 E2E 测试用）"
    )
    parser.add_argument(
        "--db",
        required=True,
        type=Path,
        help="trajectory.db 文件路径（将被清表后重写）",
    )
    args = parser.parse_args()
    n = seed(args.db)
    print(f"seeded {n} mock feedback records into {args.db}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
