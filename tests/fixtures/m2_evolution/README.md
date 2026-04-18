# M2 Evolution fixtures

用于 `tests/integration/test_m2_evolution_cycle.py`。

目前无真实专家反馈数据,本目录脚本造 30 条 mock:
- `seed_feedback.py` 幂等脚本,传入 trajectory.db 路径,自动清 feedback/phases/runs 表后插入 30 条
- Extractor / Auditor / Generator 各 10 条
- 其中每 PES 的前 3 条写入 runs + phases 表(便于 trajectory_summary 测试)

## 使用

```bash
conda run -n scrivai python -m tests.fixtures.m2_evolution.seed_feedback --db /tmp/test.db
```

脚本依赖 `scrivai.trajectory.store.TrajectoryStore` + `scrivai.models.trajectory.FeedbackRecord`,**不**依赖真 SDK。
