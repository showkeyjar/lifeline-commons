"""本地水模块 —— 数据驱动参考实现（阶段 1）。

读取本地样例数据（雨水 + 井水产量预测 + 储水罐状态），做 30 天自给模拟，
输出**社区自给覆盖率**（供应 ÷ 需求）。不做交易，只管本地生产 + 储水罐补缺；
余量入库不卖。

未来可替换为真实传感器数据（水表/水位计/雨量计），只要 conform 到
module-interface-v1，编排层无需改动。
"""

import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

# 默认每人每天基础用水（升），真实部署按社区实测替换
# 50 L/人/天 是满足饮用+炊事+基本卫生的生存基线（非城市舒适标准）
DEFAULT_PER_CAPITA_L = 50


def _load_json(name):
    with open(os.path.join(DATA, name), "r", encoding="utf-8") as f:
        return json.load(f)


def _load_supply():
    rows = []
    with open(os.path.join(DATA, "supply_forecast.csv"), "r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rows.append({
                "day": int(row["day"]),
                "rain_l": float(row["rain_l"]),
                "well_l": float(row["well_l"]),
            })
    return rows


class WaterModule:
    def __init__(self):
        self._last = None

    def name(self):
        return "water"

    def provides(self):
        return ["water"]

    def _config(self):
        try:
            return _load_json("config.json")
        except FileNotFoundError:
            return {}

    def assess_needs(self, context):
        cfg = self._config()
        population = context.get("population", cfg.get("population", 1))
        per_capita = cfg.get("per_capita_l_per_day", DEFAULT_PER_CAPITA_L)
        return {
            "need_type": "water",
            "population": population,
            "daily_l": round(population * per_capita, 1),
            "unit": "L/day",
        }

    def schedule(self, resources, needs):
        # 自给优先顺序：本地雨水/井水生产 → 储水罐补缺（仅补缺，不交易）
        order = ["rain-harvest", "well", "community-tank"]
        priority = [r for r in order if r in resources.get("available", [])]
        return {
            "strategy": "self-sufficiency",
            "priority": priority,
            "target_daily_l": needs["daily_l"],
        }

    def _simulate(self, demand):
        cfg = self._config()
        tank_cfg = _load_json("tank.json")
        cap = tank_cfg["capacity_l"]
        tank = tank_cfg.get("initial_l", cap * 0.5)
        min_reserve = tank_cfg.get("min_reserve_l", 0)

        daily = []
        for row in _load_supply():
            produced = row["rain_l"] + row["well_l"]
            if produced >= demand:
                supplied = demand
                tank = min(cap, tank + (produced - demand))  # 余量入库，不卖
            else:
                deficit = demand - produced
                draw = max(0.0, min(deficit, tank - min_reserve))
                supplied = produced + draw
                tank = tank - draw
            coverage = supplied / demand if demand else 1.0
            daily.append({
                "day": row["day"],
                "produced_l": round(produced, 1),
                "supplied_l": round(supplied, 1),
                "coverage": round(coverage, 3),
                "tank_l": round(tank, 1),
            })
        cov = [d["coverage"] for d in daily]
        avg = sum(cov) / len(cov)
        full = sum(1 for c in cov if c >= 0.999)
        return {
            "horizon_days": len(daily),
            "avg_coverage": round(avg, 3),
            "full_days": full,
            "shortfall_days": len(cov) - full,
            "min_tank_l": min(d["tank_l"] for d in daily),
            "daily": daily,
        }

    def provide(self, plan):
        demand = plan["target_daily_l"]
        sim = self._simulate(demand)
        self._last = sim
        short = sim["shortfall_days"] > 0
        return {
            "delivered_avg_coverage": sim["avg_coverage"],
            "full_days": sim["full_days"],
            "shortfall_days": sim["shortfall_days"],
            "status": "partial" if short else "ok",
            "fail_mode": "degrade-to-stored",  # 生产不足优先动用储水罐；仍不足则记录缺口
        }

    def status(self):
        if not self._last:
            return {"health": "nominal", "uptime": "99.9%"}
        return {
            "health": "nominal" if self._last["shortfall_days"] == 0 else "degraded",
            "avg_coverage": self._last["avg_coverage"],
            "min_tank_l": self._last["min_tank_l"],
        }
