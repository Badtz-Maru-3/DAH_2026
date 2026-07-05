"""Thin dispatcher for simulation-bound attack replay adapters."""

from typing import Any

from agents.contracts import AttackAction
from agents.attack import adapter_a_cmdvel, adapter_b_state, adapter_c_mavlink


ADAPTERS = {
    "A": adapter_a_cmdvel,
    "B": adapter_b_state,
    "C": adapter_c_mavlink,
}


class ReplayAgent:
    def dispatch(self, action: AttackAction) -> dict[str, Any]:
        adapter = ADAPTERS.get(action.scenario_id)
        if adapter is None:
            return {
                "status": "blocked",
                "adapter": "none",
                "mode": action.mode,
                "detail": {"reason": f"unsupported scenario_id {action.scenario_id}"},
            }

        if action.mode == "live":
            return adapter.inject(action)
        return adapter.simulate(action)

