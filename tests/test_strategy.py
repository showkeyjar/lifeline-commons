"""策略分析器测试：守护「先分析画像、荒地只是策略之一」的核心逻辑。"""

import os
import sys
import unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "lifeline-os"))

import strategy_analyzer as sa


class TestStrategyAnalyzer(unittest.TestCase):
    def test_demo_profile_prefers_distributed(self):
        p = sa._demo_profile()
        scored = sa.analyze(p)
        self.assertGreaterEqual(scored[0][1], 40)  # 首选应有实质匹配
        self.assertEqual(scored[0][0], "分布式自给（荒地/集体土地自建）")

    def test_landless_destitute_falls_to_external_floor(self):
        p = {"has_land": False, "capital": 0, "skills": [], "location": "城市",
             "household": 1, "health": "受限", "mobility": False}
        scored = sa.analyze(p)
        self.assertEqual(scored[0][4], "external_floor")
        self.assertEqual(scored[0][1], 100)
        # 诚实边界应包含"帮不了"
        report = sa.render_report(p, scored)
        self.assertIn("帮不了", report)

    def test_scores_descending(self):
        p = sa._demo_profile()
        scored = sa.analyze(p)
        vals = [s[1] for s in scored]
        self.assertEqual(vals, sorted(vals, reverse=True))

    def test_no_land_excludes_distributed(self):
        p = {"has_land": False, "capital": 2, "skills": ["远程工作", "手艺"],
             "location": "城市", "household": 3, "health": "良好", "mobility": True}
        scored = sa.analyze(p)
        dist = next(s for s in scored if s[4] == "distributed")
        self.assertEqual(dist[1], 0)  # 无地则分布式自给得 0 分


if __name__ == "__main__":
    unittest.main()
