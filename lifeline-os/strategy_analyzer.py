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
import sys

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
        "name": "分布式自给（荒地/集体土地自建）",
        "score": _score_distributed,
        "intervention": "✅ 本项目介入：协调层 + 治理 + 数据驱动规划（energy/food/water 模块）",
        "freedom": "高（若成功落地）",
    },
    {
        "key": "urban_collective",
        "name": "城市社区协作（共享空间+分工+半市场）",
        "score": _score_urban_collective,
        "intervention": "✅ 本项目介入：协调层（城市版模块）+ 治理",
        "freedom": "中",
    },
    {
        "key": "semi_self",
        "name": "半自给+基础缓冲（以降开销为主）",
        "score": _score_semi_self_sufficient,
        "intervention": "✅ 本项目介入：规划工具（算你能降多少开销/建多少缓冲）",
        "freedom": "中（降低对市场的依赖）",
    },
    {
        "key": "relocate",
        "name": "低成本地区迁移（搬去生存成本极低的地区）",
        "score": _score_relocate,
        "intervention": "⚠️ 本项目不介入执行，仅提供信息与规划辅助",
        "freedom": "中高",
    },
    {
        "key": "skill_buffer",
        "name": "技能变现+小缓冲（手艺/远程工作覆盖开销+建缓冲）",
        "score": _score_skill_buffer,
        "intervention": "❌ 本项目不介入，主人自行；可规划缓冲目标",
        "freedom": "中高",
    },
    {
        "key": "external_floor",
        "name": "依赖外部托底（政府/慈善）",
        "score": _score_external_floor,
        "intervention": "❌ 本项目帮不了——这类人只能靠政府现金底/基础服务",
        "freedom": "取决于公共政策",
    },
]


def analyze(profile):
    """返回按匹配度降序的策略列表：[(name, score, intervention, freedom), ...]。"""
    scored = []
    for st in STRATEGIES:
        sc = st["score"](profile)
        scored.append((st["name"], sc, st["intervention"], st["freedom"], st["key"]))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


def render_report(profile, scored):
    lines = []
    lines.append("# 生存策略分析报告")
    lines.append("")
    lines.append("> 由 Lifeline OS 策略分析器生成 —— 先分析画像，再决定路径。荒地只是策略之一。")
    lines.append("")
    lines.append("## 主人/社区画像")
    lines.append("")
    lines.append(f"- 是否有地：{profile.get('has_land')}")
    lines.append(f"- 启动资本（0-3）：{profile.get('capital')}")
    lines.append(f"- 技能：{', '.join(profile.get('skills', [])) or '无'}")
    lines.append(f"- 所在地：{profile.get('location')}")
    lines.append(f"- 人数：{profile.get('household')}")
    lines.append(f"- 健康：{profile.get('health')}")
    lines.append(f"- 可迁移：{profile.get('mobility')}")
    lines.append("")
    lines.append("## 推荐策略（按匹配度）")
    lines.append("")
    top = scored[0]
    for i, (name, sc, intervention, freedom, key) in enumerate(scored, 1):
        mark = " ← 首选" if i == 1 and sc >= 40 else ""
        lines.append(f"{i}. **{name}** — 匹配 {sc}/100{mark}")
        lines.append(f"   - {intervention}")
        lines.append(f"   - 预计生存自由度：{freedom}")
    lines.append("")
    lines.append("## 诚实边界")
    lines.append("")
    if top[4] == "external_floor" and top[1] >= 100:
        lines.append("- ⚠️ 当前画像下，务实路径是**依赖外部托底**——本项目（社区自组织）帮不了无地、无资本、无可变现技能的人。请优先争取政府现金底 / 基础服务。")
    else:
        lines.append("- 本分析器只「建议」，决策权与执行权留在主人与社区手里。")
        lines.append("- 若首选策略是「分布式自给」，才需要走拿地/开荒那一步；其他策略不涉及地。")
        lines.append("- 本项目是**自愿社区**的开源协调工具，不替代政府、不交付机器人、不解决人生意义。")
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
    if len(sys.argv) > 2 and sys.argv[1] == "--profile":
        with open(sys.argv[2], "r", encoding="utf-8") as f:
            profile = json.load(f)
    scored = analyze(profile)
    print(render_report(profile, scored))
