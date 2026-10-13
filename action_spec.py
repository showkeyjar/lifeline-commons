"""动作层（Action Layer, Stage 6）—— 把"够不够"翻译成人形机器人可执行的任务指令。

本文件是动作层的**核心规范与参考实现**。它定义了：

- 一条「动作」必须长什么样（``make_action`` / ``validate_action`` / ``REQUIRED_FIELDS``）。
- 任务级命令的白名单与黑名单（粒度原则，见下）。
- 世界状态的扁平表达，以及状态表达式的求值（``eval_condition`` / ``apply_effect``）。
- 把 recurring 动作铺成 30 天值守时间轴（``expand_schedule``）。
- 一个演示用的初始世界状态（``default_operational_state``）。

──────────────────────────────────────────────────────────────────────────
粒度原则（面向智能人形机器人 · 最重要的一条）
──────────────────────────────────────────────────────────────────────────
本项目**不交付机器人**，只交付"插槽与规则"。动作层只负责告诉人形机器人：

    「去哪（target）、干什么（command）、干完怎么确认（verify）」

**动作必须停在"任务/目标"这一级**，绝不能下钻到关节、抓取、步态等运动原语。
底层运动规划（怎么迈腿、怎么抓握、怎么避障）由机器人自身的控制器完成，
本项目一律不下发。

因此：
- ✅ 允许 ``harvest / pump / inspect / assist / clean / monitor / serve /
       ventilate / repair / request_help / seek_care / shed_load / draw`` 等
      **任务级**命令——它们描述的是"要达成什么"，而非"身体怎么动"。
- ❌ 禁止 ``move_to / navigate / walk / grasp / pick / place / rotate_joint /
       grip / approach / traverse / reach / step`` 等**运动原语**——
      这些必须由机器人自己处理。``make_action`` 会在构造期直接拒绝它们。

任何把动作细化到运动原语的提交，都会在 ``tests/test_actions.py`` 的
``TestActionGranularity`` 中被拦下。
"""

import re

# 动作 schema 版本（破坏性变更时升版本号；v1→v2 只加不减、向后兼容）
ACTION_SCHEMA_VERSION = "2026.1"

# 一条动作的必需字段（缺任一都会在被 ``make_action`` / ``validate_action`` 拒绝）
REQUIRED_FIELDS = [
    "id",          # 全局唯一动作 ID，建议 "<domain>.<frequency?>.<verb>"
    "domain",      # 所属供给域：energy / food / water / shelter / health
    "actor",       # 执行者：robot / community / human
    "command",     # 任务级命令（见 ALLOWED_COMMANDS，禁止运动原语）
    "target",      # 目标资源 / 地点 / 设备（人读字符串）
    "params",      # 自由格式参数字典（如 {meals: 40}），可为空 {}
    "frequency",   # once / daily / weekly / on-demand
    "priority",    # high / medium / low（执行排序用）
    "precondition",   # 前置条件：状态表达式（空串=永远满足）；不满足则跳过
    "expected_effect", # 预期效果：状态表达式（空串=不改变世界状态，仅监测/验收）
    "verify",      # 验收：状态表达式（空串=不验收）；执行后不满足记"验收失败"
    "note",        # 人读备注（为什么需要这个动作、注意事项）
]

# 任务级命令白名单（描述的是"要达成什么"）
ALLOWED_COMMANDS = {
    "harvest", "pump", "inspect", "assist", "clean", "monitor",
    "serve", "ventilate", "repair", "request_help", "seek_care",
    "shed_load", "draw",
}

# 运动原语黑名单（必须由机器人自身运动规划处理，本项目一律不下发）
FORBIDDEN_COMMANDS = {
    # 移动 / 导航
    "move_to", "navigate", "walk", "go_to", "approach", "traverse", "step", "reach",
    # 操作 / 抓取
    "grasp", "pick", "place", "grip", "rotate_joint", "manipulate", "insert",
}

# 频率合法值
FREQUENCIES = {"once", "daily", "weekly", "on-demand"}

# 优先级排序（数字越小越先执行）
PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2, "critical": -1}

# 执行结果状态
STATUS_OK = "ok"
STATUS_SKIP = "skip"
STATUS_FAILED = "failed"


# ---------------------------------------------------------------------------
# 构造与校验
# ---------------------------------------------------------------------------
def make_action(**kw):
    """构造一条动作，并在构造期做校验（缺字段 / 非法命令都会抛错）。

    用法：
        action_spec.make_action(
            id="food.daily.harvest", domain="food", actor="robot",
            command="harvest", target="local-farm", params={"meals": 40},
            frequency="daily", priority="high",
            precondition="food.inventory_meals < 600",
            expected_effect="food.inventory_meals += 40",
            verify="food.inventory_meals <= 700",
            note="本地农场地块每日采收，补足社区餐食库存。",
        )
    """
    for f in REQUIRED_FIELDS:
        if f not in kw:
            raise ValueError(f"动作缺少必需字段: {f}")
    cmd = kw["command"]
    if cmd in FORBIDDEN_COMMANDS:
        raise ValueError(
            f"命令 '{cmd}' 是运动原语，禁止下发给人形机器人"
            f"（粒度原则：动作停在任务级，运动规划交给机器人自身）。"
        )
    if kw["frequency"] not in FREQUENCIES:
        raise ValueError(
            f"frequency 必须是 {sorted(FREQUENCIES)} 之一，实为 '{kw['frequency']}'"
        )
    if kw["priority"] not in PRIORITY_RANK:
        raise ValueError(
            f"priority 必须是 {sorted(PRIORITY_RANK)} 之一，实为 '{kw['priority']}'"
        )
    if not isinstance(kw.get("params"), dict):
        raise ValueError("params 必须是字典")
    return dict(kw)


def validate_action(action):
    """校验一条既有动作字典，返回问题列表（空列表=合法）。"""
    issues = []
    if not isinstance(action, dict):
        return ["action 不是字典"]
    for f in REQUIRED_FIELDS:
        if f not in action:
            issues.append(f"缺少必需字段 {f}")
    cmd = action.get("command")
    if cmd in FORBIDDEN_COMMANDS:
        issues.append(f"命令 '{cmd}' 是运动原语，禁止下发（粒度原则）")
    if action.get("frequency") not in FREQUENCIES:
        issues.append(f"frequency 非法: {action.get('frequency')}")
    if action.get("priority") not in PRIORITY_RANK:
        issues.append(f"priority 非法: {action.get('priority')}")
    if not isinstance(action.get("params"), dict):
        issues.append("params 必须是字典")
    # 结构合法才进一步校验表达式语法可解析（不依赖具体世界状态）
    if not issues:
        for label, expr in (
            ("precondition", action.get("precondition")),
            ("verify", action.get("verify")),
        ):
            if expr and str(expr).strip():
                try:
                    _parse_cmp(expr)
                except ValueError as e:
                    issues.append(f"{label} 表达式: {e}")
        eff = action.get("expected_effect")
        if eff and str(eff).strip():
            try:
                _parse_eff(eff)
            except ValueError as e:
                issues.append(f"expected_effect 表达式: {e}")
    return issues


def validate_plan(actions):
    """校验一个动作列表，返回 [(action_id_or_index, issues), ...] 仅含有问题的项。"""
    problems = []
    for i, a in enumerate(actions):
        issues = validate_action(a)
        if issues:
            problems.append((a.get("id", f"#{i}"), issues))
    return problems


# ---------------------------------------------------------------------------
# 世界状态：扁平指标字典
# ---------------------------------------------------------------------------
def default_operational_state(asset_scale=1.0):
    """演示用的初始世界状态（扁平字典，键为带点号的字符串）。

    ``asset_scale`` 让初始库存/储量随社区产能规模缩放，与供给模拟口径一致。
    真实部署应由机器人感知层（传感器/仪表）填充这些键。
    """
    return {
        # 机器人自身
        "robot.battery_pct": 100.0,
        # 能源
        "energy.soc_kwh": round(33.0 * asset_scale, 2),
        "energy.min_soc_kwh": 5.0,
        # 食物
        "food.inventory_meals": round(400.0 * asset_scale, 2),
        "food.reserve_meals": round(50.0 * asset_scale, 2),
        "food.daily_demand_meals": 36.0,
        # 水
        "water.tank_l": round(3000.0 * asset_scale, 2),
        "water.reserve_l": round(200.0 * asset_scale, 2),
        "water.daily_demand_l": 600.0,
        # 住所
        "shelter.tenure_secure": 0.95,
        "shelter.maint_factor": 0.90,
        "shelter.damage": 0.0,
        # 健康
        "health.self_care": 0.80,
        "health.loc_factor": 0.60,
        "health.needs_care": False,
    }


# ---------------------------------------------------------------------------
# 状态表达式求值（比较 / 赋值）
# ---------------------------------------------------------------------------
# 注意：解析（语法）与求值（对状态）分离——校验阶段只需语法可解析，
# 不依赖具体世界状态；真正执行时才把表达式套到状态上。
_CMP_RE = re.compile(r"^\s*([\w.]+)\s*(>=|<=|==|!=|>|<)\s*([^\s].*?)\s*$")
_EFF_RE = re.compile(r"^\s*([\w.]+)\s*(set|inc|\+=|-=|add|=)\s*(-?\d+(?:\.\d+)?)\s*$")


def _parse_cmp(expr):
    """解析比较条件，返回 (lhs, op, rhs_token)；语法非法抛 ValueError。"""
    m = _CMP_RE.match(str(expr))
    if not m:
        raise ValueError(f"无法解析条件表达式: {expr}")
    return m.group(1), m.group(2), m.group(3)


def _parse_eff(expr):
    """解析赋值表达式，返回 (lhs, op, value)；语法非法抛 ValueError。"""
    m = _EFF_RE.match(str(expr))
    if not m:
        raise ValueError(f"无法解析状态表达式: {expr}")
    return m.group(1), m.group(2), float(m.group(3))


def _get(state, key):
    """从状态取数：优先直接键；否则按点号逐层导航（兼容嵌套字典）。"""
    if key in state:
        return state[key]
    cur = state
    for part in key.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            raise KeyError(key)
    return cur


def _set(state, key, value):
    """写入状态：直接键或按点号逐层导航写入。"""
    if key in state:
        state[key] = value
        return
    parts = key.split(".")
    cur = state
    for part in parts[:-1]:
        if not isinstance(cur.get(part), dict):
            cur[part] = {}
        cur = cur[part]
    cur[parts[-1]] = value


def _coerce(token, state):
    """把右值 token 解析为数值 / 布尔 / 或引用另一个状态键。"""
    t = token.strip()
    if t in ("True", "true"):
        return True
    if t in ("False", "false"):
        return False
    try:
        f = float(t)
        return int(f) if f.is_integer() else f
    except ValueError:
        pass
    # 否则当作另一个状态键
    try:
        return _get(state, t)
    except KeyError:
        raise ValueError(f"条件右值无法识别: {t}")


def eval_condition(state, expr):
    """求值一个比较条件表达式，如 "water.tank_l < 2500"。

    - 空串 / None → 视为"永远满足"（返回 True）。
    - 返回 bool。右值可为数值、布尔或另一个状态键。

    抛 ``ValueError`` 当表达式无法解析或右值无法识别。
    """
    if not expr or not str(expr).strip():
        return True
    lhs, op, rhs = _parse_cmp(expr)
    left = _get(state, lhs)
    right = _coerce(rhs, state)
    ops = {
        ">=": lambda a, b: a >= b,
        "<=": lambda a, b: a <= b,
        "==": lambda a, b: a == b,
        "!=": lambda a, b: a != b,
        ">": lambda a, b: a > b,
        "<": lambda a, b: a < b,
    }
    return ops[op](left, right)


def apply_effect(state, expr):
    """对状态施加一个赋值表达式，如 "energy.soc_kwh += 4" 或 "water.tank_l = 2800"。

    支持的运算符：``+=`` ``-=`` ``=``，以及等义词 ``inc``/``add``（同 ``+=``）、
    ``set``（同 ``=``）。空串 / None → 不改变状态（仅监测/验收类动作），返回 None。
    返回施加后的新值。

    抛 ``ValueError`` 当表达式无法解析。
    """
    if not expr or not str(expr).strip():
        return None
    lhs, op, rhs = _parse_eff(expr)
    cur = _get(state, lhs)
    if op in ("+=", "inc", "add"):
        new = cur + rhs
    elif op == "-=":
        new = cur - rhs
    else:  # '=' or 'set'
        new = rhs
    _set(state, lhs, new)
    return new


# ---------------------------------------------------------------------------
# 排程展开
# ---------------------------------------------------------------------------
def expand_schedule(actions, horizon_days=30):
    """把动作列表铺成值守时间轴。

    返回：
        {
          "by_day": {day: [action, ...], ...},   # 固定排程（once/daily/weekly）
          "on_demand": [action, ...],            # 按需（不进入固定排程）
        }

    - once     → 仅第 1 天执行一次
    - daily    → 每天执行
    - weekly   → 每 7 天（第 1,8,15,22,29…天）执行
    - on-demand→ 不预排，由事件/阈值触发（见 executor.run_once）
    """
    by_day = {d: [] for d in range(1, horizon_days + 1)}
    on_demand = []
    for a in actions:
        freq = a.get("frequency")
        if freq == "on-demand":
            on_demand.append(a)
        elif freq == "daily":
            for d in by_day:
                by_day[d].append(a)
        elif freq == "weekly":
            for d in by_day:
                if (d - 1) % 7 == 0:
                    by_day[d].append(a)
        elif freq == "once":
            if 1 in by_day:
                by_day[1].append(a)
        else:
            # 未知频率按 daily 处理，保证不被静默丢弃
            for d in by_day:
                by_day[d].append(a)
    return {"by_day": by_day, "on_demand": on_demand}


# ---------------------------------------------------------------------------
# 便捷：把动作的优先级转成可排序的整数
# ---------------------------------------------------------------------------
def priority_rank(action):
    return PRIORITY_RANK.get(action.get("priority"), 9)
