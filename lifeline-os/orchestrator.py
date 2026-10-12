"""Lifeline OS —— 编排骨架。

把任意一个符合 module-interface-v1 的供给模块跑成
「需求感知 → 资源调度 → 供给交付」的最小闭环。
"""

import os
import sys

# 让项目根目录可被导入（modules / lifeline_os 都在根下）
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)


def run_loop(module):
    print(f"[Lifeline OS] 加载模块: {module.name()} (provides={module.provides()})")

    context = {"community": "demo-village", "population": 12}
    needs = module.assess_needs(context)
    print(f"  1) 感知需求: {needs}")

    resources = {"available": ["solar", "local-farm", "community-storage"]}
    plan = module.schedule(resources, needs)
    print(f"  2) 调度资源: {plan}")

    delivery = module.provide(plan)
    print(f"  3) 供给交付: {delivery}")

    print(f"  状态: {module.status()}")
    print("[Lifeline OS] 闭环完成 ✓")


if __name__ == "__main__":
    from modules.food.food_module import FoodModule

    run_loop(FoodModule())
