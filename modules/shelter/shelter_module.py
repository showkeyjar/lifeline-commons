"""本地住所模块 —— 居住安全评估（Stage 4 新增，证明接口可扩展）。

与 energy/food/water 不同，住所不是"每日生产-消耗"的流资源，而是
"居住安全（产权/保有 + 可维护）"的静态评估。我们仍 conform 到同一接口：
把 30 天窗口内每天的覆盖都设为同一安全分（房子不会逐日耗尽），由编排层
统一聚合进生存自由指数。

覆盖 = min(保有安全, 可维护缓冲)
- 有地/有资本 → 自有住房，保有安全高
- 仅租房 → 保有安全低（非自由）
- 无地无资本 → 极不稳定
asset_scale（资本）提升可维护缓冲与自有概率；context 的 has_land/capital/location
决定保有安全。

参考实现只是占位模型，真实部署应替换为本地房产/租赁/社区互助数据，
只要 conform 到 module-interface-v1，编排层无需改动。
"""

import json
import os

from action_spec import make_action

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")


def _load_json(name):
    with open(os.path.join(DATA, name), "r", encoding="utf-8") as f:
        return json.load(f)


class ShelterModule:
    def __init__(self):
        self._last = None

    def name(self):
        return "shelter"

    def provides(self):
        return ["shelter"]

    def _config(self):
        try:
            return _load_json("config.json")
        except FileNotFoundError:
            return {}

    def assess_needs(self, context):
        cfg = self._config()
        population = context.get("population", cfg.get("population", 1))
        # 把画像的住房相关字段经 needs 透传给 schedule/provide（接口不含额外参数，
        # 故在 assess_needs 这唯一能拿到完整 context 的环节捕获）。
        return {
            "need_type": "shelter",
            "population": population,
            "persons_need": population,  # 需要被安全安置的人数
            "unit": "人",
            "has_land": bool(context.get("has_land", False)),
            "capital": min(int(context.get("capital", cfg.get("default_capital", 1))), 3),
            "location": context.get("location", ""),
        }

    def schedule(self, resources, needs):
        priority = [r for r in ["owned-home"] if r in resources.get("available", [])]
        return {
            "strategy": "self-sufficiency",
            "priority": priority,
            "target_persons": needs["persons_need"],
            # 把住房上下文经 plan 透传（provide 只收 plan）
            "has_land": needs.get("has_land", False),
            "capital": needs.get("capital", 1),
            "location": needs.get("location", ""),
            # asset_scale：画像驱动的资产规模系数，提升可维护缓冲（见 _simulate）
            "asset_scale": resources.get("asset_scale", 1.0),
        }

    def _simulate(self, plan):
        cfg = self._config()
        has_land = bool(plan.get("has_land", False))
        capital = min(int(plan.get("capital", cfg.get("default_capital", 1))), 3)
        asset_scale = plan.get("asset_scale", 1.0)
        # 保有安全基线（0-1）：有地/有资本 → 自有；仅租房 → 低；无 → 极低
        if has_land:
            tenure = cfg.get("tenure_owned", 0.95)
        elif capital >= 2:
            tenure = cfg.get("tenure_owned_urban", 0.90)
        elif capital == 1:
            tenure = cfg.get("tenure_rent", 0.60)
        else:
            tenure = cfg.get("tenure_none", 0.10)

        # 可维护缓冲：资产越足，越能维护/修缮/保有住房（不依赖外部市场）
        maint = min(1.0, cfg.get("maint_base", 0.6) + cfg.get("maint_per_scale", 0.4) * asset_scale)

        coverage = round(min(tenure, maint), 3)
        horizon = cfg.get("horizon_days", 30)
        daily = [{"day": d + 1, "coverage": coverage} for d in range(horizon)]
        full = sum(1 for d in daily if d["coverage"] >= 0.999)
        return {
            "horizon_days": horizon,
            "avg_coverage": coverage,
            "full_days": full,
            "shortfall_days": horizon - full,
            "tenure_secure": round(tenure, 3),
            "maint_factor": round(maint, 3),
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
            # 住所缺口无法自产补足，只能靠社区互助/共享空间求援
            "fail_mode": "request-help",
        }

    def status(self):
        if not self._last:
            return {"health": "nominal", "uptime": "100%"}
        return {
            "health": "nominal" if self._last["shortfall_days"] == 0 else "degraded",
            "avg_coverage": self._last["avg_coverage"],
            "tenure_secure": self._last["tenure_secure"],
            "maint_factor": self._last["maint_factor"],
        }

    # ------------------------------------------------------------------
    # 动作层（Stage 6，可选扩展）：人形机器人任务级指令。
    # 住所是"静态居住安全"，机器人负责巡检；损伤超阈值时维护/修缮。
    # ------------------------------------------------------------------
    def actions(self, plan, context):
        return [
            make_action(
                id="shelter.daily.inspect", domain="shelter", actor="robot",
                command="inspect", target="structure",
                params={},
                frequency="daily", priority="low",
                precondition="",
                expected_effect="",
                verify="shelter.tenure_secure >= 0",
                note="巡检房屋结构安全，仅监测不改动状态。",
            ),
            make_action(
                id="shelter.daily.monitor", domain="shelter", actor="robot",
                command="monitor", target="tenure",
                params={},
                frequency="daily", priority="low",
                precondition="",
                expected_effect="",
                verify="shelter.maint_factor >= 0",
                note="监测保有状态与可维护缓冲，仅监测不改动状态。",
            ),
            make_action(
                id="shelter.on_demand.repair", domain="shelter", actor="robot",
                command="repair", target="structure",
                params={},
                frequency="on-demand", priority="high",
                precondition="shelter.damage > 0.2",
                expected_effect="shelter.damage -= 0.1",
                verify="shelter.damage <= 0.2",
                note="当结构损伤超过阈值，实施维护/修缮；无法自修则走社区互助。",
            ),
        ]
