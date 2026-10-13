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
    python lifeline-os/lifeline.py                                  # 内置示例画像（小A·乡村有地），中文
    python lifeline-os/lifeline.py --profile x.json                 # 读 JSON 画像
    python lifeline-os/lifeline.py --profile x.json --out report.md # 写文件
    python lifeline-os/lifeline.py --lang en                        # 英文报告
    python lifeline-os/lifeline.py --lang es                        # 西班牙文报告
"""

import importlib.util
import json
import os
import sys

LIFELINE_OS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(LIFELINE_OS_DIR, "..")
sys.path.insert(0, ROOT)
if LIFELINE_OS_DIR not in sys.path:
    sys.path.insert(0, LIFELINE_OS_DIR)
import i18n  # noqa: E402  多语言：所有面向人的字符串走 t()
import executor  # noqa: E402  参考执行器（Stage 6，动作层）

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
collect_action_plan = _orch.collect_action_plan
generate_action_plan_json = _orch.generate_action_plan_json
generate_action_plan_md = _orch.generate_action_plan_md

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

    返回值：(得分, 标签键)。标签键由渲染层按当前语言翻译。
    """
    supply_score = min(1.0, avg_coverage) * 100.0
    qual = _qual_score(profile)
    w_s, w_t, w_q = STRATEGY_WEIGHTS.get(strategy_key, (0.5, 0.3, 0.2))

    if strategy_key == "external_floor":
        # 只能靠政府/慈善的人，本项目给不了自由，封顶很低且明确标注
        fi = min(30.0, w_t * strategy_score + w_q * qual)
        return round(fi, 1), "fi.external"

    fi = w_s * supply_score + w_t * strategy_score + w_q * qual
    fi = round(min(100.0, max(0.0, fi)), 1)

    # 物理自给型 vs 收入/迁移型，自由的"来源"不同，标签要讲清楚
    income_based = strategy_key in ("relocate", "skill_buffer")
    if fi >= 80:
        label_key = "fi.high_income" if income_based else "fi.high_self"
    elif fi >= 60:
        label_key = "fi.midhigh_income" if income_based else "fi.midhigh_self"
    elif fi >= 40:
        label_key = "fi.mid_income" if income_based else "fi.mid_self"
    else:
        label_key = "fi.low"
    return fi, label_key


# ---------------------------------------------------------------------------
# 画像资产 → 真实可用资源列表（资产感知；无 assets 字段则回退默认，向后兼容 demo）
# ---------------------------------------------------------------------------
def _derive_available(ctx):
    """从画像上下文推导'真实可用资产'列表。

    仅统计画像 assets 里确实拥有/运营的产能；没有 assets 字段时返回 None，
    由调用方回退到 DEFAULT_RESOURCES，保证旧 demo / 测试行为不变。

    设计要点（诚实）：has_land 只代表'有地可建'，不自动等于'已在产粮'；
    local-farm / community-storage 只有在确实运营（大棚或显式 farm 标记）时才计入，
    否则视为'尚未耕种'，让零装备户型的供给地板诚实地趋近于 0。
    """
    assets = ctx.get("assets")
    if not isinstance(assets, dict):
        return None
    avail = []
    if (assets.get("solar_kw") or 0) > 0:
        avail.append("solar")
    if (assets.get("battery_kwh") or 0) > 0:
        avail.append("battery")
    if assets.get("wind_kw"):
        avail.append("wind")
    if assets.get("well"):
        avail.append("well")
    if assets.get("rainwater_harvesting"):
        avail.append("rain-harvest")
    if (assets.get("water_storage_l") or 0) > 0:
        avail.append("community-tank")
    if (assets.get("greenhouse_m2") or 0) > 0:
        avail.append("greenhouse")
    has_land = ctx.get("has_land")
    farming = (assets.get("greenhouse_m2") or 0) > 0 or assets.get("farm")
    if has_land and farming:
        avail.append("local-farm")
    if (assets.get("water_storage_l") or 0) > 0 or farming:
        avail.append("community-storage")
    return avail


# ---------------------------------------------------------------------------
# 跑供给层（画像驱动）
# ---------------------------------------------------------------------------
def run_supply(population, asset_scale, community="profile-run", context=None):
    """按人口与资产系数跑所有合规模块，返回 [(module_id, module, needs, delivery), ...]。

    context 可携带画像字段（has_land/capital/location/skills/health），供住所/健康类
    模块使用；流资源模块（energy/food/water）忽略多余键。
    """
    results = []
    for entry, klass in discover_modules():
        module = klass()
        ctx = {"community": community, "population": population}
        if isinstance(context, dict):
            ctx.update(context)
        needs = module.assess_needs(ctx)
        # 资产感知：画像带来真实资产记录时，用它推导可用资产；否则回退默认（向后兼容 demo）
        avail = _derive_available(ctx)
        if avail is None:
            avail = DEFAULT_RESOURCES
        resources = {"available": avail, "asset_scale": asset_scale}
        plan = module.schedule(resources, needs)
        delivery = module.provide(plan)
        # 6 元组：(module_id, module, needs, plan, delivery, context)
        results.append((entry, module, needs, plan, delivery, ctx))
    return results


# ---------------------------------------------------------------------------
# 渲染合并报告
# ---------------------------------------------------------------------------
def _bool(v):
    return i18n.t("bool.true") if v else i18n.t("bool.false")


def _cat(prefix, value):
    """翻译用户数据里的可选分类值（如地点/健康）；中文保持原值，未登记的值原样返回。"""
    if value is None:
        return ""
    if i18n.get_language() == "zh":
        return value
    out = i18n.t(f"{prefix}.{value}")
    return value if out.startswith(f"{prefix}.") else out


def render_report(profile, scored, asset_scale, results):
    lines = []
    lines.append(i18n.t("title.lifeline"))
    lines.append("")
    lines.append(i18n.t("sub.lifeline"))
    lines.append("")

    # 1. 画像
    lines.append("## 1. " + i18n.t("sec.profile"))
    lines.append("")
    lines.append(f"- {i18n.t('prof.has_land')}：{_bool(profile.get('has_land'))}")
    lines.append(f"- {i18n.t('prof.capital')}：{profile.get('capital')}")
    lines.append(f"- {i18n.t('prof.skills')}：{', '.join(profile.get('skills', [])) or i18n.t('prof.none')}")
    lines.append(f"- {i18n.t('prof.location')}：{_cat('loc', profile.get('location'))}")
    lines.append(f"- {i18n.t('prof.household_full')}：{profile.get('household')}")
    lines.append(f"- {i18n.t('prof.health')}：{_cat('health', profile.get('health'))}")
    lines.append(f"- {i18n.t('prof.mobility')}：{_bool(profile.get('mobility'))}")
    lines.append(f"- {i18n.t('prof.asset_scale')}：**{asset_scale}**{i18n.t('prof.asset_scale_note')}")
    lines.append("")

    # 2. 推荐策略
    lines.append("## 2. " + i18n.t("sec.strategies"))
    lines.append("")
    top = scored[0]
    for i, (name_key, sc, intervention_key, freedom_key, key) in enumerate(scored, 1):
        mark = i18n.t("r.recommended") if i == 1 and sc >= 40 else ""
        lines.append(f"{i}. **{i18n.t(name_key)}** — {i18n.t('r.match')} {sc}/100{mark}")
        lines.append(f"   - {i18n.t(intervention_key)}")
    lines.append("")

    # 3. 供给层模拟
    lines.append("## 3. " + i18n.t("sec.supply"))
    lines.append("")
    lines.append(f"| {i18n.t('th.domain')} | {i18n.t('th.demand')} | {i18n.t('th.coverage')} | "
                 f"{i18n.t('th.full')} | {i18n.t('th.short')} | {i18n.t('th.weak')} |")
    lines.append("|---|---|---|---|---|---|")
    covs = []
    for mid, module, needs, plan, delivery, ctx in results:
        unit = i18n.t(f"unit.{mid}")
        demand = _demand_value(needs, mid)
        avg = delivery.get("delivered_avg_coverage", 0)
        full = delivery.get("full_days", 0)
        short = delivery.get("shortfall_days", 0)
        weak = _weakest_day(module)
        covs.append(avg)
        lines.append(f"| {i18n.t(f'dom.{mid}')} | {demand} {unit} | {avg:.3f} | {full}/30 | {short}/30 | {weak} |")
    lines.append("")

    # 4. 自由指数
    avg_cov = sum(covs) / max(len(covs), 1) if covs else 0.0
    fi, fi_label_key = freedom_index(avg_cov, top[1], top[4], profile)
    lines.append("## 4. " + i18n.t("sec.freedom"))
    lines.append("")
    lines.append(f"- **{i18n.t('ff.score')}：{fi}/100**")
    lines.append(f"- **{i18n.t('ff.tier')}：{i18n.t(fi_label_key)}**")
    lines.append(f"- {i18n.t('ff.compose', pct=int(min(1.0, avg_cov)*100), top=top[1], qual=_qual_score(profile))}")
    lines.append("")

    # 5. 诚实边界
    lines.append("## 5. " + i18n.t("sec.honest"))
    lines.append("")
    if top[4] == "external_floor" and top[1] >= 100:
        lines.append("- " + i18n.t("honest.external"))
    else:
        lines.append("- " + i18n.t("honest.tool"))
        lines.append("- " + i18n.t("honest.land"))
        lines.append("- " + i18n.t("honest.sim"))
        lines.append("- " + i18n.t("honest.gov"))
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
    lang = "en"
    do_execute = False

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
        elif a == "--lang" and i + 1 < len(argv):
            lang = argv[i + 1]
            i += 2
        elif a == "--execute":
            do_execute = True
            i += 1
        else:
            i += 1

    i18n.set_language(lang)

    # 延迟导入，避免循环；strategy_analyzer 与 lifeline.py 同目录
    sa_spec = importlib.util.spec_from_file_location(
        "strategy_analyzer", os.path.join(LIFELINE_OS_DIR, "strategy_analyzer.py")
    )
    sa = importlib.util.module_from_spec(sa_spec)
    sa_spec.loader.exec_module(sa)

    scored = sa.analyze(profile)
    top = scored[0]
    asset_scale = compute_asset_scale(profile, top[4])
    profile_ctx = {
        "has_land": profile.get("has_land"),
        "capital": profile.get("capital"),
        "location": profile.get("location"),
        "skills": profile.get("skills", []),
        "health": profile.get("health"),
        "assets": profile.get("assets"),
    }
    results = run_supply(profile.get("household", 1), asset_scale, context=profile_ctx)
    report = render_report(profile, scored, asset_scale, results)

    print(report)
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(report + "\n")
        print(f"\n[Lifeline] {i18n.t('lf.written')}: {out_path}")

    # 动作层（Stage 6）：汇集任务级指令，写计划；可选驱动参考执行器
    actions = collect_action_plan(results)
    plan_json = generate_action_plan_json(actions, community=profile.get("community", "profile-run"))
    plan_md = generate_action_plan_md(actions)
    action_plan_path = os.path.join(LIFELINE_OS_DIR, "last-action-plan.json")
    action_plan_md_path = os.path.join(LIFELINE_OS_DIR, "last-action-plan.md")
    with open(action_plan_path, "w", encoding="utf-8") as f:
        json.dump(plan_json, f, ensure_ascii=False, indent=2)
    with open(action_plan_md_path, "w", encoding="utf-8") as f:
        f.write(plan_md + "\n")
    print(f"\n[Lifeline] {i18n.t('oc.action_plan_written')}: {action_plan_path} "
          f"({plan_json['meta']['action_count']} actions)")

    if do_execute:
        print(f"\n[Lifeline] {i18n.t('oc.action_execute')} ...")
        out = executor.execute_plan(plan_json["actions"])
        s = out["summary"]
        print(f"  {i18n.t('oc.action_exec_summary')}: "
              f"{i18n.t('oc.action_ok')}={s['ok']} "
              f"{i18n.t('oc.action_skip')}={s['skip']} "
              f"{i18n.t('oc.action_failed')}={s['failed']}")
    return report


if __name__ == "__main__":
    main()
