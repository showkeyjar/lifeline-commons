"""情景轨迹模拟器测试：守护「希望可被模拟」的核心逻辑。

要点：
- 第 0 月（地板）自给率应明显偏低；
- 第 12 月（走完桥）自给率应大幅爬升；
- 食物必须有「收获滞后」——种地当月（第 1 月）不产粮，第 6-8 月三阶爬坡；
- 资产随时间逐步解锁（第 0 月无装备，第 12 月有光伏/农地/集雨）。
"""

import os
import sys
import unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "lifeline-os"))

import lifeline
import strategy_analyzer as sa
import trajectory as traj


def _zero_profile():
    """模拟北京极限示范的零装备画像（资产全 0）。"""
    return {
        "has_land": True,
        "capital": 1,
        "skills": ["IT"],
        "location": "郊区",
        "household": 4,
        "health": "良好",
        "mobility": True,
        "relocation_willingness": False,
        "assets": {
            "solar_kw": 0,
            "battery_kwh": 0,
            "well": False,
            "rainwater_harvesting": False,
            "water_storage_l": 0,
            "greenhouse_m2": 0,
            "farm": False,
        },
    }


def _ctx(profile):
    return {
        "has_land": profile.get("has_land"),
        "capital": profile.get("capital"),
        "location": profile.get("location"),
        "skills": profile.get("skills", []),
        "health": profile.get("health"),
        "assets": profile.get("assets"),
    }


class TestTrajectory(unittest.TestCase):
    def setUp(self):
        self.profile = _zero_profile()
        self.scored = sa.analyze(self.profile)
        self.asset_scale = lifeline.compute_asset_scale(self.profile, self.scored[0][4])
        self.ctx = _ctx(self.profile)
        self.t = traj.project_trajectory(
            self.profile, self.scored, self.asset_scale, self.ctx, months=12
        )

    def test_floor_is_low(self):
        # 第 0 月（零装备）自给率应明显偏低（仅健康/住所撑着）
        self.assertLess(self.t["series"][0]["avg"], 0.4)

    def test_climbs_after_bridge(self):
        # 走完 12 个月建设，自给率应大幅高于地板
        t0 = self.t["series"][0]["avg"]
        t12 = self.t["series"][-1]["avg"]
        self.assertGreater(t12, 0.8)
        self.assertGreater(t12, t0 + 0.4)

    def test_food_harvest_lag(self):
        # 第 1 月已种地但仍是生长期，食物覆盖率必须为 0
        self.assertEqual(self.t["series"][1]["cov"].get("food", 1.0), 0.0)
        # 第 6-8 月应处于三阶爬坡（< 满产），第 9 月起满产
        food6 = self.t["series"][6]["cov"].get("food", 0.0)
        food9 = self.t["series"][9]["cov"].get("food", 0.0)
        self.assertGreater(food6, 0.0)
        self.assertLess(food6, food9)
        self.assertAlmostEqual(food9, 1.0, delta=0.05)

    def test_assets_unlock_over_time(self):
        # 第 0 月无装备；第 12 月应有光伏/农地/集雨
        self.assertNotIn("solar", self.t["series"][0]["avail"])
        self.assertNotIn("local-farm", self.t["series"][0]["avail"])
        last = self.t["series"][-1]["avail"]
        self.assertIn("solar", last)
        self.assertIn("local-farm", last)
        self.assertIn("rain-harvest", last)

    def test_freedom_index_climbs(self):
        fi0 = self.t["series"][0]["fi"]
        fi12 = self.t["series"][-1]["fi"]
        self.assertGreater(fi12, fi0)

    def test_render_is_markdown(self):
        md = traj.render_trajectory_md(self.t, lang="zh")
        self.assertIn("## 6.", md)
        self.assertIn("|", md)


if __name__ == "__main__":
    unittest.main()
