# 本地住所模块（shelter）

居住安全评估模块，是 **Stage 4 协议硬化** 的"第三方扩展样板"：仅凭
[`docs/module-interface-v1.md`](../../docs/module-interface-v1.md) 的契约，就能写出
一个可被自动发现、纳入生存自由指数的新模块。

## 它评估什么

住所不是"每日生产-消耗"的流资源，而是 **居住安全（产权/保有 + 可维护）** 的静态评估：

```
覆盖 = min(保有安全, 可维护缓冲)
```

| 画像 | 保有安全 | 含义 |
|------|----------|------|
| 有地 | 0.95 | 自有住房（地在手，屋可自建/已有） |
| 无地但资本≥2 | 0.90 | 大概率城市自有住房 |
| 无地资本=1 | 0.60 | 稳定租房（保有不安全，非自由） |
| 无地无资本 | 0.10 | 极不稳定 / 无安全住所 |

`asset_scale`（资本）提升 **可维护缓冲**：资产越足，越能不依赖外部市场去维护、修缮、保有住房。

## 接口

完全 conform `module-interface-v1`：
- `assess_needs(context)` 在唯一能拿到完整 `context` 的环节，把 `has_land/capital/location`
  经 `needs` 透传给 `schedule → provide`（接口不含额外参数）。
- `provide(plan)` 返回 `delivered_avg_coverage`（30 天窗口恒定，房子不会逐日耗尽）、
  `full_days / shortfall_days`、`fail_mode="request-help"`（住所缺口只能靠社区互助/共享空间）。

## 验证

```bash
python lifeline-os/contract.py modules/shelter   # 必须全绿
python lifeline-os/lifeline.py --profile examples/profiles/xiao_a_rural.json
```

## 替换真实数据

当前是占位模型。真实部署应把 `data/config.json` 换成本地房产/租赁/社区互助数据，
只要 conform 接口，编排层无需改动。
