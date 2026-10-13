# 供给模块接口标准 v1（稳定契约 · 可执行规范）

> 目标：**实现可以换，接口必须留住。** 今天的模拟食物模块、未来的具身 AI 农场，都要 conform 到同一个契约，编排层（`lifeline-os/orchestrator.py`）无需改动。
>
> 本文件是**契约的唯一权威来源**。任何模块只要通过 `lifeline-os/contract.py` 的全部检查，即可被自动发现并接入闭环——无需改编排层。

---

## 1. 模块发现约定（自动发现，零登记）

编排器扫描 `modules/<id>/` 目录，要求：

1. 目录名 = 模块 `id`（小写 ASCII，如 `food`、`shelter`）。
2. 目录内必须有 `<id>_module.py`，其中定义一个 PascalCase 类 `<Id>Module`（如 `FoodModule`）。
3. 该类实现下面全部 6 个方法，且均为可调用。
4. 目录内必须有 `module.toml`（manifest，见 §4）。

不满足任意一条 → 编排器打印原因并**跳过**该模块（CI 据此拦下破坏契约的提交）。

---

## 2. 必需方法（精确签名与返回形状）

| 方法 | 签名 | 返回 | 语义 |
|------|------|------|------|
| `name()` | `name() -> str` | 字符串，必须等于 `module.toml` 的 `id` | 模块标识 |
| `provides()` | `provides() -> list[str]` | 非空字符串列表，必须等于 manifest 的 `provides` | 该模块满足的需求类型 |
| `assess_needs` | `assess_needs(context: dict) -> dict` | 需求报告（见下） | 感知社区缺什么、缺多少 |
| `schedule` | `schedule(resources: dict, needs: dict) -> dict` | 调度计划（见下） | 决定用什么、怎么供 |
| `provide` | `provide(plan: dict) -> dict` | 交付报告（见下） | 真正交付，并声明失败模式 |
| `status` | `status() -> dict` | 健康字典（见下） | 当前状态，供编排层监控 |

### 2.1 `assess_needs(context)` 返回形状
```python
{
    "need_type": str,        # 与 provides()[0] 一致，如 "shelter"
    "population": int,       # 从 context["population"] 取，缺省用模块自身 config
    # ... 域特定的日均需求数值，如 daily_kwh / daily_meals / daily_l / persons_need
    "unit": str,             # 人读单位
}
```

### 2.2 `schedule(resources, needs)` 返回形状
```python
{
    "strategy": str,          # 当前固定为 "self-sufficiency"（本项目不做交易）
    "priority": list[str],    # 实际可用的资源清单（resources["available"] 的子集）
    # ... 域特定的 target_*（要满足的需求量）
    "asset_scale": float,     # 必须透传 resources.get("asset_scale", 1.0)（见 §3）
}
```

### 2.3 `provide(plan)` 返回形状（**强制字段**）
```python
{
    "delivered_avg_coverage": float,   # 平均覆盖率 ∈ [0.0, 1.0]，供应 ÷ 需求
    "full_days": int,                  # 覆盖 ≥ 0.999 的天数
    "shortfall_days": int,             # 覆盖 < 0.999 的天数
    "status": str,                     # "ok" 或 "partial"
    "fail_mode": str,                  # 资源不足时的安全降级方式（见 §5）
    # ... 域特定的最低状态量（如 min_soc_kwh / min_inventory / min_tank_l）
}
```
并且 `provide` 必须保存本次运行结果，使 `status()` 能反映它（`_last` 模式）。

### 2.4 `status()` 返回形状
```python
{
    "health": str,        # "nominal"（无缺口）或 "degraded"（有缺口）；与 shortfall_days 一致
    # ... 其他监测量
}
```
**一致性不变量**：若 `provide` 后 `shortfall_days > 0`，则 `status()["health"]` 必须为 `"degraded"`；否则必须为 `"nominal"`。

---

## 3. `asset_scale` 约定（供给侧缩放）

`asset_scale`（资产规模系数）是让供给模拟**真正吃进主人画像**的关键量：

- 含义：主人实际能建起的产能，相对"基准社区"的比例。**1.0 = 持有与基准社区匹配的产能**。
- 它由上层（`lifeline.py` 的 `compute_asset_scale`）按画像（资本/有地/策略）推算后，通过 `resources["asset_scale"]` 传入。
- **每个模块的 `schedule` 必须把它透传到 `provide → _simulate`，且产能（发电/产量/储水/可维护容量）与储能/库存容量随它同比缩放。**
- 需求侧由 `context["population"]` 缩放（`assess_needs` 已按人口缩放日均需求）。
- 默认 `asset_scale = 1.0`（未指定时）。编排器 standalone 跑默认 1.0。

> 不消费 `asset_scale` 的模块，其覆盖率将不随画像变化——校验器会判为可疑（§6 压力测试）。

---

## 4. `context` 约定（需求侧 + 画像透传）

`context` 是自由格式字典，至少含：
```python
{
    "community": str,       # 社区标识
    "population": int,      # 人口/家庭人数（驱动需求）
    # 以下为可选画像字段，住所类等模块会用到：
    "has_land": bool,       # 是否有可用土地
    "capital": int,         # 启动资本 0-3
    "location": str,        # 城市/郊区/乡村/离网
}
```
其他模块忽略自己不认识的键（向后兼容）。上层 `lifeline.py` 会把画像的 `has_land/capital/location` 透传进 `context`。

---

## 5. 失败模式（fail_mode）

每个模块必须声明它在资源不足/故障时如何**安全降级**，例如：
- `degrade-to-stored`：优先动用储备（储能/库存/储水罐）
- `request-help`：向其他模块/社区求援
- `graceful-stop`：停下但不扩散故障

本项目不做任何交易/售卖逻辑；缺口只记录，不"补自外部市场"。

---

## 6. 一致性不变量（校验器 `contract.py` 必须检查）

一个合规模块必须通过这些检查（详见 `lifeline-os/contract.py`）：

1. **结构**：6 方法全 callable；`name()` == manifest `id`；`provides()` 列表 == manifest `provides` 且非空。
2. **行为形状**：`assess → schedule → provide → status` 全链路不抛异常，且 `provide` 返回含全部 §2.3 强制字段、`status` 含 `health`。
3. **health 一致性**：`status()["health"]` 与 `provide` 的 `shortfall_days` 严格一致（见 §2.4）。
4. **防硬编码压力测试**：在极端画像（人口放大、asset_scale 压到 0.2、无地无资本）下，`delivered_avg_coverage` **必须 < 0.99**。任何永远返回 100% 的"假满供"模块一律判 FAIL——本项目拒绝假数据。
5. **响应性**：宽裕画像（有地 + 高资本 + 小人口 + 高资产系数）下的覆盖率，必须**严格高于**极端画像（无地 + 零资本 + 大人口 + 低资产系数）。方向安全，适用于流资源与住所两类；任何不读输入、返回常量的模块都会被抓出。

---

## 7. Manifest（`module.toml`）

```toml
id = "shelter"            # 必须等于目录名、name() 返回值
name = "本地住所模块"      # 人读名称
provides = ["shelter"]    # 必须等于 provides() 内容
version = "0.1.0"         # 模块自身版本
interface = "v1"          # 遵循的接口大版本
maintainer = "community"  # 维护者
```

---

## 8. 版本演进规则（v1 → v2 及以后）

- **只加不减、向后兼容**：新大版本可新增可选方法/字段，不可删除或改变既有方法的必需语义。
- 破坏既有语义时，必须升大版本号（v1→v2），并保留 v1 兼容层一段时间。
- 编排器按 `interface` 字段选择兼容路径。

---

## 9. 如何新增一个模块（清单）

1. `modules/<id>/<id>_module.py` 定义 `<Id>Module`，实现 §2 全部方法。
2. 写好 `module.toml`（§7）与 `data/` 样例数据（让 clone 即可复现）。
3. 跑 `python lifeline-os/contract.py modules/<id>` —— 必须全绿。
4. 跑 `python lifeline-os/lifeline.py --profile examples/profiles/<你的画像>.json` 确认被自动发现并纳入自由指数。
5. 提 PR，按 `GOVERNANCE.md` 的模块准入清单评审。

> 接口是本项目真正的持久资产。实现可以推倒重来，接口尽量不动。

---

## 10. 动作层扩展（可选 · Stage 6）

供给闭环（§2 的 6 方法）只回答"够不够"。**动作层**让模块进一步吐出"该让机器人做什么"的任务级指令，把覆盖率报告翻译成人形机器人可执行的任务——去哪、干什么、怎么确认。

### 10.1 粒度原则（红线）

动作**必须停在任务级**，绝不下发运动原语。详见 [`docs/action-layer.md`](action-layer.md)。核心约束：

- 命令必须是任务级（`harvest / pump / inspect / serve / repair / request_help / seek_care / shed_load / draw` …）。
- 禁止 `move_to / navigate / walk / grasp / pick / place / rotate_joint` 等运动原语——这些是机器人自身运动规划的职责。
- `make_action()` 在构造期拒绝黑名单命令；`tests/test_actions.py` 永久守护。

### 10.2 可选方法签名

在 `<Id>Module` 上加一个**可选**方法（未实现则编排器/契约安全跳过，向后兼容）：

```python
from action_spec import make_action

def actions(self, plan, context) -> list[dict]:
    """返回任务级动作列表。plan/context 用于推导参数。"""
    ...
```

### 10.3 单条动作形状

每条动作由 `action_spec.make_action()` 构造，含 `id / domain / actor / command / target / params / frequency / priority / precondition / expected_effect / verify / note`（详见 `action_spec.REQUIRED_FIELDS`）。

- `frequency`：`once` / `daily` / `weekly` / `on-demand`。
- `precondition`（空=永远满足）/ `expected_effect`（空=只监测/验收）/ `verify`（空=不验收）都是**世界状态表达式**：
  - 比较 `eval_condition`：`water.tank_l < 2500`、`health.needs_care == True`。
  - 赋值 `apply_effect`：`food.inventory_meals += 40`、`energy.soc_kwh = 5`。
- 世界状态是扁平指标字典（键如 `energy.soc_kwh`），由机器人感知层填充；`action_spec.default_operational_state()` 提供演示初值。

### 10.4 编排与执行

- 编排器 `collect_action_plan(results)` 汇集各模块动作 → 生成 `last-action-plan.json` / `.md`（多语言）。
- 参考执行器 `executor.py` 在世界状态上模拟值守：续航门槛 → 前置门控 → 施加效果 → 扣电 → 验收；`expand_schedule()` 把 `daily/weekly/once` 铺成 30 天排程，`on-demand` 由事件触发。

### 10.5 版本演进

动作层 schema 版本见 `action_spec.ACTION_SCHEMA_VERSION`。与 §8 一致：只加不减、向后兼容；破坏性变更升主版本号。
