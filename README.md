# 生命线公地 · Lifeline Commons

一句话：**不做跟巨头比谁机器人更强的项目，而是做一套开放的"生存供给协议 + 一个小而真的社区实例"，专门服务大公司懒得管的角落——让"不绑定巨头"这个选项真实存在。**

## 语言 / Languages

本项目的**工具与文档**支持多语言（当前：中文 `zh`、English `en`、Español `es`）：

- 运行报告可切换语言：`python lifeline-os/lifeline.py --lang en`（或 `es`）。详见 [`docs/i18n.md`](docs/i18n.md)。
- 本文档的英文版：[`README.en.md`](README.en.md)；接口规范的英文版：[`docs/en/module-interface-v1.md`](docs/en/module-interface-v1.md)。
- 想新增一种语言？照 [`docs/i18n.md`](docs/i18n.md) 在 `lifeline-os/i18n.py` 的 `CATALOG` 里加一个键即可——缺失键会自动回退中文，不会让报告开天窗。

## 这是个啥
- 开源项目。目标是让普通人最基本的生存供给（食物、能源、住所、健康…）能被社区自己掌握，而不是只能从少数巨头手里拿。
- 我们不造万能机器人。我们造**协议**（模块怎么互操作、社区怎么治理）+ **一个跑得起来的小实例**。

## 常见误区（先看这个）
- ❌ "小A失业后买台智能机器人就足够活下去" —— **不成立**。详见 [`docs/feasibility.md`](docs/feasibility.md)：社会的技术"做得到" ≠ 一台可购买的机器人会替你种粮发电 ≠ 它能被造出来并卖给你。机器人做的是便利劳动，不是生计生产；它不开闭环，仍要钱养。
- ✅ 本项目要解决的，是"无需收入也能被供给"的**生计公地**，不是某台机器。机器人只是里面降本的工具。

## 你到底怎么用（三步上手）

先把一句话说死：**Lifeline Commons 不是一个能双击打开的 App，也不是一台机器人。** 它是一个跑在你自己电脑上的开源工具包——你给它一份"资源画像"，它帮你算清"靠你手里的资源能不能活、怎么活、差在哪"，并且能顺手生成一份**机器人照着干就行的活儿清单**。

下面三个场景对应三种人，挑跟你相关的看：

### 场景 A：我想知道"我 / 我的社区能不能靠自己活下去"
1. 抄一份最接近你的画像：打开 `examples/profiles/`（里面有 `xiao_a_rural` 乡村有地小A、`urban_landless_unemployed` 城市无地失业、`urban_skilled_remote` 城市有技能远程三个样例）。
2. 跑一条命令：
   ```bash
   python lifeline-os/lifeline.py --profile examples/profiles/xiao_a_rural.json
   ```
3. 读报告：它会给你**推荐策略** + 食物/能源/水/住所/健康五个域的**自给覆盖率** + 一个综合的"生存自由指数"，并**诚实标出短板**（比如"健康覆盖只有 0.65，是现实更大的短板"）。
   - 想算你自己的真实账？把 `modules/*/data/` 下的样例数据换成你社区的真实数据，再把画像换成你的，重跑即可。

### 场景 B：我想给机器人一份能干的活儿清单（Stage 6 动作层）
1. 跑：
   ```bash
   python lifeline-os/orchestrator.py --execute
   ```
2. 它吐出 `lifeline-os/last-action-plan.json`——**17 条任务级指令**（去哪、干什么、干完怎么确认），例如"水罐不满就抽水补满""库存低于阈值就收割补给""设备坏了就报修"。
3. 这份 JSON 交给机器人的**机载控制器**去读（本地文件、内网、U 盘都行）。机器人只认"任务"——怎么迈腿、怎么抓握、怎么避障是它自己底层控制器的事。**本项目绝不下发运动原语**，所以宇树、波士顿动力、任何厂家的机器人都能接。
   - ⚠️ 划重点：**机器人不访问 git。** git 是给开发者协作用的。真实流程是——**你（运营者）在电脑上生成计划 → 把 JSON 交给机器人**，而不是让机器人自己去 clone 仓库、拉计划。

### 场景 C：我是开发者，想加一个供给模块（比如"医疗""交通"）
→ 照 `docs/module-interface-v1.md` 写一个满足 6 个方法的模块，丢进 `modules/<你的域>/`，跑 `python lifeline-os/contract.py` 全绿，就被自动发现、自动接入了。

## 三层结构
```
治理 / 公地层   规则 · 反圈地 · 社区决策
编排层 Lifeline OS   感知 → 调度 → 供给 的闭环
供给模块层   食物 / 能源 / 水 / 住所 / 健康 …… 各自独立、可插拔、可替换
```

## 项目里有什么（速览，按需查阅，不是必读）

> 上面三段"你到底怎么用"已经够上手了。下面是物件清单，写代码或贡献模块时再回来查。

- `docs/module-interface-v1.md`：供给模块必须实现的**稳定接口**（实现可以换，接口留住）。这是项目的核心持久资产，也是中立协议的载体
- `modules/food`、`modules/energy`、`modules/water`、`modules/shelter`、`modules/health`：食物 / 能源 / 水 / **住所** / **基础健康**模块的**数据驱动**参考实现（各 30 天自给模拟，算覆盖率，纯自给不交易）。`shelter` 与 `health` 都是"仅凭接口文档就能写出可插拔模块"的扩展样板
- `lifeline-os`：编排骨架（**自动发现**模块 + 接口契约校验），把模块跑起来，并生成**社区自给评估报告**（见 [`docs/example-report.md`](docs/example-report.md)）。报告支持多语言（`--lang`）
- `lifeline-os/contract.py`：**协议一致性校验器**——任何第三方写完模块，跑它全绿即通过契约、可被自动发现接入（查结构 / 行为 / health 一致性 / 防硬编码 / 响应性）
- `lifeline-os/strategy_analyzer.py`：**生存策略分析器**——先分析主人/社区资源画像，推荐最佳生存策略（荒地只是策略之一，目标是让主人实现生存自由）。见 [`docs/example-strategy-report.md`](docs/example-strategy-report.md)
- `lifeline-os/lifeline.py`：**顶层闭环**（推荐入口）——把"画像 → 策略推荐 → 按画像跑供给模拟 → 生存自由指数"串成一条命令，输出一份完整的**生存自由报告**。荒地只是策略之一。见 [`docs/freedom-index.md`](docs/freedom-index.md)
- `ROADMAP.md`：项目长期路线（协议层 + 社区实例层，分阶段、可落地）
- `docs/action-layer.md`：**动作层（Stage 6）**——把"够不够"翻译成人形机器人可执行的**任务级指令**（去哪、干什么、怎么确认），粒度停在任务级、绝不下发运动原语
- `CONTRIBUTING.md`：怎么 conform 到接口贡献一个新模块
- `GOVERNANCE.md`：**治理 + 模块准入评审清单 + 范围红线 + 抗捕获护栏**
- `docs/feasibility.md`：**可行性分析**——为什么"买台机器人≠自给自足"（小A失业场景）
- `docs/blueprint.md`：**项目蓝图**——把零散设想整理成可落地设计（小A荒地案例串起四层）
- `docs/community-playbook.md`：**自愿社区启动清单**——把蓝图案例变成可复制部署剧本（含诚实门槛）
- `docs/floor-options.md`：**托底反思**——荒地方案是最优托底吗？与现金底/基础服务的对比
- `docs/commercialization.md`：**商业化边界**——公益优先、核心不圈地、明确排除电力交易
- `tests/`：**单元测试**（契约合规 + 覆盖率自洽），守护接口不被破坏

## 怎么跑
```
python lifeline-os/lifeline.py                                  # 顶层闭环：内置小A画像 → 生存自由报告（推荐入口，中文）
python lifeline-os/lifeline.py --lang en                         # 同一报告，英文
python lifeline-os/lifeline.py --lang es                         # 同一报告，西班牙文
python lifeline-os/lifeline.py --profile examples/profiles/xiao_a_rural.json        # 读画像文件
python lifeline-os/lifeline.py --profile your_profile.json --out report.md          # 写文件
python lifeline-os/strategy_analyzer.py           # 只跑策略分析（想单独看策略推荐时用）
python lifeline-os/strategy_analyzer.py --lang en # 英文策略报告
python lifeline-os/orchestrator.py                # 只跑供给层闭环（自动发现 + 契约校验）+ 社区自给评估报告
python lifeline-os/orchestrator.py --lang en      # 英文社区报告
python lifeline-os/contract.py                     # 协议一致性校验：校验 modules/ 下全部模块（或传单个目录）
python lifeline-os/i18n.py --check                 # 检查 en/es 是否补全了全部中文键
python lifeline-os/orchestrator.py --execute       # 生成机器人动作计划并跑参考执行器（Stage 6）
python lifeline-os/executor.py --plan lifeline-os/last-action-plan.json   # 单独跑参考执行器
python -m unittest discover -s tests -t . -v       # 跑单元测试（契约一致性 + 多语言 + 动作层）
```
`lifeline.py` 跑完会输出一份**生存自由报告**（画像 + 推荐策略 + 各域自给模拟 + 自由指数），可用 `--lang` 切换语言。把 `modules/*/data/` 换成真实数据、把 `examples/profiles/*.json` 换成你的画像再跑，即得专属报告。
每次 push / PR 会自动在 Python 3.11/3.12/3.13 上跑闭环 **和** 单元测试（见 `.github/workflows/smoke.yml`）。

## 许可证
AGPL-3.0（强 copyleft + 反圈地）。详见 `LICENSE`。

---
想参与？从 `CONTRIBUTING.md` 和一个你关心的供给模块开始。
