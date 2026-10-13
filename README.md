# Lifeline Commons

One line: **Not a project that races the giants to build a better robot — but an open "survival-supply protocol + one small, real community instance", serving the corners big companies can't be bothered with, so that the option of "not being tied to the giants" actually exists.**

> 🌐 This README is in **English** — the project's default language. **[中文版 / Chinese](README.zh.md)**

## Languages

The project's **tools and docs** are multilingual (currently: 中文 `zh`, English `en`, Español `es`); **English is the default** and Chinese is the fallback for any missing key.

- Run reports in another language: `python lifeline-os/lifeline.py --lang zh` (or `es`). See [`docs/i18n.md`](docs/i18n.md).
- Chinese version of this README: [`README.zh.md`](README.zh.md); English version of the interface spec: [`docs/en/module-interface-v1.md`](docs/en/module-interface-v1.md).
- Want to add a language? Follow [`docs/i18n.md`](docs/i18n.md) and add one key to the `CATALOG` in `lifeline-os/i18n.py` — any missing key falls back to Chinese automatically, so reports never go blank.

## What is this

- An open-source project. The goal: let ordinary people's most basic survival supplies (food, energy, shelter, health…) be held by their own community, instead of only obtainable from a handful of giants.
- We don't build a universal robot. We build a **protocol** (how modules interoperate, how communities govern) + **one runnable small instance**.

## Common misconceptions (read this first)

- ❌ "Once unemployed, Xiao A just buys a smart robot and that's enough to survive" — **false**. See [`docs/feasibility.md`](docs/feasibility.md): the fact that society *can* do something ≠ a purchasable robot will grow your food and generate your power for you ≠ it can be built and sold to you. A robot does convenience labor, not livelihood production; it doesn't close the loop and still needs money to maintain.
- ✅ What this project solves is a **livelihood commons** of "being supplied without needing income" — not a particular machine. The robot is only a cost-reduction tool inside it.

## How do I actually use this (3-step quickstart)

One sentence up front: **Lifeline Commons is not an app you double-click open, and it is not a robot.** It's an open-source toolkit that runs on your own computer — you hand it a "resource profile", and it figures out "can I survive on what I have, how, and where are the gaps", and it can also hand you a **task list a robot can just follow**.

Three scenarios for three kinds of people — read the one that fits you:

### Scenario A: I want to know "can I / my community survive on our own?"
1. Copy the sample profile closest to you: open `examples/profiles/` (`xiao_a_rural` rural-with-land Xiao A, `urban_landless_unemployed` urban landless unemployed, `urban_skilled_remote` urban skilled remote).
2. Run one command:
   ```bash
   python lifeline-os/lifeline.py --profile examples/profiles/xiao_a_rural.json
   ```
3. Read the report: it gives you a **recommended strategy** + **self-sufficiency coverage** for the five domains (food / energy / water / shelter / health) + a composite **survival-freedom index**, and **honestly flags the weak spots** (e.g. "health coverage is only 0.65, the bigger real-world gap").
   - Want your own real numbers? Swap the sample data under `modules/*/data/` for your community's real data, change the profile to yours, re-run.

### Scenario B: I want to give a robot a task list it can actually do (Stage 6 Action Layer)
1. Run:
   ```bash
   python lifeline-os/orchestrator.py --execute
   ```
2. It emits `lifeline-os/last-action-plan.json` — **17 task-level commands** (where to go, what to do, how to confirm), e.g. "if the water tank isn't full, pump to refill", "if inventory drops below threshold, harvest to resupply", "if equipment breaks, report for repair".
3. Hand this JSON to the robot's **onboard controller** to read (local file, LAN, USB stick — any of them). The robot only sees "tasks" — how to step, how to grasp, how to avoid obstacles is its own low-level controller's job. **This project never emits motion primitives**, so Unitree, Boston Dynamics, any vendor's robot can plug in.
   - ⚠️ Key point: **the robot does not touch git.** git is for developers collaborating. The real flow is — **you (the operator) generate the plan on your computer → hand the JSON to the robot**, not "let the robot clone the repo and pull the plan".

### Scenario C: I'm a developer who wants to add a supply module (e.g. "medical", "transport")
→ Follow `docs/en/module-interface-v1.md` to write a module with the 6 required methods, drop it in `modules/<your-domain>/`, run `python lifeline-os/contract.py` — all green means it's auto-discovered and plugged in.

## Three layers

```
Governance / Commons layer   rules · anti-enclosure · community decisions
Orchestration layer Lifeline OS   perceive → schedule → supply loop
Supply-module layer   food / energy / water / shelter / health … independent, pluggable, replaceable
```

## What's in the project (quick reference, read on demand)

> The three "how do I actually use this" sections above are enough to get started. The list below is an inventory — come back to it when writing code or contributing a module.

- `docs/module-interface-v1.md`: the **stable interface** every supply module must implement (implementations can change; the interface stays). This is the project's core durable asset and the carrier of the neutral protocol.
- `modules/food`, `modules/energy`, `modules/water`, `modules/shelter`, `modules/health`: **data-driven** reference implementations of food / energy / water / **shelter** / **basic health** (each a 30-day self-sufficiency simulation, computing coverage; pure self-sufficiency, no trading). `shelter` and `health` are extension templates proving "a pluggable module can be written from the interface doc alone".
- `lifeline-os`: the orchestration skeleton (**auto-discovery** of modules + interface-contract checks) that runs the modules and produces a **community self-sufficiency report** (see [`docs/example-report.md`](docs/example-report.md)). Reports are multilingual (`--lang`).
- `lifeline-os/contract.py`: the **protocol conformance checker** — any third party who finishes a module runs it; all green means the contract passes and the module can be auto-discovered and plugged in (checks structure / behavior / health consistency / anti-hardcoding / responsiveness).
- `lifeline-os/strategy_analyzer.py`: the **survival-strategy analyzer** — first analyze the owner's / community's resource profile, then recommend the best survival strategy (wasteland is only one strategy among many; the goal is the owner's survival-freedom). See [`docs/example-strategy-report.md`](docs/example-strategy-report.md).
- `lifeline-os/lifeline.py`: the **top-level closed loop** (recommended entry) — chaining "profile → strategy recommendation → profile-driven supply simulation → survival-freedom index" into one command, outputting a complete **survival-freedom report**. Wasteland is only one strategy. See [`docs/freedom-index.md`](docs/freedom-index.md).
- `ROADMAP.md`: the long-term roadmap (protocol layer + community-instance layer, staged and actionable).
- `docs/action-layer.md`: the **Action Layer (Stage 6)** — translates "is there enough" into **task-level commands** a humanoid robot can execute (where to go, what to do, how to confirm); granularity stops at the task level, never emits motion primitives.
- `CONTRIBUTING.md`: how to conform to the interface and contribute a new module.
- `GOVERNANCE.md`: **governance + module-admission checklist + scope red lines + anti-capture guardrails**.
- `docs/feasibility.md`: **feasibility analysis** — why "buy a robot ≠ self-sufficiency" (Xiao A unemployment scenario).
- `docs/blueprint.md`: **project blueprint** — turning scattered ideas into an actionable design (the Xiao A wasteland case stringing the four layers together).
- `docs/community-playbook.md`: **voluntary-community startup checklist** — turning the blueprint case into a replicable deployment playbook (with honest thresholds).
- `docs/floor-options.md`: **floor reflection** — is the wasteland plan the best floor? vs. cash floor / basic services.
- `docs/commercialization.md`: **commercialization boundaries** — public good first, core not enclosed, power trading explicitly excluded.
- `tests/`: **unit tests** (contract conformance + coverage self-consistency), guarding the interface from breakage.

## How to run

```
python lifeline-os/lifeline.py                                  # top-level loop: built-in Xiao A profile → survival-freedom report (recommended entry, Chinese)
python lifeline-os/lifeline.py --lang en                         # same report, English
python lifeline-os/lifeline.py --lang es                         # same report, Spanish
python lifeline-os/lifeline.py --profile examples/profiles/xiao_a_rural.json        # read a profile file
python lifeline-os/lifeline.py --profile your_profile.json --out report.md          # write to file
python lifeline-os/strategy_analyzer.py           # strategy analysis only
python lifeline-os/strategy_analyzer.py --lang en # English strategy report
python lifeline-os/orchestrator.py                # supply-layer loop only (auto-discovery + contract check) + community self-sufficiency report
python lifeline-os/orchestrator.py --lang en      # English community report
python lifeline-os/contract.py                     # protocol conformance check: all modules under modules/ (or pass a single dir)
python lifeline-os/i18n.py --check                 # check that en/es cover all Chinese keys
python lifeline-os/orchestrator.py --execute       # generate the robot action plan and run the reference executor (Stage 6)
python lifeline-os/executor.py --plan lifeline-os/last-action-plan.json   # run the reference executor standalone
python -m unittest discover -s tests -t . -v       # run unit tests (contract conformance + i18n + action layer)
```

`lifeline.py` outputs a **survival-freedom report** (profile + recommended strategies + per-domain simulation + freedom index), with `--lang` to switch language. Replace `modules/*/data/` with real data and `examples/profiles/*.json` with your profile, then re-run to get your own report.

Every push / PR automatically runs the loop **and** unit tests on Python 3.11/3.12/3.13 (see `.github/workflows/smoke.yml`).

## License

AGPL-3.0 (strong copyleft + anti-enclosure). See `LICENSE`.

---

Want to join? Start from `CONTRIBUTING.md` and a supply module you care about.
