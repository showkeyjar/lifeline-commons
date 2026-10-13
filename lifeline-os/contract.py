"""Lifeline OS —— 协议一致性校验器（Stage 4 协议硬化核心）。

让"接口是中立协议"真正落地：任何第三方只需照 docs/module-interface-v1.md
写一个模块，然后跑本校验器，全绿即通过契约，可被编排层自动发现接入。

校验维度（详见 docs/module-interface-v1.md §6）：
  1. 结构：6 方法齐全、name()==manifest.id、provides()==manifest.provides 且非空
  2. 行为形状：assess→schedule→provide→status 全链路不抛异常且返回形状合法
  3. health 一致性：status().health 与 provide 的 shortfall_days 严格一致
  4. 防硬编码压力测试：极端画像下覆盖率必须 < 0.99（拒绝永远 100% 的假满供）
  5. 响应性：宽裕画像（有地+高资本+小人口+高资产）覆盖率必须严格高于极端画像
     （捕捉不读输入、返回常量的模块；方向安全，适用于流资源与住所两类）

零依赖（仅用 stdlib；manifest 用 tomllib 读 *.toml，Python 3.11+ 自带）。

用法：
    python lifeline-os/contract.py                 # 校验 modules/ 下全部模块
    python lifeline-os/contract.py modules/shelter # 校验单个模块目录
退出码：全部通过 0，任一失败 1。
"""

import importlib.util
import os
import sys

LIFELINE_OS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(LIFELINE_OS_DIR, "..")
sys.path.insert(0, ROOT)
import action_spec  # noqa: E402  动作层核心规范（Stage 6）

REQUIRED_METHODS = ["name", "provides", "assess_needs", "schedule", "provide", "status"]

# 默认可用资源（保证各模块 schedule 不因缺资源而抛异常）
DEFAULT_AVAILABLE = [
    "solar", "local-farm", "community-storage", "battery",
    "rain-harvest", "well", "community-tank", "owned-home",
]

# 基准人口（压力测试的相对基准）
BASE_POPULATION = 12


def _load_toml(path):
    try:
        import tomllib  # Python 3.11+
        with open(path, "rb") as f:
            return tomllib.load(f)
    except ModuleNotFoundError:
        return None  # 老版本 Python 无 tomllib：跳过 manifest 解析（CI 为 3.11+，不受影响）


def _load_module_class(module_dir):
    entry = os.path.basename(os.path.normpath(module_dir))
    mod_file = os.path.join(module_dir, f"{entry}_module.py")
    if not os.path.isfile(mod_file):
        raise FileNotFoundError(f"缺少 {entry}_module.py")
    spec = importlib.util.spec_from_file_location(f"contract_{entry}", mod_file)
    pkg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pkg)
    klass = None
    for name in dir(pkg):
        obj = getattr(pkg, name)
        if isinstance(obj, type) and name.lower() == f"{entry}module":
            klass = obj
            break
    if klass is None:
        raise AttributeError(f"未找到 {entry.capitalize()}Module 类")
    return klass, entry


# ---------------------------------------------------------------------------
# 各检查项：返回 (status, detail)，status ∈ {"pass","fail","warn"}
# ---------------------------------------------------------------------------
def _check_structure(klass, entry, manifest):
    msgs = []
    ok = True
    inst = klass()
    for m in REQUIRED_METHODS:
        if not callable(getattr(inst, m, None)):
            ok = False
            msgs.append(f"缺少必需方法 {m}")
    # name() == manifest id
    try:
        nm = inst.name()
    except Exception as e:
        ok = False
        msgs.append(f"name() 抛异常: {e}")
        nm = None
    if manifest is not None:
        mid = manifest.get("id")
        if mid is not None and nm != mid:
            ok = False
            msgs.append(f"name()='{nm}' 与 manifest.id='{mid}' 不一致")
    # provides() 非空且 == manifest.provides
    try:
        prov = inst.provides()
    except Exception as e:
        ok = False
        msgs.append(f"provides() 抛异常: {e}")
        prov = None
    if prov is not None:
        if not isinstance(prov, list) or not prov or not all(isinstance(x, str) for x in prov):
            ok = False
            msgs.append("provides() 必须返回非空字符串列表")
        elif manifest is not None:
            mprov = manifest.get("provides")
            if mprov is not None and sorted(prov) != sorted(mprov):
                ok = False
                msgs.append(f"provides()={prov} 与 manifest.provides={mprov} 不一致")
    return ("pass" if ok else "fail", "; ".join(msgs) or "结构齐全")


def _run_chain(klass, context, asset_scale):
    """跑通 assess→schedule→provide→status，返回 (delivery, status, exc)。"""
    inst = klass()
    needs = inst.assess_needs(context)
    resources = {"available": DEFAULT_AVAILABLE, "asset_scale": asset_scale}
    plan = inst.schedule(resources, needs)
    delivery = inst.provide(plan)
    st = inst.status()
    return delivery, st, needs


def _check_behavior(klass):
    ok = True
    msgs = []
    try:
        delivery, st, _ = _run_chain(klass, {"community": "ct", "population": BASE_POPULATION}, 1.0)
    except Exception as e:
        return ("fail", f"全链路抛异常: {e}")
    # provide 强制字段
    need = ["delivered_avg_coverage", "full_days", "shortfall_days", "status", "fail_mode"]
    for k in need:
        if k not in delivery:
            ok = False
            msgs.append(f"provide 缺字段 {k}")
    cov = delivery.get("delivered_avg_coverage")
    if cov is None or not isinstance(cov, (int, float)) or not (0.0 <= cov <= 1.0):
        ok = False
        msgs.append(f"delivered_avg_coverage 必须 ∈[0,1]，实为 {cov}")
    if delivery.get("full_days", 0) + delivery.get("shortfall_days", 0) != delivery.get("horizon_days", 30) and \
       delivery.get("full_days", 0) + delivery.get("shortfall_days", 0) != 30:
        msgs.append("full_days+shortfall_days 与 horizon 不一致（warn）")
    if not isinstance(st, dict) or "health" not in st:
        ok = False
        msgs.append("status() 必须返回含 health 的字典")
    return ("pass" if ok else "fail", "; ".join(msgs) or "行为形状合法")


def _check_health_consistency(klass):
    try:
        delivery, st, _ = _run_chain(klass, {"community": "ct", "population": BASE_POPULATION}, 1.0)
    except Exception as e:
        return ("fail", f"抛异常: {e}")
    short = delivery.get("shortfall_days", 0)
    health = st.get("health")
    if short > 0 and health != "degraded":
        return ("fail", f"有缺口({short}天)但 health='{health}'，应为 degraded")
    if short == 0 and health != "nominal":
        return ("fail", f"无缺口但 health='{health}'，应为 nominal")
    return ("pass", f"health='{health}' 与 shortfall_days={short} 一致")


def _check_stress(klass):
    """压力测试：极端画像下必须出现缺口（覆盖率 < 0.99）。"""
    # 最坏画像：人口放大、资产系数压到 0.2、无地无资本
    context = {"community": "stress", "population": BASE_POPULATION * 3,
               "has_land": False, "capital": 0, "location": "城市"}
    try:
        delivery, _, _ = _run_chain(klass, context, 0.2)
    except Exception as e:
        return ("fail", f"压力测试抛异常: {e}")
    cov = delivery.get("delivered_avg_coverage")
    if cov is None:
        return ("fail", "未返回覆盖率")
    if cov >= 0.99:
        return ("fail", f"极端画像下覆盖率仍={cov:.3f}≥0.99，疑似硬编码假满供")
    return ("pass", f"极端画像覆盖率={cov:.3f}<0.99，能体现缺口")


def _check_responsive(klass):
    """响应性：宽裕画像覆盖率必须严格高于极端画像（模块确实读了输入）。

    方向安全——适用于两类模块：流资源（人多/资产少→覆盖低）与住所
    （有地+高资本→居住更安全）。任何不读输入、返回常量的模块都会被抓出。
    """
    benign = {"community": "benign", "population": 4,
              "has_land": True, "capital": 3, "location": "乡村"}
    stressed = {"community": "stress", "population": BASE_POPULATION * 3,
                "has_land": False, "capital": 0, "location": "城市"}
    try:
        d_benign, _, _ = _run_chain(klass, benign, 1.3)
        d_stress, _, _ = _run_chain(klass, stressed, 0.2)
    except Exception as e:
        return ("fail", f"响应性测试抛异常: {e}")
    cb = d_benign.get("delivered_avg_coverage")
    cs = d_stress.get("delivered_avg_coverage")
    if cb is None or cs is None:
        return ("fail", "未返回覆盖率")
    if cb <= cs + 1e-9:
        return ("fail", f"宽裕({cb:.3f})未严格高于极端({cs:.3f})，疑似不读输入/硬编码")
    return ("pass", f"响应性成立(宽裕 {cb:.3f} > 极端 {cs:.3f})")


def _check_actions(klass):
    """动作层（Stage 6）可选检查：模块若实现了 actions()，则返回的动作必须合规。

    未实现 actions() 的模块 → skip（动作层是向后兼容的可选扩展，不强制）。
    """
    if not callable(getattr(klass, "actions", None)):
        return ("skip", "未实现动作层 actions()（可选扩展，跳过）")
    try:
        inst = klass()
        acts = inst.actions({}, {})
    except Exception as e:  # noqa: BLE001
        return ("fail", f"调用 actions() 抛异常: {e}")
    if not isinstance(acts, list) or not acts:
        return ("fail", "actions() 必须返回非空动作列表")
    problems = action_spec.validate_plan(acts)
    if problems:
        return ("fail", f"动作计划存在 {len(problems)} 处问题: " +
                "; ".join(f"{pid}: {iss}" for pid, iss in problems))
    return ("pass", f"动作合规（{len(acts)} 条任务级指令）")


# ---------------------------------------------------------------------------
# 汇总
# ---------------------------------------------------------------------------
CHECKS = [
    ("结构合规", _check_structure),
    ("行为形状", _check_behavior),
    ("health 一致性", _check_health_consistency),
    ("防硬编码压力测试", _check_stress),
    ("响应性", _check_responsive),
    ("动作规范（可选）", _check_actions),
]


def validate_module(module_dir):
    """对单个模块目录跑全部检查。

    返回 (ok: bool, findings: list[(name, status, detail)], entry: str)
    """
    module_dir = os.path.abspath(module_dir)
    entry = os.path.basename(os.path.normpath(module_dir))
    manifest = None
    toml_path = os.path.join(module_dir, "module.toml")
    if os.path.isfile(toml_path):
        manifest = _load_toml(toml_path)
    else:
        # manifest 缺失：结构检查会记一笔，但不阻断其他检查
        pass

    try:
        klass, _ = _load_module_class(module_dir)
    except Exception as e:
        return False, [( "模块加载", "fail", str(e))], entry

    findings = []
    overall_ok = True
    for cname, cfn in CHECKS:
        if cname == "结构合规":
            status, detail = cfn(klass, entry, manifest)
        else:
            status, detail = cfn(klass)
        if status == "fail":
            overall_ok = False
        findings.append((cname, status, detail))

    # manifest 缺失单独提示
    if manifest is None:
        findings.append(("manifest", "warn", "缺少 module.toml（建议补齐，便于第三方理解）"))
    return overall_ok, findings, entry


def discover_module_dirs():
    out = []
    mod_root = os.path.join(ROOT, "modules")
    if not os.path.isdir(mod_root):
        return out
    for entry in sorted(os.listdir(mod_root)):
        d = os.path.join(mod_root, entry)
        if os.path.isdir(d) and os.path.isfile(os.path.join(d, f"{entry}_module.py")):
            out.append(d)
    return out


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if argv:
        dirs = [os.path.abspath(a) for a in argv]
    else:
        dirs = discover_module_dirs()

    if not dirs:
        print("[contract] 未发现任何模块目录。")
        return 1

    all_ok = True
    print("=" * 70)
    print("Lifeline OS · 协议一致性校验（module-interface-v1）")
    print("=" * 70)
    for d in dirs:
        ok, findings, entry = validate_module(d)
        all_ok = all_ok and ok
        verdict = "✅ 通过" if ok else "❌ 不通过"
        print(f"\n[{verdict}] 模块: {entry}  ({d})")
        for cname, status, detail in findings:
            icon = {"pass": "✓", "fail": "✗", "warn": "!", "skip": "·"}.get(status, "?")
            print(f"   {icon} {cname}: {detail}")
    print("\n" + "=" * 70)
    if all_ok:
        print("全部模块通过契约 ✓")
        return 0
    print("存在未通过契约的模块，请修复后再提交。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
