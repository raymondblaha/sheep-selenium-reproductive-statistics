"""Streamlit dashboard for sheep selenium and reproduction statistics."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = ROOT / "data" / "sample"
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "tables"


@st.cache_data
def load_csv(path: str) -> pd.DataFrame | None:
    p = Path(path)
    if not p.exists():
        return None
    return pd.read_csv(p)


def design_caveat() -> None:
    st.warning(
        "Design caveat: this project explicitly tracks pen as a study-design limitation. "
        "If each selenium treatment group is housed in one pen, then pen and treatment are "
        "confounded. The analysis can describe treatment-group differences, but cannot fully "
        "separate selenium dose effects from pen-level conditions."
    )


def show_study_design(animals: pd.DataFrame | None) -> None:
    st.subheader("1. Study Design and Caveats")
    design_caveat()
    st.write(
        "The public data are synthetic, but they mimic the original analysis structure: "
        "two sheep reproduction studies, selenium treatment groups, longitudinal selenium "
        "measurements, baseline body weight, breeding-cycle outcomes, and final pregnancy."
    )
    if animals is None:
        st.info("Run the synthetic-data generator to view design tables.")
        return

    design = (
        animals.groupby(["study", "group", "pen"], sort=False)
        .agg(
            animals=("animal_id", "nunique"),
            pregnant=("pregnant", "sum"),
            repeat_breeding=("repeat_breeding", "sum"),
            mean_baseline_weight_kg=("baseline_weight_kg", "mean"),
        )
        .reset_index()
    )
    st.dataframe(design, use_container_width=True)
    fig = px.bar(
        design,
        x="group",
        y="animals",
        color="pen",
        facet_col="study",
        title="Animals by Treatment Group and Pen",
    )
    st.plotly_chart(fig, use_container_width=True)


def show_longitudinal(longitudinal: pd.DataFrame | None, tests: pd.DataFrame | None) -> None:
    st.subheader("2. Longitudinal Selenium Models")
    st.write(
        "This tab shows the repeated-measures part of the workflow: selenium concentrations "
        "over time by treatment group. The analysis script fits log-scale longitudinal models "
        "with animal-level repeated measures."
    )
    if longitudinal is None:
        st.info("Synthetic longitudinal data not found.")
        return

    study = st.selectbox("Study", sorted(longitudinal["study"].unique()))
    matrix_options = ["whole_blood_se"]
    if longitudinal.loc[longitudinal["study"].eq(study), "liver_se"].notna().any():
        matrix_options.append("liver_se")
    matrix = st.selectbox("Matrix", matrix_options)
    dat = longitudinal[longitudinal["study"].eq(study) & longitudinal[matrix].notna()].copy()
    fig = px.line(
        dat.groupby(["study", "group", "month"], as_index=False)[matrix].mean(),
        x="month",
        y=matrix,
        color="group",
        markers=True,
        title=f"{study}: Mean {matrix.replace('_', ' ').title()} Over Time",
    )
    st.plotly_chart(fig, use_container_width=True)

    if tests is not None:
        label = "Whole Blood Se" if matrix == "whole_blood_se" else "Liver Se"
        subset = tests[
            tests["study"].eq(study)
            & tests["analysis"].str.contains(label, regex=False)
        ]
        st.dataframe(subset, use_container_width=True)


def show_reproduction(
    animals: pd.DataFrame | None,
    outcomes: pd.DataFrame | None,
    pairwise: pd.DataFrame | None,
) -> None:
    st.subheader("3. Reproductive Outcomes")
    st.write(
        "This tab summarizes breeding-cycle and final pregnancy outcomes. Global treatment "
        "tests are primary; control-vs-treatment contrasts are secondary and include adjusted "
        "p-values."
    )
    if outcomes is not None:
        st.dataframe(outcomes, use_container_width=True)
        fig = px.bar(
            outcomes,
            x="group",
            y="pregnancy_percent",
            color="group",
            facet_col="study",
            title="Final Pregnancy Percent by Treatment Group",
            text_auto=".1f",
        )
        st.plotly_chart(fig, use_container_width=True)
        fig2 = px.bar(
            outcomes,
            x="group",
            y="repeat_breeding_percent",
            color="group",
            facet_col="study",
            title="Repeat Breeding Percent by Treatment Group",
            text_auto=".1f",
        )
        st.plotly_chart(fig2, use_container_width=True)
    elif animals is not None:
        st.dataframe(animals, use_container_width=True)

    if pairwise is not None:
        st.subheader("Control Contrasts")
        st.dataframe(pairwise, use_container_width=True)


def show_hypotheses(tests: pd.DataFrame | None) -> None:
    st.subheader("4. Hypothesis Tests")
    if tests is None:
        st.info("Analysis outputs not found.")
        return

    priority = st.multiselect(
        "Priority",
        sorted(tests["priority"].dropna().unique()),
        default=sorted(tests["priority"].dropna().unique()),
    )
    subset = tests[tests["priority"].isin(priority)].copy()
    st.dataframe(subset, use_container_width=True)

    plot_df = subset[pd.to_numeric(subset["p_value"], errors="coerce").notna()].copy()
    if not plot_df.empty:
        plot_df["minus_log10_p"] = -plot_df["p_value"].clip(lower=1e-300).apply(lambda x: __import__("math").log10(x))
        fig = px.bar(
            plot_df.sort_values("minus_log10_p"),
            x="minus_log10_p",
            y="analysis",
            color="decision",
            orientation="h",
            hover_data=["study", "term", "method", "p_value"],
            title="-log10(p-value) by Analysis",
        )
        st.plotly_chart(fig, use_container_width=True)


def show_methods() -> None:
    st.subheader("Methods and Public-Safe Boundary")
    st.write(
        "This dashboard is a public-safe demonstration. It does not publish collaborator raw "
        "data. It shows the analysis structure: longitudinal selenium models, reproductive "
        "outcome tests, baseline-weight checks, pairwise control contrasts, and interpretation "
        "notes."
    )
    st.markdown(
        """
Key interpretation rules:

- Significant treatment-by-time interactions should be interpreted as different temporal
  trajectories, not just a single average treatment difference.
- Reproductive-window selenium analyses are supporting associations, not independent proof
  of causation.
- Full-follow-up selenium analyses include post-breeding measurements and should not be
  used to claim later selenium values caused earlier pregnancy outcomes.
- Small sample sizes mean nonsignificant p-values are not proof of no effect.
- One pen per treatment means pen-level and treatment-level effects cannot be separated.
"""
    )


def main() -> None:
    st.set_page_config(page_title="Sheep Selenium Statistics", layout="wide")
    st.title("Sheep Selenium and Reproductive Outcomes")
    st.caption(
        "Public-safe statistical analysis dashboard for longitudinal selenium exposure and "
        "reproductive outcomes."
    )

    with st.sidebar:
        data_dir = Path(st.text_input("Synthetic data directory", str(DEFAULT_DATA_DIR.relative_to(ROOT))))
        output_dir = Path(st.text_input("Analysis output directory", str(DEFAULT_OUTPUT_DIR.relative_to(ROOT))))
        if not data_dir.is_absolute():
            data_dir = ROOT / data_dir
        if not output_dir.is_absolute():
            output_dir = ROOT / output_dir
        st.code(
            "python scripts/generate_synthetic_sheep_data.py\n"
            "python scripts/analyze_sheep_stats.py\n"
            "streamlit run dashboard/app.py",
            language="bash",
        )

    animals = load_csv(str(data_dir / "synthetic_sheep_animals.csv"))
    longitudinal = load_csv(str(data_dir / "synthetic_sheep_longitudinal.csv"))
    tests = load_csv(str(output_dir / "hypothesis_tests.csv"))
    outcomes = load_csv(str(output_dir / "reproductive_outcomes.csv"))
    pairwise = load_csv(str(output_dir / "pairwise_control_contrasts.csv"))

    tabs = st.tabs(
        [
            "1. Study Design",
            "2. Selenium Over Time",
            "3. Reproduction",
            "4. Hypothesis Tests",
            "Methods",
        ]
    )
    with tabs[0]:
        show_study_design(animals)
    with tabs[1]:
        show_longitudinal(longitudinal, tests)
    with tabs[2]:
        show_reproduction(animals, outcomes, pairwise)
    with tabs[3]:
        show_hypotheses(tests)
    with tabs[4]:
        show_methods()


if __name__ == "__main__":
    main()
