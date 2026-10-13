"""本地健康模块 —— 基础健康安全评估（第 5 插槽，多语言就绪）。

与 energy/food/water 的"每日流资源"、shelter 的"静态居住安全"都不同，本模块
把**基础健康安全**建模为一阶代理指标：

    覆盖 = min(1, 自护能力 × (0.7 + 0.3 × 在地可及性))

- 自护能力：主人是否有医护技能、启动资本能否买到药/补给、asset_scale（资产规模）
  能否支撑常备物资。有医护技能 → 高；有资本 → 中；赤贫 → 低。
- 在地可及性：乡村/离网低、郊区中、城市高（离正式医疗的距离代理）。

这是一个**粗粒度、诚实的第一阶代理**，不是医疗建议，也不声称能"解决健康"。
真实部署应替换为本地卫生站/互助照护/保险数据，只要 conform 到
module-interface-v1，编排层无需改动。
"""

import json
import os

from action_spec import make_action

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")


def _load_json(name):
    with open(os.path.join(DATA, name), "r", encoding="utf-8") as f:
        return json.load(f)


class HealthModule:
    def __init__(self):
        self._last = None

    def name(self):
        return "health"

    def provides(self):
        return ["basic-health-security"]

    def _config(self):
        try:
            return _load_json("config.json")
        except FileNotFoundError:
            return {}

    def assess_needs(self, context):
        cfg = self._config()
        population = context.get("population", cfg.get("population", 1))
        # 把画像的健康相关字段经 needs 透传给 schedule/provide（接口不含额外参数）。
        return {
            "need_type": "basic-health-security",
            "population": population,
            "persons_need": population,
            "unit": "人",
            "skills": context.get("skills", []) or [],
            "capital": min(int(context.get("capital", cfg.get("default_capital", 1))), 3),
            "location": context.get("location", ""),
            "health": context.get("health", "良好"),
        }

    def schedule(self, resources, needs):
        return {
            "strategy": "self-sufficiency",
            "priority": ["self-care"],
            "target_persons": needs["persons_need"],
            # 经 plan 透传（provide 只收 plan）
            "skills": needs.get("skills", []),
            "capital": needs.get("capital", 1),
            "location": needs.get("location", ""),
            "health": needs.get("health", "良好"),
            "asset_scale": resources.get("asset_scale", 1.0),
        }

    def _simulate(self, plan):
        cfg = self._config()
        skills = plan.get("skills", [])
        capital = min(int(plan.get("capital", cfg.get("default_capital", 1))), 3)
        location = plan.get("location", "")
        asset_scale = plan.get("asset_scale", 1.0)

        # 自护能力基线
        if "医护" in skills:
            base = cfg.get("self_care_medical_skill", 0.90)
        elif capital >= 2:
            base = cfg.get("self_care_capital_2", 0.65)
        elif capital == 1:
            base = cfg.get("self_care_capital_1", 0.45)
        else:
            base = cfg.get("self_care_base", 0.30)
        self_care = min(1.0, base + cfg.get("self_care_per_scale", 0.12) * asset_scale)

        # 在地可及性（离正式医疗的距离代理）
        loc_factor = cfg.get("loc_factor", {}).get(location, cfg.get("loc_default", 0.6))
        coverage = round(min(1.0, self_care * (0.7 + cfg.get("loc_weight", 0.3) * loc_factor)), 3)

        horizon = cfg.get("horizon_days", 30)
        daily = [{"day": d + 1, "coverage": coverage} for d in range(horizon)]
        full = sum(1 for d in daily if d["coverage"] >= 0.999)
        return {
            "horizon_days": horizon,
            "avg_coverage": coverage,
            "full_days": full,
            "shortfall_days": horizon - full,
            "self_care": round(self_care, 3),
            "loc_factor": loc_factor,
            "daily": daily,
        }

    def provide(self, plan):
        sim = self._simulate(plan)
        self._last = sim
        short = sim["shortfall_days"] > 0
        return {
            "delivered_avg_coverage": sim["avg_coverage"],
            "full_days": sim["full_days"],
            "shortfall_days": sim["shortfall_days"],
            "status": "partial" if short else "ok",
            # 健康缺口无法自产补足，只能靠社区互助照护/就近卫生站求援
            "fail_mode": "seek-care",
        }

    def status(self):
        if not self._last:
            return {"health": "nominal", "uptime": "100%"}
        return {
            "health": "nominal" if self._last["shortfall_days"] == 0 else "degraded",
            "avg_coverage": self._last["avg_coverage"],
            "self_care": self._last["self_care"],
            "loc_factor": self._last["loc_factor"],
        }

    # ------------------------------------------------------------------
    # 动作层（Stage 6，可选扩展）：人形机器人任务级指令。
    # 健康缺口无法自产补足——机器人负责监测与提醒，就医由人完成。
    # ------------------------------------------------------------------
    def actions(self, plan, context):
        return [
            make_action(
                id="health.daily.monitor", domain="health", actor="robot",
                command="monitor", target="care-station",
                params={},
                frequency="daily", priority="low",
                precondition="",
                expected_effect="",
                verify="health.self_care >= 0",
                note="监测常备药与自护物资，仅监测不改动状态。",
            ),
            make_action(
                id="health.daily.inspect", domain="health", actor="robot",
                command="inspect", target="first-aid",
                params={},
                frequency="daily", priority="low",
                precondition="",
                expected_effect="",
                verify="health.self_care >= 0.3",
                note="巡检急救包与在地可及性，仅监测不改动状态。",
            ),
            make_action(
                id="health.on_demand.seek_care", domain="health", actor="human",
                command="seek_care", target="clinic",
                params={},
                frequency="on-demand", priority="high",
                precondition="health.needs_care == True",
                expected_effect="",
                verify="",
                note="当触发就医需求（伤病情形），由人前往就近卫生站；机器人不替代专业医疗。",
            ),
        ]
