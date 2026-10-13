"""协议一致性测试：守护「第三方能仅靠接口文档写出合规模块并通过校验」。

验证：
- 内置 energy/food/water/shelter 全部通过 contract.py 的全部检查。
- 故意构造一个"硬编码 100%、不读输入"的假模块，断言校验器能抓出（FAIL）。
- 故意构造一个"缺方法"的假模块，断言结构检查能抓出。

运行：python -m unittest discover -s tests -t . -v
"""

import importlib.util
import os
import sys
import tempfile
import textwrap
import unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
LIFELINE_OS_DIR = os.path.join(ROOT, "lifeline-os")
sys.path.insert(0, LIFELINE_OS_DIR)

import contract as C


def _findings(ok, findings):
    return {name: status for name, status, _ in findings}


class TestBuiltinModulesPass(unittest.TestCase):
    """内置模块必须全部通过契约。"""

    def test_energy_passes(self):
        ok, findings, _ = C.validate_module(os.path.join(ROOT, "modules", "energy"))
        self.assertTrue(ok, f"energy 未通过: {findings}")

    def test_food_passes(self):
        ok, findings, _ = C.validate_module(os.path.join(ROOT, "modules", "food"))
        self.assertTrue(ok, f"food 未通过: {findings}")

    def test_water_passes(self):
        ok, findings, _ = C.validate_module(os.path.join(ROOT, "modules", "water"))
        self.assertTrue(ok, f"water 未通过: {findings}")

    def test_shelter_passes(self):
        ok, findings, _ = C.validate_module(os.path.join(ROOT, "modules", "shelter"))
        self.assertTrue(ok, f"shelter 未通过: {findings}")

    def test_all_builtin_findings_are_pass(self):
        for mid in ("energy", "food", "water", "shelter"):
            ok, findings, _ = C.validate_module(os.path.join(ROOT, "modules", mid))
            fmap = _findings(ok, findings)
            for name, status in fmap.items():
                self.assertNotEqual(status, "fail", f"{mid} 的 {name} 判了 fail")


class TestContractCatchesViolations(unittest.TestCase):
    """校验器必须能抓出违规模块（否则契约形同虚设）。"""

    def _make_module(self, code, dirname="fake", manifest=None):
        parent = tempfile.mkdtemp(prefix="lifeline_ct_")
        d = os.path.join(parent, dirname)  # 目录名必须正好等于模块 id
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, f"{dirname}_module.py"), "w", encoding="utf-8") as f:
            f.write(code)
        if manifest is not None:
            with open(os.path.join(d, "module.toml"), "w", encoding="utf-8") as f:
                f.write(manifest)
        return d

    def test_hardcoded_module_fails(self):
        """永远返回 100% 覆盖、不读输入的模块必须被压力测试/响应性抓出。"""
        code = textwrap.dedent("""
            class FakeModule:
                def name(self): return "fake"
                def provides(self): return ["fake"]
                def assess_needs(self, context):
                    return {"need_type": "fake", "population": context.get("population", 1)}
                def schedule(self, resources, needs):
                    return {"strategy": "self-sufficiency",
                            "target": needs.get("population", 1),
                            "asset_scale": resources.get("asset_scale", 1.0)}
                def provide(self, plan):
                    return {"delivered_avg_coverage": 1.0, "full_days": 30,
                            "shortfall_days": 0, "status": "ok", "fail_mode": "x"}
                def status(self):
                    return {"health": "nominal"}
        """)
        d = self._make_module(code, "fake",
                              manifest='id = "fake"\nname = "fake"\nprovides = ["fake"]\n')
        ok, findings, _ = C.validate_module(d)
        self.assertFalse(ok, "硬编码 100% 的模块竟通过了契约！")
        fmap = _findings(ok, findings)
        # 至少压力测试或响应性其一判 fail
        self.assertTrue(
            fmap.get("防硬编码压力测试") == "fail" or fmap.get("响应性") == "fail",
            f"未抓出硬编码: {findings}",
        )

    def test_missing_method_fails(self):
        """缺必需方法的模块必须被结构检查抓出。"""
        code = textwrap.dedent("""
            class BrokenModule:
                def name(self): return "broken"
                def provides(self): return ["broken"]
                def assess_needs(self, context): return {}
                def schedule(self, resources, needs): return {}
                # 故意缺少 provide / status
        """)
        d = self._make_module(code, "broken",
                              manifest='id = "broken"\nname = "broken"\nprovides = ["broken"]\n')
        ok, findings, _ = C.validate_module(d)
        self.assertFalse(ok)
        fmap = _findings(ok, findings)
        self.assertEqual(fmap.get("结构合规"), "fail")


class TestContractCli(unittest.TestCase):
    """CLI 校验全部内置模块应返回 0（全绿）。"""

    def test_cli_all_pass(self):
        rc = C.main([])
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
