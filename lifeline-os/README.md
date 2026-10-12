# Lifeline OS（编排层）

编排骨架：把符合 `docs/module-interface-v1.md` 的供给模块跑成闭环。

## 运行
```
python orchestrator.py
```

## 接入新模块
1. 在 `modules/<你的模块>/` 下实现接口（`name / provides / assess_needs / schedule / provide / status`）。
2. 在 `orchestrator.py` 的 `__main__` 里把 `FoodModule` 换成你的模块。
3. 跑起来，看闭环。

接口稳、实现随便换——这就是设计纪律。
