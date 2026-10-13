"""Lifeline Commons 单元测试 —— 零依赖（仅用 stdlib unittest）。

验证两件事：
1. 每个供给模块 conform 到 module-interface-v1 的必需方法（契约守门）。
2. 数据驱动的覆盖率计算返回合理、自洽的结果（不只会喊 ok）。

运行：python -m unittest discover -s tests -t . -v
"""

import importlib.util
import os
import sys
import unittest

# 把仓库根目录加入 sys.path，保证能 import modules.* 与 lifeline-os/orchestrator
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

REQUIRED_METHODS = ["name", "provides", "assess_needs", "schedule", "provide", "status"]


def _load_module_class(file_path, class_name):
    spec = importlib.util.spec_from_file_location("mod_under_test", file_path)
    pkg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pkg)
    return getattr(pkg, class_name)


ENERGY_FILE = os.path.join(ROOT, "modules", "energy", "energy_module.py")
FOOD_FILE = os.path.join(ROOT, "modules", "food", "food_module.py")
WATER_FILE = os.path.join(ROOT, "modules", "water", "water_module.py")
ORCH_FILE = os.path.join(ROOT, "lifeline-os", "orchestrator.py")


class TestConformance(unittest.TestCase):
    """契约守门：模块必须实现全部 6 个接口方法。"""

    def test_energy_conforms(self):
        cls = _load_module_class(ENERGY_FILE, "EnergyModule")
        inst = cls()
        for m in REQUIRED_METHODS:
            self.assertTrue(callable(getattr(inst, m, None)),
                            f"EnergyModule 缺少必需方法: {m}")

    def test_food_conforms(self):
        cls = _load_module_class(FOOD_FILE, "FoodModule")
        inst = cls()
        for m in REQUIRED_METHODS:
            self.assertTrue(callable(getattr(inst, m, None)),
                            f"FoodModule 缺少必需方法: {m}")

    def test_provides_is_list(self):
        energy = _load_module_class(ENERGY_FILE, "EnergyModule")()
        food = _load_module_class(FOOD_FILE, "FoodModule")()
        water = _load_module_class(WATER_FILE, "WaterModule")()
        self.assertIsInstance(energy.provides(), list)
        self.assertIsInstance(food.provides(), list)
        self.assertIsInstance(water.provides(), list)
        self.assertIn("electricity", energy.provides())
        self.assertIn("nutrition", food.provides())
        self.assertIn("water", water.provides())

    def test_water_conforms(self):
        cls = _load_module_class(WATER_FILE, "WaterModule")
        inst = cls()
        for m in REQUIRED_METHODS:
            self.assertTrue(callable(getattr(inst, m, None)),
                            f"WaterModule 缺少必需方法: {m}")


class TestEnergyCoverage(unittest.TestCase):
    """能源模块 30 天自给模拟的自洽性。"""

    def setUp(self):
        self.mod = _load_module_class(ENERGY_FILE, "EnergyModule")()
        needs = self.mod.assess_needs({"population": 12})
        plan = self.mod.schedule({"available": ["solar", "battery"]}, needs)
        self.result = self.mod.provide(plan)

    def test_avg_coverage_in_range(self):
        cov = self.result["delivered_avg_coverage"]
        self.assertGreaterEqual(cov, 0.0)
        self.assertLessEqual(cov, 1.0)

    def test_days_sum_to_horizon(self):
        self.assertEqual(
            self.result["full_days"] + self.result["shortfall_days"], 30
        )

    def test_status_exposes_min_soc(self):
        st = self.mod.status()
        self.assertIn("min_soc_kwh", st)
        self.assertGreaterEqual(st["min_soc_kwh"], 0.0)

    def test_status_health_consistent(self):
        st = self.mod.status()
        if self.result["shortfall_days"] > 0:
            self.assertEqual(st["health"], "degraded")
        else:
            self.assertEqual(st["health"], "nominal")


class TestFoodCoverage(unittest.TestCase):
    """食物模块 30 天自给模拟的自洽性。"""

    def setUp(self):
        self.mod = _load_module_class(FOOD_FILE, "FoodModule")()
        needs = self.mod.assess_needs({"population": 12})
        plan = self.mod.schedule({"available": ["local-farm", "community-storage"]}, needs)
        self.result = self.mod.provide(plan)

    def test_avg_coverage_in_range(self):
        cov = self.result["delivered_avg_coverage"]
        self.assertGreaterEqual(cov, 0.0)
        self.assertLessEqual(cov, 1.0)

    def test_days_sum_to_horizon(self):
        self.assertEqual(
            self.result["full_days"] + self.result["shortfall_days"], 30
        )

    def test_status_exposes_min_inventory(self):
        st = self.mod.status()
        self.assertIn("min_inventory", st)
        self.assertGreaterEqual(st["min_inventory"], 0.0)


class TestWaterCoverage(unittest.TestCase):
    """水模块 30 天自给模拟的自洽性。"""

    def setUp(self):
        self.mod = _load_module_class(WATER_FILE, "WaterModule")()
        needs = self.mod.assess_needs({"population": 12})
        plan = self.mod.schedule(
            {"available": ["rain-harvest", "well", "community-tank"]}, needs
        )
        self.result = self.mod.provide(plan)

    def test_avg_coverage_in_range(self):
        cov = self.result["delivered_avg_coverage"]
        self.assertGreaterEqual(cov, 0.0)
        self.assertLessEqual(cov, 1.0)

    def test_days_sum_to_horizon(self):
        self.assertEqual(
            self.result["full_days"] + self.result["shortfall_days"], 30
        )

    def test_status_exposes_min_tank(self):
        st = self.mod.status()
        self.assertIn("min_tank_l", st)
        self.assertGreaterEqual(st["min_tank_l"], 0.0)


class TestOrchestratorDiscovery(unittest.TestCase):
    """编排器能自动发现 energy + food + water 模块。"""

    def test_discovers_all_modules(self):
        spec = importlib.util.spec_from_file_location("orchestrator", ORCH_FILE)
        orch = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(orch)
        found = [mid for mid, _ in orch.discover_modules()]
        self.assertIn("energy", found)
        self.assertIn("food", found)
        self.assertIn("water", found)


if __name__ == "__main__":
    unittest.main(verbosity=2)
