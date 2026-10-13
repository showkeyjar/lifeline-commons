"""本地能源模块 —— 数据驱动参考实现（阶段 1）。

读取本地样例数据（光伏预测 + 储能状态），做 30 天自给模拟，
输出**社区自给覆盖率**（供应 ÷ 需求）。不做电力交易，只管"自己够不够用"。

未来可替换为真实传感器数据（电表/逆变器），只要 conform 到
module-interface-v1，编排层无需改动。
"""

import csv
import json
import os

from action_spec import make_action

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

# 默认每人每天基础用电（kWh），真实部署按社区实测替换
DEFAULT_PER_CAPITA_KWH = 2.5


def _load_json(name):
    with open(os.path.join(DATA, name), "r", encoding="utf-8") as f:
        return json.load(f)


def _load_solar():
    rows = []
    with open(os.path.join(DATA, "solar_forecast.csv"), "r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rows.append({"day": int(row["day"]), "kwh_per_kwp": float(row["kwh_per_kwp"])})
    return rows


class EnergyModule:
    def __init__(self):
        self._last = None

    def name(self):
        return "energy"

    def provides(self):
        return ["electricity"]

    def _config(self):
        try:
            return _load_json("config.json")
        except FileNotFoundError:
            return {}

    def assess_needs(self, context):
        cfg = self._config()
        population = context.get("population", cfg.get("population", 1))
        per_capita = cfg.get("per_capita_kwh", DEFAULT_PER_CAPITA_KWH)
        return {
            "need_type": "electricity",
            "population": population,
            "daily_kwh": round(population * per_capita, 1),
            "unit": "kWh/day",
        }

    def schedule(self, resources, needs):
        # 自给优先顺序：光伏直供 → 储能放电 → 社区共享缓冲（仅补缺，不交易）
        order = ["solar", "battery", "community-storage"]
        priority = [r for r in order if r in resources.get("available", [])]
        return {
            "strategy": "self-sufficiency",
            "priority": priority,
            "target_daily_kwh": needs["daily_kwh"],
            # asset_scale：画像驱动的"资产规模系数"（1.0 = 持有与基准社区匹配的产能）。
            # 它让供给模拟真正吃进主人画像，而非永远用 12 人基准社区的数据。
            "asset_scale": resources.get("asset_scale", 1.0),
        }

    def _simulate(self, demand, asset_scale=1.0, priority=None):
        cfg = self._config()
        # 资产感知：仅统计画像真实拥有的资源；priority=None 表示沿用内置基准（向后兼容 demo）。
        has_solar = priority is None or "solar" in priority
        pv_kwp = (cfg.get("pv_kwp", 0) * asset_scale) if has_solar else 0.0
        battery = _load_json("battery.json")
        has_battery = priority is None or "battery" in priority
        cap = (battery["capacity_kwh"] * asset_scale) if has_battery else 0.0
        soc = (battery.get("initial_soc_kwh", cap * 0.5) * asset_scale) if has_battery else 0.0
        max_disch = (battery["max_discharge_kwh_per_day"] * asset_scale) if has_battery else 0.0
        min_soc = (battery.get("min_soc_kwh", 0) * asset_scale) if has_battery else 0.0

        daily = []
        for row in _load_solar():
            gen = pv_kwp * row["kwh_per_kwp"]
            if gen >= demand:
                supplied = demand
                soc = min(cap, soc + (gen - demand))  # 余电充电，不卖只存
            else:
                deficit = demand - gen
                disch = max(0.0, min(deficit, max_disch, soc - min_soc))
                supplied = gen + disch
                soc = soc - disch
            coverage = supplied / demand if demand else 1.0
            daily.append({
                "day": row["day"],
                "gen_kwh": round(gen, 2),
                "supplied_kwh": round(supplied, 2),
                "coverage": round(coverage, 3),
                "soc_kwh": round(soc, 2),
            })
        cov = [d["coverage"] for d in daily]
        avg = sum(cov) / len(cov)
        full = sum(1 for c in cov if c >= 0.999)
        return {
            "horizon_days": len(daily),
            "avg_coverage": round(avg, 3),
            "full_days": full,
            "shortfall_days": len(cov) - full,
            "min_soc_kwh": min(d["soc_kwh"] for d in daily),
            "daily": daily,
        }

    def provide(self, plan):
        demand = plan["target_daily_kwh"]
        sim = self._simulate(demand, plan.get("asset_scale", 1.0), plan.get("priority"))
        self._last = sim
        short = sim["shortfall_days"] > 0
        return {
            "delivered_avg_coverage": sim["avg_coverage"],
            "full_days": sim["full_days"],
            "shortfall_days": sim["shortfall_days"],
            "status": "partial" if short else "ok",
            "fail_mode": "degrade-to-stored",  # 光伏不足优先放电储能；仍不足则记录缺口
        }

    def status(self):
        if not self._last:
            return {"health": "nominal", "uptime": "99.7%"}
        return {
            "health": "nominal" if self._last["shortfall_days"] == 0 else "degraded",
            "avg_coverage": self._last["avg_coverage"],
            "min_soc_kwh": self._last["min_soc_kwh"],
        }

    # ------------------------------------------------------------------
    # 动作层（Stage 6，可选扩展）：人形机器人任务级指令。
    # 能源的"生产"来自光伏/储能（由供给模拟建模），机器人负责巡检与保电。
    # ------------------------------------------------------------------
    def actions(self, plan, context):
        return [
            make_action(
                id="energy.daily.inspect", domain="energy", actor="robot",
                command="inspect", target="solar-array",
                params={},
                frequency="daily", priority="low",
                precondition="",
                expected_effect="",
                verify="energy.soc_kwh > 0",
                note="巡检光伏阵列与逆变器，仅监测不改动状态。",
            ),
            make_action(
                id="energy.daily.monitor", domain="energy", actor="robot",
                command="monitor", target="battery",
                params={},
                frequency="daily", priority="low",
                precondition="",
                expected_effect="",
                verify="energy.soc_kwh >= 0",
                note="监测储能 SOC，仅监测不改动状态。",
            ),
            make_action(
                id="energy.on_demand.shed_load", domain="energy", actor="robot",
                command="shed_load", target="distribution-board",
                params={"recover_kwh": 4},
                frequency="on-demand", priority="high",
                precondition="energy.soc_kwh < 5",
                expected_effect="energy.soc_kwh += 4",
                verify="energy.soc_kwh >= 0",
                note="当储能逼近下限，切除非必要负载以保住关键供电；不自行发电。",
            ),
        ]
