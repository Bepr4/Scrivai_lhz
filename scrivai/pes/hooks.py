"""HookManager — pluggy.PluginManager 轻量封装。

参考:
- docs/design.md §4.3(9 hook 触点 + 异常传播矩阵)
- docs/TD.md T0.5
- docs/superpowers/specs/2026-04-16-scrivai-m0.25-design.md §4.2

设计要点:
- HookManager 只提供同步 dispatch / 非阻塞 dispatch 两个方法;
  哪个 hook 用哪种由 BasePES (M0.5) 决定。
- 9 个 hook 的 spec 集中在 PESHookSpec 类。
- HookContext 的全部 9 种 pydantic 类来自 scrivai.models.pes(M0 已定义)。
"""

from __future__ import annotations

import pluggy
from loguru import logger

from scrivai.models.pes import (
    CancelHookContext,
    FailureHookContext,
    HookContext,
    OutputHookContext,
    PhaseHookContext,
    PromptHookContext,
    PromptTurnHookContext,
    RunHookContext,
)

# 模块级标记 — 与 Herald2 完全对称(只是 namespace 改 scrivai_pes)
hookspec = pluggy.HookspecMarker("scrivai_pes")
hookimpl = pluggy.HookimplMarker("scrivai_pes")


class PESHookSpec:
    """9 个 hook 触点的规范声明(对应 design §4.3 表格)。"""

    @hookspec
    def before_run(self, context: RunHookContext) -> None:
        """整次 run 开始前(同步,异常→run failed)。"""

    @hookspec
    def before_phase(self, context: PhaseHookContext) -> None:
        """每个 phase 每次 attempt 前(同步,异常→phase failed)。"""

    @hookspec
    def before_prompt(self, context: PromptHookContext) -> None:
        """prompt 渲染后、调 SDK 前(同步,可修改 context.prompt)。"""

    @hookspec
    def after_prompt_turn(self, context: PromptTurnHookContext) -> None:
        """每个 SDK turn 收到后(同步)。"""

    @hookspec
    def after_phase(self, context: PhaseHookContext) -> None:
        """phase 最终成功后(同步)。"""

    @hookspec
    def on_phase_failed(self, context: FailureHookContext) -> None:
        """phase 本次尝试失败时(非阻塞,异常仅 log)。"""

    @hookspec
    def on_output_written(self, context: OutputHookContext) -> None:
        """summarize validate 通过后、after_phase 前触发一次(同步)。"""

    @hookspec
    def on_run_cancelled(self, context: CancelHookContext) -> None:
        """收到 KeyboardInterrupt / asyncio.CancelledError 时(非阻塞)。"""

    @hookspec
    def after_run(self, context: RunHookContext) -> None:
        """整次 run 结束(finally;非阻塞)。"""


class HookManager:
    """pluggy.PluginManager 轻量封装。

    用法:
        mgr = HookManager()
        mgr.register(MyPlugin())
        mgr.dispatch("before_run", RunHookContext(run=run))
    """

    def __init__(self) -> None:
        self._mgr = pluggy.PluginManager("scrivai_pes")
        self._mgr.add_hookspecs(PESHookSpec)

    def register(self, plugin: object, name: str | None = None) -> None:
        """注册 hook 插件(支持 pluggy 同名插件去重的可选 name)。"""
        self._mgr.register(plugin, name=name)

    def dispatch(self, hook_name: str, context: HookContext) -> None:
        """同步 dispatch;插件异常**冒泡**(由调用方决定怎么处理)。"""
        getattr(self._mgr.hook, hook_name)(context=context)

    def dispatch_non_blocking(self, hook_name: str, context: HookContext) -> None:
        """非阻塞 dispatch;插件异常仅 loguru.exception,不冒泡。"""
        try:
            self.dispatch(hook_name, context)
        except Exception:
            logger.exception("Hook 执行失败 [hook=%s]", hook_name)
