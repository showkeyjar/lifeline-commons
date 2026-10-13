"""Lifeline OS —— 生存策略分析器。

核心原则：**在决定"怎么做"之前，先分析"主人/社区的资源画像，哪种生存策略最匹配"。**
荒地（分布式自给）只是众多策略中的一种，不是唯一范式。本分析器根据画像
给每种策略打分，输出推荐 + 理由 + 本项目能在哪一步介入。

注意边界：
- 本分析器是**软件分析层**，不是机器人、不替主人决策、不解决人生意义。
- 它只"建议"，执行权与决策权留在主人与社区手里。
- 它诚实标注"本项目帮不了的人"（赤贫无地、健康受限），这部分只能靠政府托底。

用法：
    python lifeline-os/strategy_analyzer.py            # 跑内置示例画像
    python lifeline-os/strategy_analyzer.py --profile x.json  # 读 JSON 画像
"""

import json
import os
import sys

# 让同目录的 i18n 可被导入（多语言）
LIFELINE_OS_DIR = os.path.dirname(os.path.abspath(__file__))
if LIFELINE_OS_DIR not in sys.path:
    sys.path.insert(0, LIFELINE_OS_DIR)
import i18n  # noqa: E402  多语言：所有面向人的字符串走 t()

# 画像字段约定（缺省按"最受限"处理，宁可不夸大）：
#   has_land:    bool            是否有可用土地（自有/长租/承包）
#   capital:     0-3             启动资本水平（0 无 / 1 少 / 2 中 / 3 足）
#   skills:      list[str]       技能（种地/电工/医护/组织/远程工作/手艺）
#   location:    str             城市/郊区/乡村/离网
#   household:   int             家庭/社区人数
#   health:      str             良好/受限
#   mobility:    bool            是否可迁移到低成本地区


def _has(p, skill):
    return skill in p.get("skills", [])


def _score_distributed(p):
    """策略1：分布式自给（荒地/集体土地自建）。适用：有地+有资本+有组织力。"""
    if not p.get("has_land"):
        return 0
    s = 40
    s += min(p.get("capital", 0), 3) * 10          # 0-30
    if _has(p, "组织"):
        s += 15
    if _has(p, "种地"):
        s += 10
    if p.get("location") in ("乡村", "离网"):
        s += 5
    return min(s, 100)


def _score_urban_collective(p):
    """策略2：城市社区协作（共享空间+分工+半市场）。适用：城市/郊区+有技能+有资本。"""
    loc = p.get("location", "")
    if loc not in ("城市", "郊区"):
        return 0
    s = 35
    s += min(p.get("capital", 0), 3) * 8            # 0-24
    if _has(p, "组织"):
        s += 20
    if _has(p, "手艺") or _has(p, "电工") or _has(p, "医护"):
        s += 15
    if p.get("household", 1) >= 5:                  # 多人分摊共享更划算
        s += 6
    return min(s, 100)


def _score_semi_self_sufficient(p):
    """策略3：半自给+基础缓冲（以降开销为主，任何有微量稳定收入者通用）。"""
    s = 30
    if min(p.get("capital", 0), 3) >= 1:
        s += 15
    if _has(p, "种地") or _has(p, "电工"):
        s += 15
    if p.get("health") == "良好":
        s += 10
    if p.get("location") in ("郊区", "乡村", "离网"):
        s += 10
    return min(s, 100)


def _score_relocate(p):
    """策略4：低成本地区迁移（搬去生存成本极低的地区）。适用：可迁移者。"""
    if not p.get("mobility"):
        return 0
    s = 45
    if p.get("health") == "良好":
        s += 15
    if _has(p, "远程工作"):
        s += 20
    if min(p.get("capital", 0), 3) >= 1:
        s += 10
    return min(s, 100)


def _score_skill_buffer(p):
    """策略5：技能变现+小缓冲（靠手艺/远程工作覆盖基础开销+建缓冲）。适用：有技能+健康。"""
    has_marketable = _has(p, "远程工作") or _has(p, "手艺") or _has(p, "医护") or _has(p, "电工")
    if not has_marketable:
        return 0
    if p.get("health") != "良好":
        return 20
    s = 50
    if _has(p, "远程工作"):
        s += 20
    if min(p.get("capital", 0), 3) >= 1:
        s += 10
    return min(s, 100)


def _score_external_floor(p):
    """策略6：依赖外部托底（政府/慈善）。诚实标注：本项目帮不了这类人。"""
    no_land = not p.get("has_land")
    no_capital = min(p.get("capital", 0), 3) == 0
    no_marketable = not (_has(p, "远程工作") or _has(p, "手艺") or _has(p, "医护") or _has(p, "电工"))
    if no_land and no_capital and no_marketable:
        return 100  # 这是唯一现实的路径，但项目本身无法提供
    return 0


STRATEGIES = [
    {
        "key": "distributed",
        "name_key": "strat.distributed.name",
        "score": _score_distributed,
        "intervention_key": "strat.distributed.intervention",
        "freedom_key": "strat.distributed.freedom",
    },
    {
        "key": "urban_collective",
        "name_key": "strat.urban_collective.name",
        "score": _score_urban_collective,
        "intervention_key": "strat.urban_collective.intervention",
        "freedom_key": "strat.urban_collective.freedom",
    },
    {
        "key": "semi_self",
        "name_key": "strat.semi_self.name",
        "score": _score_semi_self_sufficient,
        "intervention_key": "strat.semi_self.intervention",
        "freedom_key": "strat.semi_self.freedom",
    },
    {
        "key": "relocate",
        "name_key": "strat.relocate.name",
        "score": _score_relocate,
        "intervention_key": "strat.relocate.intervention",
        "freedom_key": "strat.relocate.freedom",
    },
    {
        "key": "skill_buffer",
        "name_key": "strat.skill_buffer.name",
        "score": _score_skill_buffer,
        "intervention_key": "strat.skill_buffer.intervention",
        "freedom_key": "strat.skill_buffer.freedom",
    },
    {
        "key": "external_floor",
        "name_key": "strat.external_floor.name",
        "score": _score_external_floor,
        "intervention_key": "strat.external_floor.intervention",
        "freedom_key": "strat.external_floor.freedom",
    },
]


def analyze(profile):
    """返回按匹配度降序的策略列表：[(name_key, score, intervention_key, freedom_key, key), ...]。

    返回的是**翻译键**而非成品文案；渲染时再按当前语言翻译（见 render_report）。
    """
    scored = []
    for st in STRATEGIES:
        sc = st["score"](profile)
        scored.append((st["name_key"], sc, st["intervention_key"], st["freedom_key"], st["key"]))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


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


def render_report(profile, scored):
    lines = []
    lines.append(i18n.t("title.strategy"))
    lines.append("")
    lines.append(i18n.t("sub.strategy"))
    lines.append("")
    lines.append("## " + i18n.t("sec.profile"))
    lines.append("")
    lines.append(f"- {i18n.t('prof.has_land')}：{_bool(profile.get('has_land'))}")
    lines.append(f"- {i18n.t('prof.capital')}：{profile.get('capital')}")
    lines.append(f"- {i18n.t('prof.skills')}：{', '.join(profile.get('skills', [])) or i18n.t('prof.none')}")
    lines.append(f"- {i18n.t('prof.location')}：{_cat('loc', profile.get('location'))}")
    lines.append(f"- {i18n.t('prof.household_short')}：{profile.get('household')}")
    lines.append(f"- {i18n.t('prof.health')}：{_cat('health', profile.get('health'))}")
    lines.append(f"- {i18n.t('prof.mobility')}：{_bool(profile.get('mobility'))}")
    lines.append("")
    lines.append("## " + i18n.t("sec.strategies"))
    lines.append("")
    top = scored[0]
    for i, (name_key, sc, intervention_key, freedom_key, key) in enumerate(scored, 1):
        mark = i18n.t("r.recommended") if i == 1 and sc >= 40 else ""
        lines.append(f"{i}. **{i18n.t(name_key)}** — {i18n.t('r.match')} {sc}/100{mark}")
        lines.append(f"   - {i18n.t(intervention_key)}")
        lines.append(f"   - {i18n.t('r.exp_freedom')}：{i18n.t(freedom_key)}")
    lines.append("")
    lines.append("## " + i18n.t("sec.honest"))
    lines.append("")
    if top[4] == "external_floor" and top[1] >= 100:
        lines.append("- " + i18n.t("honest.external"))
    else:
        lines.append("- " + i18n.t("honest.tool"))
        lines.append("- " + i18n.t("honest.land"))
        lines.append("- " + i18n.t("honest.gov"))
    lines.append("")
    return "\n".join(lines)


def _demo_profile():
    """内置示例：一个乡村有地、少资本、会种地和组织的小群体。"""
    return {
        "has_land": True,
        "capital": 1,
        "skills": ["种地", "组织"],
        "location": "乡村",
        "household": 12,
        "health": "良好",
        "mobility": False,
    }


if __name__ == "__main__":
    profile = _demo_profile()
    lang = "zh"
    i = 1
    while i < len(sys.argv):
        a = sys.argv[i]
        if a == "--profile" and i + 1 < len(sys.argv):
            with open(sys.argv[i + 1], "r", encoding="utf-8") as f:
                profile = json.load(f)
            i += 2
        elif a == "--lang" and i + 1 < len(sys.argv):
            lang = sys.argv[i + 1]
            i += 2
        else:
            i += 1
    i18n.set_language(lang)
    scored = analyze(profile)
    print(render_report(profile, scored))
