"""Print a proposed budget from a saved public rate snapshot."""

import json
from pathlib import Path


def estimate() -> dict:
    rates = json.loads(Path("data/pricing.json").read_text())["pricing"]
    input_rate, output_rate = float(rates["prompt"]), float(rates["completion"])
    typical = 12000 * input_rate + 2000 * output_rate
    target_limit = 15 * (12000 * input_rate + 1200 * output_rate)
    rows = {}
    for name, targets, proposals, cap in (
        ("pilot", 45, 1, 6),
        ("full", 285, 6, 35),
    ):
        rows[name] = {
            "target_attempts_max": targets,
            "optimizer_calls_max": proposals,
            "assumed_typical_usd": round((targets + proposals) * typical, 4),
            "planning_upper_usd": round(
                3 * (targets * target_limit + proposals * typical), 4
            ),
            "proposed_spend_cap_usd": cap,
        }
    return {
        "source": "https://openrouter.ai/api/v1/models",
        "snapshot_date": "2026-10-02",
        "input_usd_per_million": input_rate * 1000000,
        "output_usd_per_million": output_rate * 1000000,
        "steps": rows,
        "warning": "Planning assumptions, not measured usage or authorization.",
    }


if __name__ == "__main__":
    print(json.dumps(estimate(), indent=2))
