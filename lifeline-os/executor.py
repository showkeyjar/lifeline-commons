"""动作层参考执行器（Stage 6）—— 在「世界状态」上跑动作计划的人形机器人替身。

这不是真机器人，而是一个**本地可用的参考解释器**：拿到一份动作计划
（``action_spec`` 定义的任务级指令）和一个世界状态，按天推进，验证：

    1. 续航门槛：机器人电量不足时整体停工（真实机器人会先回去充电）。
    2. 前置条件门控：``precondition`` 不满足 → 跳过该动作，不浪费电量。
    3. 施加效果：``expected_effect`` 改变世界状态（空串=只监测/验收，不改状态）。
    4. 扣电：每个真正执行的动作消耗 ``ROBOT_BATTERY_COST_PER_ACTION`` 电量。
    5. 验收：``verify`` 执行后必须满足，否则记"验收失败"。

执行模式：
- ``execute_plan(actions, horizon=30)``：模拟 30 天值守，每天清晨满电，
  把 daily/weekly/once 动作铺进时间轴；on-demand 动作不预排（由事件触发）。
- ``execute_plan(actions, once=True)``：只跑一遍所有动作（含 on-demand），
  用于一次性校验门控 / 验收，不铺时间轴。

CLI：
    python lifeline-os/executor.py --plan last-action-plan.json
    python lifeline-os/executor.py --plan <plan.json> --horizon 30
    python lifeline-os/executor.py --once --plan <plan.json>

写出 ``lifeline-os/last-execution-log.json``（最终状态 + 逐条结果 + 汇总）。
"""

import json
import os
import sys

LIFELINE_OS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(LIFELINE_OS_DIR, "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, LIFELINE_OS_DIR)

import action_spec as spec  # noqa: E402

EXECUTION_LOG_PATH = os.path.join(LIFELINE_OS_DIR, "last-execution-log.json")

# 每个真正执行的动作消耗的电量（百分比）。真实机器人的能耗模型可替换此常数。
ROBOT_BATTERY_COST_PER_ACTION = 2.0

# 机器人电量低于此值则当天剩余动作全部停工（回去充电）。
ROBOT_BATTERY_FLOOR_PCT = 5.0


def _execute_one(action, state):
    """执行单条动作，返回结果字典。

    状态：ok（执行且验收通过）/ skip（前置不满足）/ failed（效果或验收异常）。
    """
    aid = action.get("id", "?")
    pre = action.get("precondition") or ""
    if not spec.eval_condition(state, pre):
        return {"id": aid, "status": spec.STATUS_SKIP,
                "reason": f"前置条件不满足: {pre}"}

    # 续航门槛
    if state.get("robot.battery_pct", 100.0) < ROBOT_BATTERY_FLOOR_PCT:
        return {"id": aid, "status": spec.STATUS_SKIP,
                "reason": "电量低于门槛，机器人回去充电"}

    # 施加效果
    eff = action.get("expected_effect") or ""
    try:
        spec.apply_effect(state, eff)
    except Exception as e:  # noqa: BLE001
        return {"id": aid, "status": spec.STATUS_FAILED,
                "reason": f"效果表达式错误: {e}"}

    # 扣电
    state["robot.battery_pct"] = round(
        max(0.0, state.get("robot.battery_pct", 100.0) - ROBOT_BATTERY_COST_PER_ACTION), 2
    )

    # 验收
    verify = action.get("verify") or ""
    if verify and not spec.eval_condition(state, verify):
        return {"id": aid, "status": spec.STATUS_FAILED,
                "reason": f"验收失败: {verify}"}

    return {"id": aid, "status": spec.STATUS_OK}


def run_once(actions, state):
    """一次性跑完所有动作（含 on-demand），返回结果列表。"""
    results = []
    for a in sorted(actions, key=spec.priority_rank):
        results.append(_execute_one(a, state))
    return results


def _summarize(results):
    ok = sum(1 for r in results if r["status"] == spec.STATUS_OK)
    skip = sum(1 for r in results if r["status"] == spec.STATUS_SKIP)
    failed = sum(1 for r in results if r["status"] == spec.STATUS_FAILED)
    return {"ok": ok, "skip": skip, "failed": failed, "total": len(results)}


def execute_plan(actions, state=None, horizon=30, once=False):
    """执行一份动作计划。

    参数：
        actions : action_spec.make_action 列表（或等价的字典列表）。
        state   : 初始世界状态；缺省用 ``default_operational_state()``。
        horizon: 模拟天数（仅非 once 模式使用）。
        once    : True 时只跑一遍所有动作，不铺时间轴。

    返回：
        {"state", "results", "summary", ["schedule"]}
    """
    if state is None:
        state = spec.default_operational_state()
    # 入参校验（非法动作会被拦下并计入 failed）
    problems = spec.validate_plan(actions)
    if problems:
        raise ValueError(f"动作计划存在 {len(problems)} 处问题: {problems}")

    if once:
        results = run_once(actions, state)
        return {"state": state, "results": results, "summary": _summarize(results)}

    schedule = spec.expand_schedule(actions, horizon)
    all_results = []
    for day in range(1, horizon + 1):
        state["robot.battery_pct"] = 100.0  # 清晨满电
        day_actions = sorted(schedule["by_day"].get(day, []), key=spec.priority_rank)
        for a in day_actions:
            res = _execute_one(a, state)
            res["day"] = day
            all_results.append(res)
    summary = _summarize([r for r in all_results if "day" in r])
    return {"state": state, "results": all_results, "schedule": schedule,
            "summary": summary}


def summarize_by_domain(results):
    """按 domain 聚合执行结果，便于人读。"""
    by = {}
    for r in results:
        # 从动作 id 推断 domain（约定 "<domain>.*"）
        did = r.get("id", "?")
        dom = did.split(".", 1)[0] if "." in did else "?"
        d = by.setdefault(dom, {"ok": 0, "skip": 0, "failed": 0})
        d[r["status"]] = d.get(r["status"], 0) + 1
    return by


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    plan_path = None
    horizon = 30
    once = False
    state = None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--plan" and i + 1 < len(argv):
            plan_path = argv[i + 1]
            i += 2
        elif a == "--state" and i + 1 < len(argv):
            with open(argv[i + 1], "r", encoding="utf-8") as f:
                state = json.load(f)
            i += 2
        elif a == "--horizon" and i + 1 < len(argv):
            horizon = int(argv[i + 1])
            i += 2
        elif a == "--once":
            once = True
            i += 1
        else:
            i += 1

    if plan_path is None:
        print("[executor] 用法: python lifeline-os/executor.py --plan <plan.json> [--horizon N] [--once]")
        return 1

    with open(plan_path, "r", encoding="utf-8") as f:
        plan = json.load(f)
    actions = plan.get("actions", [])

    out = execute_plan(actions, state=state, horizon=horizon, once=once)

    by_domain = summarize_by_domain(out["results"])
    print("=" * 56)
    print("Lifeline OS · 参考执行器（动作层 Stage 6）")
    print("=" * 56)
    s = out["summary"]
    print(f"执行结果：成功 {s['ok']} · 跳过 {s['skip']} · 验收失败 {s['failed']}")
    print("\n按域汇总：")
    for dom, d in sorted(by_domain.items()):
        print(f"  {dom:>8}: ok={d.get('ok',0)}  skip={d.get('skip',0)}  failed={d.get('failed',0)}")
    if s["failed"]:
        print("\n验收失败明细：")
        for r in out["results"]:
            if r["status"] == spec.STATUS_FAILED:
                print(f"  - {r['id']}: {r.get('reason','')}")

    with open(EXECUTION_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n[executor] 执行日志已写入: {EXECUTION_LOG_PATH}")
    return 0 if s["failed"] == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
