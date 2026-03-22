# Horizon Estimation Methodology

## 1. Introduction

Horizon is a data-driven estimation tool that replaces single-point gut-feel estimates with probabilistic forecasts grounded in your team's actual historical performance. Given a new task's story points and an initial effort estimate, Horizon runs 10,000 Monte Carlo simulations using weighted bootstrap resampling of past actual-vs-estimated ratios to produce confidence intervals for both effort (man-days) and calendar delivery (elapsed days).

### Why Monte Carlo?

A single-point estimate ("this will take 5 days") communicates no information about uncertainty. In practice, software tasks vary widely around their estimates due to hidden complexity, interruptions, and optimism bias. Monte Carlo simulation addresses this by generating a full probability distribution of outcomes rather than a single number, letting stakeholders see the range of likely results and make risk-aware decisions.

Instead of asking "how long will this take?", Horizon answers: "there is a 90% chance this will take between X and Y days."

---

## 2. Conceptual Overview

Think of Horizon as running 10,000 "what-if" scenarios based on your team's real track record:

1. **Gather history**: Collect past tasks with their original estimates and actual completion times.
2. **Find similar tasks**: Weight historical tasks by how similar they are in size (story points) to the task being estimated.
3. **Simulate**: Randomly sample from past estimation accuracy ratios (weighted toward similar tasks) and apply each sampled ratio to the new estimate.
4. **Measure the spread**: From 10,000 simulated outcomes, extract the 10th percentile (optimistic), 50th percentile (most likely), and 90th percentile (pessimistic).

```
                          Historical Tasks
                                |
                                v
    ┌─────────────────────────────────────────────┐
    │  Compute Ratios:  actual / estimated        │
    │  Compute Weights: Gaussian on story points  │
    └──────────────────┬──────────────────────────┘
                       │
                       v
    ┌─────────────────────────────────────────────┐
    │  Weighted Bootstrap Resampling              │
    │  (10,000 draws with replacement)            │
    └──────────────────┬──────────────────────────┘
                       │
           ┌───────────┼───────────┐
           │           │           │
           v           v           v
      ┌─────────┐ ┌─────────┐ ┌───────────────┐
      │ Effort  │ │Calendar │ │  Reference     │
      │ P10/50/ │ │ P10/50/ │ │  Cases (top 5) │
      │ 90      │ │ 90      │ │               │
      └─────────┘ └─────────┘ └───────────────┘
```

The key insight is that **you don't need to know the true distribution of task durations** — you only need enough historical data points for the bootstrap to capture the natural variability of your team's estimation accuracy.

---

## 3. The Algorithm in Detail

### 3.1 Estimation Accuracy Ratios

For each historical task *i*, Horizon computes the ratio of actual effort to estimated effort:

```
r_i = actual_days_i / estimated_days_i
```

- A ratio of **1.0** means the estimate was perfectly accurate.
- A ratio of **1.5** means the task took 50% longer than estimated.
- A ratio of **0.8** means the task finished 20% faster than estimated.

These ratios capture the systematic patterns in your team's estimation accuracy — both the average bias (do you tend to underestimate?) and the variance (how spread out are your misses?).

*Source: `horizon/mc_utils.py::compute_ratios()`*

### 3.2 Story-Point Similarity Weighting

Not all historical tasks are equally relevant. A 2-point bug fix tells you little about how long a 13-point epic will take. Horizon uses a **Gaussian (bell curve) kernel** to weight historical tasks by their story-point similarity to the target task:

```
w_i = exp( -0.5 × ((sp_i - sp_target) / σ)² )
```

where:
- **sp_i** is the story points of historical task *i*
- **sp_target** is the story points of the task being estimated
- **σ** (sigma) is the bandwidth parameter (default: **2.5**)

The weights are then **normalized** so they sum to 1:

```
W_i = w_i / Σ_j(w_j)
```

**Why Gaussian?** The Gaussian kernel provides a smooth, symmetric falloff: tasks with identical story points get the highest weight, nearby tasks still contribute meaningfully, and distant tasks are down-weighted exponentially. This is preferable to hard cutoffs (e.g., "only use tasks with the same story points") because it uses more of the available data while still respecting size similarity.

**The role of σ:** The sigma parameter controls how quickly the influence drops off:

| σ value | Behavior |
|---------|----------|
| **0.5** | Very tight — almost exclusively uses tasks with the same story points |
| **2.5** (default) | Moderate — a 5-SP target gives meaningful weight to 3-SP and 8-SP tasks |
| **10.0** | Very wide — nearly uniform weighting, all tasks contribute equally |

As a fallback, if all weights compute to zero (mathematically impossible with finite sigma, but guarded against), Horizon falls back to uniform weights.

*Source: `horizon/mc_utils.py::compute_weights()`*

### 3.3 Weighted Bootstrap Resampling

The **bootstrap** is a non-parametric statistical method introduced by Bradley Efron in 1979. The core idea: rather than assuming a particular probability distribution (normal, log-normal, etc.), you resample from the empirical data itself to estimate the sampling distribution of a statistic.

Horizon performs **weighted** bootstrap resampling:

1. You have *n* historical ratios: `[r_1, r_2, ..., r_n]`
2. You have corresponding weights: `[W_1, W_2, ..., W_n]` (from the Gaussian kernel)
3. For each of 10,000 iterations, **randomly select one ratio** with probability proportional to its weight (sampling with replacement)
4. Multiply the selected ratio by the initial estimate to produce an effort sample:

```
effort_k = r_sampled_k × initial_estimate_days
```

The result is 10,000 effort samples that form an empirical probability distribution of the likely actual effort.

**Why bootstrap instead of parametric methods?** Software estimation errors are notoriously non-normal — they tend to be right-skewed (tasks are more likely to take much longer than estimated than much shorter). The bootstrap makes no distributional assumptions and naturally captures whatever shape the data has: skewness, heavy tails, multimodality, etc.

*Source: `horizon/mc_utils.py::bootstrap_sample()`*

### 3.4 Percentile Extraction (P10 / P50 / P90)

From the 10,000 simulated effort values, Horizon extracts three percentiles:

| Percentile | Meaning | Interpretation |
|------------|---------|----------------|
| **P10** | 10th percentile | Optimistic estimate — there's only a 10% chance the actual will be this low or lower |
| **P50** | 50th percentile (median) | Most likely estimate — the midpoint of the distribution |
| **P90** | 90th percentile | Pessimistic estimate — there's a 90% chance the actual will be this or lower |

In practical terms:
- **P10** is the "everything goes right" scenario.
- **P50** is your best single-number estimate if forced to give one.
- **P90** is the "buffer for surprises" number that should be used for commitments and deadlines.

The spread between P10 and P90 directly communicates the **uncertainty** in the estimate. A narrow spread means the team's past performance on similar tasks was consistent; a wide spread means high variance and greater risk.

*Source: `horizon/mc_utils.py::extract_percentiles()`*

### 3.5 Calendar Day Estimation

Effort days (pure work time) and calendar days (elapsed wall-clock time) diverge because of weekends, holidays, meetings, context-switching, and parallel work. Horizon models this with a **second-order Monte Carlo** step.

First, compute a **calendar ratio** for each historical task:

```
cal_ratio_i = calendar_days_i / actual_days_i
```

where `calendar_days = completed_date - started_date` (computed as a property from the two stored dates). A calendar ratio of 1.5 means a task that took 4 man-days of effort actually spanned 6 calendar days.

Then, using the same Gaussian weighting by story points:

1. Bootstrap-sample a calendar ratio (with replacement, weighted)
2. Multiply each effort sample by its independently sampled calendar ratio:

```
calendar_sample_k = effort_sample_k × cal_ratio_sampled_k
```

This pairing is **independent** — the effort ratio and calendar ratio for each simulation are drawn separately. This captures the fact that a task's estimation accuracy and its calendar overhead are separate sources of uncertainty that compound.

Finally, extract P10/P50/P90 from the 10,000 calendar samples.

*Source: `horizon/calendar_estimator.py`*

### 3.6 Three-Point (PERT) Estimation

In addition to the raw percentiles, Horizon computes a **PERT weighted average**:

```
E_pert = (P10 + 4 × P50 + P90) / 6
```

This formula comes from the **Program Evaluation and Review Technique** (PERT), developed by the U.S. Navy in 1958 for the Polaris missile program. The weighting (1-4-1) reflects the assumption that the most likely value (P50) should dominate the estimate while still accounting for optimistic and pessimistic extremes. It approximates the mean of a beta distribution fitted to the three-point estimate.

The PERT average is useful as a single-number summary that is more risk-aware than the median alone: it pulls slightly toward the pessimistic end when the distribution is right-skewed (which is typical for software tasks).

### 3.7 Reference Case Finder

To complement the quantitative estimates with qualitative context, Horizon identifies the most similar historical tasks using the same Gaussian similarity kernel:

```
score_i = exp( -0.5 × ((sp_i - sp_target) / σ)² )
```

Scores are then **normalized to [0, 1]** by dividing by the maximum score (so the best match always scores 1.0). The top *N* tasks (default: 5) are returned, sorted by descending similarity.

These reference cases help stakeholders ground the estimates in reality: "your 5-point task estimate is statistically similar to these 5 past tasks, which took between 3 and 7 days."

*Source: `horizon/reference_finder.py`*

---

## 4. Worked Example

Consider a team with 4 completed tasks:

| Task | Story Points | Estimated Days | Actual Days | Started | Completed | Calendar Days |
|------|-------------|---------------|-------------|---------|-----------|---------------|
| T-1  | 3           | 2.0           | 2.4         | Jan 8   | Jan 11    | 3             |
| T-2  | 5           | 3.0           | 4.5         | Jan 15  | Jan 22    | 7             |
| T-3  | 5           | 4.0           | 5.0         | Feb 1   | Feb 9     | 8             |
| T-4  | 8           | 5.0           | 7.0         | Feb 12  | Feb 22    | 10            |

**New task to estimate:** 5 story points, initial estimate = 3.0 days.

### Step 1: Compute Ratios

```
r_1 = 2.4 / 2.0 = 1.20
r_2 = 4.5 / 3.0 = 1.50
r_3 = 5.0 / 4.0 = 1.25
r_4 = 7.0 / 5.0 = 1.40
```

The team tends to underestimate by 20-50%.

### Step 2: Compute Gaussian Weights (σ = 2.5, target SP = 5)

```
w_1 = exp(-0.5 × ((3 - 5) / 2.5)²) = exp(-0.5 × 0.64) = exp(-0.32) = 0.726
w_2 = exp(-0.5 × ((5 - 5) / 2.5)²) = exp(0)             = 1.000
w_3 = exp(-0.5 × ((5 - 5) / 2.5)²) = exp(0)             = 1.000
w_4 = exp(-0.5 × ((8 - 5) / 2.5)²) = exp(-0.5 × 1.44)   = exp(-0.72) = 0.487
```

Sum = 0.726 + 1.000 + 1.000 + 0.487 = 3.213

Normalized weights:
```
W_1 = 0.726 / 3.213 = 0.226  (3-SP task)
W_2 = 1.000 / 3.213 = 0.311  (5-SP task)
W_3 = 1.000 / 3.213 = 0.311  (5-SP task)
W_4 = 0.487 / 3.213 = 0.152  (8-SP task)
```

The two 5-SP tasks together receive 62% of the weight — they're most relevant.

### Step 3: Bootstrap Sampling

Each of 10,000 iterations randomly picks one ratio with these probabilities:
- 22.6% chance of picking r_1 = 1.20
- 31.1% chance of picking r_2 = 1.50
- 31.1% chance of picking r_3 = 1.25
- 15.2% chance of picking r_4 = 1.40

Then multiplies by the initial estimate (3.0 days):

| Sampled Ratio | Effort Sample |
|--------------|---------------|
| 1.50         | 4.50 days     |
| 1.25         | 3.75 days     |
| 1.25         | 3.75 days     |
| 1.20         | 3.60 days     |
| 1.40         | 4.20 days     |
| ...          | ...           |

### Step 4: Extract Percentiles

After 10,000 samples, sort and find:
- **P10 ~ 3.60 days** (optimistic)
- **P50 ~ 3.75 days** (most likely)
- **P90 ~ 4.50 days** (pessimistic)

PERT average: (3.60 + 4 × 3.75 + 4.50) / 6 = **3.85 days**

### Step 5: Calendar Day Estimation

Compute calendar ratios:
```
cal_1 = 3 / 2.4 = 1.25
cal_2 = 7 / 4.5 = 1.56
cal_3 = 8 / 5.0 = 1.60
cal_4 = 10 / 7.0 = 1.43
```

For each of the 10,000 effort samples, independently sample a calendar ratio (with the same Gaussian weights) and multiply:

```
calendar_sample = effort_sample × cal_ratio_sampled
```

For example: 3.75 days effort × 1.56 calendar ratio = 5.85 calendar days.

This might yield:
- **Calendar P10 ~ 4.5 days**
- **Calendar P50 ~ 5.7 days**
- **Calendar P90 ~ 7.2 days**

### Step 6: Reference Cases

Similarity scores (normalized to max = 1.0):
```
T-1 (3 SP): 0.726 / 1.000 = 0.73
T-2 (5 SP): 1.000 / 1.000 = 1.00  ← best match
T-3 (5 SP): 1.000 / 1.000 = 1.00  ← best match
T-4 (8 SP): 0.487 / 1.000 = 0.49
```

Returned: T-2 (100%), T-3 (100%), T-1 (73%), T-4 (49%).

---

## 5. Parameter Guide

| Parameter | Default | Range | Effect |
|-----------|---------|-------|--------|
| **iterations** | 10,000 | 1,000 – 100,000 | Number of Monte Carlo samples. Higher = smoother distribution, more stable percentiles. 10,000 is sufficient for most uses; diminishing returns above 50,000. |
| **sigma (σ)** | 2.5 | 0.1 – 100 | Gaussian kernel bandwidth in story-point units. Lower = only very similar tasks contribute. Higher = more uniform weighting. For Fibonacci SP sequences (1,2,3,5,8,13), σ=2.5 provides a good balance. |
| **top_references** | 5 | 1 – N | Number of similar historical tasks to display in the report. |
| **seed** | None | Any integer | Random seed for reproducibility. Set to a fixed value for deterministic results (useful for testing and auditing). |

### Sigma Tuning Guidance

The right sigma depends on your dataset size and story-point distribution:

- **Small dataset (< 20 tasks):** Consider a larger σ (3.0 – 5.0) to avoid over-concentrating weight on too few tasks.
- **Large dataset (> 100 tasks):** A smaller σ (1.5 – 2.5) can safely focus on the most similar tasks.
- **Non-Fibonacci points:** If your team uses a linear scale (1–10), adjust σ proportionally to the spacing.

---

## 6. Assumptions and Limitations

### Assumptions

1. **Team stationarity**: The model assumes your team's estimation accuracy patterns are roughly stable over time. If the team has recently undergone a major process change, onboarded many new members, or switched tech stacks, historical ratios may not be representative of future performance.

2. **Story points as the primary similarity dimension**: Weighting uses only story points to determine how relevant a historical task is. It does not account for task type (frontend vs. backend vs. infrastructure), technology complexity, or individual assignee skill level.

3. **Independence of tasks**: Each simulation draw is independent. The model does not account for task dependencies, parallel work, or resource contention. If your next task is blocked by another in-progress task, the calendar estimate will not reflect that.

4. **Calendar ratio stability**: The conversion from effort to calendar days assumes that the factors driving the calendar/effort ratio (weekends, meetings, context-switching load) are roughly consistent with historical patterns.

5. **Quality of the initial estimate**: The model **scales** the initial estimate by historically observed ratios. If the initial estimate is fundamentally wrong (e.g., missing a major component of work), the Monte Carlo output will be proportionally wrong. Garbage in, garbage out — but with well-calibrated confidence intervals.

### Limitations

1. **Minimum data requirement**: Bootstrap resampling needs a meaningful pool to draw from. With fewer than 10-15 historical tasks, the distribution will be sparse and percentiles may be unreliable. **Recommended minimum: 15-20 tasks**, with at least a few near the target story-point size.

2. **Outlier sensitivity**: A single extreme outlier (e.g., a task that took 10x the estimate due to an exceptional blocker) will be included in the bootstrap pool. With small datasets, this outlier may be sampled frequently and dominate the P90. Consider reviewing and potentially removing data quality issues before running estimates.

3. **No task-type differentiation**: A 5-point bug fix and a 5-point new feature are treated identically by the weighting scheme. If your team's estimation accuracy differs significantly by task type, consider maintaining separate data files per task category.

4. **Right-skew not guaranteed but typical**: The model faithfully reproduces whatever distribution your data has. If your team consistently overestimates (ratios < 1.0), the model will correctly show that — but this is uncommon in practice.

5. **Calendar estimation is second-order**: The calendar estimate compounds two sources of uncertainty (effort ratio and calendar ratio), so its confidence interval will typically be wider than the effort interval. This is a feature, not a bug — it reflects genuine additional uncertainty.

### When NOT to Trust the Estimates

- **Brand new team** with no historical data yet.
- **Immediately after a major process change** (new methodology, new tooling, team reorganization) — wait for 15-20 tasks under the new process.
- **Task is fundamentally different** from anything in the history (e.g., first-ever mobile app when history is all backend).
- **Extreme story points** far outside the historical range (e.g., estimating a 21-point epic when the largest historical task was 8 points).
- **Very small dataset** (< 10 tasks) — the bootstrap will be unreliable.

---

## 7. References

### Foundational Texts

- **Efron, B. (1979)**. "Bootstrap Methods: Another Look at the Jackknife." *The Annals of Statistics*, 7(1), 1-26. The original bootstrap paper.
  https://projecteuclid.org/euclid.aos/1176344552

- **Efron, B. & Tibshirani, R.J. (1993)**. *An Introduction to the Bootstrap*. Chapman & Hall/CRC. The definitive textbook on bootstrap methods, covering the theory, variations, and practical applications of the technique used in Horizon's core algorithm.
  https://doi.org/10.1007/978-1-4899-4541-9

- **Vose, D. (2008)**. *Risk Analysis: A Quantitative Guide*, 3rd ed. Wiley. Comprehensive treatment of Monte Carlo simulation applied to project risk analysis, including the bootstrapping approach to schedule estimation.
  https://doi.org/10.1002/9781119995104

### Software Estimation

- **McConnell, S. (2006)**. *Software Estimation: Demystifying the Black Art*. Microsoft Press. Covers the cone of uncertainty, reference class forecasting, and why probabilistic estimates outperform single-point estimates. Chapters 1 and 4 are particularly relevant.
  https://www.microsoftpressstore.com/store/software-estimation-demystifying-the-black-art-9780735605350

- **Little, T. (2006)**. "Schedule Estimation and Uncertainty Surrounding the Cone of Uncertainty." *IEEE Software*, 23(3), 48-54. Empirical validation of the cone of uncertainty in software projects.
  https://doi.org/10.1109/MS.2006.82

### Reference Class Forecasting and Cognitive Bias

- **Kahneman, D. & Tversky, A. (1979)**. "Intuitive Prediction: Biases and Corrective Procedures." *TIMS Studies in Management Science*, 12, 313-327. Foundational work on the planning fallacy — the systematic tendency to underestimate task duration — which motivates data-driven estimation approaches like Horizon.
  https://doi.org/10.1017/CBO9780511809477.031

- **Flyvbjerg, B. (2006)**. "From Nobel Prize to Project Management: Getting Risks Right." *Project Management Journal*, 37(3), 5-15. Applies Kahneman's reference class forecasting concept to project estimation, arguing that historical data from similar projects is the best antidote to optimism bias.
  https://doi.org/10.1177/875697280603700302

### PERT Method

- **Malcolm, D.G., Roseboom, J.H., Clark, C.E. & Fazar, W. (1959)**. "Application of a Technique for Research and Development Program Evaluation." *Operations Research*, 7(5), 646-669. The original PERT paper, introducing the three-point estimation technique and the (a + 4m + b) / 6 formula used in Horizon's PERT weighted average.
  https://doi.org/10.1287/opre.7.5.646

### Monte Carlo in Agile Contexts

- **Vacanti, D. (2015)**. *Actionable Agile Metrics for Predictability*. Covers using historical flow data and Monte Carlo methods for delivery forecasting in agile teams.

- **Magennis, T. (2011)**. "Forecasting and Simulating Software Development Projects." A practical guide to applying Monte Carlo simulation in agile project management, including story-point-based estimation approaches similar to Horizon's methodology.
  https://github.com/FocusedObjective/FocusedObjective.Resources

### Kernel Density Estimation (Related Theory)

- **Silverman, B.W. (1986)**. *Density Estimation for Statistics and Data Analysis*. Chapman & Hall/CRC. While Horizon uses discrete weighted bootstrap rather than continuous KDE, the Gaussian kernel weighting draws from the same mathematical framework. Chapter 2 on kernel functions is relevant to understanding the σ bandwidth parameter.
  https://doi.org/10.1007/978-1-4899-3324-9
