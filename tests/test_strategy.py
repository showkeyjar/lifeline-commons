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
        # analyze 返回翻译键，而非成品文案（渲染层按语言翻译）
        self.assertEqual(scored[0][4], "distributed")
        self.assertEqual(scored[0][0], "strat.distributed.name")
        # 中文渲染下，首选策略名应出现（显式指定语言，不依赖全局默认）
        sa.i18n.set_language("zh")
        report = sa.render_report(p, scored)
        self.assertIn("分布式自给", report)

    def test_landless_destitute_falls_to_external_floor(self):
        p = {"has_land": False, "capital": 0, "skills": [], "location": "城市",
             "household": 1, "health": "受限", "mobility": False}
        scored = sa.analyze(p)
        self.assertEqual(scored[0][4], "external_floor")
        self.assertEqual(scored[0][1], 100)
        # 诚实边界应包含"帮不了"（显式指定语言，不依赖全局默认）
        sa.i18n.set_language("zh")
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

    def test_mobility_is_evacuation_not_relocation(self):
        # 关键守护：有"撤离能力"(mobility) 但无"迁移意愿"，relocate 必须得 0 分。
        # 历史上 mobility 被误当成"想搬家"的触发器，导致有撤离韧性的人被误推去搬迁。
        p = {"has_land": True, "capital": 1, "skills": ["IT"],
             "location": "郊区", "household": 4, "health": "良好",
             "mobility": True, "relocation_willingness": False}
        scored = sa.analyze(p)
        reloc = next(s for s in scored if s[4] == "relocate")
        self.assertEqual(reloc[1], 0)  # 不想搬家 → 迁移策略不触发
        # 相贴切的"半自给+基础缓冲"应成为首选（而不是被 relocate 抢走）
        self.assertEqual(scored[0][4], "semi_self")

    def test_relocation_willingness_triggers_relocate(self):
        # 仅当显式表态"愿意迁移"(relocation_willingness=true) 才触发 relocate，
        # 即便 mobility（撤离能力）为 False 也应能触发。
        p = {"has_land": False, "capital": 1, "skills": ["IT"],
             "location": "城市", "household": 1, "health": "良好",
             "mobility": False, "relocation_willingness": True}
        scored = sa.analyze(p)
        reloc = next(s for s in scored if s[4] == "relocate")
        self.assertGreater(reloc[1], 0)  # 想搬家 → 迁移策略触发


if __name__ == "__main__":
    unittest.main()
