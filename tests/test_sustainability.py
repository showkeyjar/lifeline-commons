"""可持续性护栏测试（阶段 5 — 抗捕获与可持续）。

这些不是"摆设文档"，而是可被 CI 守护的硬约束：
- 许可证必须是 AGPL-3.0 且带反圈地条款（防止核心被重新私有化）。
- 治理文档必须写明 Fork 抗性硬规则（关键决策不依赖单点个人、需 ≥2 维护者）。
- 必须存在 CODEOWNERS，把核心文件路由到维护者评审（具体审查路由）。
- 商业化文档必须含"资金模型 + 抗捕获"设计（收入组合不依赖单一来源）。

任何一条被删改，CI 都会红——这正是"护栏非摆设"的实证。
"""

import os
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(rel):
    p = os.path.join(REPO_ROOT, rel)
    if not os.path.exists(p):
        raise FileNotFoundError(p)
    with open(p, "r", encoding="utf-8") as f:
        return f.read()


class TestLicenseGuardrail(unittest.TestCase):
    """许可证即护栏：AGPL-3.0 + 反圈地条款必须同时存在。"""

    def test_license_file_exists(self):
        self.assertTrue(
            os.path.exists(os.path.join(REPO_ROOT, "LICENSE")),
            "LICENSE 文件缺失",
        )

    def test_license_is_agpl(self):
        text = _read("LICENSE")
        self.assertIn(
            "AFFERO GENERAL PUBLIC LICENSE",
            text.upper(),
            "LICENSE 不是 GNU Affero (AGPL) 许可证",
        )

    def test_license_has_anti_enclosure(self):
        text = _read("LICENSE")
        # 反圈地条款：保留使用者获得源码/自部署/治理的权利，防重新私有化
        has = ("反圈地" in text) or ("anti-enclosure" in text.lower())
        self.assertTrue(has, "LICENSE 缺少反圈地 (anti-enclosure) 条款")


class TestForkResistance(unittest.TestCase):
    """Fork 抗性：治理必须写明关键决策不依赖单点个人。"""

    def test_governance_mentions_fork_resistance(self):
        text = _read("GOVERNANCE.md")
        # 硬规则关键词：不能只靠一个人拍板
        signals = ["不依赖单点", "两名维护者", "2 名维护者", "≥2", "至少 2"]
        self.assertTrue(
            any(s in text for s in signals),
            "GOVERNANCE.md 缺少 Fork 抗性硬规则（关键决策需 ≥2 维护者批准）",
        )

    def test_governance_requires_two_approvals(self):
        text = _read("GOVERNANCE.md")
        self.assertIn(
            "独立批准",
            text,
            "GOVERNANCE.md 未写明高门槛 PR 需多名维护者'独立批准'",
        )

    def test_codeowners_exists(self):
        path = os.path.join(REPO_ROOT, ".github", "CODEOWNERS")
        self.assertTrue(os.path.exists(path), "缺少 .github/CODEOWNERS（审查路由工件）")
        body = _read(".github/CODEOWNERS")
        self.assertTrue(body.strip(), "CODEOWNERS 为空")


class TestFundingModel(unittest.TestCase):
    """资金模型：商业化文档必须落地抗捕获的收入组合设计。"""

    def test_commercialization_has_funding_model(self):
        text = _read("docs/commercialization.md")
        self.assertIn("资金模型", text, "commercialization.md 缺少'资金模型'章节")
        self.assertIn("抗捕获", text, "资金模型未说明抗捕获设计")

    def test_funding_model_caps_single_source(self):
        text = _read("docs/commercialization.md")
        # 不依赖单一来源：必须给出阈值护栏（33% / 50%）
        has_threshold = ("33%" in text) or ("50%" in text)
        self.assertTrue(
            has_threshold,
            "资金模型未给出'单一来源占比'阈值护栏（33% 观察 / 50% 强制复核）",
        )


if __name__ == "__main__":
    unittest.main()
