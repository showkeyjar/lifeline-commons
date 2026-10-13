# 数据来源说明 · 北京郊区极限示范

本档案每一个数字的出处。原则：**真实自报的标真实来源，缺少的就填 0 / null 并标注"未采集"，绝不编造。**

| 字段 | 数值 | 来源 | 采集时间 | 可信度 |
|---|---|---|---|---|
| household | 4 | 实际同住并一起吃饭的人头（自报） | 2026-10 | 高 |
| land_area_m2 | 2666.7 | 自报 4 亩 × 666.67；待合同 / GPS 复核 | 2026-10 | 中（换算自报） |
| capital | 1 | 自评 0–3 档（有限可变现资产） | 2026-10 | 中（主观） |
| location | 郊区 | 自报：北京郊区 | 2026-10 | 高 |
| skills | ["IT"] | 自报真实技能 | 2026-10 | 高 |
| health | 良好 | 自报 | 2026-10 | 高 |
| mobility | true | 自报：可自由移动 / 撤离 | 2026-10 | 高 |
| solar_kwh_per_m2_day | 3.953 | **NASA POWER** ALLSKY_SFC_SW_DWN 25 年气候年均（39.9°N,116.4°E） | 数据期 2001–2025 | 中高 |
| rainfall_mm_year | 533.0 | **NASA POWER** PRECTOTCORR 年均 1.46 mm/天 × 365 | 数据期 2001–2025 | 中高 |
| avg_temp_c | 11.61 | **NASA POWER** T2M 25 年气候年均 | 数据期 2001–2025 | 中高 |
| frost_free_days | 190 | 由 NASA POWER 月均温推导 + 北京农气参考（近似） | 2026-10 | 中（近似） |
| solar_kw | 0 | 无光伏 | 2026-10 | 高 |
| battery_kwh | 0 | 无储能 | 2026-10 | 高 |
| water_storage_l | 0 | 无水箱 / 水塔 | 2026-10 | 高 |
| well | false | 无井 | 2026-10 | 高 |
| rainwater_harvesting | false | 无集雨 | 2026-10 | 高 |
| greenhouse_m2 | 0 | 无大棚 | 2026-10 | 高 |
| livestock | [] | 无牲畜 | 2026-10 | 高 |

## 气候数据获取方式（可复核）

```
GET https://power.larc.nasa.gov/api/temporal/climatology/point
  ?parameters=ALLSKY_SFC_SW_DWN,PRECTOT,T2M
  &community=RE
  &longitude=116.40&latitude=39.90
  &format=JSON
```

返回（节选）：
- `ALLSKY_SFC_SW_DWN.ANN` = 3.953 （kW-hr/m²/day）
- `PRECTOTCORR.ANN` = 1.46 （mm/day）→ ×365 ≈ 533 mm/年
- `T2M.ANN` = 11.61 （°C）
- 数据期：25-year Meteorological and Solar Monthly & Annual Climatologies (January 2001 – December 2025)

## 未采集 / 不确定项

- `land_area_m2`：基于"4 亩"自报换算，尚未用土地承包合同或 GPS 围合复核，可能与实测有偏差。
- `frost_free_days`：NASA POWER 不直接提供，由月均温 + 北京农气经验推算为 ~190 天，属近似值。
- `wind_kw`：本地未评估风电，填 null。

## 模型语义偏差（重要）

- **技能词典不匹配（已修复）**：本实例自报技能为 `IT`，原策略分析器可变现词典只有
  `远程工作 / 手艺 / 医护 / 电工`，不含 `IT`，导致 `skill_buffer` 得 0 分。现已把 `IT / 远程 / Remote`
  纳入可变现词典——本户 `skill_buffer` 升至 60、`relocate` 升至 90。原则：不篡改自报数据，让模型学会认识现代技能。
- **mobility 语义双重（仍需注意）**：本实例 `mobility=true` 指"能自由撤离（灾害韧性）"，但策略分析器把它当作
  "是否适合低成本迁移"的触发器，可能误推"迁移"为首选策略。见 `notes.md` 的重新解读。

## 偏差与现场笔记

- **仿真资产假设（已修复）**：早期版本硬编码 `DEFAULT_RESOURCES`（光伏/电池/井/集雨/仓储全在），
  零装备户也被算出 100% 覆盖。现已让仿真只统计画像 `assets` 里真实拥有/运营的资源——本户 `assets` 全为 0/false，
  于是能源/食物/水诚实显示 0，供给均值 27%。详见 `notes.md` §1。
- 食物=0 的口径：因 4 亩地**当前未耕种**，local-farm 仅运营后计入；非"不能种"。
