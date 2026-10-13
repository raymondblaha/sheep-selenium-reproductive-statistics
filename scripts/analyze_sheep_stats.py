"""Analyze synthetic sheep selenium and reproductive outcome data."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, fisher_exact, kruskal
from scipy.stats import f as f_dist
from scipy.stats import mannwhitneyu


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data/sample")
    parser.add_argument("--output-dir", default="outputs/tables")
    return parser.parse_args()


def decision(p_value: float, alpha: float = 0.05) -> str:
    if not np.isfinite(p_value):
        return "NOT ESTIMABLE"
    return "REJECT H0" if p_value < alpha else "FAIL TO REJECT H0"


def safe_pvalue(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return np.nan


def ols_term_pvalues(dat: pd.DataFrame) -> dict[str, float]:
    """Fit a compact OLS model and return approximate term-level F-test p-values."""

    groups = sorted(dat["group"].dropna().unique())
    reference = groups[0]
    x_parts = [np.ones((len(dat), 1))]
    names = ["Intercept"]
    for group in groups:
        if group == reference:
            continue
        x_parts.append(dat["group"].eq(group).astype(float).to_numpy()[:, None])
        names.append(f"group:{group}")
    x_parts.append(dat["month_scaled"].to_numpy()[:, None])
    names.append("time")
    for group in groups:
        if group == reference:
            continue
        interaction = (
            dat["group"].eq(group).astype(float).to_numpy() * dat["month_scaled"].to_numpy()
        )
        x_parts.append(interaction[:, None])
        names.append(f"interaction:{group}")

    x_full = np.hstack(x_parts)
    y = dat["log_outcome"].to_numpy()
    beta, *_ = np.linalg.lstsq(x_full, y, rcond=None)
    resid = y - x_full @ beta
    sse_full = float(np.sum(resid**2))
    df_full = max(len(y) - np.linalg.matrix_rank(x_full), 1)

    def f_test(drop_prefixes: tuple[str, ...]) -> float:
        keep = [
            idx
            for idx, name in enumerate(names)
            if not any(name.startswith(prefix) for prefix in drop_prefixes)
        ]
        x_reduced = x_full[:, keep]
        beta_r, *_ = np.linalg.lstsq(x_reduced, y, rcond=None)
        resid_r = y - x_reduced @ beta_r
        sse_reduced = float(np.sum(resid_r**2))
        df_num = max(np.linalg.matrix_rank(x_full) - np.linalg.matrix_rank(x_reduced), 1)
        f_stat = ((sse_reduced - sse_full) / df_num) / (sse_full / df_full)
        return float(f_dist.sf(max(f_stat, 0), df_num, df_full))

    return {
        "group": f_test(("group:",)),
        "time": f_test(("time",)),
        "interaction": f_test(("interaction:",)),
    }


def fit_longitudinal(
    df: pd.DataFrame,
    *,
    study: str,
    outcome: str,
    label: str,
) -> list[dict[str, Any]]:
    dat = df[(df["study"] == study) & df[outcome].notna()].copy()
    dat["log_outcome"] = np.log(dat[outcome].clip(lower=1e-6))
    dat["month_scaled"] = (dat["month"] - dat["month"].mean()) / dat["month"].std()
    pvals = ols_term_pvalues(dat)
    group_p = safe_pvalue(pvals["group"])
    time_p = safe_pvalue(pvals["time"])
    interaction_p = safe_pvalue(pvals["interaction"])
    method = "portable fixed-effect OLS approximation on log outcome"

    return [
        {
            "study": study,
            "priority": "Primary",
            "analysis": f"{label} over time",
            "term": "Treatment group",
            "p_value": group_p,
            "decision": decision(group_p),
            "method": method,
            "interpretation": f"{label} concentrations differed among treatment groups."
            if group_p < 0.05
            else f"No statistically significant evidence that {label} differed by group.",
        },
        {
            "study": study,
            "priority": "Primary",
            "analysis": f"{label} over time",
            "term": "Time",
            "p_value": time_p,
            "decision": decision(time_p),
            "method": method,
            "interpretation": f"{label} changed over time."
            if time_p < 0.05
            else f"No statistically significant evidence that {label} changed over time.",
        },
        {
            "study": study,
            "priority": "Primary",
            "analysis": f"{label} over time",
            "term": "Treatment x time",
            "p_value": interaction_p,
            "decision": decision(interaction_p),
            "method": method,
            "interpretation": f"{label} trajectories differed by treatment over time."
            if interaction_p < 0.05
            else f"No statistically significant evidence that {label} trajectories differed by group.",
        },
    ]


def reproductive_summary(animals: pd.DataFrame) -> pd.DataFrame:
    grouped = animals.groupby(["study", "group"], sort=False)
    out = grouped.agg(
        n=("animal_id", "nunique"),
        repeat_breeding_n=("repeat_breeding", "sum"),
        one_cycle_n=("repeat_breeding", lambda x: int((x == 0).sum())),
        pregnant_n=("pregnant", "sum"),
        open_n=("pregnant", lambda x: int((x == 0).sum())),
        mean_breeding_cycles=("breeding_cycles", "mean"),
        median_breeding_cycles=("breeding_cycles", "median"),
        mean_baseline_weight_kg=("baseline_weight_kg", "mean"),
        sd_baseline_weight_kg=("baseline_weight_kg", "std"),
    ).reset_index()
    out["repeat_breeding_percent"] = 100 * out["repeat_breeding_n"] / out["n"]
    out["pregnancy_percent"] = 100 * out["pregnant_n"] / out["n"]
    return out


def global_binary_test(
    animals: pd.DataFrame,
    *,
    study: str,
    outcome: str,
    label: str,
) -> dict[str, Any]:
    dat = animals[animals["study"] == study].copy()
    table = pd.crosstab(dat["group"], dat[outcome])
    chi2, p_value, _, _ = chi2_contingency(table)
    return {
        "study": study,
        "priority": "Primary",
        "analysis": label,
        "term": "Treatment association",
        "p_value": float(p_value),
        "decision": decision(float(p_value)),
        "method": "chi-square test on treatment by binary outcome table",
        "interpretation": f"{label} differed among treatment groups."
        if p_value < 0.05
        else f"No statistically significant overall difference in {label.lower()} among groups.",
    }


def pairwise_vs_control(
    animals: pd.DataFrame,
    *,
    study: str,
    outcome: str,
) -> pd.DataFrame:
    dat = animals[animals["study"] == study].copy()
    rows = []
    control = dat[dat["group"] == "Control"]
    for group in sorted(g for g in dat["group"].unique() if g != "Control"):
        treated = dat[dat["group"] == group]
        table = [
            [int(control[outcome].sum()), int((control[outcome] == 0).sum())],
            [int(treated[outcome].sum()), int((treated[outcome] == 0).sum())],
        ]
        _, p_value = fisher_exact(table)
        rows.append({"study": study, "comparison": f"Control vs {group}", "outcome": outcome, "p_value": p_value})
    out = pd.DataFrame(rows).sort_values("p_value").reset_index(drop=True)
    if out.empty:
        return out
    out["p_holm"] = [min(1.0, p * (len(out) - i)) for i, p in enumerate(out["p_value"])]
    out["decision_raw"] = out["p_value"].map(decision)
    out["decision_holm"] = out["p_holm"].map(decision)
    return out.sort_values(["study", "outcome", "comparison"]).reset_index(drop=True)


def baseline_weight_tests(animals: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for study, dat in animals.groupby("study", sort=False):
        groups = [x["baseline_weight_kg"].dropna().to_numpy() for _, x in dat.groupby("group")]
        p_group = kruskal(*groups).pvalue if len(groups) > 1 else np.nan
        rows.append(
            {
                "study": study,
                "priority": "Primary",
                "analysis": "Baseline body weight",
                "term": "Treatment group",
                "p_value": float(p_group),
                "decision": decision(float(p_group)),
                "method": "Kruskal-Wallis test",
                "interpretation": "No statistically significant evidence that baseline weights differed by group."
                if p_group >= 0.05
                else "Baseline weights differed by group.",
            }
        )
        try:
            pregnant = dat.loc[dat["pregnant"].eq(1), "baseline_weight_kg"].dropna()
            open_ = dat.loc[dat["pregnant"].eq(0), "baseline_weight_kg"].dropna()
            p_weight = float(mannwhitneyu(pregnant, open_, alternative="two-sided").pvalue)
        except Exception:
            p_weight = np.nan
        rows.append(
            {
                "study": study,
                "priority": "Primary",
                "analysis": "Baseline body weight",
                "term": "Weight to pregnancy",
                "p_value": p_weight,
                "decision": decision(p_weight),
                "method": "Mann-Whitney U baseline-weight comparison by pregnancy status",
                "interpretation": "No statistically significant evidence that baseline weight explained pregnancy."
                if p_weight >= 0.05
                else "Baseline weight was associated with pregnancy outcome.",
            }
        )
    return rows


def make_report(tests: pd.DataFrame, output_dir: Path) -> None:
    lines = [
        "Sheep Selenium / Reproduction Statistical Report",
        "",
        "This report is generated from synthetic public-safe data.",
        "It mirrors the analysis structure of the original study but is not a biological result.",
        "",
        "Important design caveat:",
        "Treatment groups are represented as one pen per treatment in this public demo.",
        "If the original study also used one pen per treatment, pen and treatment are confounded.",
        "That means treatment effects should be interpreted cautiously because pen-level conditions",
        "cannot be separated statistically from treatment dose.",
        "",
        "Hypothesis test summary:",
    ]
    for row in tests.itertuples(index=False):
        lines.extend(
            [
                "",
                f"{row.study} - {row.analysis} - {row.term}",
                f"p-value: {row.p_value:.4g}" if np.isfinite(row.p_value) else "p-value: not estimable",
                f"decision: {row.decision}",
                f"method: {row.method}",
                f"interpretation: {row.interpretation}",
            ]
        )
    (output_dir / "statistical_report.txt").write_text("\n".join(lines) + "\n")


def main() -> None:
    args = parse_args()
    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    animals = pd.read_csv(data_dir / "synthetic_sheep_animals.csv")
    longitudinal = pd.read_csv(data_dir / "synthetic_sheep_longitudinal.csv")

    tests: list[dict[str, Any]] = []
    tests.extend(
        fit_longitudinal(
            longitudinal,
            study="Study 1",
            outcome="liver_se",
            label="Liver Se",
        )
    )
    tests.extend(
        fit_longitudinal(
            longitudinal,
            study="Study 1",
            outcome="whole_blood_se",
            label="Whole Blood Se",
        )
    )
    tests.extend(
        fit_longitudinal(
            longitudinal,
            study="Study 2",
            outcome="whole_blood_se",
            label="Whole Blood Se",
        )
    )
    for study in ["Study 1", "Study 2"]:
        tests.append(
            global_binary_test(
                animals,
                study=study,
                outcome="repeat_breeding",
                label="Repeat breeding",
            )
        )
        tests.append(
            global_binary_test(
                animals,
                study=study,
                outcome="pregnant",
                label="Final pregnancy",
            )
        )
    tests.extend(baseline_weight_tests(animals))

    tests_df = pd.DataFrame(tests)
    summary = reproductive_summary(animals)
    pairwise = pd.concat(
        [
            pairwise_vs_control(animals, study="Study 1", outcome="repeat_breeding"),
            pairwise_vs_control(animals, study="Study 1", outcome="pregnant"),
            pairwise_vs_control(animals, study="Study 2", outcome="repeat_breeding"),
            pairwise_vs_control(animals, study="Study 2", outcome="pregnant"),
        ],
        ignore_index=True,
    )

    tests_df.to_csv(output_dir / "hypothesis_tests.csv", index=False)
    summary.to_csv(output_dir / "reproductive_outcomes.csv", index=False)
    pairwise.to_csv(output_dir / "pairwise_control_contrasts.csv", index=False)
    make_report(tests_df, output_dir)
    print(f"Wrote analysis outputs to {output_dir}")


if __name__ == "__main__":
    main()
