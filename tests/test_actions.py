"""动作层（Stage 6）测试：良构性 / 粒度原则 / 执行器门控与验收 / 契约检查。

核心守护目标：
- 所有模块提供的动作都合规（必需字段齐全、命令在白名单）。
- **粒度原则**：动作停在任务级——make_action 必须拒绝 move_to/grasp 等运动原语，
  且没有任何模块动作偷偷使用它们。
- 参考执行器正确做"前置门控 / 扣电 / 验收"，on-demand 不进固定排程。
- 契约的动作层可选检查对实现了 actions() 的模块判 pass。
"""

import importlib
import os
import sys
import unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
LIFELINE_OS_DIR = os.path.join(ROOT, "lifeline-os")
sys.path.insert(0, ROOT)
sys.path.insert(0, LIFELINE_OS_DIR)

import action_spec as A
import executor as EX


def _load_module_class(entry):
    mod_file = os.path.join(ROOT, "modules", entry, f"{entry}_module.py")
    spec = importlib.util.spec_from_file_location(f"test_{entry}", mod_file)
    pkg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pkg)
    return getattr(pkg, f"{entry.capitalize()}Module")


def _all_module_actions():
    """收集所有模块（实现了 actions() 的）提供的动作。"""
    actions = []
    mod_root = os.path.join(ROOT, "modules")
    for entry in sorted(os.listdir(mod_root)):
        d = os.path.join(mod_root, entry)
        if not os.path.isdir(d) or not os.path.isfile(os.path.join(d, f"{entry}_module.py")):
            continue
        klass = _load_module_class(entry)
        inst = klass()
        method = getattr(inst, "actions", None)
        if callable(method):
            actions.extend(method({}, {}))
    return actions


def _mk(**over):
    """构造一条测试动作，缺省值保证合法。"""
    base = dict(
        id="t.test", domain="t", actor="robot", command="monitor", target="x",
        params={}, frequency="daily", priority="low", precondition="",
        expected_effect="", verify="", note="x",
    )
    base.update(over)
    return A.make_action(**base)


class TestActionsWellFormed(unittest.TestCase):
    def test_all_actions_well_formed(self):
        acts = _all_module_actions()
        self.assertTrue(acts, "应至少收集到若干动作")
        problems = A.validate_plan(acts)
        self.assertEqual(problems, [], f"动作计划存在问题: {problems}")

    def test_all_required_fields_present(self):
        for a in _all_module_actions():
            for f in A.REQUIRED_FIELDS:
                self.assertIn(f, a, f"动作 {a.get('id')} 缺字段 {f}")

    def test_commands_in_allowlist(self):
        for a in _all_module_actions():
            self.assertIn(a["command"], A.ALLOWED_COMMANDS,
                          f"命令 {a['command']} 不在任务级白名单")


class TestActionGranularity(unittest.TestCase):
    def test_forbidden_commands_rejected(self):
        for cmd in A.FORBIDDEN_COMMANDS:
            with self.assertRaises(ValueError, msg=f"应拒绝运动原语 {cmd}"):
                _mk(command=cmd)

    def test_no_forbidden_in_module_actions(self):
        for a in _all_module_actions():
            self.assertNotIn(a["command"], A.FORBIDDEN_COMMANDS,
                             f"模块动作 {a['id']} 使用了运动原语 {a['command']}")

    def test_forbidden_disjoint_from_allowlist(self):
        self.assertTrue(A.FORBIDDEN_COMMANDS.isdisjoint(A.ALLOWED_COMMANDS),
                        "黑名单与白名单不得重叠")


class TestExecutor(unittest.TestCase):
    def test_daily_unconditional_full_attendance(self):
        acts = [_mk(id="t.daily.monitor", command="monitor", frequency="daily",
                    precondition="", expected_effect="", verify="")]
        out = EX.execute_plan(acts, state=A.default_operational_state(), horizon=30)
        ok = sum(1 for r in out["results"] if r["status"] == A.STATUS_OK)
        self.assertEqual(ok, 30, "无前置条件的 daily 应满勤 30 天")

    def test_on_demand_not_scheduled_but_runs_via_run_once(self):
        od = _mk(id="t.od.help", command="request_help", actor="community",
                 frequency="on-demand", precondition="", expected_effect="", verify="")
        sched = A.expand_schedule([od])
        self.assertEqual(len(sched["on_demand"]), 1)
        self.assertEqual(sum(len(v) for v in sched["by_day"].values()), 0,
                         "on-demand 不应进入固定排程")
        st = A.default_operational_state()
        res = EX.run_once([od], st)
        self.assertEqual(res[0]["status"], A.STATUS_OK, "前置为空时应执行")

    def test_precondition_gating_ok(self):
        a = _mk(id="t.daily.serve", command="serve",
                precondition="tank.test >= 0", expected_effect="tank.test += 1", verify="")
        st = dict(A.default_operational_state())
        st["tank.test"] = 0
        out = EX.execute_plan([a], state=st, horizon=30)
        ok = sum(1 for r in out["results"] if r["status"] == A.STATUS_OK)
        self.assertEqual(ok, 30, "前置恒真时应全部执行")

    def test_precondition_gating_skip(self):
        a = _mk(id="t.daily.serve", command="serve",
                precondition="tank.test > 1000", expected_effect="", verify="")
        st = dict(A.default_operational_state())
        st["tank.test"] = 5
        out = EX.execute_plan([a], state=st, horizon=30)
        skip = sum(1 for r in out["results"] if r["status"] == A.STATUS_SKIP)
        self.assertEqual(skip, 30, "前置恒假时应全部跳过（不浪费电量）")

    def test_verify_failure_detected(self):
        a = _mk(id="t.daily.inspect", command="inspect",
                precondition="", expected_effect="tank.test -= 100", verify="tank.test > 0")
        st = dict(A.default_operational_state())
        st["tank.test"] = 50
        out = EX.execute_plan([a], state=st, horizon=30)
        failed = [r for r in out["results"] if r["status"] == A.STATUS_FAILED]
        self.assertTrue(failed, "预期会出现验收失败")


class TestContractActionsCheck(unittest.TestCase):
    def test_contract_actions_check_passes_for_modules(self):
        import contract as C
        for entry in ["energy", "food", "water", "shelter", "health"]:
            klass = _load_module_class(entry)
            status, detail = C._check_actions(klass)
            self.assertIn(status, ("pass", "skip"),
                          f"{entry}: 状态异常 {status} {detail}")
            if status != "skip":
                self.assertEqual(status, "pass", f"{entry}: {detail}")


if __name__ == "__main__":
    unittest.main()
