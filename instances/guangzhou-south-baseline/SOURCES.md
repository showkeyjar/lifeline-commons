# 数据来源与可追溯性 · 广州郊区·极限示范（南方气候对照）

本实例刻意与 [`beijing-suburb-baseline/`](../beijing-suburb-baseline/) 保持**完全相同的家庭条件**，
唯一变量是**气候**。下表每个数字都可在 `profile.json` 的 `sources` 字段复核。

## 气候数据（NASA POWER，真实）

取数接口（可复核）：

```
https://power.larc.nasa.gov/api/temporal/climatology/point
  ?parameters=ALLSKY_SFC_SW_DWN,PRECTOTCORR,T2M
  &community=RE&longitude=113.26&latitude=23.13&format=JSON
```

返回为 25 年气象与太阳能月/年气候平均（2001–2025，SYN1DEG / MERRA2）。

| 字段 | 值 | 来源 | 数据期 | 可信度 |
|---|---|---|---|---|
| solar_kwh_per_m2_day | 3.766 | **NASA POWER** ALLSKY_SFC_SW_DWN 25 年气候年均 | 2001–2025 | 中高 |
| rainfall_mm_year | 1730.0 | **NASA POWER** PRECTOTCORR 年均 4.74 mm/天 × 365 | 2001–2025 | 中高 |
| avg_temp_c | 22.61 | **NASA POWER** T2M 25 年气候年均 | 2001–2025 | 中高 |
| frost_free_days | 350 | 由月均温推导（广州最低月均温 14°C，全年无霜）+ 农气参考，近似 340–350 天 | — | 中（近似） |

## 家庭 / 资产数据（自报真实）

> 与北京实例**逐项一致**，确保气候是唯一变量。详见 `profile.json → sources`。

| 字段 | 值 | 说明 | 可信度 |
|---|---|---|---|
| household | 4 | 实际同住吃饭人头 | 高 |
| land_area_m2 | 2666.7 | 自报 4 亩（1 亩=666.67 m²） | 中（待土地承包/ GPS 复核） |
| capital | 1 | 自评档（0 赤贫 → 3 宽裕） | 中 |
| skills | IT | 自报 | 高 |
| health | 良好 | 自报 | 中 |
| mobility | true | 撤离能力（灾害韧性），非"想搬家" | 高 |
| solar_kw / battery_kwh / water_storage_l | 0 | 零装备（与北京一致） | 高 |
| well / rainwater_harvesting / greenhouse_m2 | false / false / 0 | 零装备（与北京一致） | 高 |

## 模型语义偏差（诚实标注）

- **技能词典不含 `IT`**：可变现技能词典只有 `远程工作/手艺/医护/电工`，IT 远程变现潜力被低估。
  与北京实例相同——但本示范已在本仓库修复（`IT/远程` 现被识别），故 `skill_buffer` 仍得 60 分。
- **`mobility` 语义已拆分**：`mobility=true` 仅表示撤离能力（韧性），不再触发迁移策略；
  `relocation_willingness=false` 使 relocate 得 0 分，semi_self 为首选。详见北京实例 `SOURCES.md`。
- **⚠️ 水与能源产能尚未气候化（保守低估南方优势）**：当前供给模拟器的水/能源产能由模块内置基准决定，**不读取气候**。
  广州年降雨是北京 3.2 倍、年均温高 11°C 的真实优势，在水（集雨产能）与能源（光伏略低 5%）两项**未被完全计入**——
  本对比中"南方"的领先幅度，实际应比模拟显示的**更大**。这是模型已知待改进项，已在 `notes.md` 记录。

## 偏差与现场笔记

- 模拟假设"设备正常 / 已建好基础资产"，但本户当前**零装备**。模型给出的覆盖率是"可建成的上限"。
- 食物参数**已气候化**：`frost_free_days=350` 使首收滞后缩短为 ~3 个月、爬坡更快、年度多熟有余粮（≤1.2×）。
  这正是本实例相对北京（滞后 5 个月）的核心增量。
- 水/能源产能未气候化（见上），南方真实优势被保守低估。
