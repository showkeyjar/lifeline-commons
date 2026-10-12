"""Lifeline OS —— 编排骨架。

把任意一个符合 module-interface-v1 的供给模块跑成
「需求感知 → 资源调度 → 供给交付」的最小闭环。

编排器**自动发现** modules/ 下的模块：每个子目录 <id> 里放一个
<id>_module.py，其中定义一个 <Id>Module 类即可，无需手动登记。
"""

import importlib
import os
import sys

# 让项目根目录可被导入（modules / lifeline_os 都在根下）
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)

MODULES_DIR = os.path.join(ROOT, "modules")


def discover_modules():
    """扫描 modules/ 下所有 <id>/<id>_module.py，返回 [(id, Class), ...]。"""
    found = []
    if not os.path.isdir(MODULES_DIR):
        return found
    for entry in sorted(os.listdir(MODULES_DIR)):
        mod_dir = os.path.join(MODULES_DIR, entry)
        if not os.path.isdir(mod_dir):
            continue
        mod_file = os.path.join(mod_dir, f"{entry}_module.py")
        if not os.path.isfile(mod_file):
            continue
        try:
            pkg = importlib.import_module(f"modules.{entry}.{entry}_module")
        except Exception as e:
            print(f"[Lifeline OS] 跳过模块 {entry}: 导入失败 ({e})")
            continue
        target = f"{entry}module"
        klass = None
        for name in dir(pkg):
            obj = getattr(pkg, name)
            if isinstance(obj, type) and name.lower() == target:
                klass = obj
                break
        if klass is None:
            print(f"[Lifeline OS] 跳过模块 {entry}: 未找到 {entry.capitalize()}Module 类")
            continue
        found.append((entry, klass))
    return found


def run_loop(module):
    print(f"[Lifeline OS] 加载模块: {module.name()} (provides={module.provides()})")

    context = {"community": "demo-village", "population": 12}
    needs = module.assess_needs(context)
    print(f"  1) 感知需求: {needs}")

    resources = {"available": ["solar", "local-farm", "community-storage", "battery"]}
    plan = module.schedule(resources, needs)
    print(f"  2) 调度资源: {plan}")

    delivery = module.provide(plan)
    print(f"  3) 供给交付: {delivery}")

    print(f"  状态: {module.status()}")
    print("[Lifeline OS] 闭环完成 ✓")


if __name__ == "__main__":
    modules = discover_modules()
    if not modules:
        print("[Lifeline OS] 未发现任何供给模块，退出。")
        sys.exit(1)
    print(f"[Lifeline OS] 发现 {len(modules)} 个供给模块: {[m[0] for m in modules]}")
    print("=" * 48)
    for entry, klass in modules:
        print()
        run_loop(klass())
