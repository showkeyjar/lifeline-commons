"""Lifeline OS —— 顶层闭环（分析 → 模拟 → 生存自由指数）。

把两个原本脱节的半截接到一起：

1. **分析**：读主人/社区画像，用策略分析器推荐最匹配的生存策略
   （荒地/分布式自给只是策略之一，不是唯一范式）。
2. **模拟**：把画像（人口、资产规模系数）喂给供给层模块
   （energy/food/water），跑数据驱动的 30 天自给模拟。
3. **指数**：综合"供给覆盖率 + 策略可行性 + 定性韧性"给出生存自由指数，
   让主人一眼看懂"我现在离生存自由有多远、卡在哪"。

纯软件分析 + 模拟，不替人决策、不交付机器人、不解决人生意义。
诚实标注"本项目帮不了的人"（赤贫无地、健康受限、只能靠政府托底）。

用法：
    python lifeline-os/lifeline.py                       # 内置示例画像（小A·乡村有地）
    python lifeline-os/lifeline.py --profile x.json      # 读 JSON 画像
    python lifeline-os/lifeline.py --profile x.json --out report.md   # 写文件
"""

import importlib.util
import json
import os
import sys

LIFELINE_OS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(LIFELINE_OS_DIR, "..")
sys.path.insert(0, ROOT)

# 复用编排器的模块自动发现、最弱日、需求单位等逻辑（目录名含连字符，无法当包名导入）
_spec = importlib.util.spec_from_file_location(
    "lifeline_orchestrator", os.path.join(LIFELINE_OS_DIR, "orchestrator.py")
)
_orch = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_orch)
discover_modules = _orch.discover_modules
_weakest_day = _orch._weakest_day
NEED_UNITS = _orch.NEED_UNITS
_demand_value = _orch._demand_value

# 默认可用资源（画像未特别指定时，按"已建好基础资产"假设）
DEFAULT_RESOURCES = [
    "solar", "local-farm", "community-storage", "battery",
    "rain-harvest", "well", "community-tank",
]

# 资本 → 资产规模系数（0 无 / 1 少 / 2 中 / 3 足）。1.0 = 持有与 12 人基准社区匹配的产能。
CAPITAL_FACTOR = {0: 0.4, 1: 0.7, 2: 1.0, 3: 1.3}

# 各策略在"生存自由指数"中的权重（供给覆盖 / 策略可行性 / 定性韧性），三者和为 1。
# 物理自给型策略更看重供给覆盖；收入/迁移型更看重策略本身是否可行。
STRATEGY_WEIGHTS = {
    "distributed":      (0.60, 0.25, 0.15),
    "urban_collective": (0.50, 0.30, 0.20),
    "semi_self":        (0.50, 0.30, 0.20),
    "relocate":         (0.25, 0.45, 0.30),
    "skill_buffer":     (0.25, 0.45, 0.30),
    "external_floor":   (0.15, 0.50, 0.35),
}


# ---------------------------------------------------------------------------
# 画像 → 资产规模系数
# ---------------------------------------------------------------------------
def compute_asset_scale(profile, strategy_key):
    """把画像翻译成供给层的'资产规模系数'。

    含义：主人实际能建起多少产能，相对 12 人基准社区（系数 1.0）。
    - 资本越多，越能堆资产；有地再叠加红利。
    - 依赖收入/迁移/外部托底的策略不靠物理资产，系数上限压低。
    - 纯外部托底（赤贫无地无可变现技能）→ 几乎无资产可自建。
    """
    cap = min(int(profile.get("capital", 0)), 3)
    scale = CAPITAL_FACTOR.get(cap, 0.7)
    if profile.get("has_land"):
        scale += 0.3
    if strategy_key in ("relocate", "skill_buffer"):
        scale = min(scale, 0.7)
    if strategy_key == "external_floor":
        scale = 0.3
    return round(scale, 2)


# ---------------------------------------------------------------------------
# 画像 → 定性韧性分（健康 / 家庭规模 / 在地支持）
# ---------------------------------------------------------------------------
def _qual_score(profile):
    s = 50
    if profile.get("health") == "良好":
        s += 25
    if profile.get("household", 1) <= 4:
        s += 15
    elif profile.get("household", 1) <= 8:
        s += 5
    if profile.get("has_land") or profile.get("location") in ("郊区", "乡村", "离网"):
        s += 10
    return min(100, s)


# ---------------------------------------------------------------------------
# 生存自由指数
# ---------------------------------------------------------------------------
def freedom_index(avg_coverage, strategy_score, strategy_key, profile):
    """0-100 的生存自由度。越高越不依赖市场工资 / 外部托底。

    构成：供给覆盖 * w_s + 策略可行性 * w_t + 定性韧性 * w_q。
    纯外部托底路径特殊封顶：它"匹配度满分"但本质是依赖，不算自由。
    """
    supply_score = min(1.0, avg_coverage) * 100.0
    qual = _qual_score(profile)
    w_s, w_t, w_q = STRATEGY_WEIGHTS.get(strategy_key, (0.5, 0.3, 0.2))

    if strategy_key == "external_floor":
        # 只能靠政府/慈善的人，本项目给不了自由，封顶很低且明确标注
        fi = min(30.0, w_t * strategy_score + w_q * qual)
        return round(fi, 1), "依赖外部托底（非自主）"

    fi = w_s * supply_score + w_t * strategy_score + w_q * qual
    fi = round(min(100.0, max(0.0, fi)), 1)

    # 物理自给型 vs 收入/迁移型，自由的"来源"不同，标签要讲清楚
    income_based = strategy_key in ("relocate", "skill_buffer")
    if fi >= 80:
        label = ("高（靠可携带收入/低生活成本，基本不依赖本地工资市场）"
                 if income_based else "高（基本退可守，不依赖市场工资）")
    elif fi >= 60:
        label = ("中高（靠可携带收入，需持续接单/远程工作）"
                 if income_based else "中高（大部分自主，仍需少量外部收入/缓冲）")
    elif fi >= 40:
        label = ("中（半自由，靠收入但缓冲薄，需持续外部收入）"
                 if income_based else "中（半自由，需持续外部收入补足缺口）")
    else:
        label = "低（难独立，需外部托底或更多积累）"
    return fi, label


# ---------------------------------------------------------------------------
# 跑供给层（画像驱动）
# ---------------------------------------------------------------------------
def run_supply(population, asset_scale, community="profile-run"):
    """按人口与资产系数跑所有合规模块，返回 [(module_id, module, needs, delivery), ...]。"""
    results = []
    for entry, klass in discover_modules():
        module = klass()
        context = {"community": community, "population": population}
        needs = module.assess_needs(context)
        resources = {"available": DEFAULT_RESOURCES, "asset_scale": asset_scale}
        plan = module.schedule(resources, needs)
        delivery = module.provide(plan)
        results.append((entry, module, needs, delivery))
    return results


# ---------------------------------------------------------------------------
# 渲染合并报告
# ---------------------------------------------------------------------------
def render_report(profile, scored, asset_scale, results):
    lines = []
    lines.append("# 生存自由报告（Lifeline OS）")
    lines.append("")
    lines.append("> 画像 → 策略推荐 → 供给模拟 → 自由指数，一条闭环。荒地只是策略之一。")
    lines.append("")

    # 1. 画像
    lines.append("## 1. 主人/社区画像")
    lines.append("")
    lines.append(f"- 是否有地：{profile.get('has_land')}")
    lines.append(f"- 启动资本（0-3）：{profile.get('capital')}")
    lines.append(f"- 技能：{', '.join(profile.get('skills', [])) or '无'}")
    lines.append(f"- 所在地：{profile.get('location')}")
    lines.append(f"- 家庭/社区人数：{profile.get('household')}")
    lines.append(f"- 健康：{profile.get('health')}")
    lines.append(f"- 可迁移：{profile.get('mobility')}")
    lines.append(f"- 资产规模系数（本项目推算）：**{asset_scale}**（1.0 = 持有与基准社区匹配的产能）")
    lines.append("")

    # 2. 推荐策略
    lines.append("## 2. 推荐生存策略（按匹配度）")
    lines.append("")
    top = scored[0]
    for i, (name, sc, intervention, freedom, key) in enumerate(scored, 1):
        mark = " ← 首选" if i == 1 and sc >= 40 else ""
        lines.append(f"{i}. **{name}** — 匹配 {sc}/100{mark}")
        lines.append(f"   - {intervention}")
    lines.append("")

    # 3. 供给层模拟
    lines.append("## 3. 供给层 30 天自给模拟（按本画像）")
    lines.append("")
    lines.append("| 域 | 日均需求 | 平均自给率 | 满供天数 | 缺口天数 | 最弱日 |")
    lines.append("|---|---|---|---|---|---|")
    covs = []
    for mid, module, needs, delivery in results:
        unit = NEED_UNITS.get(mid, "")
        demand = _demand_value(needs, mid)
        avg = delivery.get("delivered_avg_coverage", 0)
        full = delivery.get("full_days", 0)
        short = delivery.get("shortfall_days", 0)
        weak = _weakest_day(module)
        covs.append(avg)
        lines.append(f"| {mid} | {demand} {unit} | {avg:.3f} | {full}/30 | {short}/30 | {weak} |")
    lines.append("")

    # 4. 自由指数
    avg_cov = sum(covs) / max(len(covs), 1) if covs else 0.0
    fi, fi_label = freedom_index(avg_cov, top[1], top[4], profile)
    lines.append("## 4. 生存自由指数")
    lines.append("")
    lines.append(f"- **综合得分：{fi}/100**")
    lines.append(f"- **分档：{fi_label}**")
    lines.append(f"- 构成：供给覆盖均值 {min(1.0, avg_cov)*100:.0f}% × 策略权重 + 策略匹配 {top[1]}/100 + 定性韧性 {_qual_score(profile)}/100")
    lines.append("")

    # 5. 诚实边界
    lines.append("## 5. 诚实边界")
    lines.append("")
    if top[4] == "external_floor" and top[1] >= 100:
        lines.append("- ⚠️ 当前画像下，务实路径是**依赖外部托底**——无地、无资本、无可变现技能的人，本项目（社区自组织 + 自动化）帮不了。请优先争取政府现金底 / 基础服务。")
    else:
        lines.append("- 本工具只「分析 + 模拟」，决策权与执行权留在主人与社区手里。")
        lines.append("- 若首选是「分布式自给」才需要走拿地/开荒；其他策略不涉及地。")
        lines.append("- 模拟是一阶线性规划工具（产能/需求同比缩放），不是承诺；落地前请用你们社区的真实数据替换 `modules/*/data/`。")
        lines.append("- 本项目是**自愿社区**的开源协调工具，不替代政府、不交付机器人、不解决人生意义。")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 内置示例画像：小A · 乡村有地、少资本、会种地和组织
# ---------------------------------------------------------------------------
def _demo_profile():
    return {
        "has_land": True,
        "capital": 1,
        "skills": ["种地", "组织"],
        "location": "乡村",
        "household": 12,
        "health": "良好",
        "mobility": False,
    }


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    profile = _demo_profile()
    out_path = None

    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--profile" and i + 1 < len(argv):
            with open(argv[i + 1], "r", encoding="utf-8") as f:
                profile = json.load(f)
            i += 2
        elif a == "--out" and i + 1 < len(argv):
            out_path = argv[i + 1]
            i += 2
        else:
            i += 1

    # 延迟导入，避免循环；strategy_analyzer 与 lifeline.py 同目录
    sa_spec = importlib.util.spec_from_file_location(
        "strategy_analyzer", os.path.join(LIFELINE_OS_DIR, "strategy_analyzer.py")
    )
    sa = importlib.util.module_from_spec(sa_spec)
    sa_spec.loader.exec_module(sa)

    scored = sa.analyze(profile)
    top = scored[0]
    asset_scale = compute_asset_scale(profile, top[4])
    results = run_supply(profile.get("household", 1), asset_scale)
    report = render_report(profile, scored, asset_scale, results)

    print(report)
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(report + "\n")
        print(f"\n[Lifeline] 报告已写入: {out_path}")
    return report


if __name__ == "__main__":
    main()
