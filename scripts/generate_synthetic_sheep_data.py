"""Generate public-safe synthetic sheep selenium and reproduction data."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


STUDY1_GROUPS = {"Control": 3, "10 ppm": 5, "30 ppm": 4, "60 ppm": 5}
STUDY2_GROUPS = {"Control": 10, "10 ppm": 10, "30 ppm": 10}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="data/sample")
    parser.add_argument("--random-state", type=int, default=42)
    return parser.parse_args()


def group_dose(group: str) -> int:
    if group == "Control":
        return 0
    return int(group.split()[0])


def build_animals(rng: np.random.Generator) -> pd.DataFrame:
    rows = []

    study1_outcomes = {
        "Control": [(1, 1), (1, 1), (1, 1)],
        "10 ppm": [(1, 1), (1, 1), (2, 1), (1, 0), (1, 0)],
        "30 ppm": [(2, 0), (2, 0), (3, 0), (4, 0)],
        "60 ppm": [(1, 1), (2, 0), (2, 0), (3, 0), (4, 0)],
    }
    for group, n in STUDY1_GROUPS.items():
        for i in range(n):
            animal_id = f"S1_{group.replace(' ', '').replace('ppm', 'PPM')}_{i + 1:02d}"
            cycles, pregnant = study1_outcomes[group][i]
            rows.append(
                {
                    "study": "Study 1",
                    "animal_id": animal_id,
                    "group": group,
                    "dose_ppm": group_dose(group),
                    "pen": f"S1_pen_{group.replace(' ', '_')}",
                    "baseline_weight_kg": rng.normal(68 + 0.04 * group_dose(group), 11),
                    "breeding_cycles": cycles,
                    "repeat_breeding": int(cycles > 1),
                    "pregnant": pregnant,
                }
            )

    study2_outcomes = {
        "Control": [1] * 10,
        "10 ppm": [1] * 9 + [0],
        "30 ppm": [1] * 6 + [0] * 4,
    }
    study2_cycles = {
        "Control": [1] * 10,
        "10 ppm": [1, 1, 1, 1, 1, 2, 2, 2, 3, 3],
        "30 ppm": [1, 1, 1, 1, 1, 1, 2, 2, 3, 4],
    }
    for group, n in STUDY2_GROUPS.items():
        for i in range(n):
            animal_id = f"S2_{group.replace(' ', '').replace('ppm', 'PPM')}_{i + 1:02d}"
            cycles = study2_cycles[group][i]
            pregnant = study2_outcomes[group][i]
            rows.append(
                {
                    "study": "Study 2",
                    "animal_id": animal_id,
                    "group": group,
                    "dose_ppm": group_dose(group),
                    "pen": f"S2_pen_{group.replace(' ', '_')}",
                    "baseline_weight_kg": rng.normal(72 + 0.05 * group_dose(group), 23),
                    "breeding_cycles": cycles,
                    "repeat_breeding": int(cycles > 1),
                    "pregnant": pregnant,
                }
            )

    return pd.DataFrame(rows)


def se_curve(month: int, dose_ppm: int, rng: np.random.Generator, matrix: str) -> float:
    if matrix == "whole_blood":
        base = 0.12
        peak = 0.018 * dose_ppm
        decay = np.exp(-0.18 * max(month - 3, 0))
        trend = base + peak * min(month, 3) / 3 * decay
        return float(max(0.02, rng.lognormal(np.log(trend), 0.18)))

    base = 0.45
    peak = 0.07 * dose_ppm
    decay = np.exp(-0.25 * max(month - 3, 0))
    trend = base + peak * min(month, 3) / 3 * decay
    return float(max(0.05, rng.lognormal(np.log(trend), 0.22)))


def build_longitudinal(animals: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    for row in animals.itertuples(index=False):
        months = range(1, 16) if row.study == "Study 1" else [0, 1, 2, 3, 4, 6, 8, 10]
        for month in months:
            whole_blood = se_curve(month=max(month, 1), dose_ppm=row.dose_ppm, rng=rng, matrix="whole_blood")
            liver = np.nan
            if row.study == "Study 1":
                liver = se_curve(month=month, dose_ppm=row.dose_ppm, rng=rng, matrix="liver")
            weight_gain = 0.45 * month + 0.03 * row.dose_ppm * np.sin(month / 2)
            rows.append(
                {
                    "study": row.study,
                    "animal_id": row.animal_id,
                    "group": row.group,
                    "dose_ppm": row.dose_ppm,
                    "pen": row.pen,
                    "month": month,
                    "whole_blood_se": whole_blood,
                    "liver_se": liver,
                    "body_weight_kg": row.baseline_weight_kg + weight_gain + rng.normal(0, 2.5),
                    "pregnant": row.pregnant,
                    "repeat_breeding": row.repeat_breeding,
                    "breeding_cycles": row.breeding_cycles,
                }
            )
    return pd.DataFrame(rows)


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(args.random_state)

    animals = build_animals(rng)
    longitudinal = build_longitudinal(animals, rng)
    animals.to_csv(output_dir / "synthetic_sheep_animals.csv", index=False)
    longitudinal.to_csv(output_dir / "synthetic_sheep_longitudinal.csv", index=False)
    print(f"Wrote {output_dir / 'synthetic_sheep_animals.csv'}")
    print(f"Wrote {output_dir / 'synthetic_sheep_longitudinal.csv'}")


if __name__ == "__main__":
    main()
