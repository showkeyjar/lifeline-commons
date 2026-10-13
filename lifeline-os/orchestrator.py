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
import os
import sys

# 让项目根目录与同目录可被导入（modules 在根下；i18n 在同目录）
LIFELINE_OS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(LIFELINE_OS_DIR, "..")
sys.path.insert(0, ROOT)
if LIFELINE_OS_DIR not in sys.path:
    sys.path.insert(0, LIFELINE_OS_DIR)
import i18n  # noqa: E402  多语言：所有面向人的字符串走 t()

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
    return module, needs, delivery


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
    lines.append(f"- **{i18n.t('oc.domains')}**: {', '.join(i18n.t(f'dom.{mid}') for mid, _, _, _ in results)}")
    lines.append("")
    lines.append("## " + i18n.t("sec.domains"))
    lines.append("")
    lines.append(f"| {i18n.t('th.domain')} | {i18n.t('th.demand')} | {i18n.t('th.coverage')} | "
                 f"{i18n.t('th.full')} | {i18n.t('th.short')} | {i18n.t('th.weak')} | {i18n.t('th.health')} |")
    lines.append("|---|---|---|---|---|---|---|")
    for mid, module, needs, delivery in results:
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
    avg_all = sum(d.get("delivered_avg_coverage", 0) for _, _, _, d in results) / max(len(results), 1)
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
    lang = "zh"
    args = sys.argv[1:]
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
        module, needs, delivery = run_loop(klass())
        results.append((entry, module, needs, delivery))

    print()
    print("=" * 48)
    report = generate_report(results)
    print(report)

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report + "\n")
    print(f"\n[Lifeline OS] {i18n.t('oc.report_written')}: {REPORT_PATH}")
