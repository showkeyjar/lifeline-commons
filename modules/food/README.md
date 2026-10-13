# 食物模块（food）

数据驱动参考实现（阶段 1）。读取本地样例数据做 30 天自给模拟，
输出**可供应餐数 vs 缺口**，解决"这个社区自己够不够吃"。

## 数据驱动（当前）

模块读取 `data/` 下的样例数据，不依赖硬件即可复现：

- `data/config.json`：`population`（人口）、`meals_per_person_per_day`（每人每天餐数）、`storage_capacity_meals`（库存上限）
- `data/inventory.json`：`initial_meals`（初始库存）、`min_reserve_meals`（最低储备，不被动用）
- `data/yield_forecast.csv`：未来 30 天每日 `meals`（本地产量，餐数）

模拟逻辑：`本地生产 → 不足则动用库存 → 仍不足记录缺口`；余量入库不卖。
产出 `avg_coverage`（平均自给率）、`full_days` / `shortfall_days`、`min_inventory`。

## 下一步可以真起来的方向
- 接入开源垂直农场 / 营养自动化（参考 MIT OpenAg Food Computer）
- 用真实传感器做 `assess_needs`（库存、消耗、人口）
- 把 `provide` 接到实际执行器（播种、采收、分配）

## 接口
必须 conform `docs/module-interface-v1.md`。换实现不换接口。
