# 动作层（Action Layer · Stage 6）

> **一句话**：供给模拟只能回答"够不够"；动作层把这份覆盖率报告，翻译成人形机器人**可执行的任务指令**——去哪、干什么、干完怎么确认。

本项目不交付机器人，只交付**插槽与规则**。动作层是这套规则的延伸：它让一个符合 `module-interface-v1` 的供给模块，除了报告"自给率"，还能吐出"该让机器人做什么"的任务级清单。

---

## 1. 粒度原则（最重要的一条）

动作**必须停在"任务 / 目标"这一级**，绝不能下钻到关节、抓取、步态等运动原语。底层运动规划（怎么迈腿、怎么抓握、怎么避障）由机器人自身控制器完成，本项目一律不下发。

- ✅ **允许**（`ALLOWED_COMMANDS`）：`harvest / pump / inspect / assist / clean / monitor / serve / ventilate / repair / request_help / seek_care / shed_load / draw`——描述的是"要达成什么"。
- ❌ **禁止**（`FORBIDDEN_COMMANDS`）：`move_to / navigate / walk / grasp / pick / place / rotate_joint / grip / approach / traverse / reach / step` 等运动原语——必须由机器人自己处理。

`make_action()` 在**构造期**就拒绝任何黑名单命令；`tests/test_actions.py::TestActionGranularity` 永久守护这条红线。

---

## 2. 一条动作长什么样

定义在 [`action_spec.py`](https://github.com/showkeyjar/lifeline-commons/blob/main/action_spec.py)，由 `make_action()` 构造并校验。必需字段：

| 字段 | 含义 |
|------|------|
| `id` | 全局唯一 ID（建议 `<domain>.<频率?>.<动词>`） |
| `domain` | 所属域：energy / food / water / shelter / health |
| `actor` | 执行者：robot / community / human |
| `command` | **任务级**命令（白名单；运动原语一律拒绝） |
| `target` | 目标资源 / 地点 / 设备（人读字符串） |
| `params` | 自由格式参数字典 |
| `frequency` | `once` / `daily` / `weekly` / `on-demand` |
| `priority` | `high` / `medium` / `low`（执行排序） |
| `precondition` | 前置条件（状态表达式；空=永远满足；不满足则跳过） |
| `expected_effect` | 预期效果（状态表达式；空=只监测/验收，不改状态） |
| `verify` | 验收（状态表达式；空=不验收；执行后不满足记"验收失败"） |
| `note` | 人读备注 |

### 世界状态与状态表达式

世界状态是一个**扁平指标字典**（键为带点号的字符串，如 `energy.soc_kwh`、`food.inventory_meals`），由机器人感知层（传感器/仪表）填充；[`action_spec.default_operational_state()`](https://github.com/showkeyjar/lifeline-commons/blob/main/action_spec.py) 提供演示初值。

- **比较**（`eval_condition`）：`water.tank_l < 2500`、`food.inventory_meals < food.reserve_meals`、`health.needs_care == True`。右值可为数值、布尔，或另一个状态键。
- **赋值**（`apply_effect`）：`food.inventory_meals += 40`、`energy.soc_kwh -= 5`、`water.tank_l = 2800`。支持 `+=` / `-=` / `=`（含等义词 `inc`/`add`/`set`）。

> 解析（语法）与求值（对状态）分离：模块/契约做合规校验时只检查语法，不依赖具体世界状态。

---

## 3. 模块如何提供动作（向后兼容的可选扩展）

在模块的 `<Id>Module` 类里加一个**可选**方法：

```python
from action_spec import make_action

def actions(self, plan, context):
    demand = plan.get("target_daily_meals", 36)
    return [
        make_action(
            id="food.daily.harvest", domain="food", actor="robot",
            command="harvest", target="local-farm",
            params={"meals": int(demand * 1.2)},
            frequency="daily", priority="high",
            precondition="food.inventory_meals < 600",
            expected_effect=f"food.inventory_meals += {int(demand*1.2)}",
            verify="food.inventory_meals <= 800",
            note="本地农场地块每日采收，补足社区餐食库存。",
        ),
        # ... 更多任务级指令；on-demand 动作由事件/阈值触发
    ]
```

- `plan` / `context` 让动作能推导参数（如按画像算出的每日需求量）。
- **没实现 `actions()` 的模块完全不受影响**——编排器与契约都会安全跳过（向后兼容）。

契约检查器 `contract.py` 的"动作规范（可选）"一项：实现了 `actions()` 则校验其返回的动作合规；未实现则报 `·`（skip）。

---

## 4. 编排与执行

1. 编排器（`orchestrator.py`）跑完供给闭环后，调用 `collect_action_plan(results)` 汇集各模块动作，生成 `last-action-plan.json` / `last-action-plan.md`（多语言）。`lifeline.py` 同理。
2. 参考执行器（`executor.py`）在世界上**模拟值守**：
   - 续航门槛：电量低于门槛当天停工（真实机器人会先回去充电）；每天清晨满电。
   - 前置门控：`precondition` 不满足 → 跳过，不浪费电量。
   - 施加效果：`expected_effect` 改变世界状态。
   - 扣电：每个真正执行的动作消耗 `ROBOT_BATTERY_COST_PER_ACTION`（默认 2%）电量。
   - 验收：`verify` 执行后必须满足，否则记"验收失败"。
3. `expand_schedule()` 把 `daily/weekly/once` 铺成 30 天排程；`on-demand` 不预排，由事件触发。

运行：

```bash
python lifeline-os/orchestrator.py --execute     # 生成动作计划并跑参考执行器
python lifeline-os/lifeline.py --execute         # 顶层闭环同样支持
python lifeline-os/executor.py --plan lifeline-os/last-action-plan.json
```

---

## 5. 设计边界

- 动作层**不规定机器人怎么动**，只规定它要达成什么任务。运动规划是机器人厂商/控制器的职责。
- 动作层不改变供给模拟口径，也不引入任何交易/售卖逻辑。
- 这是一个**诚实的第一阶**指令层：它把"自给率缺口"映射成"该巡检/补罐/求援"的任务，但真正能否执行、执行得好不好，取决于机器人的实际能力——本层不做越俎代庖的承诺。
