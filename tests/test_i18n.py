"""多语言（i18n）与 Health 模块测试。

守护：
- en / es 覆盖全部中文键（与 i18n.py --check 同源校验）。
- t() 的占位符格式化与缺失键回退。
- 语言切换生效，且报告中不出现未翻译的 'unit.<domain>' 之类的键名泄漏。
- Health 模块（第 5 插槽）通过协议一致性契约。
- 所有 freedom-index 标签键在 en/es 中都能翻译。
"""

import importlib.util
import os
import unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
LIFELINE_OS_DIR = os.path.join(ROOT, "lifeline-os")


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(LIFELINE_OS_DIR, filename)
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestI18n(unittest.TestCase):

    def setUp(self):
        self.i18n = _load("i18n_test", "i18n.py")
        # 复位为默认语言，避免测试间串扰
        self.i18n.set_language("zh")

    def test_all_languages_complete(self):
        ok, problems, _n = self.i18n._check_langs()
        self.assertTrue(ok, f"缺失键: {problems}")
        # 显式断言两种目标语言都齐备
        for lang in ("en", "es"):
            self.assertNotIn(lang, problems)

    def test_fallback_and_format(self):
        self.i18n.set_language("en")
        # 占位符格式化
        self.assertEqual(
            self.i18n.t("ff.compose", pct=80, top=70, qual=60),
            "Composition: mean supply coverage 80% × strategy weight + "
            "strategy fit 70/100 + qualitative resilience 60/100",
        )
        # 缺失键回退到键本身
        self.assertEqual(self.i18n.t("no.such.key"), "no.such.key")

    def test_language_switch(self):
        self.i18n.set_language("zh")
        self.assertIn("生存自由报告", self.i18n.t("title.lifeline"))
        self.i18n.set_language("en")
        self.assertIn("Survival-Freedom Report", self.i18n.t("title.lifeline"))
        self.i18n.set_language("es")
        self.assertIn("Libertad de Supervivencia", self.i18n.t("title.lifeline"))

    def test_freedom_label_keys_translate(self):
        for lang in ("en", "es"):
            self.i18n.set_language(lang)
            for key in ("fi.high_self", "fi.high_income", "fi.midhigh_self",
                        "fi.midhigh_income", "fi.mid_self", "fi.mid_income",
                        "fi.low", "fi.external"):
                self.assertNotEqual(
                    self.i18n.t(key), key,
                    f"{lang} 下 {key} 未翻译（回退成键本身）",
                )

    def test_no_untranslated_unit_leak_in_reports(self):
        ll = _load("lifeline_i18n", "lifeline.py")
        prof_dir = os.path.join(ROOT, "examples", "profiles")
        for lang in ("en", "es"):
            for fn in os.listdir(prof_dir):
                if not fn.endswith(".json"):
                    continue
                report = ll.main(["--profile", os.path.join(prof_dir, fn), "--lang", lang])
                self.assertNotIn(
                    "unit.", report,
                    f"{lang}/{fn} 报告中泄漏了未翻译的单位键",
                )

    def test_health_module_passes_contract(self):
        contract = _load("contract_i18n", "contract.py")
        health_dir = os.path.join(ROOT, "modules", "health")
        ok, findings, entry = contract.validate_module(health_dir)
        self.assertTrue(ok, f"Health 模块未通过契约: {findings}")
        failed = [(n, s, d) for n, s, d in findings if s == "fail"]
        self.assertEqual(failed, [], f"Health 模块有失败项: {failed}")

    def test_five_modules_discovered(self):
        orch = _load("orchestrator_i18n", "orchestrator.py")
        modules = orch.discover_modules()
        ids = [m[0] for m in modules]
        for expected in ("energy", "food", "water", "shelter", "health"):
            self.assertIn(expected, ids, f"未自动发现模块 {expected}")


if __name__ == "__main__":
    unittest.main()
