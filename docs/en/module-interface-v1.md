# Supply-Module Interface Standard v1 (Stable Contract · Executable Spec)

> Goal: **Implementations may change, but the interface must stay.** Today's simulated food module and tomorrow's embodied-AI farm must both conform to the same contract; the orchestration layer (`lifeline-os/orchestrator.py`) needs no changes.
>
> This file is the **single source of truth for the contract**. Any module that passes all checks in `lifeline-os/contract.py` is auto-discovered and plugged into the loop — no orchestration changes required.

---

## 1. Module Discovery Convention (auto-discovery, zero registration)

The orchestrator scans the `modules/<id>/` directory and requires:

1. Directory name = module `id` (lowercase ASCII, e.g. `food`, `shelter`).
2. The directory must contain `<id>_module.py`, which defines a PascalCase class `<Id>Module` (e.g. `FoodModule`).
3. That class implements all 6 methods below and they are all callable.
4. The directory must contain `module.toml` (manifest, see §4).

Failing any condition → the orchestrator prints the reason and **skips** the module (CI uses this to block contract-breaking commits).

---

## 2. Required Methods (exact signatures and return shapes)

| Method | Signature | Returns | Semantics |
|--------|----------|---------|-----------|
| `name()` | `name() -> str` | string, must equal manifest `id` | module identifier |
| `provides()` | `provides() -> list[str]` | non-empty string list, must equal manifest `provides` | need types this module satisfies |
| `assess_needs` | `assess_needs(context: dict) -> dict` | needs report (below) | sense what the community lacks and how much |
| `schedule` | `schedule(resources: dict, needs: dict) -> dict` | scheduling plan (below) | decide what to use and how to supply |
| `provide` | `provide(plan: dict) -> dict` | delivery report (below) | actually deliver and declare failure mode |
| `status` | `status() -> dict` | health dict (below) | current state for orchestrator monitoring |

### 2.1 `assess_needs(context)` return shape
```python
{
    "need_type": str,        # matches provides()[0], e.g. "shelter"
    "population": int,       # from context["population"], falling back to module's own config
    # ... domain-specific daily-demand numbers, e.g. daily_kwh / daily_meals / daily_l / persons_need
    "unit": str,             # human-readable unit
}
```

### 2.2 `schedule(resources, needs)` return shape
```python
{
    "strategy": str,          # currently fixed to "self-sufficiency" (no trading in this project)
    "priority": list[str],    # actually available resources (subset of resources["available"])
    # ... domain-specific target_* (the demand amount to satisfy)
    "asset_scale": float,     # must pass through resources.get("asset_scale", 1.0) (see §3)
}
```

### 2.3 `provide(plan)` return shape (**mandatory fields**)
```python
{
    "delivered_avg_coverage": float,   # mean coverage ∈ [0.0, 1.0], supply ÷ demand
    "full_days": int,                  # days with coverage ≥ 0.999
    "shortfall_days": int,             # days with coverage < 0.999
    "status": str,                     # "ok" or "partial"
    "fail_mode": str,                  # safe degradation when resources are insufficient (see §5)
    # ... domain-specific lowest-state quantities (e.g. min_soc_kwh / min_inventory / min_tank_l)
}
```
Also, `provide` must persist the run result so `status()` reflects it (the `_last` pattern).

### 2.4 `status()` return shape
```python
{
    "health": str,        # "nominal" (no shortfall) or "degraded" (has shortfall); consistent with shortfall_days
    # ... other monitoring quantities
}
```
**Consistency invariant**: after `provide`, if `shortfall_days > 0` then `status()["health"]` must be `"degraded"`; otherwise it must be `"nominal"`.

---

## 3. `asset_scale` Convention (supply-side scaling)

`asset_scale` (asset-scale factor) is the key quantity that lets the supply simulation **actually consume the owner's profile**:

- Meaning: the capacity the owner can actually build, relative to a "baseline community". **1.0 = capacity matching the baseline community**.
- It is computed by the upper layer (`lifeline.py`'s `compute_asset_scale`) from the profile (capital / land / strategy), then passed in via `resources["asset_scale"]`.
- **Every module's `schedule` must pass it through to `provide → _simulate`, and capacity (generation / yield / water storage / maintainable capacity) plus storage / inventory capacity must scale proportionally with it.**
- Demand side is scaled by `context["population"]` (`assess_needs` already scales daily demand by population).
- Default `asset_scale = 1.0` (when unspecified). The orchestrator standalone runs with default 1.0.

> A module that does not consume `asset_scale` will have coverage that doesn't vary with the profile — the checker treats that as suspicious (§6 stress test).

---

## 4. `context` Convention (demand side + profile pass-through)

`context` is a free-form dict, minimally containing:
```python
{
    "community": str,       # community identifier
    "population": int,      # population / household size (drives demand)
    # optional profile fields below, used by shelter-class modules:
    "has_land": bool,       # whether usable land is available
    "capital": int,         # startup capital 0-3
    "location": str,        # Urban / Suburb / Rural / Off-grid
}
```
Other modules ignore keys they don't understand (backward compatible). The upper layer `lifeline.py` passes the profile's `has_land/capital/location` into `context`.

---

## 5. Failure Modes (fail_mode)

Every module must declare how it **degrades safely** when resources are insufficient / faulty, e.g.:
- `degrade-to-stored`: draw down reserves first (battery / inventory / water tank)
- `request-help`: call for help from other modules / the community
- `graceful-stop`: stop without propagating the fault

This project has no trading / selling logic; shortfalls are only recorded, never "filled from an external market".

---

## 6. Consistency Invariants (the checker `contract.py` must verify)

A conforming module must pass these checks (see `lifeline-os/contract.py` for details):

1. **Structure**: all 6 methods callable; `name()` == manifest `id`; `provides()` list == manifest `provides` and non-empty.
2. **Behavior shape**: `assess → schedule → provide → status` runs without exceptions; `provide` returns all §2.3 mandatory fields; `status` contains `health`.
3. **Health consistency**: `status()["health"]` strictly matches `provide`'s `shortfall_days` (see §2.4).
4. **Anti-hardcode stress test**: under an extreme profile (population amplified, `asset_scale` pushed to 0.2, no land / no capital), `delivered_avg_coverage` **must be < 0.99**. Any module that always returns 100% ("fake full supply") fails outright — this project rejects fake data.
5. **Responsiveness**: coverage under a comfortable profile (land + high capital + small population + high asset factor) must be **strictly higher** than under an extreme profile (no land + zero capital + large population + low asset factor). Direction-safe, works for both flow resources and shelter; any module that ignores its inputs and returns a constant is caught.

---

## 7. Manifest (`module.toml`)

```toml
id = "shelter"            # must equal directory name and name() return
name = "Local shelter module"   # human-readable name
provides = ["shelter"]    # must equal provides() content
version = "0.1.0"         # module's own version
interface = "v1"          # interface major version followed
maintainer = "community"  # maintainer
```

---

## 8. Versioning Rules (v1 → v2 and beyond)

- **Add-only, backward compatible**: a new major version may add optional methods / fields, but must not remove or change the required semantics of existing methods.
- When breaking existing semantics, you must bump the major version (v1→v2) and keep a v1 compatibility layer for a while.
- The orchestrator selects the compatible path by the `interface` field.

---

## 9. How to Add a Module (checklist)

1. `modules/<id>/<id>_module.py` defines `<Id>Module`, implementing all methods in §2.
2. Write `module.toml` (§7) and `data/` sample data (so a clone reproduces immediately).
3. Run `python lifeline-os/contract.py modules/<id>` — must be all green.
4. Run `python lifeline-os/lifeline.py --profile examples/profiles/<your-profile>.json` to confirm it is auto-discovered and included in the freedom index.
5. Open a PR reviewed against the module-admission checklist in `GOVERNANCE.md`.

> The interface is this project's true durable asset. Implementations can be rewritten from scratch; the interface should stay put.

---

## 10. Action-Layer Extension (optional · Stage 6)

The supply loop (the 6 methods in §2) only answers "is there enough?". The **action layer** lets a module additionally emit *task-level* commands a humanoid robot can execute — translating the coverage report into "where to go, what to do, how to confirm". See [`docs/action-layer.md`](../action-layer.md).

### 10.1 Granularity principle (red line)

Actions must stop at the **task level**; never emit motion primitives. Core constraints:

- Commands must be task-level (`harvest / pump / inspect / serve / repair / request_help / seek_care / shed_load / draw` …).
- Forbidden: `move_to / navigate / walk / grasp / pick / place / rotate_joint` … — those are the robot's own motion-planning job.
- `make_action()` rejects blacklisted commands at construction; `tests/test_actions.py` guards this permanently.

### 10.2 Optional method signature

Add an **optional** method to `<Id>Module` (if absent, the orchestrator/contract safely skip — backward compatible):

```python
from action_spec import make_action

def actions(self, plan, context) -> list[dict]:
    """Return task-level actions. plan/context help derive parameters."""
    ...
```

### 10.3 Single-action shape

Each action is built by `action_spec.make_action()` and contains `id / domain / actor / command / target / params / frequency / priority / precondition / expected_effect / verify / note` (see `action_spec.REQUIRED_FIELDS`).

- `frequency`: `once` / `daily` / `weekly` / `on-demand`.
- `precondition` (empty = always met) / `expected_effect` (empty = monitor/verify only) / `verify` (empty = no verification) are **world-state expressions**:
  - comparison `eval_condition`: `water.tank_l < 2500`, `health.needs_care == True`.
  - assignment `apply_effect`: `food.inventory_meals += 40`, `energy.soc_kwh = 5`.
- World state is a flat metric dict (keys like `energy.soc_kwh`), filled by the robot's perception layer; `action_spec.default_operational_state()` provides a demo initial state.

### 10.4 Orchestration & execution

- Orchestrator `collect_action_plan(results)` gathers module actions → writes `last-action-plan.json` / `.md` (multilingual).
- Reference executor `executor.py` simulates duty on the world state: battery threshold → precondition gate → apply effect → deduct battery → verify; `expand_schedule()` spreads `daily/weekly/once` across a 30-day timeline, `on-demand` is event-triggered.

### 10.5 Versioning

Action-layer schema version: `action_spec.ACTION_SCHEMA_VERSION`. Same rule as §8: add-only, backward compatible; bump the major version on breaking changes.
