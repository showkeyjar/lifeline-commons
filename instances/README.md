# 真实社区实例（Real Instances）

本项目野心的最硬承诺，不是"一个漂亮的工具包"，而是 **"一个小而真的社区实例"**——
让"不绑定巨头、靠自己也能活"这个选项，在一个真实地点、真实家庭/社群身上**被验证过**。

`examples/profiles/` 里的是**示意性 demo**（合成数据，用来演示算法）。
`instances/` 里放的是**真实、可追溯、带来源的实例**：每一份档案的每一个数字，
都必须来自真实采集（户口本、电表、气象站、土地承包合同、实地测量……），并在 `sources` 里写清出处。

> 一个"真实实例" = 一个文件夹，里面至少一份 `profile.json` + 一份 `SOURCES.md`（来源说明）。
> 可选：本地化的模块参数（`modules/<域>/data/` 的实例覆盖）、现场照片/测绘图、运行日志。

## 目录约定

```
instances/
  README.md                        你正在看的文件
  _template/
    profile.template.json          真实档案模板（含 provenance 字段，复制后填写）
    SOURCES.md                     模板来源说明范本
  <your-instance-name>/            ← 每个真实实例一个文件夹，名字用地点或社群名
    profile.json                   真实资源/家庭档案（核心 7 键 + 真实资产/气候 + 来源）
    SOURCES.md                     这份档案每个数字的出处
    notes.md                       可选：现场笔记、踩坑、与模拟的偏差
```

## 已落地的真实实例

本项目野心的最硬证明——**被真实数据验证过的社区实例**：

| 实例 | 地点 | 类型 | 一句话 |
|---|---|---|---|
| [`beijing-suburb-baseline/`](beijing-suburb-baseline/) | 北京郊区 | 郊区家庭·极限示范（零装备起点） | 4 人 / 4 亩地 / 资本档 1 / 仅 IT 技能 / 零能源·储水装备——模型诚实显示供给地板仅 29%（能源/食物/水=0），仍给出 65 分半自给路 + 60 分远程收入杠杆；叠加 12 个月建设轨迹模拟后，**自给率从 29% 爬升至 86%、自由指数 54→82.5** |
| [`beijing-suburb-equipped/`](beijing-suburb-equipped/) | 北京郊区 | 郊区家庭·条件稍好（对照） | 同 baseline 同一家庭，**唯一变量** = 资本档 2 + 已备基础装备（5kW 光伏/10kWh 储能/井/2 吨储水/50㎡ 大棚）——起点即从 29% 跳到 **74%**，第 12 月 **94%**，早 2 个月越过 80%；与 baseline 的并排对比见 [`compare.md`](beijing-suburb-equipped/compare.md) |
| [`guangzhou-south-baseline/`](guangzhou-south-baseline/) | 广州郊区 | 郊区家庭·极限示范（南方气候对照） | 与 beijing-suburb-baseline **完全相同的家庭条件**，**唯一变量 = 气候**（华南长生长季，NASA POWER 真实数据）——食物滞后仅 3 个月、第 5 月即达 90%，把"食物瓶颈更短"变成可模拟的数字；三实例并排对比见 [`compare.md`](guangzhou-south-baseline/compare.md) |

> 欢迎贡献你自己的真实实例（匿名或署名均可）。每个数字都要能在 `SOURCES.md` 复核。

## 多实例对比（让"条件更好的人看到希望"）

模拟器最有说服力的形态，是把若干实例的建设轨迹**叠成一张并排曲线**——让条件更好的人
直接看到两件事：① 仅因"提前备好基础装备"，起点就高出一个台阶；② 仅因"生活在南方长生长季"，
食物瓶颈就短 3 个月、末月更高（纯地理红利，钱买不来）。

```bash
# 把多个实例叠在一起对比（任意数量）：
python lifeline-os/lifeline.py --compare \
    instances/beijing-suburb-baseline/profile.json \
    instances/beijing-suburb-equipped/profile.json \
    instances/guangzhou-south-baseline/profile.json
# 对比报告会单独写 compare.md（与 --out 同目录）
```

- 对比引擎见 [`lifeline-os/compare.py`](../lifeline-os/compare.py)：复用 `prepare()` / `trajectory.project_trajectory`，
  不重复实现供给与策略逻辑（单一事实来源）。
- 起点已带装备的实例，第 0 月即计入（不被迫从 0 归零重建）——这是对比想暴露的增量。

## 怎么跑一个真实实例

真实实例就是一份带真实数据的 profile，直接喂给顶层闭环即可（无需改代码）：

```bash
python lifeline-os/lifeline.py --profile instances/<your-instance-name>/profile.json
# 想要机器人任务清单：
python lifeline-os/orchestrator.py --profile instances/<your-instance-name>/profile.json --execute
# 想要 12 个月建设轨迹模拟：
python lifeline-os/lifeline.py --profile instances/<your-instance-name>/profile.json --trajectory
```

> 提示：`orchestrator.py` 当前 `--profile` 已支持；若你的副本没有，用
> `python lifeline-os/lifeline.py --profile ... --execute` 同样能产出动作计划 JSON。

## 怎么新增一个真实实例

1. `cp -r instances/_template instances/<名字>`
2. 按 `docs/real-instance-onboarding.md` 的指引，**逐项采集真实数据**填进 `profile.json`
3. 在 `SOURCES.md` 写清每个数字的出处（谁测的、哪年、哪份单据/数据集）
4. 跑一遍，把模拟结果和现实偏差记到 `notes.md`
5. 提 PR——真实实例是公地最值钱的部分，欢迎匿名或署名贡献

**原则：宁可字段为 `null` 并标注"未采集"，也不要填一个编出来的数。**
一份带着"未知"的真实实例，价值远高于一份看起来完美但假的 demo。
