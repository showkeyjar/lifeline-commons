# 机器人动作计划（Action Plan）

> 把「够不够」翻译成人形机器人可执行的任务指令：去哪（target）、干什么（command）、干完怎么确认（verify）。粒度停在任务级——绝不下发 move_to / grasp 等运动原语。

## 动作清单

| 动作 ID | 域 | 执行者 | 指令 | 目标 | 频率 | 优先级 | 前置条件 | 预期效果 | 验收 |
|---|---|---|---|---|---|---|---|---|---|
| energy.daily.inspect | 能源 | 机器人 | inspect | solar-array | 每日 | 低 | — | — | energy.soc_kwh > 0 |
| energy.daily.monitor | 能源 | 机器人 | monitor | battery | 每日 | 低 | — | — | energy.soc_kwh >= 0 |
| energy.on_demand.shed_load | 能源 | 机器人 | shed_load | distribution-board | on-demand | 高 | energy.soc_kwh < 5 | energy.soc_kwh += 4 | energy.soc_kwh >= 0 |
| food.daily.harvest | 食物 | 机器人 | harvest | local-farm | 每日 | 高 | food.inventory_meals < 600 | food.inventory_meals += 14 | food.inventory_meals <= 800 |
| food.daily.serve | 食物 | 机器人 | serve | community | 每日 | 高 | food.inventory_meals >= 12 | food.inventory_meals -= 12 | food.inventory_meals >= 0 |
| food.daily.monitor | 食物 | 机器人 | monitor | community-storage | 每日 | 低 | — | — | food.inventory_meals >= 0 |
| food.on_demand.request_help | 食物 | 社区 | request_help | community | on-demand | 高 | food.inventory_meals < food.reserve_meals | — | — |
| health.daily.monitor | 健康 | 机器人 | monitor | care-station | 每日 | 低 | — | — | health.self_care >= 0 |
| health.daily.inspect | 健康 | 机器人 | inspect | first-aid | 每日 | 低 | — | — | health.self_care >= 0.3 |
| health.on_demand.seek_care | 健康 | 人 | seek_care | clinic | on-demand | 高 | health.needs_care == True | — | — |
| shelter.daily.inspect | 住所 | 机器人 | inspect | structure | 每日 | 低 | — | — | shelter.tenure_secure >= 0 |
| shelter.daily.monitor | 住所 | 机器人 | monitor | tenure | 每日 | 低 | — | — | shelter.maint_factor >= 0 |
| shelter.on_demand.repair | 住所 | 机器人 | repair | structure | on-demand | 高 | shelter.damage > 0.2 | shelter.damage -= 0.1 | shelter.damage <= 0.2 |
| water.daily.pump | 水 | 机器人 | pump | well | 每日 | 高 | water.tank_l < 2500 | water.tank_l += 200 | water.tank_l <= 3200 |
| water.daily.draw | 水 | 机器人 | draw | community | 每日 | 高 | water.tank_l >= 200 | water.tank_l -= 200 | water.tank_l >= 0 |
| water.daily.monitor | 水 | 机器人 | monitor | community-tank | 每日 | 低 | — | — | water.tank_l >= 0 |
| water.daily.inspect | 水 | 机器人 | inspect | rain-harvest | 每日 | 低 | water.tank_l < 100 | — | water.tank_l >= 100 |

## 前置条件与验收

- 前置条件（precondition）：不满足条件则机器人跳过该动作，不浪费电量。
- 预期效果（expected_effect）：执行后施加到世界状态的状态表达式；空串表示仅监测/验收，不改状态。
- 验收（verify）：执行后必须满足的校验条件；不满足记为「验收失败」。

