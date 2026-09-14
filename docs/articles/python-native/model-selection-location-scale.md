# Choosing a location–scale model

> **Python-native explanation article.** This page explains the development-line model family; it is not one of the 26 frozen R vignette companions.

Hierarchical location–scale models separate two questions: how predictors relate to the conditional **location** of an outcome, and how they relate to its conditional **residual scale**. The Python-native family progressively adds robustness, random slopes, and crossed participant–item structures while keeping each extension explicit.

## Start from the scientific contrast

A location effect asks whether the expected outcome changes. A scale effect asks whether residual dispersion changes after accounting for the specified mean structure. These are not interchangeable, and neither is automatically causal.

## Current family

| Family | Latent structure | Integration | Use when |
|---|---|---|---|
| Gaussian location–scale | location intercept + log-scale intercept | adaptive Gauss–Hermite quadrature | one grouping factor; mean and dispersion heterogeneity |
| Robust Student-t | same random effects, Student-t outcome | adaptive quadrature | symmetric heavy tails matter |
| Random location slope | location intercept + location slope + log-scale intercept | 3D adaptive quadrature | a numeric predictor has group-specific mean association |
| Random scale slope | location intercept + log-scale intercept + log-scale slope | 3D adaptive quadrature | a numeric predictor has group-specific dispersion association |
| Joint random slopes | intercept/slope in both equations | 4D adaptive quadrature | both location and scale slopes are substantively needed |
| Crossed intercepts | participant + item intercepts in both equations | joint Laplace approximation | observations are crossed by participant and item/stimulus |
| Crossed location slopes | participant/item location intercept + slope + log-scale intercept | joint dense-Laplace approximation | both crossed factors need mean-equation random slopes |

## Why crossed models use a different integration strategy

With one grouping factor, independent group contributions can be integrated group by group. In a crossed participant–item design, each observation links two latent families. The latent field is therefore coupled through the incidence structure and cannot be decomposed into independent participant and item integrals.

The crossed implementation uses a joint Laplace approximation with analytic latent derivatives, incidence-connectivity checks, replication guards, and a dense-latent complexity ceiling. These are not merely performance choices; they define the design region in which the implementation is intended to operate.

## Random slopes need within-level variation

A participant-specific slope for `x` is not estimable if `x` is constant within that participant. Likewise, an item-specific slope requires variation within every relevant item. The software therefore treats within-level variation as a design guard, not a warning to ignore.

For a scale random slope, the same principle applies in the log-scale equation. The predictor must also appear as a fixed scale effect so the random slope is a deviation around a declared population association.

## Conditional versus population prediction

For seen groups, empirical-Bayes latent effects can be used for conditional prediction. For unseen groups or items, those effects do not exist and prediction must revert to the population-level component unless a scientifically justified new-level mechanism is available.

This distinction matters in benchmarking. Performance on observed participants answers a different question from generalisation to new participants.

## Model escalation should be evidence-driven

Move to a richer model when the richer random structure is scientifically necessary *and* supported by the design. Useful evidence includes:

- known-truth recovery under realistic sample sizes;
- covariance recovery rather than only fixed-effect recovery;
- stable optimization across deterministic starting conditions;
- sensible empirical-Bayes summaries;
- prediction semantics that remain explicit for unseen levels;
- adequate replication and connected crossed incidence;
- sensitivity to the integration approximation where relevant.

Do not add a random slope merely because the software can fit one.

## The next structural gap

The current crossed random-slope model adds **location** slopes for participants and items but deliberately omits **log-scale** random slopes. The next methodological extension should therefore introduce crossed participant–item scale slopes while preserving the same design guards, prediction semantics, deterministic certificates, and conservative interpretation.

That extension should be validated before a still richer crossed joint location+scale slope model is attempted.

See the practical [model-selection guide](../../guides/model-selection.md) and the exact [Methods](../../methods/index.md) documentation.
