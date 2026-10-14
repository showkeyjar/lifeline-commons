"""情景轨迹模拟器测试：守护「希望可被模拟」的核心逻辑。

要点：
- 第 0 月（地板）自给率应明显偏低；
- 第 12 月（走完桥）自给率应大幅爬升；
- 食物必须有「收获滞后」——种地当月（第 1 月）不产粮，按生长季长度决定首收与爬坡
  （北方第 6-8 月三阶，南方更快）；稳态接近或略超满产（长生长季年度多熟有余粮）；
- 资产随时间逐步解锁（第 0 月无装备，第 12 月有光伏/农地/集雨）。
"""

import os
import sys
import json
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
        # 北方：第 6-8 月处于三阶爬坡（< 满产），第 9 月起稳态满产（可略超，代表余粮）
        food6 = self.t["series"][6]["cov"].get("food", 0.0)
        food9 = self.t["series"][9]["cov"].get("food", 0.0)
        self.assertGreater(food6, 0.0)
        self.assertLess(food6, food9)
        self.assertGreaterEqual(food9, 0.95)

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


class TestFoodClimate(unittest.TestCase):
    """守护「食物参数依赖生长季长度」——这是南北对比诚实性的根基。"""

    def test_food_params_north(self):
        lag, ramp, mc = traj._food_params({"frost_free_days": 190})
        self.assertEqual(lag, 5)
        self.assertEqual(ramp, (0.3, 0.6, 1.0))
        self.assertAlmostEqual(
            mc, 1.0 + 0.25 * max(0.0, min(1.0, (190 - 150) / 180)), places=4
        )

    def test_food_params_south(self):
        lag, ramp, mc = traj._food_params({"frost_free_days": 350})
        self.assertEqual(lag, 3)
        self.assertEqual(ramp, (0.5, 1.0))
        self.assertAlmostEqual(mc, 1.25, places=4)

    def test_food_params_default_is_north(self):
        # 缺省（无 climate 字段）按偏北处理，保证旧画像 / 测试向后兼容
        lag, ramp, mc = traj._food_params({})
        self.assertEqual(lag, 5)
        self.assertEqual(ramp, (0.3, 0.6, 1.0))

    def test_south_food_full_earlier_than_north(self):
        # 广州（南方）零装备 vs 北京（北方）零装备：食物应更早达到 ≥80%
        base = os.path.join(os.path.dirname(__file__), "..", "instances")
        guang = json.load(
            open(os.path.join(base, "guangzhou-south-baseline", "profile.json"), encoding="utf-8")
        )
        beijing = json.load(
            open(os.path.join(base, "beijing-suburb-baseline", "profile.json"), encoding="utf-8")
        )

        def first_food_full(prof):
            scored, asset_scale, ctx = lifeline.prepare(prof)
            t = traj.project_trajectory(prof, scored, asset_scale, ctx, 12)
            for row in t["series"]:
                if row["cov"].get("food", 0) >= 0.8:
                    return row["month"]
            return None

        g = first_food_full(guang)
        b = first_food_full(beijing)
        self.assertIsNotNone(g)
        self.assertIsNotNone(b)
        self.assertLess(g, b)  # 南方食物更早满产 → 瓶颈更短


if __name__ == "__main__":
    unittest.main()
