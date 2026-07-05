"""Scenario C replay adapter wrapping existing MAVLink test tools."""

import hashlib
import subprocess
import sys
from pathlib import Path
from typing import Any

from agents.contracts import AttackAction, AnomalySignal


ADAPTER_NAME = "adapter_c_mavlink"
REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "Bridge" / "tools"
SCRIPT_PATHS = {
    "mission": (TOOLS_DIR / "send_mission_upload.py").resolve(),
    "gps": (TOOLS_DIR / "send_gps_input.py").resolve(),
    "manual": (TOOLS_DIR / "send_manual_control.py").resolve(),
}
DEFAULT_TIMEOUT_S = 10.0


def result(status: str, action: AttackAction, detail: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": status,
        "adapter": ADAPTER_NAME,
        "mode": action.mode,
        "detail": detail,
    }


def make_signal_id(
    run_id: str,
    round_id: int,
    signal_type: str,
    observed_at: str,
) -> str:
    raw = f"{run_id}:{round_id}:{ADAPTER_NAME}:{signal_type}:{observed_at}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def signal_dict(signal: AnomalySignal) -> dict[str, Any]:
    return signal.to_dict()


def simulate(action: AttackAction) -> dict[str, Any]:
    params = action.parameters
    observed_at = str(params.get("observed_at", params.get("fresh_after", "")))
    fresh_after = str(params.get("fresh_after", observed_at))
    mission = AnomalySignal(
        signal_id=make_signal_id(action.run_id, action.round_id, "mission_rejected", observed_at),
        run_id=action.run_id,
        round_id=action.round_id,
        scenario_id="C",
        source_agent=ADAPTER_NAME,
        surface="mission",
        signal_type="mission_rejected",
        severity="high",
        observed_value={"event": "synthetic_mission_audit_result", "reason": "dry-run rejected mission"},
        expected="accepted",
        observed_at=observed_at,
        evidence_refs=[
            {"source": ADAPTER_NAME, "kind": "synthetic", "surface": "mission", "ts": observed_at}
        ],
        fresh_after=fresh_after,
        confidence=1.0,
    )
    gnss = AnomalySignal(
        signal_id=make_signal_id(action.run_id, action.round_id, "spoof_jump", observed_at),
        run_id=action.run_id,
        round_id=action.round_id,
        scenario_id="C",
        source_agent=ADAPTER_NAME,
        surface="gnss",
        signal_type="spoof_jump",
        severity="high",
        observed_value={"event": "synthetic_gnss_integrity_result", "reasons": ["position residual dry-run"]},
        expected="within GNSS integrity limits",
        observed_at=observed_at,
        evidence_refs=[
            {"source": ADAPTER_NAME, "kind": "synthetic", "surface": "gnss", "ts": observed_at}
        ],
        fresh_after=fresh_after,
        confidence=1.0,
    )
    return result("simulated", action, {"signals": [signal_dict(mission), signal_dict(gnss)]})


def safe_script(name: str) -> Path:
    script = SCRIPT_PATHS[name]
    if not script.exists() or script.parent != TOOLS_DIR.resolve():
        raise FileNotFoundError(str(script))
    return script


def run_tool(name: str, args: list[str], timeout_s: float) -> dict[str, Any]:
    script = safe_script(name)
    completed = subprocess.run(
        [sys.executable, str(script), *args],
        cwd=str(REPO_ROOT),
        text=True,
        capture_output=True,
        timeout=timeout_s,
        shell=False,
        check=False,
    )
    return {
        "tool": name,
        "script": str(script),
        "returncode": completed.returncode,
        "stdout": completed.stdout[-1000:],
        "stderr": completed.stderr[-1000:],
    }


def inject(action: AttackAction) -> dict[str, Any]:
    if action.mode != "live" or not action.confirm_live_testbed_only:
        return result(
            "blocked",
            action,
            {"reason": "live injection requires --live --confirm-live-testbed-only"},
        )

    params = action.parameters
    port = str(int(params.get("port", 14551)))
    timeout_s = float(params.get("timeout_s", DEFAULT_TIMEOUT_S))
    mission_case = str(params.get("mission_case", "malicious_jump"))
    gps_case = str(params.get("gps_case", "spoof_jump"))
    manual_mode = str(params.get("manual_mode", "forward"))
    manual_duration = str(float(params.get("manual_duration", 0.5)))
    manual_rate = str(float(params.get("manual_rate", 2.0)))

    allowed_mission = {"normal", "malicious_far", "malicious_jump"}
    allowed_gps = {"normal", "spoof_jump", "poor_fix"}
    allowed_manual = {"forward", "turn", "stop"}
    if mission_case not in allowed_mission or gps_case not in allowed_gps or manual_mode not in allowed_manual:
        return result("blocked", action, {"reason": "adapter C parameter outside allowlist"})

    try:
        outputs = [
            run_tool("mission", [mission_case, "--port", port], timeout_s),
            run_tool("gps", [gps_case, "--port", port], timeout_s),
            run_tool(
                "manual",
                [manual_mode, "--port", port, "--duration", manual_duration, "--rate", manual_rate],
                timeout_s,
            ),
        ]
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return result("unavailable", action, {"reason": "Bridge tool unavailable or timed out", "error": str(exc)})

    status = "injected" if all(item["returncode"] == 0 for item in outputs) else "unavailable"
    return result(status, action, {"port": int(port), "tools": outputs})

