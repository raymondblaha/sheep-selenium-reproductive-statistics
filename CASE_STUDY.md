# Case Study: Sheep Selenium and Reproductive Outcomes

## Executive Summary

This project demonstrates a statistical analysis workflow for a sheep selenium
supplementation and reproductive-efficiency study.

The portfolio value is different from the CWD telemetry project. This project is meant to
show classical data-science judgment: study design review, longitudinal modeling,
categorical outcome testing, small-sample interpretation, and transparent communication of
limitations.

The public repository contains:

1. a public-safe source snapshot of the original R Markdown analysis;
2. synthetic data that mimics the structure of the original studies;
3. reproducible Python scripts for statistical summaries and tests;
4. a Streamlit dashboard for inspecting design, selenium trajectories, reproductive
   outcomes, and hypothesis tests.

## Research Question

The original analysis asked whether selenium treatment groups differed in:

- longitudinal selenium concentrations;
- repeat-breeding frequency;
- final pregnancy outcome;
- baseline body weight;
- body-weight trajectories;
- supporting associations between selenium concentrations and reproductive outcomes.

The biological context is reproductive efficiency in sheep under different selenium
supplementation groups.

## Original Analysis Structure

The supplied archive included:

| Source file | Role |
| --- | --- |
| `Sheep_4.0_Analysis_UPDATED_v2.Rmd` | Main R Markdown analysis workflow |
| `Final_Statistical_Report.txt` | Final written statistical report |
| `Table_Final_Hypothesis_Tests.csv` | Hypothesis-test table |
| `Table_Study1_Reproductive_Outcomes.csv` | Study 1 reproduction summary |
| `Table_Study2_Reproductive_Outcomes.csv` | Study 2 reproduction summary |
| `Pairwise_*csv` | Control-vs-treatment contrasts |
| `Study2_Cohort_QC.csv` | Study 2 ID matching and cohort checks |

The public workflow does not publish collaborator raw data. It recreates the analysis shape
using synthetic data.

## Statistical Workflow

The public pipeline follows the same broad structure as the original analysis:

1. Generate synthetic animal-level and longitudinal sheep data.
2. Summarize reproductive outcomes by study and treatment group.
3. Model longitudinal selenium trajectories over time.
4. Test repeat breeding and final pregnancy associations by treatment group.
5. Compare each treatment group against control as secondary contrasts.
6. Evaluate whether baseline body weight differs by group or predicts pregnancy.
7. Write clean output tables and a report.
8. Display the results in a dashboard.

## Main Methods Demonstrated

| Analytical task | Public implementation |
| --- | --- |
| Longitudinal selenium over time | original R workflow used repeated-measures models; public Python demo uses a portable log-scale fixed-effect approximation on synthetic data |
| Binary reproductive outcomes | treatment-by-outcome contingency tests |
| Control contrasts | pairwise Fisher exact tests with Holm-style adjusted p-values |
| Baseline body weight | group comparison and pregnancy association check |
| Reporting | generated hypothesis table and plain-language statistical report |
| Dashboard | Streamlit + Plotly visual inspection layer |

## Original Result Context

The original report found strong evidence that selenium concentrations differed by treatment
group and changed over time. The report also found reproductive-outcome differences in some
primary tests, including Study 1 repeat breeding and final pregnancy.

Study 2 showed clear selenium trajectory differences by treatment group, while the actual
breeding-cycle distribution did not meet the 0.05 threshold in the primary global test.
Supporting reproductive-window analyses suggested associations between selenium measures
and reproductive outcomes, but the report correctly treated these as supporting rather than
standalone causal evidence.

The original report also emphasized that nonsignificant results are not proof of no
biological effect, especially with small samples.

## Critical Study-Design Issue

The most important limitation is potential pen confounding.

If each treatment group is housed in one pen, then pen and treatment are statistically
confounded. That means any group difference could reflect selenium treatment, pen-level
conditions, or both. Without treatment replication across multiple pens, the analysis cannot
cleanly separate treatment effects from pen effects.

This limitation should be stated directly in any serious interpretation. The right framing
is:

- treatment-group differences can be described;
- statistical evidence can be reported;
- causal claims about selenium dose should be cautious;
- future designs should replicate treatments across pens when feasible.

## Public Dashboard

Run:

```bash
pip install -e .
python scripts/generate_synthetic_sheep_data.py
python scripts/analyze_sheep_stats.py
streamlit run dashboard/app.py
```

Dashboard tabs:

1. **Study Design**: treatment groups, pens, sample sizes, and design caveat.
2. **Selenium Over Time**: longitudinal selenium trajectories.
3. **Reproduction**: pregnancy and repeat-breeding summaries.
4. **Hypothesis Tests**: statistical table with p-values, decisions, and methods.
5. **Methods**: interpretation rules and public-safe boundary.

## What This Demonstrates To Employers

This project shows that I can:

- translate an R Markdown analysis into a public reproducible project;
- distinguish primary, secondary, and supporting analyses;
- identify design limitations before overclaiming results;
- handle small-sample categorical outcomes carefully;
- communicate p-values with plain-language interpretations;
- build an interactive dashboard around statistical results;
- protect private data while still showing real analytical competence.

## Public-Safe Boundary

The public dataset is synthetic. It is intended to demonstrate the analysis and dashboard
workflow only. It should not be used for biological inference.
