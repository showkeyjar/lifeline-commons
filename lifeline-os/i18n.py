"""Lifeline OS —— 多语言支持 (i18n)。

设计原则
--------
- 所有**面向人**的字符串（报告标题、章节、表头、策略名、边界说明等）都集中在本
  文件的 CATALOG 里，按语言键组织。代码里只写 `t("some.key", **kw)`，不直接写文案。
- 支持的语言：``zh``（中文，源语言）、``en``（English）、``es``（Español）。
  新增语言只需在 CATALOG 里加一个键并补全所有字符串——缺失的键会回退到中文，
  不会让程序崩溃，也不会让报告出现空白。
- ``--check`` 模式可以自检：en / es 是否漏翻了任何中文键，方便 CI 与贡献者。

用法
----
    from i18n import set_language, t, get_language, SUPPORTED
    set_language("en")
    print(t("title.lifeline"))                 # Survival-Freedom Report (Lifeline OS)
    print(t("ff.compose", pct=80, top=70, qual=60))

CLI
---
    python lifeline-os/i18n.py --check         # 检查各语言是否补全
    python lifeline-os/i18n.py --list           # 列出支持的语言
"""

import sys

SUPPORTED = ("zh", "en", "es")
DEFAULT_LANG = "en"
_CURRENT = {"lang": DEFAULT_LANG}

# 源语言（zh）拥有全部键；en/es 必须覆盖同样的键集合（--check 会校验）。
CATALOG = {
    "zh": {
        # ---- 报告标题 ----
        "title.lifeline": "# 生存自由报告（Lifeline OS）",
        "title.strategy": "# 生存策略分析报告",
        "title.community": "# 社区自给评估报告",

        # ---- 副标题 ----
        "sub.lifeline": "> 画像 → 策略推荐 → 供给模拟 → 自由指数，一条闭环。荒地只是策略之一。",
        "sub.strategy": "> 由 Lifeline OS 策略分析器生成 —— 先分析画像，再决定路径。荒地只是策略之一。",
        "sub.community": "> 由 Lifeline OS 自动生成 —— 数据驱动 30 天模拟，纯自给视角，不含任何交易逻辑。",

        # ---- 章节 ----
        "sec.profile": "主人/社区画像",
        "sec.strategies": "推荐策略（按匹配度）",
        "sec.supply": "供给层 30 天自给模拟（按本画像）",
        "sec.freedom": "生存自由指数",
        "sec.honest": "诚实边界",
        "sec.domains": "各域自给率",
        "sec.verdict": "综合判断",

        # ---- 用户数据可选值（地点 / 健康）的翻译 ----
        "loc.乡村": "乡村",
        "loc.郊区": "郊区",
        "loc.城市": "城市",
        "loc.离网": "离网",
        "health.良好": "良好",
        "health.受限": "受限",

        # ---- 画像字段标签 ----
        "prof.has_land": "是否有地",
        "prof.capital": "启动资本（0-3）",
        "prof.skills": "技能",
        "prof.location": "所在地",
        "prof.household_full": "家庭/社区人数",
        "prof.household_short": "人数",
        "prof.health": "健康",
        "prof.mobility": "撤离能力",
        "prof.relocation": "迁移意愿",
        "prof.asset_scale": "资产规模系数（本项目推算）",
        "prof.asset_scale_note": "(1.0 = 持有与基准社区匹配的产能)",
        "prof.none": "无",
        "bool.true": "是",
        "bool.false": "否",

        # ---- 策略列表行 ----
        "r.match": "匹配",
        "r.recommended": " ← 首选",
        "r.exp_freedom": "预计生存自由度",

        # ---- 供给表头 ----
        "th.domain": "域",
        "th.demand": "日均需求",
        "th.coverage": "平均自给率",
        "th.full": "满供天数",
        "th.short": "缺口天数",
        "th.weak": "最弱日",
        "th.health": "健康",

        # ---- 域显示名 ----
        "dom.energy": "能源",
        "dom.food": "食物",
        "dom.water": "水",
        "dom.shelter": "住所",
        "dom.health": "健康",

        # ---- 单位 ----
        "unit.energy": "kWh/天",
        "unit.food": "餐/天",
        "unit.water": "L/天",
        "unit.people": "人",
        "unit.health": "人",
        "unit.shelter": "人",
        "unit.days": "天",

        # ---- 最弱日 ----
        "weak.day": "第 {d} 天 ({c})",

        # ---- 自由指数 ----
        "ff.score": "综合得分",
        "ff.tier": "分档",
        "ff.compose": "构成：供给覆盖均值 {pct}% × 策略权重 + 策略匹配 {top}/100 + 定性韧性 {qual}/100",

        # ---- 自由指数分档标签（freedom_index 返回键，此处翻译）----
        "fi.high_self": "高（基本退可守，不依赖市场工资）",
        "fi.high_income": "高（靠可携带收入/低生活成本，基本不依赖本地工资市场）",
        "fi.midhigh_self": "中高（大部分自主，仍需少量外部收入/缓冲）",
        "fi.midhigh_income": "中高（靠可携带收入，需持续接单/远程工作）",
        "fi.mid_self": "中（半自由，需持续外部收入补足缺口）",
        "fi.mid_income": "中（半自由，靠收入但缓冲薄，需持续外部收入）",
        "fi.low": "低（难独立，需外部托底或更多积累）",
        "fi.external": "依赖外部托底（非自主）",

        # ---- 诚实边界 ----
        "honest.external": "⚠️ 当前画像下，务实路径是**依赖外部托底**——无地、无资本、无可变现技能的人，本项目（社区自组织 + 自动化）帮不了。请优先争取政府现金底 / 基础服务。",
        "honest.tool": "本工具只「分析 + 模拟」，决策权与执行权留在主人与社区手里。",
        "honest.land": "若首选是「分布式自给」才需要走拿地/开荒；其他策略不涉及地。",
        "honest.sim": "模拟是一阶线性规划工具（产能/需求同比缩放），不是承诺；落地前请用你们社区的真实数据替换 `modules/*/data/`。",
        "honest.gov": "本项目是**自愿社区**的开源协调工具，不替代政府、不交付机器人、不解决人生意义。",

        # ---- 编排器元信息 ----
        "oc.community": "社区",
        "oc.population": "人口",
        "oc.period": "评估周期",
        "oc.domains": "覆盖域",
        "oc.avg": "平均自给率（各域均值）",

        # ---- 综合判断 ----
        "verdict.high": "✅ 基本退可守：多数域自给率在高位，仅个别弱日需本地缓冲或微调产能。",
        "verdict.mid": "⚠️ 部分退可守：存在结构性缺口，需扩容产能或补齐模块后再评估。",
        "verdict.low": "❌ 暂不可守：自给率偏低，当前配置不足以支撑该社区离网生存。",

        # ---- 社区报告边界 ----
        "cb1": "本报告只评估「物理供给自给率」，不涉及土地产权、启动资本、成员健康与组织力——这些是现实更大的一道坎。",
        "cb2": "本项目是**自愿社区**的开源协调工具，不替代政府的现金底 / 基础服务，也帮不了赤贫无地者。",
        "cb3": "把 `modules/*/data/` 下的样例换成你们社区的真实数据，重跑即可得到专属报告。",

        # ---- 策略（键 → 名 / 介入 / 自由度）----
        "strat.distributed.name": "分布式自给（荒地/集体土地自建）",
        "strat.distributed.intervention": "✅ 本项目介入：协调层 + 治理 + 数据驱动规划（energy/food/water 模块）",
        "strat.distributed.freedom": "高（若成功落地）",
        "strat.urban_collective.name": "城市社区协作（共享空间+分工+半市场）",
        "strat.urban_collective.intervention": "✅ 本项目介入：协调层（城市版模块）+ 治理",
        "strat.urban_collective.freedom": "中",
        "strat.semi_self.name": "半自给+基础缓冲（以降开销为主）",
        "strat.semi_self.intervention": "✅ 本项目介入：规划工具（算你能降多少开销/建多少缓冲）",
        "strat.semi_self.freedom": "中（降低对市场的依赖）",
        "strat.relocate.name": "低成本地区迁移（搬去生存成本极低的地区）",
        "strat.relocate.intervention": "⚠️ 本项目不介入执行，仅提供信息与规划辅助",
        "strat.relocate.freedom": "中高",
        "strat.skill_buffer.name": "技能变现+小缓冲（手艺/远程工作覆盖开销+建缓冲）",
        "strat.skill_buffer.intervention": "❌ 本项目不介入，主人自行；可规划缓冲目标",
        "strat.skill_buffer.freedom": "中高",
        "strat.external_floor.name": "依赖外部托底（政府/慈善）",
        "strat.external_floor.intervention": "❌ 本项目帮不了——这类人只能靠政府现金底/基础服务",
        "strat.external_floor.freedom": "取决于公共政策",

        # ---- 控制台日志（编排器）----
        "oc.loading": "加载模块",
        "oc.provides": "provides",
        "oc.step1": "1) 感知需求",
        "oc.step2": "2) 调度资源",
        "oc.step3": "3) 供给交付",
        "oc.state": "状态",
        "oc.done": "闭环完成 ✓",
        "oc.found": "发现 {n} 个供给模块",
        "oc.no_modules": "未发现任何供给模块，退出。",
        "oc.report_written": "报告已写入",
        "oc.skip_import": "跳过模块 {entry}：导入失败 ({err})",
        "oc.skip_class": "跳过模块 {entry}：未找到 {cls} 类",
        "oc.skip_contract": "跳过模块 {entry}：接口契约缺失 {missing}",

        # ---- 动作层（Stage 6，人形机器人任务级指令）----
        "title.action": "# 机器人动作计划（Action Plan）",
        "sub.action": "> 把「够不够」翻译成人形机器人可执行的任务指令：去哪（target）、干什么（command）、干完怎么确认（verify）。粒度停在任务级——绝不下发 move_to / grasp 等运动原语。",
        "sec.action.list": "动作清单",
        "sec.action.gate": "前置条件与验收",
        "th.aid": "动作 ID",
        "th.adomain": "域",
        "th.aactor": "执行者",
        "th.acommand": "指令",
        "th.atarget": "目标",
        "th.afreq": "频率",
        "th.aprio": "优先级",
        "th.apre": "前置条件",
        "th.aeffect": "预期效果",
        "th.averify": "验收",
        "freq.once": "单次",
        "freq.daily": "每日",
        "freq.weekly": "每周",
        "freq.ondemand": "按需",
        "prio.high": "高",
        "prio.medium": "中",
        "prio.low": "低",
        "actor.robot": "机器人",
        "actor.community": "社区",
        "actor.human": "人",
        "action.gate1": "前置条件（precondition）：不满足条件则机器人跳过该动作，不浪费电量。",
        "action.gate2": "预期效果（expected_effect）：执行后施加到世界状态的状态表达式；空串表示仅监测/验收，不改状态。",
        "action.gate3": "验收（verify）：执行后必须满足的校验条件；不满足记为「验收失败」。",
        "oc.action_plan_written": "动作计划已写入",
        "oc.action_execute": "执行机器人动作计划",
        "oc.action_exec_summary": "执行汇总",
        "oc.action_ok": "成功",
        "oc.action_skip": "跳过",
        "oc.action_failed": "验收失败",
        "oc.action_skip_module": "跳过模块 {entry} 的动作收集（出错: {err}）",

        # ---- 控制台日志（闭环 lifeline）----
        "lf.written": "报告已写入",

        # ---- i18n 自检信息 ----
        "check.ok": "✅ 多语言键完整：{lang} 覆盖全部 {n} 个键。",
        "check.missing": "❌ 语言 {lang} 缺失 {m} 个键：{keys}",
        "list.supported": "支持的语言：{langs}",

        # ---- 建设轨迹模拟（情景轨迹）----
        "sec.trajectory": "建设轨迹模拟（12 个月）",
        "traj.intro": "> 从今天的地板出发，按真实建设时序建起装备，自给率逐月爬升。能源/水建设周期短（数周），当月即计入；**食物需等一季收获**，种植后约第 6 个月才开始计入并三阶爬坡。",
        "traj.today": "当下（第 0 月）",
        "traj.month": "第 {m} 月",
        "traj.th_energy": "能源",
        "traj.th_food": "食物",
        "traj.th_water": "水",
        "traj.th_avg": "平均自给率",
        "traj.th_freedom": "自由指数",
        "traj.food_lag": "⚠️ 食物滞后：第 1–5 月为生长期（不产粮），第 6–8 月三阶爬坡（0.3/0.6/1.0），第 9 月起满产。",
        "traj.assumption": "假设：建设由 IT 远程收入资助（契合 skill_buffer 60），时序为保守估计；落地请以你的真实进度替换。",
        "cmp.title": "多实例对比 · 建设轨迹",
        "cmp.intro": "把同一家庭、不同起点的实例叠在一起：起点越高（已备装备 / 资本更足），曲线从第一天就站上更高台阶；但无论起点，食物生长季都是共同的长周期瓶颈。",
        "cmp.col_instance": "实例",
        "cmp.col_t0": "第 0 月（起点）",
        "cmp.col_final": "第 12 月",
        "cmp.col_fi": "末月自由指数",
        "cmp.col_m80": "达 80% 月数",
        "cmp.never": "—",
        "cmp.spark_title": "12 个月自给率轨迹（火花线，左=第 0 月，右=第 12 月）：",
        "cmp.detail_title": "逐月对比（百分比 + 自给率条形）：",
        "cmp.month": "月份",
        "cmp.today": "今日",
        "cmp.narr_gap": "第 0 月起点：{min0}% → {max0}%（差距 {gap} 个百分点）。",
        "cmp.narr_conv": "无论起点如何，所有实例约第 {m80} 月前后越过 80% 自给——食物生长季是共同的长周期瓶颈。",
        "cmp.narr_hope": "希望：即便从最低的 {min0}% 起步，{months} 个月也能爬到 {minfinal}%；起点更高的实例第一天就站在 {max0}% 之上，全程更不易在最脆弱的建设早期暴露。",
        "traj.climb": "若走完这座桥，第 12 月平均自给率可达 **{avg}%**，生存自由指数可达 **{fi}**（对比今天 {t0}%）。",
    },

    "en": {
        "title.lifeline": "# Survival-Freedom Report (Lifeline OS)",
        "title.strategy": "# Survival-Strategy Analysis Report",
        "title.community": "# Community Self-Sufficiency Report",

        "sub.lifeline": "> Profile → strategy recommendation → supply simulation → freedom index, one closed loop. Wasteland is only one strategy among many.",
        "sub.strategy": "> Generated by the Lifeline OS strategy analyzer —— analyze the profile first, then decide the path. Wasteland is only one option.",
        "sub.community": "> Auto-generated by Lifeline OS —— data-driven 30-day simulation, pure self-sufficiency view, no trading logic whatsoever.",

        "sec.profile": "Owner / Community Profile",
        "sec.strategies": "Recommended Strategies (by fit)",
        "sec.supply": "Supply Layer — 30-Day Self-Sufficiency Simulation (for this profile)",
        "sec.freedom": "Survival-Freedom Index",
        "sec.honest": "Honest Boundaries",
        "sec.domains": "Self-Sufficiency by Domain",
        "sec.verdict": "Overall Verdict",

        "loc.乡村": "Rural",
        "loc.郊区": "Suburb",
        "loc.城市": "Urban",
        "loc.离网": "Off-grid",
        "health.良好": "Good",
        "health.受限": "Limited",

        "prof.has_land": "Land available",
        "prof.capital": "Startup capital (0-3)",
        "prof.skills": "Skills",
        "prof.location": "Location",
        "prof.household_full": "Household / community size",
        "prof.household_short": "People",
        "prof.health": "Health",
        "prof.mobility": "Evacuation capability",
        "prof.relocation": "Willing to relocate",
        "prof.asset_scale": "Asset-scale factor (estimated by this project)",
        "prof.asset_scale_note": "(1.0 = capacity matching the baseline community)",
        "prof.none": "none",
        "bool.true": "yes",
        "bool.false": "no",

        "r.match": "fit",
        "r.recommended": " ← recommended",
        "r.exp_freedom": "Expected survival-freedom",

        "th.domain": "Domain",
        "th.demand": "Daily demand",
        "th.coverage": "Avg. self-suff.",
        "th.full": "Full-supply days",
        "th.short": "Shortfall days",
        "th.weak": "Weakest day",
        "th.health": "Health",

        "dom.energy": "Energy",
        "dom.food": "Food",
        "dom.water": "Water",
        "dom.shelter": "Shelter",
        "dom.health": "Health",

        "unit.energy": "kWh/day",
        "unit.food": "meals/day",
        "unit.water": "L/day",
        "unit.people": "people",
        "unit.health": "people",
        "unit.shelter": "people",
        "unit.days": "days",

        "weak.day": "Day {d} ({c})",

        "ff.score": "Overall score",
        "ff.tier": "Tier",
        "ff.compose": "Composition: mean supply coverage {pct}% × strategy weight + strategy fit {top}/100 + qualitative resilience {qual}/100",

        "fi.high_self": "High (can hold the line; no dependence on wage market)",
        "fi.high_income": "High (portable income / low cost of living; barely depends on local wage market)",
        "fi.midhigh_self": "Medium-high (largely autonomous; still needs a little external income / buffer)",
        "fi.midhigh_income": "Medium-high (portable income; needs steady gigs / remote work)",
        "fi.mid_self": "Medium (semi-free; needs steady external income to cover gaps)",
        "fi.mid_income": "Medium (semi-free; income-based with thin buffer; needs steady external income)",
        "fi.low": "Low (hard to be independent; needs external floor or more savings)",
        "fi.external": "Dependent on external floor (not autonomous)",

        "honest.external": "⚠️ For this profile the realistic path is **relying on an external floor** —— people with no land, no capital and no marketable skill cannot be helped by this project (community self-organization + automation). Prioritize a government cash floor / basic services.",
        "honest.tool": "This tool only analyzes and simulates; the right to decide and to act stays with the owner and the community.",
        "honest.land": "Only if the top strategy is 'distributed self-sufficiency' do you need to acquire/develop land; other strategies do not involve land.",
        "honest.sim": "The simulation is a first-order linear tool (capacity/demand scaled proportionally), not a promise; before deployment, replace `modules/*/data/` with your community's real data.",
        "honest.gov": "This project is an open-source coordination tool for **voluntary communities**; it does not replace government, does not deliver robots, and does not solve life's meaning.",

        "oc.community": "Community",
        "oc.population": "Population",
        "oc.period": "Assessment period",
        "oc.domains": "Covered domains",
        "oc.avg": "Avg. self-sufficiency (mean of domains)",

        "verdict.high": "✅ Can largely hold the line: most domains are high; only a few weak days need local buffering or minor capacity tuning.",
        "verdict.mid": "⚠️ Partially defensible: structural gaps exist; expand capacity or fill missing modules before re-assessing.",
        "verdict.low": "❌ Not yet defensible: self-sufficiency is too low for this community to survive off-grid with the current setup.",

        "cb1": "This report only assesses physical supply self-sufficiency; it does not cover land tenure, startup capital, members' health, or organizing capacity — those are the bigger real-world hurdles.",
        "cb2": "This project is an open-source coordination tool for voluntary communities; it does not replace the government's cash floor / basic services, nor can it help the landless destitute.",
        "cb3": "Replace the samples under `modules/*/data/` with your community's real data and re-run to get your own report.",

        "strat.distributed.name": "Distributed self-sufficiency (wasteland / collective land)",
        "strat.distributed.intervention": "✅ In scope: coordination layer + governance + data-driven planning (energy/food/water modules)",
        "strat.distributed.freedom": "High (if implemented)",
        "strat.urban_collective.name": "Urban community collaboration (shared space + division of labor + semi-market)",
        "strat.urban_collective.intervention": "✅ In scope: coordination layer (urban modules) + governance",
        "strat.urban_collective.freedom": "Medium",
        "strat.semi_self.name": "Semi-self-sufficiency + basic buffer (mainly cost reduction)",
        "strat.semi_self.intervention": "✅ In scope: planning tool (estimate cost reduction / buffer you can build)",
        "strat.semi_self.freedom": "Medium (reduces market dependence)",
        "strat.relocate.name": "Relocate to low-cost area (move where living cost is minimal)",
        "strat.relocate.intervention": "⚠️ Out of scope for execution; only information & planning aid",
        "strat.relocate.freedom": "Medium-high",
        "strat.skill_buffer.name": "Monetize skills + small buffer (craft / remote work covers costs + builds buffer)",
        "strat.skill_buffer.intervention": "❌ Out of scope; owner acts on their own; buffer targets can be planned",
        "strat.skill_buffer.freedom": "Medium-high",
        "strat.external_floor.name": "Rely on external floor (government / charity)",
        "strat.external_floor.intervention": "❌ This project cannot help — these people need a government cash floor / basic services",
        "strat.external_floor.freedom": "Depends on public policy",

        "oc.loading": "Loading module",
        "oc.provides": "provides",
        "oc.step1": "1) Assess needs",
        "oc.step2": "2) Schedule resources",
        "oc.step3": "3) Deliver supply",
        "oc.state": "Status",
        "oc.done": "Loop complete ✓",
        "oc.found": "Discovered {n} supply modules",
        "oc.no_modules": "No supply modules found; exiting.",
        "oc.report_written": "Report written to",
        "oc.skip_import": "Skipping module {entry}: import failed ({err})",
        "oc.skip_class": "Skipping module {entry}: class {cls} not found",
        "oc.skip_contract": "Skipping module {entry}: interface contract missing {missing}",

        # ---- Action Layer (Stage 6, humanoid-robot task-level commands) ----
        "title.action": "# Robot Action Plan (Action Layer)",
        "sub.action": "> Translates \"is there enough\" into task-level commands a humanoid robot can execute: where to go (target), what to do (command), how to confirm done (verify). Granularity stops at the task level — never emit motion primitives like move_to / grasp.",
        "sec.action.list": "Action list",
        "sec.action.gate": "Preconditions & verification",
        "th.aid": "Action ID",
        "th.adomain": "Domain",
        "th.aactor": "Actor",
        "th.acommand": "Command",
        "th.atarget": "Target",
        "th.afreq": "Frequency",
        "th.aprio": "Priority",
        "th.apre": "Precondition",
        "th.aeffect": "Expected effect",
        "th.averify": "Verify",
        "freq.once": "once",
        "freq.daily": "daily",
        "freq.weekly": "weekly",
        "freq.ondemand": "on-demand",
        "prio.high": "high",
        "prio.medium": "medium",
        "prio.low": "low",
        "actor.robot": "robot",
        "actor.community": "community",
        "actor.human": "human",
        "action.gate1": "Precondition: if not met, the robot skips the action (no wasted battery).",
        "action.gate2": "Expected effect: a state expression applied after execution; empty means monitor/verify only (no state change).",
        "action.gate3": "Verify: a condition that must hold after execution; otherwise the action is marked \"verify failed\".",
        "oc.action_plan_written": "Action plan written to",
        "oc.action_execute": "Executing robot action plan",
        "oc.action_exec_summary": "Execution summary",
        "oc.action_ok": "ok",
        "oc.action_skip": "skipped",
        "oc.action_failed": "failed",
        "oc.action_skip_module": "Skipped action collection for module {entry} (error: {err})",

        "lf.written": "Report written to",

        "check.ok": "✅ i18n keys complete: {lang} covers all {n} keys.",
        "check.missing": "❌ Language {lang} missing {m} keys: {keys}",
        "list.supported": "Supported languages: {langs}",

        # ---- Build trajectory simulation (scenario trajectory) ----
        "sec.trajectory": "Build Trajectory Simulation (12 months)",
        "traj.intro": "> Starting from today's floor, assets are built up on a realistic construction timeline; self-sufficiency climbs month by month. Energy/water have short build cycles (weeks) and count from the month built; **food must wait for a harvest season** — it starts counting ~month 6 after planting and ramps in three steps.",
        "traj.today": "Today (month 0)",
        "traj.month": "Month {m}",
        "traj.th_energy": "Energy",
        "traj.th_food": "Food",
        "traj.th_water": "Water",
        "traj.th_avg": "Avg self-suff.",
        "traj.th_freedom": "Freedom",
        "traj.food_lag": "⚠️ Food lag: months 1–5 are the growing season (no harvest); months 6–8 ramp in three steps (0.3/0.6/1.0); full yield from month 9.",
        "traj.assumption": "Assumption: construction is funded by IT remote income (consistent with skill_buffer 60); timeline is conservative — replace with your real progress when deploying.",
        "cmp.title": "Multi-Instance Comparison · Build Trajectory",
        "cmp.intro": "Overlay instances of the same household but different starting points: the higher the start (equipment already owned / more capital), the higher the curve from day one; yet regardless of start, the food-growing season is the shared long-pole bottleneck.",
        "cmp.col_instance": "Instance",
        "cmp.col_t0": "Month 0 (start)",
        "cmp.col_final": "Month 12",
        "cmp.col_fi": "Final freedom index",
        "cmp.col_m80": "Months to 80%",
        "cmp.never": "—",
        "cmp.spark_title": "12-month self-sufficiency trajectory (sparkline, left = month 0, right = month 12):",
        "cmp.detail_title": "Month-by-month comparison (percentage + coverage bar):",
        "cmp.month": "Month",
        "cmp.today": "Today",
        "cmp.narr_gap": "Month-0 start: {min0}% → {max0}% (a {gap}-point gap).",
        "cmp.narr_conv": "Regardless of start, every instance crosses 80% self-sufficiency around month {m80} — the food-growing season is the shared long pole.",
        "cmp.narr_hope": "The hope: even starting from the lowest {min0}%, you can climb to {minfinal}% within {months} months; the higher-start instance stands above {max0}% from day one and is far less exposed during the most fragile early build phase.",
        "traj.climb": "If you walk this bridge, by month 12 average self-sufficiency reaches **{avg}%** and the survival-freedom index reaches **{fi}** (vs {t0}% today).",
    },

    "es": {
        "title.lifeline": "# Informe de Libertad de Supervivencia (Lifeline OS)",
        "title.strategy": "# Informe de Análisis de Estrategia de Supervivencia",
        "title.community": "# Informe de Autosuficiencia Comunitaria",

        "sub.lifeline": "> Perfil → recomendación de estrategia → simulación de suministro → índice de libertad, un ciclo cerrado. Las tierras baldías son solo una estrategia entre muchas.",
        "sub.strategy": "> Generado por el analizador de estrategias de Lifeline OS —— analice el perfil primero, luego decida la ruta. Las tierras baldías son solo una opción.",
        "sub.community": "> Generado automáticamente por Lifeline OS —— simulación de 30 días basada en datos, visión de pura autosuficiencia, sin ninguna lógica de comercio.",

        "sec.profile": "Perfil del propietario / comunidad",
        "sec.strategies": "Estrategias recomendadas (por adecuación)",
        "sec.supply": "Capa de suministro — simulación de autosuficiencia de 30 días (para este perfil)",
        "sec.freedom": "Índice de Libertad de Supervivencia",
        "sec.honest": "Límites honestos",
        "sec.domains": "Autosuficiencia por dominio",
        "sec.verdict": "Veredicto general",

        "loc.乡村": "Rural",
        "loc.郊区": "Periurbano",
        "loc.城市": "Urbano",
        "loc.离网": "Fuera de red",
        "health.良好": "Buena",
        "health.受限": "Limitada",

        "prof.has_land": "¿Tierra disponible?",
        "prof.capital": "Capital inicial (0-3)",
        "prof.skills": "Habilidades",
        "prof.location": "Ubicación",
        "prof.household_full": "Tamaño del hogar / comunidad",
        "prof.household_short": "Personas",
        "prof.health": "Salud",
        "prof.mobility": "Capacidad de evacuación",
        "prof.relocation": "Dispuesto a reubicarse",
        "prof.asset_scale": "Factor de escala de activos (estimado por este proyecto)",
        "prof.asset_scale_note": "(1.0 = capacidad que coincide con la comunidad de referencia)",
        "prof.none": "ninguna",
        "bool.true": "sí",
        "bool.false": "no",

        "r.match": "adecuación",
        "r.recommended": " ← recomendada",
        "r.exp_freedom": "Libertad de supervivencia esperada",

        "th.domain": "Dominio",
        "th.demand": "Demanda diaria",
        "th.coverage": "Autosuf. media",
        "th.full": "Días de suministro completo",
        "th.short": "Días de déficit",
        "th.weak": "Día más débil",
        "th.health": "Salud",

        "dom.energy": "Energía",
        "dom.food": "Alimentos",
        "dom.water": "Agua",
        "dom.shelter": "Vivienda",
        "dom.health": "Salud",

        "unit.energy": "kWh/día",
        "unit.food": "comidas/día",
        "unit.water": "L/día",
        "unit.people": "personas",
        "unit.health": "personas",
        "unit.shelter": "personas",
        "unit.days": "días",

        "weak.day": "Día {d} ({c})",

        "ff.score": "Puntuación global",
        "ff.tier": "Nivel",
        "ff.compose": "Composición: cobertura media de suministro {pct}% × peso de estrategia + adecuación {top}/100 + resiliencia cualitativa {qual}/100",

        "fi.high_self": "Alta (puede mantener la línea; sin depender del mercado salarial)",
        "fi.high_income": "Alta (ingresos portables / bajo costo de vida; apenas depende del mercado salarial local)",
        "fi.midhigh_self": "Media-alta (en gran parte autónoma; aún necesita algo de ingreso externo / amortiguación)",
        "fi.midhigh_income": "Media-alta (ingresos portables; necesita encargos / teletrabajo constantes)",
        "fi.mid_self": "Media (semi-libre; necesita ingreso externo constante para cubrir déficits)",
        "fi.mid_income": "Media (semi-libre; basada en ingresos con amortiguación débil; necesita ingreso externo constante)",
        "fi.low": "Baja (difícil de ser independiente; necesita red de apoyo externa o más ahorro)",
        "fi.external": "Dependiente de red de apoyo externa (no autónoma)",

        "honest.external": "⚠️ Para este perfil la ruta realista es **depender de una red de apoyo externa** —— quienes no tienen tierra, ni capital, ni habilidades monetizables no pueden ser ayudados por este proyecto (autoorganización comunitaria + automatización). Priorice un piso de efectivo del gobierno / servicios básicos.",
        "honest.tool": "Esta herramienta solo analiza y simula; el derecho a decidir y a actuar queda en el propietario y la comunidad.",
        "honest.land": "Solo si la estrategia principal es 'autosuficiencia distribuida' necesita adquirir/desarrollar tierra; las demás estrategias no involucran tierra.",
        "honest.sim": "La simulación es una herramienta lineal de primer orden (capacidad/demanda escaladas proporcionalmente), no una promesa; antes de desplegar, reemplace `modules/*/data/` con los datos reales de su comunidad.",
        "honest.gov": "Este proyecto es una herramienta de coordinación de código abierto para **comunidades voluntarias**; no reemplaza al gobierno, no entrega robots y no resuelve el sentido de la vida.",

        "oc.community": "Comunidad",
        "oc.population": "Población",
        "oc.period": "Período de evaluación",
        "oc.domains": "Dominios cubiertos",
        "oc.avg": "Autosuficiencia media (promedio de dominios)",

        "verdict.high": "✅ Puede mantener la línea en gran medida: la mayoría de los dominios están altos; solo algunos días débiles necesitan amortiguación local o ajuste menor de capacidad.",
        "verdict.mid": "⚠️ Parcialmente defendible: existen déficits estructurales; expanda la capacidad o complete módulos antes de reevaluar.",
        "verdict.low": "❌ Aún no defendible: la autosuficiencia es demasiado baja para que esta comunidad sobreviva fuera de la red con la configuración actual.",

        "cb1": "Este informe solo evalúa la autosuficiencia de suministro físico; no cubre la tenencia de tierra, el capital inicial, la salud de los miembros ni la capacidad de organización — esos son los obstáculos mayores en el mundo real.",
        "cb2": "Este proyecto es una herramienta de coordinación de código abierto para comunidades voluntarias; no reemplaza el piso de efectivo / servicios básicos del gobierno, ni puede ayudar a los indefensos sin tierra.",
        "cb3": "Reemplace las muestras en `modules/*/data/` con los datos reales de su comunidad y vuelva a ejecutar para obtener su propio informe.",

        "strat.distributed.name": "Autosuficiencia distribuida (tierras baldías / comunales)",
        "strat.distributed.intervention": "✅ En alcance: capa de coordinación + gobernanza + planificación basada en datos (módulos energy/food/water)",
        "strat.distributed.freedom": "Alta (si se implementa)",
        "strat.urban_collective.name": "Colaboración comunitaria urbana (espacio compartido + división del trabajo + semi-mercado)",
        "strat.urban_collective.intervention": "✅ En alcance: capa de coordinación (módulos urbanos) + gobernanza",
        "strat.urban_collective.freedom": "Media",
        "strat.semi_self.name": "Semi-autosuficiencia + amortiguación básica (reducción de costos)",
        "strat.semi_self.intervention": "✅ En alcance: herramienta de planificación (calcula reducción de costos / amortiguación)",
        "strat.semi_self.freedom": "Media (reduce la dependencia del mercado)",
        "strat.relocate.name": "Reubicación a zona de bajo costo (mudarse donde el costo de vida es mínimo)",
        "strat.relocate.intervention": "⚠️ Fuera de alcance de ejecución; solo información y ayuda de planificación",
        "strat.relocate.freedom": "Media-alta",
        "strat.skill_buffer.name": "Monetizar habilidades + pequeña amortiguación (artesanía / teletrabajo cubre costos)",
        "strat.skill_buffer.intervention": "❌ Fuera de alcance; el propietario actúa por su cuenta; se pueden planificar metas de amortiguación",
        "strat.skill_buffer.freedom": "Media-alta",
        "strat.external_floor.name": "Depender de red de apoyo externa (gobierno / caridad)",
        "strat.external_floor.intervention": "❌ Este proyecto no puede ayudar — estas personas necesitan un piso de efectivo del gobierno / servicios básicos",
        "strat.external_floor.freedom": "Depende de la política pública",

        "oc.loading": "Cargando módulo",
        "oc.provides": "proporciona",
        "oc.step1": "1) Evaluar necesidades",
        "oc.step2": "2) Programar recursos",
        "oc.step3": "3) Entregar suministro",
        "oc.state": "Estado",
        "oc.done": "Ciclo completo ✓",
        "oc.found": "Descubiertos {n} módulos de suministro",
        "oc.no_modules": "No se encontraron módulos de suministro; saliendo.",
        "oc.report_written": "Informe escrito en",
        "oc.skip_import": "Omitiendo módulo {entry}: fallo de importación ({err})",
        "oc.skip_class": "Omitiendo módulo {entry}: clase {cls} no encontrada",
        "oc.skip_contract": "Omitiendo módulo {entry}: contrato de interfaz faltante {missing}",

        # ---- Capa de acción (Etapa 6, comandos de nivel de tarea para robot humanoide) ----
        "title.action": "# Plan de Acción del Robot (Capa de Acción)",
        "sub.action": "> Traduce \"¿hay suficiente\" en comandos de nivel de tarea que un robot humanoide puede ejecutar: a dónde ir (target), qué hacer (command), cómo confirmar (verify). La granularidad se detiene en el nivel de tarea — nunca emitir primitivas de movimiento como move_to / grasp.",
        "sec.action.list": "Lista de acciones",
        "sec.action.gate": "Precondiciones y verificación",
        "th.aid": "ID de acción",
        "th.adomain": "Dominio",
        "th.aactor": "Actor",
        "th.acommand": "Comando",
        "th.atarget": "Objetivo",
        "th.afreq": "Frecuencia",
        "th.aprio": "Prioridad",
        "th.apre": "Precondición",
        "th.aeffect": "Efecto esperado",
        "th.averify": "Verificar",
        "freq.once": "una vez",
        "freq.daily": "diario",
        "freq.weekly": "semanal",
        "freq.ondemand": "bajo demanda",
        "prio.high": "alta",
        "prio.medium": "media",
        "prio.low": "baja",
        "actor.robot": "robot",
        "actor.community": "comunidad",
        "actor.human": "humano",
        "action.gate1": "Precondición: si no se cumple, el robot omite la acción (no gasta batería).",
        "action.gate2": "Efecto esperado: expresión de estado aplicada tras ejecutar; vacío significa solo monitorear/verificar (sin cambio de estado).",
        "action.gate3": "Verificar: condición que debe cumplirse tras ejecutar; de lo contrario la acción se marca \"verificación fallida\".",
        "oc.action_plan_written": "Plan de acción escrito en",
        "oc.action_execute": "Ejecutando plan de acción del robot",
        "oc.action_exec_summary": "Resumen de ejecución",
        "oc.action_ok": "ok",
        "oc.action_skip": "omitida",
        "oc.action_failed": "fallida",
        "oc.action_skip_module": "Omitida la recolección de acciones del módulo {entry} (error: {err})",

        "lf.written": "Informe escrito en",

        "check.ok": "✅ Claves i18n completas: {lang} cubre las {n} claves.",
        "check.missing": "❌ Idioma {lang} omite {m} claves: {keys}",
        "list.supported": "Idiomas soportados: {langs}",

        # ---- Simulación de trayectoria de construcción (escenario) ----
        "sec.trajectory": "Simulación de Trayectoria de Construcción (12 meses)",
        "traj.intro": "> Partiendo del piso de hoy, los activos se construyen según una línea de tiempo realista; la autosuficiencia sube mes a mes. Energía/agua tienen ciclos cortos (semanas) y cuentan desde el mes construido; **la comida debe esperar una temporada de cosecha** — empieza a contar ~mes 6 tras la siembra y sube en tres pasos.",
        "traj.today": "Hoy (mes 0)",
        "traj.month": "Mes {m}",
        "traj.th_energy": "Energía",
        "traj.th_food": "Comida",
        "traj.th_water": "Agua",
        "traj.th_avg": "Autosuf. prom.",
        "traj.th_freedom": "Libertad",
        "traj.food_lag": "⚠️ Retraso de comida: meses 1–5 son de crecimiento (sin cosecha); meses 6–8 suben en tres pasos (0.3/0.6/1.0); cosecha plena desde mes 9.",
        "traj.assumption": "Supuesto: la construcción la financia el ingreso remoto de IT (coherente con skill_buffer 60); línea de tiempo conservadora — reemplázala con tu progreso real al desplegar.",
        "cmp.title": "Comparación Multi-Instancia · Trayectoria de Construcción",
        "cmp.intro": "Superpone instancias del mismo hogar pero con puntos de partida distintos: cuanto más alto el inicio (equipo ya adquirido / más capital), más alta la curva desde el día uno; sin embargo, cualquiera que sea el inicio, la temporada de cultivo es el cuello de botella compartido.",
        "cmp.col_instance": "Instancia",
        "cmp.col_t0": "Mes 0 (inicio)",
        "cmp.col_final": "Mes 12",
        "cmp.col_fi": "Índice final de libertad",
        "cmp.col_m80": "Meses hasta 80%",
        "cmp.never": "—",
        "cmp.spark_title": "Trayectoria de autosuficiencia a 12 meses (línea de chispas, izq = mes 0, der = mes 12):",
        "cmp.detail_title": "Comparación mes a mes (porcentaje + barra de cobertura):",
        "cmp.month": "Mes",
        "cmp.today": "Hoy",
        "cmp.narr_gap": "Inicio mes 0: {min0}% → {max0}% (brecha de {gap} puntos).",
        "cmp.narr_conv": "Cualquiera que sea el inicio, toda instancia cruza 80% de autosuficiencia cerca del mes {m80} — la temporada de cultivo es el cuello de botella compartido.",
        "cmp.narr_hope": "La esperanza: incluso partiendo del {min0}% más bajo, puedes subir a {minfinal}% en {months} meses; la instancia de inicio más alto se sitúa por encima del {max0}% desde el día uno y queda mucho menos expuesta durante la frágil fase inicial de construcción.",
        "traj.climb": "Si recorres este puente, en el mes 12 la autosuficiencia promedio alcanza **{avg}%** y el índice de libertad de supervivencia alcanza **{fi}** (vs {t0}% hoy).",
    },
}


def set_language(lang):
    """设置当前语言。未知语言回退到默认（zh），不抛异常。"""
    if lang in CATALOG:
        _CURRENT["lang"] = lang
    else:
        _CURRENT["lang"] = DEFAULT_LANG


def get_language():
    return _CURRENT["lang"]


def t(key, **kwargs):
    """取当前语言的翻译；缺失则回退中文；中文也缺失则返回键本身（便于发现漏翻）。"""
    lang = _CURRENT["lang"]
    entry = CATALOG.get(lang, CATALOG[DEFAULT_LANG]).get(key)
    if entry is None:
        entry = CATALOG[DEFAULT_LANG].get(key, key)
    if kwargs:
        try:
            return entry.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return entry
    return entry


def _check_langs():
    """校验每种非源语言是否覆盖了源语言（zh）的全部键。返回 (ok, report)。"""
    src = CATALOG[DEFAULT_LANG]
    src_keys = sorted(src.keys())
    problems = {}
    for lang in SUPPORTED:
        if lang == DEFAULT_LANG:
            continue
        missing = [k for k in src_keys if k not in CATALOG.get(lang, {})]
        if missing:
            problems[lang] = missing
    ok = not problems
    return ok, problems, len(src_keys)


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if "--list" in argv:
        print(t("list.supported", langs=", ".join(SUPPORTED)))
        return 0
    if "--check" in argv:
        ok, problems, n = _check_langs()
        if ok:
            for lang in SUPPORTED:
                if lang == DEFAULT_LANG:
                    continue
                print(t("check.ok", lang=lang, n=n))
            print(f"All {len(SUPPORTED)} languages OK.")
            return 0
        for lang, keys in problems.items():
            print(t("check.missing", lang=lang, m=len(keys), keys=", ".join(keys)))
        return 1
    print(t("list.supported", langs=", ".join(SUPPORTED)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
