"""集成测试：顶层闭环（画像 → 策略 → 模拟 → 自由指数）。

验证：
- asset_scale 真正透传到供给模块（产能随画像缩放）。
- 画像（人口/资产）驱动覆盖率差异化，而非永远用基准社区数据。
- 生存自由指数在合法区间，且诚实封顶"外部托底"路径。
- 命令行对内置画像与三个示例画像都能跑通。

注意：用 unittest.TestCase 写法，确保 `python -m unittest discover` 与 CI 能收集到。
"""

import importlib.util
import json
import os
import unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
LIFELINE_OS_DIR = os.path.join(ROOT, "lifeline-os")


def _load_lifeline():
    spec = importlib.util.spec_from_file_location(
        "lifeline_cli", os.path.join(LIFELINE_OS_DIR, "lifeline.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_analyzer():
    spec = importlib.util.spec_from_file_location(
        "strategy_analyzer", os.path.join(LIFELINE_OS_DIR, "strategy_analyzer.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _energy_avg_coverage(population, asset_scale):
    ll = _load_lifeline()
    results = ll.run_supply(population, asset_scale, community="test")
    for mid, _m, _n, d in results:
        if mid == "energy":
            return d["delivered_avg_coverage"]
    raise AssertionError("energy module missing")


class TestLifelineLoop(unittest.TestCase):

    def test_compute_asset_scale_land_and_capital(self):
        ll = _load_lifeline()
        base = {"has_land": False, "capital": 0}
        land = {"has_land": True, "capital": 1}
        self.assertLess(
            ll.compute_asset_scale(base, "distributed"),
            ll.compute_asset_scale(land, "distributed"),
        )
        self.assertGreater(
            ll.compute_asset_scale({"has_land": True, "capital": 3}, "distributed"),
            ll.compute_asset_scale({"has_land": True, "capital": 1}, "distributed"),
        )

    def test_asset_scale_lowers_coverage(self):
        full = _energy_avg_coverage(12, 1.0)
        half = _energy_avg_coverage(12, 0.5)
        self.assertLess(half, full)
        self.assertLess(half, 1.0)  # 产能减半，必然出现缺口

    def test_population_drives_coverage_differentiation(self):
        small = _energy_avg_coverage(3, 1.0)
        large = _energy_avg_coverage(24, 1.0)
        self.assertGreaterEqual(small, large)
        self.assertLess(large, 1.0)  # 24 人吃 12 人资产，必然缺口

    def test_freedom_index_bounds_and_external_floor_cap(self):
        ll = _load_lifeline()
        prof = {"has_land": False, "capital": 0, "skills": [], "health": "良好",
                "household": 1, "location": "城市", "mobility": False}
        sa = _load_analyzer()
        scored = sa.analyze(prof)
        self.assertEqual(scored[0][4], "external_floor")  # 赤贫无地 → 外部托底
        fi, _ = ll.freedom_index(0.3, scored[0][1], "external_floor", prof)
        self.assertTrue(0 <= fi <= 30)  # 诚实封顶

        fi2, _ = ll.freedom_index(0.99, 80, "distributed", prof)
        self.assertTrue(0 <= fi2 <= 100)

    def test_lifeline_main_demo_runs(self):
        ll = _load_lifeline()
        report = ll.main([])
        self.assertIn("生存自由报告", report)
        self.assertIn("推荐策略", report)
        self.assertIn("生存自由指数", report)

    def test_example_profiles_run(self):
        ll = _load_lifeline()
        prof_dir = os.path.join(ROOT, "examples", "profiles")
        for fn in os.listdir(prof_dir):
            if not fn.endswith(".json"):
                continue
            with open(os.path.join(prof_dir, fn), "r", encoding="utf-8") as f:
                profile = json.load(f)
            report = ll.main(["--profile", os.path.join(prof_dir, fn)])
            self.assertIn("生存自由报告", report, f"{fn} 未产出报告")
            self.assertIn("资产规模系数", report, f"{fn} 缺资产系数")


if __name__ == "__main__":
    unittest.main()
