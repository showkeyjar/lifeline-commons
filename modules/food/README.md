# 食物模块（参考实现）

薄参考实现，目前是**模拟**，只为跑通「感知 → 调度 → 供给」闭环。

## 下一步可以真起来的方向
- 接入开源垂直农场 / 营养自动化（参考 MIT OpenAg Food Computer）
- 用真实传感器做 `assess_needs`（库存、消耗、人口）
- 把 `provide` 接到实际执行器（播种、采收、分配）

## 接口
必须 conform `docs/module-interface-v1.md`。换实现不换接口。
