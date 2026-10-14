"""多实例对比模拟器测试：守护「起点已带装备的户不被归零」与「对比叠加正确」。

要点：
- 已装备画像的第 0 月应直接计入光伏/井（不被迫从 0 归零重建）；
- 对比能把若干实例的轨迹叠加，产出含 t0 / 末月 / 自由指数 / 达 80% 月数的汇总；
- 渲染为 Markdown，火花线长度 = 月数 + 1。
"""

import os
import re
import sys
import unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "lifeline-os"))

import lifeline
import compare


def _floor_profile():
    """零装备的北京极限示范画像（资产全 0）。"""
    return {
        "_meta": {"name": "floor"},
        "has_land": True,
        "capital": 1,
        "skills": ["IT"],
        "location": "郊区",
        "household": 4,
        "health": "良好",
        "mobility": True,
        "relocation_willingness": False,
        "assets": {
            "solar_kw": 0, "battery_kwh": 0, "well": False,
            "rainwater_harvesting": False, "water_storage_l": 0,
            "greenhouse_m2": 0, "farm": False,
        },
    }


def _equipped_profile():
    """同一家庭但已备基础装备（capital=2，光伏/井/储水/大棚已购）。"""
    return {
        "_meta": {"name": "eq"},
        "has_land": True,
        "capital": 2,
        "skills": ["IT"],
        "location": "郊区",
        "household": 4,
        "health": "良好",
        "mobility": True,
        "relocation_willingness": False,
        "assets": {
            "solar_kw": 5, "battery_kwh": 10, "well": True,
            "rainwater_harvesting": True, "water_storage_l": 2000,
            "greenhouse_m2": 50, "farm": False,
        },
    }


class TestStartingAssetsRespected(unittest.TestCase):
    def test_equipped_month0_counts_gear(self):
        # 已装备户：第 0 月就应有光伏 / 井（不被迫从 0 重建）
        run = compare.run_one(_equipped_profile(), months=12)
        s0 = run["traj"]["series"][0]
        self.assertGreater(s0["cov"].get("energy", 0.0), 0.5)
        self.assertIn("solar", s0["avail"])
        self.assertIn("well", s0["avail"])
        self.assertIn("local-farm", s0["avail"])  # 大棚 → 已在耕种
        self.assertGreater(s0["avg"], 0.5)

    def test_floor_month0_is_low(self):
        # 零装备户：第 0 月无装备（对比的干净基线）
        run = compare.run_one(_floor_profile(), months=12)
        s0 = run["traj"]["series"][0]
        self.assertNotIn("solar", s0["avail"])
        self.assertLess(s0["avg"], 0.4)


class TestComparison(unittest.TestCase):
    def setUp(self):
        self.comp = compare.run_comparison(
            [("floor", _floor_profile()), ("eq", _equipped_profile())], months=12
        )

    def test_two_runs(self):
        self.assertEqual(len(self.comp["runs"]), 2)

    def test_floor_low_and_equipped_high_at_start(self):
        floor_run = next(r for r in self.comp["runs"] if r["label"] == "floor")
        eq_run = next(r for r in self.comp["runs"] if r["label"] == "eq")
        self.assertLess(floor_run["traj"]["series"][0]["avg"], 0.4)
        self.assertGreater(eq_run["traj"]["series"][0]["avg"], 0.5)

    def test_all_reach_high_by_end(self):
        for r in self.comp["runs"]:
            self.assertGreater(r["traj"]["series"][-1]["avg"], 0.8)

    def test_render_is_markdown_with_both_labels(self):
        md = compare.render_compare_md(self.comp, lang="zh")
        self.assertIn("## 7.", md)
        self.assertIn("|", md)
        self.assertIn("floor", md)
        self.assertIn("eq", md)

    def test_sparkline_length_equals_months_plus_one(self):
        md = compare.render_compare_md(self.comp, lang="zh")
        m = re.search(r"`(.{13})`", md)
        self.assertIsNotNone(m)
        self.assertEqual(len(m.group(1)), 13)

    def test_months_to_80_present(self):
        # 两户都应能在 12 个月内越过 80%
        for r in self.comp["runs"]:
            self.assertIsNotNone(compare._months_to_80(r))


class TestSparkHelpers(unittest.TestCase):
    def test_spark_bounds(self):
        self.assertEqual(compare._spark(0.0), " ")
        self.assertEqual(compare._spark(1.0), "█")
        self.assertEqual(compare._spark(0.5), "▄")


if __name__ == "__main__":
    unittest.main()
