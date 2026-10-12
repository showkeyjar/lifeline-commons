# 如何贡献一个供给模块

本项目只要求一件事：**新模块 conform 到稳定接口，不要改编排层。**

## 1. 在 `modules/` 下新建目录

```
modules/<你的模块id>/
├── <id>_module.py     # 必须：定义 <Id>Module 类
├── module.toml        # 推荐：模块元信息
└── README.md          # 推荐：说明与未来替换方向
```

例如 `modules/water/water_module.py` + `WaterModule` 类。

## 2. 实现这 6 个方法（详见 docs/module-interface-v1.md）

| 方法 | 作用 |
|------|------|
| `name()` | 返回模块 id 字符串 |
| `provides()` | 返回它能满足的需求类型列表 |
| `assess_needs(context)` | 感知社区缺什么、缺多少 |
| `schedule(resources, needs)` | 决定用什么、怎么供 |
| `provide(plan)` | 真正交付，并声明 `fail_mode` |
| `status()` | 返回健康字典，供编排层监控 |

## 3. 必须声明失败模式（fail_mode）

资源不足/故障时如何**安全降级**，例如：
`degrade-to-stored`（动用储备）/ `request-help`（求援）/ `graceful-stop`（停下不扩散）。

## 4. 跑通闭环

```
python lifeline-os/orchestrator.py
```

编排器会自动发现 `modules/` 下所有模块并逐个跑闭环，**不需要手动登记**。
提交 PR 前请确认闭环无报错。

## 约定

- 实现可以推倒重来，**接口尽量不动**——接口是本项目真正的持久资产。
- 薄参考实现（模拟）完全 OK，重点是 conform 到接口；真实数据/硬件后续替换。
- 保持 AGPL-3.0 + 反圈地条款，别引入会重新私有化生存基建的依赖。
