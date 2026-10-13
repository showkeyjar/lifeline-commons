"""本地食物模块 —— 数据驱动参考实现（阶段 1）。

读取本地样例数据（产量预测 + 库存状态），做 30 天自给模拟，
输出**可供应餐数 vs 缺口**，解决"这个社区自己够不够吃"。

不做交易，只管本地生产 + 库存补缺；余量入库不卖。
未来可替换为真实传感器/垂直农场数据，只要 conform 到
module-interface-v1，编排层无需改动。
"""

import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

DEFAULT_MEALS_PER_PERSON = 3


def _load_json(name):
    with open(os.path.join(DATA, name), "r", encoding="utf-8") as f:
        return json.load(f)


def _load_yield():
    rows = []
    with open(os.path.join(DATA, "yield_forecast.csv"), "r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rows.append({"day": int(row["day"]), "meals": float(row["meals"])})
    return rows


class FoodModule:
    def __init__(self):
        self._last = None

    def name(self):
        return "food"

    def provides(self):
        return ["nutrition"]

    def _config(self):
        try:
            return _load_json("config.json")
        except FileNotFoundError:
            return {}

    def assess_needs(self, context):
        cfg = self._config()
        population = context.get("population", cfg.get("population", 1))
        per = cfg.get("meals_per_person_per_day", DEFAULT_MEALS_PER_PERSON)
        return {
            "need_type": "nutrition",
            "population": population,
            "daily_meals": population * per,
            "unit": "meals/day",
        }

    def schedule(self, resources, needs):
        order = ["local-farm", "community-storage"]
        priority = [r for r in order if r in resources.get("available", [])]
        return {
            "strategy": "self-sufficiency",
            "priority": priority,
            "target_daily_meals": needs["daily_meals"],
            # asset_scale：画像驱动的"资产规模系数"（1.0 = 持有与基准社区匹配的产能）。
            "asset_scale": resources.get("asset_scale", 1.0),
        }

    def _simulate(self, demand, asset_scale=1.0):
        cfg = self._config()
        inv_cfg = _load_json("inventory.json")
        cap = inv_cfg["storage_capacity_meals"] * asset_scale
        inv = inv_cfg.get("initial_meals", cap * 0.5) * asset_scale
        min_reserve = inv_cfg.get("min_reserve_meals", 0) * asset_scale

        daily = []
        for row in _load_yield():
            produced = row["meals"] * asset_scale
            if produced >= demand:
                supplied = demand
                inv = min(cap, inv + (produced - demand))  # 余量入库，不卖
            else:
                deficit = demand - produced
                draw = max(0.0, min(deficit, inv - min_reserve))
                supplied = produced + draw
                inv = inv - draw
            coverage = supplied / demand if demand else 1.0
            daily.append({
                "day": row["day"],
                "produced": round(produced, 1),
                "supplied": round(supplied, 1),
                "coverage": round(coverage, 3),
                "inventory": round(inv, 1),
            })
        cov = [d["coverage"] for d in daily]
        avg = sum(cov) / len(cov)
        full = sum(1 for c in cov if c >= 0.999)
        return {
            "horizon_days": len(daily),
            "avg_coverage": round(avg, 3),
            "full_days": full,
            "shortfall_days": len(cov) - full,
            "min_inventory": min(d["inventory"] for d in daily),
            "daily": daily,
        }

    def provide(self, plan):
        demand = plan["target_daily_meals"]
        sim = self._simulate(demand, plan.get("asset_scale", 1.0))
        self._last = sim
        short = sim["shortfall_days"] > 0
        return {
            "delivered_avg_coverage": sim["avg_coverage"],
            "full_days": sim["full_days"],
            "shortfall_days": sim["shortfall_days"],
            "status": "partial" if short else "ok",
            "fail_mode": "degrade-to-stored",  # 产量不足优先动用库存；仍不足则记录缺口
        }

    def status(self):
        if not self._last:
            return {"health": "nominal", "uptime": "99.9%"}
        return {
            "health": "nominal" if self._last["shortfall_days"] == 0 else "degraded",
            "avg_coverage": self._last["avg_coverage"],
            "min_inventory": self._last["min_inventory"],
        }
