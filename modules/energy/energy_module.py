"""本地能源模块 —— 薄参考实现（先模拟，跑通闭环）。

未来可替换为：开源离网光伏 + 储能 + 智能配电（参考
OpenEMS / Sandia PV Lib）。只要继续 conform 到 module-interface-v1，
编排层无需改动。
"""

# 每人每天基础用电基线（kWh），薄参考值，真实部署按社区实测替换
KWH_PER_PERSON_PER_DAY = 2.5


class EnergyModule:
    def name(self):
        return "energy"

    def provides(self):
        return ["electricity"]

    def assess_needs(self, context):
        population = context.get("population", 1)
        return {
            "need_type": "electricity",
            "daily_kwh": round(population * KWH_PER_PERSON_PER_DAY, 1),
            "unit": "kWh/day",
        }

    def schedule(self, resources, needs):
        available = resources.get("available", [])
        if "solar" in available:
            source = "solar"
            mode = "renewable-direct"
        elif "battery" in available:
            source = "battery"
            mode = "stored-discharge"
        else:
            source = "community-storage"
            mode = "shared-buffer"
        return {
            "source": source,
            "kwh": needs["daily_kwh"],
            "mode": mode,
        }

    def provide(self, plan):
        return {
            "delivered_kwh": plan["kwh"],
            "status": "ok",
            "fail_mode": "degrade-to-stored",  # 光伏不足时优先放电储能
        }

    def status(self):
        return {"health": "nominal", "uptime": "99.7%"}
