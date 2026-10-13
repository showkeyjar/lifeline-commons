# 本地能源模块（energy）

薄参考实现，先把「需求感知 → 调度 → 交付」闭环跑通。当前为模拟：
按人口给出每日用电基线，优先用光伏，不足时降级到储能放电。

## 接口（module-interface-v1）

- `provides()`: `["electricity"]`
- `assess_needs(context)`: 返回 `daily_kwh`
- `schedule(resources, needs)`: 选 `solar` / `battery` / `community-storage`
- `provide(plan)`: 交付并声明 `fail_mode = "degrade-to-stored"`

## 范围（重要）
- 本模块的目标是**社区自身的自给覆盖率**（供应 ÷ 需求），解决"这个社区自己够不够用"。
- **明确排除电力交易**：不做余电上网售卖、电价套利、虚拟电厂、需求响应变现。本项目当前及可预见阶段与电力市场无关。

## 未来替换方向（实现可换，接口留住）

- 开源离网光伏 + 储能 + 智能配电：OpenEMS、Sandia PV Lib
- 微电网调度（限本地共享，非交易）：把多个社区的储能当成一个本地共享缓冲池，仅用于互相补缺，不进入市场
- 接真实电表/逆变器数据，让 `assess_needs` 从估算变实测
