"""多实例对比模拟器 —— 把若干真实实例的建设轨迹叠加成一张并排曲线。

这是"极限示范"说服力的最后一公里：不再只讲"你家能从 29% 爬到 86%"，而是把
"极限地板户"和"条件稍好户"的 12 个月轨迹叠在一起，让"条件更好的人"直接看到——
**即便只是多了一点积蓄、提前备好基础装备，曲线从第一天就高出一个台阶**。

设计原则
--------
- 复用 lifeline 的 prepare() / freedom_index 与 trajectory 的 project_trajectory，
  不重复实现供给与策略逻辑（单一事实来源）。
- 对比是"同一家庭、单变量"的干净 A/B：本模块只负责叠加渲染，不修改任何仿真口径。
- 起点已带装备的实例，其第 0 月即计入（project_trajectory 已尊重 base_assets），
  不会也被迫"等 3 个月"，这正是对比想暴露的增量。

与 CLI 的关系
------------
lifeline.py 的 --compare a.json b.json 调用本模块；CLI 上下文下 lifeline 已注册为
sys.modules['lifeline']，故 import 取到同一份（i18n 状态一致）。
"""

import os
import sys

if "lifeline" not in sys.modules:  # pragma: no cover - 保险
    _ilu = __import__("importlib.util", fromlist=["spec_from_file_location"])
    _p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lifeline.py")
    _s = _ilu.spec_from_file_location("lifeline", _p)
    _m = _ilu.module_from_spec(_s)
    sys.modules["lifeline"] = _m
    _s.loader.exec_module(_m)

import lifeline  # noqa: E402
import trajectory  # noqa: E402
import i18n  # noqa: E402


# 火花线字符：0→空格，1..8→逐级方块（▁▂▃▄▅▆▇█）
_SPARK = " ▁▂▃▄▅▆▇█"


def _spark(avg):
    level = max(0, min(8, int(round((avg or 0.0) * 8))))
    return _SPARK[level]


def _bar(pct, width=10):
    """把 0-100 百分比渲染成 width 格条形（█ 已填 · 空缺）。"""
    n = max(0, min(width, round(pct / (100.0 / width))))
    return "█" * n + "·" * (width - n)


def _label(profile):
    return (profile.get("_meta") or {}).get("name") or "instance"


def run_one(profile, months=12):
    """对单个画像跑分析 + 12 个月轨迹，返回结构化结果。"""
    scored, asset_scale, profile_ctx = lifeline.prepare(profile)
    traj = trajectory.project_trajectory(profile, scored, asset_scale, profile_ctx, months)
    top = scored[0]
    return {
        "profile": profile,
        "label": _label(profile),
        "scored": scored,
        "asset_scale": asset_scale,
        "top_key": top[4],
        "traj": traj,
    }


def run_comparison(profiles_meta, months=12):
    """profiles_meta: [(label, profile_dict), ...] → 对比结构。"""
    runs = [run_one(p, months) for _lbl, p in profiles_meta]
    labels = [r["label"] for r in runs]
    return {"runs": runs, "labels": labels, "months": months}


def _months_to_80(run):
    """该实例首次达到 ≥80% 平均自给的月份；未达则返回 None。"""
    for row in run["traj"]["series"]:
        if row["avg"] >= 0.80:
            return row["month"]
    return None


def render_compare_md(comp, lang="en"):
    i18n.set_language(lang)
    months = comp["months"]
    runs = comp["runs"]
    lines = []
    lines.append("## 7. " + i18n.t("cmp.title"))
    lines.append("")
    lines.append(i18n.t("cmp.intro"))
    lines.append("")

    # ---- 汇总表 ----
    lines.append(
        f"| {i18n.t('cmp.col_instance')} | {i18n.t('cmp.col_t0')} "
        f"| {i18n.t('cmp.col_final')} | {i18n.t('cmp.col_fi')} "
        f"| {i18n.t('cmp.col_m80')} |"
    )
    lines.append("|---|---|---|---|---|")
    for r in runs:
        s = r["traj"]["series"]
        t0 = s[0]["avg"] * 100
        final = s[-1]["avg"] * 100
        fi = s[-1]["fi"]
        m80 = _months_to_80(r)
        m80_cell = i18n.t("cmp.never") if m80 is None else f"{m80}"
        lines.append(
            f"| {r['label']} | {t0:.0f}% | {final:.0f}% | {fi:.1f} | {m80_cell} |"
        )
    lines.append("")

    # ---- 火花线（并排看曲线形状）----
    lines.append(i18n.t("cmp.spark_title"))
    lines.append("")
    for r in runs:
        spark = "".join(_spark(row["avg"]) for row in r["traj"]["series"])
        lines.append(f"- **{r['label']}**：`{spark}`")
    lines.append("")

    # ---- 逐月对比表 ----
    lines.append(i18n.t("cmp.detail_title"))
    lines.append("")
    header = f"| {i18n.t('cmp.month')} | " + " | ".join(r["label"] for r in runs) + " |"
    lines.append(header)
    lines.append("|---" * (len(runs) + 1) + "|")
    for m in range(months + 1):
        m_label = i18n.t("cmp.today") if m == 0 else str(m)
        cells = []
        for r in runs:
            row = r["traj"]["series"][m]
            pct = row["avg"] * 100
            cells.append(f"{pct:.0f}% {_bar(pct)}")
        lines.append(f"| {m_label} | " + " | ".join(cells) + " |")
    lines.append("")

    # ---- 叙述（诚实结论）----
    t0s = [r["traj"]["series"][0]["avg"] for r in runs]
    finals = [r["traj"]["series"][-1]["avg"] for r in runs]
    min0, max0 = min(t0s) * 100, max(t0s) * 100
    gap = round(max0 - min0)
    minfinal = min(finals) * 100
    m80s = [m for m in (_months_to_80(r) for r in runs) if m is not None]
    m80min = min(m80s) if m80s else None
    m80max = max(m80s) if m80s else None
    m80min_txt = i18n.t("cmp.never") if m80min is None else str(m80min)
    m80max_txt = i18n.t("cmp.never") if m80max is None else str(m80max)

    # 气候/地理杠杆：起点最低 vs 起点最高 实例
    low_idx = int(min(range(len(runs)), key=lambda i: t0s[i]))
    high_idx = int(max(range(len(runs)), key=lambda i: t0s[i]))
    low_run, high_run = runs[low_idx], runs[high_idx]
    low_final = finals[low_idx] * 100
    high_final = finals[high_idx] * 100

    lines.append(i18n.t("cmp.narr_gap", min0=f"{min0:.0f}", max0=f"{max0:.0f}", gap=gap))
    lines.append("")
    lines.append(i18n.t("cmp.narr_conv", m80min=m80min_txt, m80max=m80max_txt))
    lines.append("")
    lines.append(i18n.t("cmp.narr_climate", lowstart_label=low_run["label"],
                        lowstart_final=f"{low_final:.0f}", min0=f"{min0:.0f}",
                        highstart_label=high_run["label"], max0=f"{max0:.0f}",
                        highstart_final=f"{high_final:.0f}"))
    lines.append("")
    lines.append(i18n.t("cmp.narr_hope", min0=f"{min0:.0f}", max0=f"{max0:.0f}",
                        months=months, minfinal=f"{minfinal:.0f}"))
    lines.append("")
    return "\n".join(lines)
