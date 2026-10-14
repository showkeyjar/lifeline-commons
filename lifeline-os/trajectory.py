"""情景轨迹模拟器 —— 把静态快照扩展为 12 个月动态爬升曲线。

这是模拟器区别于"工具包"的灵魂：不只在说"你今天在 29% 的地板"，而是沿着那 17 条
任务指令建起装备后，逐月看到自给率爬升的数字轨迹，把"希望"从叙述变成可模拟的结果。

诚实建模原则
------------
- 能源（光伏）/ 水（集雨+储水罐）建设周期短（数周），建成当月即计入。
- **食物有"收获滞后"**：种地当月不产粮，首收时间取决于生长季长度（由画像气候
  `frost_free_days` 推导）：北方单熟约种植后 5 个月首收、三阶爬坡；南方长生长季可早种、
  一年多熟，约 3 个月首收、更快满产，且年度总产更高（有余粮）。这正是对比"南北食物瓶颈"
  的关键——南方食物自给更早达成。
- 建设时序可由画像 `build_plan` 覆盖；缺省使用 `DEFAULT_BUILD_PLAN`（保守估计，
  假设由 IT 远程收入资助，契合 skill_buffer 60）。

与 lifeline.py 的关系
-------------------
本模块复用 lifeline 的 `run_supply` / `compute_asset_scale` / `_derive_available` /
`freedom_index`，不重复实现供给逻辑，保证单一事实来源。导入 lifeline 在测试上下文
下为正常模块；在 CLI 上下文下由 lifeline.main 预先把自身注册为 sys.modules['lifeline']
以避免重复加载。
"""

import os
import sys

# 测试上下文：lifeline 已是普通模块，可直接 import。
# CLI 上下文：lifeline.main 会把自身注册到 sys.modules['lifeline']，故同一份。
if "lifeline" not in sys.modules:  # pragma: no cover - 保险，正常应能直接 import
    _spec = importlib_spec = None
    import importlib.util as _ilu
    _p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lifeline.py")
    _s = _ilu.spec_from_file_location("lifeline", _p)
    _m = _ilu.module_from_spec(_s)
    sys.modules["lifeline"] = _m
    _s.loader.exec_module(_m)

import lifeline  # noqa: E402

import i18n  # noqa: E402


# 食物收获参数不再写死——由 _food_params(climate) 按生长季长度推导，区分南北。
# 短生长季（北方，~190 天）：单熟春种秋收，首收晚、爬坡慢。
# 长生长季（南方，~330+ 天）：可早种、一年多熟，首收早、爬坡快，年度总产更高（余粮）。
# 以下常量仅作函数内缺省参考，不直接参与计算。
_NORTH_LAG = 5
_NORTH_RAMP = (0.3, 0.6, 1.0)
_MULTI_CROP_MAX = 1.25  # 长生长季年度多熟带来余粮系数的上限（clamp）

# 缺省建设时序：从零装备出发，按"先种地 → 集雨 → 光伏"的保守顺序。
# 每个里程碑的 build 是写进画像 assets 的字段增量（仅作资产"可用性"开关，
# 产能大小仍由模块内置基准 × asset_scale 决定，保证单一事实来源）。
DEFAULT_BUILD_PLAN = [
    {"month": 1, "build": {"farm": True},
     "note": "整地播种 4 亩地（当地作物）"},
    {"month": 2, "build": {"rainwater_harvesting": True, "water_storage_l": 2000},
     "note": "建雨水收集 + 储水罐（约 2 吨）"},
    {"month": 3, "build": {"solar_kw": 5, "battery_kwh": 10},
     "note": "装小规模光伏（约 5kW）+ 储能（约 10kWh）"},
]


def _food_params(climate):
    """从生长季长度推导食物收获参数（诚实区分南北）。

    短生长季（北方，~190 天 frost_free_days）：单熟春种秋收，首收晚、爬坡慢。
    长生长季（南方，~330+ 天）：可早种、一年多熟，首收早、爬坡快，年度总产更高（余粮）。
    climate 缺省按偏北（200 天）处理，保证无 climate 字段时向后兼容旧行为。
    """
    ffd = (climate or {}).get("frost_free_days")
    if not isinstance(ffd, (int, float)):
        ffd = 200  # 缺省：偏北，兼容无 climate 字段的画像
    # 生长季因子：150 天（单熟受限）→ 0；330 天（可多熟）→ 1
    season = max(0.0, min(1.0, (ffd - 150) / (330 - 150)))
    if season >= 0.5:
        lag = 3
        ramp = (0.5, 1.0)
    else:
        lag = 5
        ramp = (0.3, 0.6, 1.0)
    multi_crop = 1.0 + 0.25 * season  # 长生长季年度多熟 → 余粮系数（≤1.25）
    return lag, ramp, multi_crop


def _assets_for_month(base_assets, plan, month):
    """叠加截至 month 的所有建设里程碑，返回该月的画像 assets 字典。"""
    a = {}
    if isinstance(base_assets, dict):
        a.update(base_assets)
    for step in plan:
        if step["month"] <= month:
            a.update(step.get("build", {}))
    return a


def _plant_month(base_assets, plan, months):
    """找到 local-farm 首次出现的月份（种植月）。"""
    for m in range(months + 1):
        a = _assets_for_month(base_assets, plan, m)
        ctx = {"has_land": True, "assets": a}
        avail = lifeline._derive_available(ctx)
        if avail and "local-farm" in avail:
            return m
    return None


def project_trajectory(profile, scored, asset_scale, profile_ctx, months=12):
    """投影 12 个月（含第 0 月地板）的自给率与自由指数轨迹。

    返回 dict：
        series: [ {month, cov:{domain:cov}, avg, fi, fi_label, avail} , ... ]
        plant_month: int | None
        t0_avg: 第 0 月平均自给率（0-1）
        plan: 实际使用的建设时序
    """
    base_assets = profile.get("assets")
    plan = profile.get("build_plan") or DEFAULT_BUILD_PLAN
    top = scored[0]
    population = profile.get("household", 1)
    food_lag, food_ramp, food_mc = _food_params(profile.get("climate"))
    plant = _plant_month(base_assets, plan, months)

    series = []
    for m in range(months + 1):
        a = _assets_for_month(base_assets, plan, m)
        ctx = dict(profile_ctx)
        ctx["assets"] = a
        avail = lifeline._derive_available(ctx)
        results = lifeline.run_supply(population, asset_scale, context=ctx)

        cov = {}
        for mid, _module, _needs, _plan, delivery, _ctx in results:
            cov[mid] = float(delivery.get("delivered_avg_coverage", 0.0))

        # 食物收获滞后：种植后 food_lag 个月内为生长期（不产粮），随后按 food_ramp 爬坡；
        # 长生长季另乘多熟余粮系数 food_mc（clamp 到 1.2，代表有余粮可储存/补缺口）。
        if plant is not None and "local-farm" in (avail or []) and m >= plant:
            k = m - (plant + food_lag)
            if k < 0:
                cov["food"] = 0.0
            elif 0 <= k < len(food_ramp):
                cov["food"] = round(min(1.2, cov.get("food", 0.0) * food_ramp[k] * food_mc), 3)
            else:
                cov["food"] = round(min(1.2, cov.get("food", 0.0) * food_mc), 3)

        allcov = list(cov.values())
        avg = (sum(allcov) / len(allcov)) if allcov else 0.0
        fi, fi_label = lifeline.freedom_index(avg, top[1], top[4], profile)
        series.append({
            "month": m,
            "cov": cov,
            "avg": round(avg, 3),
            "fi": fi,
            "fi_label": fi_label,
            "avail": avail or [],
        })

    return {
        "series": series,
        "plant_month": plant,
        "food_lag": food_lag,
        "t0_avg": series[0]["avg"],
        "plan": plan,
    }


def _bar(pct):
    """把 0-100 的百分比渲染成 10 格条形（█ 已填 · 空缺）。"""
    n = max(0, min(10, round(pct / 10)))
    return "█" * n + "·" * (10 - n)


def render_trajectory_md(traj, lang="en"):
    i18n.set_language(lang)
    series = traj["series"]
    lines = []
    lines.append("## 6. " + i18n.t("sec.trajectory"))
    lines.append("")
    lines.append(i18n.t("traj.intro"))
    lines.append("")
    lines.append(
        f"| {i18n.t('traj.month').format(m='') or '月份'} "
        f"| {i18n.t('traj.th_energy')} | {i18n.t('traj.th_food')} "
        f"| {i18n.t('traj.th_water')} | {i18n.t('traj.th_avg')} | "
        f"{i18n.t('traj.th_freedom')} |"
    )
    lines.append("|---|---|---|---|---|---|")

    for row in series:
        m_label = i18n.t("traj.today") if row["month"] == 0 else i18n.t("traj.month").format(m=row["month"])
        e = row["cov"].get("energy")
        f = row["cov"].get("food")
        w = row["cov"].get("water")
        fmt = lambda v: ("%.0f%%" % (v * 100)) if isinstance(v, (int, float)) else "—"
        avg_pct = row["avg"] * 100
        bar = _bar(avg_pct)
        lines.append(
            f"| {m_label} | {fmt(e)} | {fmt(f)} | {fmt(w)} "
            f"| {fmt(row['avg'])} {bar} | {row['fi']:.1f} |"
        )

    lines.append("")
    lines.append(i18n.t("traj.food_lag", lag=traj.get("food_lag", 5)))
    lines.append("")
    last = series[-1]
    lines.append(i18n.t("traj.climb",
                         avg="%.0f" % (last["avg"] * 100),
                         fi="%.1f" % last["fi"],
                         t0="%.0f" % (traj["t0_avg"] * 100)))
    lines.append("")
    lines.append("> " + i18n.t("traj.assumption"))
    lines.append("")
    return "\n".join(lines)
