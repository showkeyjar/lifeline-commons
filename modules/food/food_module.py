"""本地食物模块 —— 薄参考实现（先模拟，跑通闭环）。

未来可替换为：开源垂直农场 + 营养自动化（参考 MIT OpenAg Food Computer）。
只要继续 conform 到 module-interface-v1，编排层无需改动。
"""


class FoodModule:
    def name(self):
        return "food"

    def provides(self):
        return ["nutrition"]

    def assess_needs(self, context):
        population = context.get("population", 1)
        return {
            "need_type": "nutrition",
            "daily_meals": population * 3,
            "unit": "meals/day",
        }

    def schedule(self, resources, needs):
        source = "local-farm" if "local-farm" in resources.get("available", []) else "community-storage"
        return {
            "source": source,
            "meals": needs["daily_meals"],
            "mode": "controlled-environment",
        }

    def provide(self, plan):
        return {
            "delivered": plan["meals"],
            "status": "ok",
            "fail_mode": "degrade-to-stored",
        }

    def status(self):
        return {"health": "nominal", "uptime": "99.9%"}
