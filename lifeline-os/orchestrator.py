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

# 让项目根目录可被导入（modules / lifeline_os 都在根下）
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)

MODULES_DIR = os.path.join(ROOT, "modules")
REPORT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "last-report.md")

# 接口契约：一个合规模块必须实现的 6 个方法（详见 docs/module-interface-v1.md）
REQUIRED_METHODS = ["name", "provides", "assess_needs", "schedule", "provide", "status"]

# 各域的「日均需求」可读单位（用于报告）
NEED_UNITS = {"energy": "kWh/天", "food": "餐/天", "water": "L/天"}


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
            print(f"[Lifeline OS] 跳过模块 {entry}: 导入失败 ({e})")
            continue
        target = f"{entry}module"
        klass = None
        for name in dir(pkg):
            obj = getattr(pkg, name)
            if isinstance(obj, type) and name.lower() == target:
                klass = obj
                break
        if klass is None:
            print(f"[Lifeline OS] 跳过模块 {entry}: 未找到 {entry.capitalize()}Module 类")
            continue
        missing = _conforms(klass)
        if missing:
            print(f"[Lifeline OS] 跳过模块 {entry}: 接口契约缺失 {missing}")
            continue
        found.append((entry, klass))
    return found


def _weakest_day(module):
    """从模块跑后记录里取最弱那天（覆盖最低）。"""
    last = getattr(module, "_last", None)
    if not last or not last.get("daily"):
        return "—"
    weak = min(last["daily"], key=lambda x: x["coverage"])
    return f"第 {weak['day']} 天 ({weak['coverage']:.2f})"


def run_loop(module):
    print(f"[Lifeline OS] 加载模块: {module.name()} (provides={module.provides()})")

    context = {"community": "demo-village", "population": 12}
    needs = module.assess_needs(context)
    print(f"  1) 感知需求: {needs}")

    resources = {"available": ["solar", "local-farm", "community-storage", "battery",
                              "rain-harvest", "well", "community-tank"]}
    plan = module.schedule(resources, needs)
    print(f"  2) 调度资源: {plan}")

    delivery = module.provide(plan)
    print(f"  3) 供给交付: {delivery}")

    print(f"  状态: {module.status()}")
    print("[Lifeline OS] 闭环完成 ✓")
    return module, needs, delivery


def generate_report(results):
    """汇总所有模块跑通结果，生成人读报告。

    results: [(module_id, module_instance, needs, delivery), ...]
    """
    lines = []
    lines.append("# 社区自给评估报告")
    lines.append("")
    lines.append("> 由 Lifeline OS 自动生成 —— 数据驱动 30 天模拟，纯自给视角，不含任何交易逻辑。")
    lines.append("")
    lines.append(f"- **社区**: demo-village")
    lines.append(f"- **人口**: 12")
    lines.append(f"- **评估周期**: 30 天")
    lines.append(f"- **覆盖域**: {', '.join(mid for mid, _, _, _ in results)}")
    lines.append("")
    lines.append("## 各域自给率")
    lines.append("")
    lines.append("| 域 | 日均需求 | 平均自给率 | 满供天数 | 缺口天数 | 最弱日 | 健康 |")
    lines.append("|---|---|---|---|---|---|---|")
    for mid, module, needs, delivery in results:
        unit = NEED_UNITS.get(mid, "")
        demand = _demand_value(needs, mid)
        avg = delivery.get("delivered_avg_coverage", 0)
        full = delivery.get("full_days", 0)
        short = delivery.get("shortfall_days", 0)
        weak = _weakest_day(module)
        health = delivery.get("health", module.status().get("health", "—"))
        lines.append(
            f"| {mid} | {demand} {unit} | {avg:.3f} | {full}/30 | {short}/30 | {weak} | {health} |"
        )
    lines.append("")
    lines.append("## 综合判断")
    lines.append("")
    avg_all = sum(d.get("delivered_avg_coverage", 0) for _, _, _, d in results) / max(len(results), 1)
    if avg_all >= 0.95:
        verdict = "✅ 基本退可守：多数域自给率在高位，仅个别弱日需本地缓冲或微调产能。"
    elif avg_all >= 0.80:
        verdict = "⚠️ 部分退可守：存在结构性缺口，需扩容产能或补齐模块后再评估。"
    else:
        verdict = "❌ 暂不可守：自给率偏低，当前配置不足以支撑该社区离网生存。"
    lines.append(f"- **平均自给率（各域均值）**: {avg_all:.3f}")
    lines.append(f"- **结论**: {verdict}")
    lines.append("")
    lines.append("## 诚实边界")
    lines.append("")
    lines.append("- 本报告只评估「物理供给自给率」，不涉及土地产权、启动资本、成员健康与组织力——这些是现实更大的一道坎。")
    lines.append("- 本项目是**自愿社区**的开源协调工具，不替代政府的现金底 / 基础服务，也帮不了赤贫无地者。")
    lines.append("- 把 `modules/*/data/` 下的样例换成你们社区的真实数据，重跑即可得到专属报告。")
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
    return "—"


if __name__ == "__main__":
    modules = discover_modules()
    if not modules:
        print("[Lifeline OS] 未发现任何供给模块，退出。")
        sys.exit(1)
    print(f"[Lifeline OS] 发现 {len(modules)} 个供给模块: {[m[0] for m in modules]}")
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
    print(f"\n[Lifeline OS] 报告已写入: {REPORT_PATH}")
