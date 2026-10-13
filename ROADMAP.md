# 路线图（ROADMAP）

项目的价值不在"造机器人"，而在两件事：
1. **中立协议**——供给模块怎么互操作、治理怎么运作的开放标准（能力无关，类比 ROS / HTTP）。
2. **真实社区实例**——一个小型、社区运行、服务巨头不愿服务群体（偏远、贫困、被市场放弃的角落）的部署。

下面是把这两件事从口号变成可执行阶段的路线。

---

## 阶段 0 — 骨架与契约（已完成 ✅）

**交付物**：仓库、AGPL-3.0+反圈地、治理草案、稳定接口 v1、自动发现编排器、2 个薄模拟模块（food/energy）、接口契约校验、CI 冒烟测试。

**判定完成**：`python lifeline-os/orchestrator.py` 跑通双模块闭环；push 触发 CI 绿。

---

## 阶段 1 — 让模块从"模拟"变"数据驱动"

**目标**：模块不再硬编码，而是读本地数据做真实计算。不要求真实硬件，先用数据文件跑通。

- 能源：读 `solar_forecast` + `battery_state` 数据，按"光伏优先→储能放电→共享缓冲"三级调度，输出实际覆盖率（供应/需求）。
- 食物：读 `inventory` + `yield_estimate`，输出可供应餐数 vs 需求缺口。
- 每个模块提供 `data/` 下的样例数据，让任何人 clone 就能复现。
- 可选：加 `adapters/` 层，把模块和"数据从哪来"（CSV / API / 传感器）解耦。

**判定完成**：模块无硬编码假数；样例数据下跑出有意义的实际供需数字。

---

## 阶段 1.5 — 画像驱动的生存自由闭环（已完成 ✅）

**目标**：把"策略推荐"和"供给模拟"两个脱节的半截接成一条命令，让"机器人先分析最佳生存策略、目标生存自由"真正可跑。

- ✅ [`lifeline-os/lifeline.py`](https://github.com/showkeyjar/lifeline-commons/blob/main/lifeline-os/lifeline.py)：顶层闭环——读画像 → 策略分析器推荐策略 → 把画像（人口 + `asset_scale` 资产系数）喂给供给层模拟 → 综合成**生存自由指数**，输出一份完整的生存自由报告。
- ✅ 供给模块接入 `asset_scale`：产能随画像缩放、需求随人口缩放，模拟不再永远用 12 人基准社区数据。
- ✅ 3 个示例画像（`examples/profiles/`）：乡村有地小A、城市无地失业、城市有技能远程——分别演示"高自由度 / 需外部托底 / 靠可携带收入"。
- ✅ 集成测试（`tests/test_lifeline.py`）+ CI 冒烟已覆盖闭环。
- 模型与诚实边界见 [`docs/freedom-index.md`](docs/freedom-index.md)。

**判定完成**：`python lifeline-os/lifeline.py --profile examples/profiles/*.json` 三种画像都能产出可信、差异化、诚实标注边界的报告；CI 绿。

---

## 阶段 2 — 治理最小可用（MVP governance）

**目标**：把 GOVERNANCE.md 从草案变成能真正运转的决策流程。

- 明确"加一个新模块"的评审流程（谁拍板、按什么标准）。
- 重申**范围纪律**：本项目只解决马斯洛 1–2 层（物质），**不替人解决意义/角色**；后者靠人在系统中的治理权提供。
- 建立"范围溢出"的拒绝机制（避免项目被空泛化成万能框）。

**判定完成**：有人提第一个社区 PR 加模块时，流程能跑；范围争议有据可依。

---

## 阶段 3 — 第一个真实社区实例

**目标**：落地一个最小部署，证明"不绑定巨头"的供给选项真实存在。

- ✅ **启动清单已起草**：[`docs/community-playbook.md`](docs/community-playbook.md)——把蓝图案例变成 5 步可复制剧本（组队共识 → 拿地 → 部署产能 → 接入 Lifeline OS → 持续治理），含诚实门槛（不服务赤贫无地者）。
- ✅ **实例载体已建**（2026-10-13）：`instances/` 目录 + 带溯源字段的 [`profile.template.json`](instances/_template/profile.template.json) + [`SOURCES.md`](instances/_template/SOURCES.md) 范本 + [`docs/real-instance-onboarding.md`](docs/real-instance-onboarding.md) 数据来源指南。真实实例与 `examples/`（示意 demo）明确区分——**真实实例的每个数字都必须带来源**。
- ✅ **第一个真实实例已落地**（2026-10-13）：`instances/beijing-suburb-baseline/`——用户自家真实数据（北京郊区，4 人 / 4 亩地 / 资本档 1 / IT 技能 / 零装备），NASA POWER 真实气候，带 `SOURCES.md` + `notes.md`。仿真已资产感知，诚实显示供给地板 27%（能源/食物/水=0），仍给出 65 分半自给路 + 90 分远程收入杠杆。
- 找 1 个离网/欠服务社区做伙伴（先谈，不急着上硬件）。
- 部署最小栈（energy + food），用阶段 1 的数据驱动模块 + 真实本地数据。
- 写一份公开的运行报告：解决了谁、覆盖多少、没解决什么（诚实记录边界）。

**判定完成**：有一个真实社区在用；报告公开；明确标注本项目能/不能做什么。

> **方向 A 已启动**：第一个真实实例选定"用户自家真实数据"（北京郊区极限示范，见上）。
> 后续可叠加更多真实实例（你家 / 某社群 / 我以公开数据锚定的真实地点），每个都带 `SOURCES.md`。
> 仿真资产感知已接通——零装备户不再被假设全套设备，供给地板诚实地趋近于 0，让"极限示范"真正可信。

---

## 阶段 4 — 协议硬化（已完成 ✅）

**目标**：让接口从"v1 草稿"变成可信、可互操作的标准。

- ✅ [`docs/module-interface-v1.md`](docs/module-interface-v1.md) 重写为**精确可执行契约**：方法签名/返回形状、`asset_scale` 与 `context` 约定、`module.toml` manifest schema、一致性不变量、版本演进规则（v1→v2 只加不减、向后兼容）。
- ✅ [`lifeline-os/contract.py`](https://github.com/showkeyjar/lifeline-commons/blob/main/lifeline-os/contract.py)：协议一致性校验器（零依赖），查**结构 / 行为形状 / health 一致性 / 防硬编码压力测试 / 响应性**五类，CLI 跑全模块或单模块，失败非零退出。
- ✅ 契约一致性测试（`tests/test_interface_contract.py`）：对 energy/food/water/shelter 跑全绿；并故意构造"硬编码 100%""缺方法"的假模块，断言校验器能抓出——证明契约不是摆设。
- ✅ 新增 [`modules/shelter`](https://github.com/showkeyjar/lifeline-commons/blob/main/modules/shelter) 住所模块，**仅凭接口文档写成**，被自动发现并纳入生存自由指数——兑现"第三方能仅靠文档写出可插拔模块"的判定完成标准。住所维度让"有饭吃电用但无安全住房"的画像被诚实暴露（城市无地失业者住所覆盖仅 0.10）。
- ✅ CI（`smoke.yml`）已加入运行 contract.py。
- 后续（未做）：探索与既有开源项目的互操作（OpenAg / OpenEMS / Sandia PV Lib）；真要破 v1 语义时再升 `module-interface-v2`。

**判定完成**：第三方能仅靠接口文档写出一个可插拔模块并通过一致性测试 —— 已用 shelter 模块实证。

---

## 阶段 4.5 — 多语言化（已完成 ✅）

**目标**：把"中立协议 + 社区实例"真正做成**多国语言**——工具报告与文档都不限于中文，让非中文社区也能用、也能贡献。

- ✅ [`lifeline-os/i18n.py`](https://github.com/showkeyjar/lifeline-commons/blob/main/lifeline-os/i18n.py)：零依赖多语言内核，集中全部面向人字符串的三语目录（中文 `zh` / English `en` / Español `es`）；提供 `set_language / t() / --check`；缺失键自动回退中文、绝不空屏。
- ✅ 三个报告生成器（`lifeline.py` / `strategy_analyzer.py` / `orchestrator.py`）全部接上 `t()`，新增 `--lang en|es` 参数；策略名/介入/自由度/自由指数分档/边界说明/表头全翻译；用户数据里的地点(`乡村/城市…`)、健康(`良好/受限`)分类值也随语言切换。
- ✅ 新增 [`modules/health`](https://github.com/showkeyjar/lifeline-commons/blob/main/modules/health) 基础健康模块（**第 5 插槽**），建模"自护能力 × 在地可及性"的第一阶代理指标，conform v1、消费 `asset_scale` 与画像，被自动发现并纳入自由指数与多语言报告。
- ✅ 多语言文档：英文门面 [`README.en.md`](README.en.md)、英文接口规范 [`docs/en/module-interface-v1.md`](docs/en/module-interface-v1.md)、新增 [`docs/i18n.md`](docs/i18n.md) 说清"如何新增语言（代码 + 文档）"。
- ✅ 测试：`tests/test_i18n.py` 守护 en/es 键完整性、t() 占位符与回退、语言切换、health 经契约通过、报告中无未翻译键泄漏；全套 **40 个测试通过**。
- ✅ `--check` 自检纳入日常；CI（`smoke.yml`）已加入运行 `i18n.py --check`。

**判定完成**：同一份画像，`--lang zh/en/es` 输出三语报告；新增语言只需在 `CATALOG` 加一个键。

---

## 阶段 6 — 动作层（机器人可执行指令）（已完成 ✅）

**目标**：把"供给模拟只能回答够不够"推进到"能指导人形机器人行动"——让符合接口 v1 的模块除了报自给率，还能吐出**任务级**指令：去哪、干什么、干完怎么确认。

- ✅ [`action_spec.py`](action_spec.py)：动作层核心规范与参考实现——动作 schema（`make_action` / `validate_action` / `validate_plan`）、**任务级命令白名单 + 运动原语黑名单（粒度红线）**、世界状态与状态表达式求值（`eval_condition` / `apply_effect`，解析与求值分离）、`default_operational_state` 演示初值、`expand_schedule` 30 天排程展开。
- ✅ [`lifeline-os/executor.py`](lifeline-os/executor.py)：参考机器人执行器——续航门槛 → 前置门控 → 施加效果 → 扣电 → 验收；`execute_plan`（30 天值守 / `once` 单次两种模式）；按域汇总；CLI 写 `last-execution-log.json`。
- ✅ 5 个供给模块（food/energy/water/shelter/health）各加**可选** `actions(plan, context)` 方法，返回任务级指令（共 17 条：含 on-demand 的 `request_help` / `shed_load` / `repair` / `seek_care`）。
- ✅ 编排器（`orchestrator.py`）/ 顶层闭环（`lifeline.py`）：供给结果 → `collect_action_plan` 汇集 → 生成 `last-action-plan.json` / `.md`（多语言）；新增 `--execute` 直接驱动参考执行器。闭环返回签名升级为 6 元组 `(module_id, module, needs, plan, delivery, context)` 以贯通动作层。
- ✅ 契约检查器（`contract.py`）新增"动作规范（可选）"项：实现了 `actions()` 则校验其合规，未实现则报 `·`（skip），**向后兼容**。
- ✅ 多语言：i18n 新增约 34 个动作层键（zh/en/es 三语对齐，`i18n.py --check` 通过）。
- ✅ 测试：`tests/test_actions.py` 守护良构性、粒度红线（运动原语一律拒绝）、执行器门控与验收、契约动作检查；全量 **52 个测试通过**。
- ✅ CI（`smoke.yml`）新增"生成机器人动作计划 + 跑参考执行器"步骤。
- ✅ [`docs/action-layer.md`](docs/action-layer.md) 新增动作层说明；[`docs/module-interface-v1.md`](docs/module-interface-v1.md) 补 §10 动作层扩展。

**判定完成**：`python lifeline-os/orchestrator.py --execute` 产出 17 条任务级指令并以参考执行器模拟 30 天值守（成功 / 跳过 / 验收失败全统计，验收失败为 0）；`make_action` 在构造期拒绝任何运动原语，粒度红线由测试永久守护。

**边界**：动作层只规定"要达成什么任务"，运动规划（怎么迈腿、怎么抓握、怎么避障）是机器人自身控制器的职责；本项目不下发任何运动原语，也不做任何交易/售卖逻辑。

---

## 阶段 5 — 抗捕获与可持续（已完成 ✅）

**目标**：让"公地"长期不被重新私有化、不断粮。详见 [`docs/commercialization.md`](docs/commercialization.md) 与 [`GOVERNANCE.md`](GOVERNANCE.md)。

- ✅ **定位纪律**：公益/公地是核心与目的；商业化是给公地输血的边缘手段，不可反客为主、不可圈地（见 commercialization.md §1）。
- ✅ **明确排除电力交易**：能源模块只算社区自身自给覆盖率，不做余电上网/电价套利/虚拟电厂（commercialization.md §1 / GOVERNANCE §4 红线 2）。
- ✅ **资金模型（抗捕获设计）**：[`docs/commercialization.md` §4](docs/commercialization.md) 把 6 个商业点组织成 **A 服务与硬件 / B 托管与认证 / C 资助与影响力** 三类收入组合，并落地护栏——单一来源 **>33% 观察、>50% 强制治理复核**、核心免费基线（自托管永久免费）、透明年度核算、收益反哺公地、公益优先定价。目标不是最大化收入，而是"公地在没有单一金主、没有单点关键人的情况下也能持续演进"。
- ✅ **许可证执行（AGPL + 反圈地 + 监控）**：`LICENSE` 已是 AGPL-3.0 并带**反圈地条款**；由 `tests/test_sustainability.py` 守护（CI 红即说明条款被删改）。
- ✅ **Fork 抗性（治理去中心 + 具体路由）**：[`GOVERNANCE.md` §5](GOVERNANCE.md) 写明硬规则——高门槛 PR **须 ≥2 名维护者独立批准**、维护者名单公开且最少 2 人、单维护者状态为临时过渡；新增 [`.github/CODEOWNERS`](.github/CODEOWNERS) 把核心文件（`LICENSE` / `GOVERNANCE.md` / `contract.py` / 接口文档 / `action_spec.py`）路由到维护者评审。
- ✅ **护栏测试 + CI**：`tests/test_sustainability.py`（8 用例）守护许可证/反圈地/治理 Fork 抗性/CODEOWNERS/资金模型；`smoke.yml` 新增 "Sustainability guardrails" 步骤，CI 三版本（3.11/3.12/3.13）全跑。

**判定完成**：全套 **60 个测试通过**；许可证与反圈地条款被测试守护、Fork 抗性规则与 CODEOWNERS 已落地、资金模型含单一来源阈值护栏；项目能在无单一资助方、无单点关键人的情况下持续演进，且核心永不圈地。

---

## 不做什么（边界）

- 不造通用 AI 助手 / 不解决"意义""目的"问题。
- 不跟巨头在机器人能力上赛跑——我们做插槽与规则，不做更大的机器。
- 不假设"巨头必然作恶"作为唯一前提；公地的价值在"有选项"，不在"预言灾难"。
