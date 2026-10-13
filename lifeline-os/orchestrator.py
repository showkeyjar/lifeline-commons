"""Lifeline OS —— 编排骨架。

把任意一个符合 module-interface-v1 的供给模块跑成
「需求感知 → 资源调度 → 供给交付」的最小闭环。

编排器**自动发现** modules/ 下的模块：每个子目录 <id> 里放一个
<id>_module.py，其中定义一个 <Id>Module 类即可，无需手动登记。

跑完所有模块后，生成一份人读的「社区自给评估报告」，让社区
直接判断「我们退可守吗」（这是自愿社区实例真正要用的产出）。

> 提示：在跑具体模块之前，建议先用 `lifeline-os/strategy_analyzer.py`
> 分析主人/社区的资源画像，让系统推荐最匹配的策略（荒地只是策略之一）。
> 本编排器只负责"给定产能数据后算自给率"，不做策略决策。
"""

import importlib
import json
import os
import sys
from datetime import datetime, timezone

# 让项目根目录与同目录可被导入（modules 在根下；i18n 在同目录）
LIFELINE_OS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(LIFELINE_OS_DIR, "..")
sys.path.insert(0, ROOT)
if LIFELINE_OS_DIR not in sys.path:
    sys.path.insert(0, LIFELINE_OS_DIR)
import i18n  # noqa: E402  多语言：所有面向人的字符串走 t()
import action_spec  # noqa: E402  动作层核心规范（Stage 6）
import executor  # noqa: E402  参考执行器（Stage 6）

MODULES_DIR = os.path.join(ROOT, "modules")
REPORT_PATH = os.path.join(LIFELINE_OS_DIR, "last-report.md")

# 接口契约：一个合规模块必须实现的 6 个方法（详见 docs/module-interface-v1.md）
REQUIRED_METHODS = ["name", "provides", "assess_needs", "schedule", "provide", "status"]

# 各域的「日均需求」可读单位（用于报告；也可经 i18n 的 unit.<domain> 取多语言版）
NEED_UNITS = {"energy": "kWh/天", "food": "餐/天", "water": "L/天", "shelter": "人", "health": "人"}


def _conforms(klass):
    """校验类是否实现了全部必需方法（且为可调用）。"""
    missing = [m for m in REQUIRED_METHODS if not callable(getattr(klass, m, None))]
    return missing


def discover_modules():
    """扫描 modules/ 下所有 <id>/<id>_module.py，返回 [(id, Class), ...]。

    只收录**符合接口契约**的模块；不符合的打印原因并跳过，
    这样 CI 能拦下破坏契约的提交。
    """
    found = []
    if not os.path.isdir(MODULES_DIR):
        return found
    for entry in sorted(os.listdir(MODULES_DIR)):
        mod_dir = os.path.join(MODULES_DIR, entry)
        if not os.path.isdir(mod_dir):
            continue
        mod_file = os.path.join(mod_dir, f"{entry}_module.py")
        if not os.path.isfile(mod_file):
            continue
        try:
            pkg = importlib.import_module(f"modules.{entry}.{entry}_module")
        except Exception as e:
            print(f"[Lifeline OS] {i18n.t('oc.skip_import', entry=entry, err=e)}")
            continue
        target = f"{entry}module"
        klass = None
        for name in dir(pkg):
            obj = getattr(pkg, name)
            if isinstance(obj, type) and name.lower() == target:
                klass = obj
                break
        if klass is None:
            print(f"[Lifeline OS] {i18n.t('oc.skip_class', entry=entry, cls=entry.capitalize() + 'Module')}")
            continue
        missing = _conforms(klass)
        if missing:
            print(f"[Lifeline OS] {i18n.t('oc.skip_contract', entry=entry, missing=missing)}")
            continue
        found.append((entry, klass))
    return found


def _weakest_day(module):
    """从模块跑后记录里取最弱那天（覆盖最低）。"""
    last = getattr(module, "_last", None)
    if not last or not last.get("daily"):
        return "—"
    weak = min(last["daily"], key=lambda x: x["coverage"])
    return i18n.t("weak.day", d=weak["day"], c=f"{weak['coverage']:.2f}")


def run_loop(module):
    print(f"[Lifeline OS] {i18n.t('oc.loading')}: {module.name()} ({i18n.t('oc.provides')}={module.provides()})")

    # 基准社区画像（demo-village）：默认按"已建立、自有住房"的乡村社区假设，
    # 让住所类模块也有合理输入；真实画像请走 lifeline.py。
    context = {"community": "demo-village", "population": 12,
               "has_land": True, "capital": 2, "location": "乡村"}
    needs = module.assess_needs(context)
    print(f"  {i18n.t('oc.step1')}: {needs}")

    resources = {"available": ["solar", "local-farm", "community-storage", "battery",
                              "rain-harvest", "well", "community-tank"]}
    plan = module.schedule(resources, needs)
    print(f"  {i18n.t('oc.step2')}: {plan}")

    delivery = module.provide(plan)
    print(f"  {i18n.t('oc.step3')}: {delivery}")

    print(f"  {i18n.t('oc.state')}: {module.status()}")
    print(f"[Lifeline OS] {i18n.t('oc.done')}")
    # 6 元组：(module_id, module, needs, plan, delivery, context)
    # plan/context 供动作层（actions()）推导任务级指令参数。
    return module, needs, plan, delivery, context


def generate_report(results):
    """汇总所有模块跑通结果，生成人读报告。

    results: [(module_id, module_instance, needs, delivery), ...]
    """
    lines = []
    lines.append(i18n.t("title.community"))
    lines.append("")
    lines.append(i18n.t("sub.community"))
    lines.append("")
    lines.append(f"- **{i18n.t('oc.community')}**: demo-village")
    lines.append(f"- **{i18n.t('oc.population')}**: 12")
    lines.append(f"- **{i18n.t('oc.period')}**: 30 {i18n.t('unit.days')}")
    lines.append(f"- **{i18n.t('oc.domains')}**: {', '.join(i18n.t(f'dom.{mid}') for mid, _, _, _, _, _ in results)}")
    lines.append("")
    lines.append("## " + i18n.t("sec.domains"))
    lines.append("")
    lines.append(f"| {i18n.t('th.domain')} | {i18n.t('th.demand')} | {i18n.t('th.coverage')} | "
                 f"{i18n.t('th.full')} | {i18n.t('th.short')} | {i18n.t('th.weak')} | {i18n.t('th.health')} |")
    lines.append("|---|---|---|---|---|---|---|")
    for mid, module, needs, plan, delivery, context in results:
        unit = i18n.t(f"unit.{mid}")
        demand = _demand_value(needs, mid)
        avg = delivery.get("delivered_avg_coverage", 0)
        full = delivery.get("full_days", 0)
        short = delivery.get("shortfall_days", 0)
        weak = _weakest_day(module)
        health = delivery.get("health", module.status().get("health", "—"))
        lines.append(
            f"| {i18n.t(f'dom.{mid}')} | {demand} {unit} | {avg:.3f} | {full}/30 | {short}/30 | {weak} | {health} |"
        )
    lines.append("")
    lines.append("## " + i18n.t("sec.verdict"))
    lines.append("")
    avg_all = sum(d.get("delivered_avg_coverage", 0) for _, _, _, _, d, _ in results) / max(len(results), 1)
    if avg_all >= 0.95:
        verdict = i18n.t("verdict.high")
    elif avg_all >= 0.80:
        verdict = i18n.t("verdict.mid")
    else:
        verdict = i18n.t("verdict.low")
    lines.append(f"- **{i18n.t('oc.avg')}**: {avg_all:.3f}")
    lines.append(f"- **{i18n.t('ff.tier')}**: {verdict}")
    lines.append("")
    lines.append("## " + i18n.t("sec.honest"))
    lines.append("")
    lines.append("- " + i18n.t("cb1"))
    lines.append("- " + i18n.t("cb2"))
    lines.append("- " + i18n.t("cb3"))
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 动作层（Stage 6）：把供给结果翻译成人形机器人可执行的任务级指令
# ---------------------------------------------------------------------------
ACTION_PLAN_PATH = os.path.join(LIFELINE_OS_DIR, "last-action-plan.json")
ACTION_PLAN_MD_PATH = os.path.join(LIFELINE_OS_DIR, "last-action-plan.md")


def collect_action_plan(results):
    """从各模块的 results（6 元组）收集动作层指令。

    仅调用实现了 ``actions(plan, context)`` 的模块；未实现的模块被安全跳过
    （动作层是向后兼容的可选扩展）。
    """
    actions = []
    for mid, module, needs, plan, delivery, context in results:
        method = getattr(module, "actions", None)
        if callable(method):
            try:
                acts = method(plan, context)
            except Exception as e:  # noqa: BLE001
                print(f"[Lifeline OS] {i18n.t('oc.action_skip_module', entry=mid, err=e)}")
                continue
            actions.extend(acts)
    return actions


def generate_action_plan_json(actions, community="demo-village"):
    """生成动作计划 JSON（供参考执行器消费）。"""
    schedule = action_spec.expand_schedule(actions)
    on_demand = [a["id"] for a in schedule["on_demand"]]
    meta = {
        "schema_version": action_spec.ACTION_SCHEMA_VERSION,
        "action_count": len(actions),
        "on_demand": on_demand,
        "community": community,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "granularity": "task-level (humanoid-robot ready; no motion primitives)",
    }
    return {
        "meta": meta,
        "actions": actions,
        "schedule": {
            "by_day": {str(d): v for d, v in schedule["by_day"].items()},
            "on_demand": schedule["on_demand"],
        },
    }


def generate_action_plan_md(actions):
    """生成人读的动作计划 Markdown（多语言）。"""
    lines = []
    lines.append(i18n.t("title.action"))
    lines.append("")
    lines.append(i18n.t("sub.action"))
    lines.append("")
    lines.append("## " + i18n.t("sec.action.list"))
    lines.append("")
    header = "| " + " | ".join([
        i18n.t("th.aid"), i18n.t("th.adomain"), i18n.t("th.aactor"),
        i18n.t("th.acommand"), i18n.t("th.atarget"), i18n.t("th.afreq"),
        i18n.t("th.aprio"), i18n.t("th.apre"), i18n.t("th.aeffect"),
        i18n.t("th.averify"),
    ]) + " |"
    lines.append(header)
    lines.append("|" + "---|" * 10)
    for a in actions:
        def _tr(prefix, val):
            if not val:
                return val
            key = f"{prefix}.{val}"
            out = i18n.t(key)
            return val if out.startswith(prefix + ".") else out
        cells = [
            a.get("id", ""),
            _tr("dom", a.get("domain", "")),
            _tr("actor", a.get("actor", "")),
            a.get("command", ""),
            a.get("target", ""),
            _tr("freq", a.get("frequency", "")),
            _tr("prio", a.get("priority", "")),
            a.get("precondition") or "—",
            a.get("expected_effect") or "—",
            a.get("verify") or "—",
        ]
        lines.append("| " + " | ".join(str(c) for c in cells) + " |")
    lines.append("")
    lines.append("## " + i18n.t("sec.action.gate"))
    lines.append("")
    lines.append("- " + i18n.t("action.gate1"))
    lines.append("- " + i18n.t("action.gate2"))
    lines.append("- " + i18n.t("action.gate3"))
    lines.append("")
    return "\n".join(lines)


def _demand_value(needs, mid):
    """从 needs 字典里取该域的日均需求数值。"""
    if mid == "energy":
        return needs.get("daily_kwh", needs.get("daily_energy_kwh", "—"))
    if mid == "food":
        return needs.get("daily_meals", "—")
    if mid == "water":
        return needs.get("daily_l", "—")
    if mid == "shelter":
        return needs.get("persons_need", "—")
    if mid == "health":
        return needs.get("persons_need", "—")
    return "—"


if __name__ == "__main__":
    lang = "en"
    args = sys.argv[1:]
    do_execute = "--execute" in args
    if "--lang" in args:
        idx = args.index("--lang")
        if idx + 1 < len(args):
            lang = args[idx + 1]
    i18n.set_language(lang)

    modules = discover_modules()
    if not modules:
        print(f"[Lifeline OS] {i18n.t('oc.no_modules')}")
        sys.exit(1)
    print(f"[Lifeline OS] {i18n.t('oc.found', n=len(modules))}: {[m[0] for m in modules]}")
    print("=" * 48)

    results = []
    for entry, klass in modules:
        print()
        # run_loop 返回 5 元组；补上 module_id 形成 6 元组 (mid, module, needs, plan, delivery, context)
        module, needs, plan, delivery, context = run_loop(klass())
        results.append((entry, module, needs, plan, delivery, context))

    print()
    print("=" * 48)
    report = generate_report(results)
    print(report)

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report + "\n")
    print(f"\n[Lifeline OS] {i18n.t('oc.report_written')}: {REPORT_PATH}")

    # 动作层（Stage 6）：汇集各模块的任务级指令，生成计划并可选执行
    actions = collect_action_plan(results)
    plan_json = generate_action_plan_json(actions)
    plan_md = generate_action_plan_md(actions)
    with open(ACTION_PLAN_PATH, "w", encoding="utf-8") as f:
        json.dump(plan_json, f, ensure_ascii=False, indent=2)
    with open(ACTION_PLAN_MD_PATH, "w", encoding="utf-8") as f:
        f.write(plan_md + "\n")
    print(f"[Lifeline OS] {i18n.t('oc.action_plan_written')}: {ACTION_PLAN_PATH} "
          f"({plan_json['meta']['action_count']} actions)")

    if do_execute:
        print(f"\n[Lifeline OS] {i18n.t('oc.action_execute')} ...")
        out = executor.execute_plan(plan_json["actions"])
        s = out["summary"]
        print(f"  {i18n.t('oc.action_exec_summary')}: "
              f"{i18n.t('oc.action_ok')}={s['ok']} "
              f"{i18n.t('oc.action_skip')}={s['skip']} "
              f"{i18n.t('oc.action_failed')}={s['failed']}")
