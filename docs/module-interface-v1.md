# 供给模块接口标准 v1（稳定契约）

目标：**实现可以换，接口必须留住。** 今天的模拟食物模块、未来的具身 AI 农场，都要 conform 到同一个契约，这样编排层不用改。

一个供给模块必须暴露：

| 方法 | 输入 | 输出 | 说明 |
|------|------|------|------|
| `name()` | — | 字符串 | 模块标识，如 `"food"` |
| `provides()` | — | 需求类型列表 | 如 `["nutrition"]` |
| `assess_needs(context)` | 社区上下文 | 需求报告 | 感知这个社区缺什么、缺多少 |
| `schedule(resources, needs)` | 可用资源 + 需求 | 调度计划 | 决定用什么、怎么供 |
| `provide(plan)` | 调度计划 | 交付报告 | 真正交付，并声明失败模式 |
| `status()` | — | 健康字典 | 当前状态，供编排层监控 |

## 失败模式（fail_mode）
每个模块必须声明它在资源不足/故障时如何**安全降级**，例如：
- `degrade-to-stored`：优先动用储备
- `request-help`：向其他模块/社区求援
- `graceful-stop`：停下但不扩散故障

## 元信息（manifest）
模块根目录放 `module.toml`：
```toml
id = "food"
name = "本地食物模块"
provides = ["nutrition"]
version = "0.1.0"
interface = "v1"
maintainer = "community"
```

> 接口是本项目真正的持久资产。实现可以推倒重来，接口尽量不动。
