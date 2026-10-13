# 本地能源模块（energy）

数据驱动参考实现（阶段 1）。读取本地样例数据做 30 天自给模拟，
输出**社区自给覆盖率**（供应 ÷ 需求），解决"这个社区自己够不够用"。

## 数据驱动（当前）

模块读取 `data/` 下的样例数据，不依赖硬件即可复现：

- `data/config.json`：`pv_kwp`（光伏装机 kWp）、`per_capita_kwh`（每人每天基线）、`population`（人口）
- `data/solar_forecast.csv`：未来 30 天每日 `kwh_per_kwp`（每 kWp 实际发电）
- `data/battery.json`：储能 `capacity_kwh` / `initial_soc_kwh` / `max_discharge_kwh_per_day` / `min_soc_kwh`

模拟逻辑：`光伏直供 → 不足则储能放电 → 仍不足记录缺口`；余电只充电不卖。
产出 `avg_coverage`（平均自给率）、`full_days` / `shortfall_days`、`min_soc_kwh`。

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
