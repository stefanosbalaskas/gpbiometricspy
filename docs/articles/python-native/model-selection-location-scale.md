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
| Crossed scale slopes | participant/item location intercept + log-scale intercept + slope | joint dense-Laplace approximation | both crossed factors need log-scale random slopes |
| Crossed joint slopes | participant/item intercept + slope in both equations | joint dense-Laplace approximation | both mean and dispersion associations require crossed random slopes |

## Why crossed models use a different integration strategy

With one grouping factor, independent group contributions can be integrated group by group. In a crossed participant–item design, each observation links two latent families. The latent field is therefore coupled through the incidence structure and cannot be decomposed into independent participant and item integrals.

The crossed implementation uses a joint Laplace approximation with analytic latent derivatives, incidence-connectivity checks, replication guards, and a dense-latent complexity ceiling. These are not merely performance choices; they define the design region in which the implementation is intended to operate.

For the crossed joint model the latent dimension becomes `4(P + I)`, because both participants and items carry location intercepts/slopes and log-scale intercepts/slopes. This is a meaningful increase in covariance and latent-field complexity, so richer crossed structures require stronger design support than simpler random-intercept models.

## Random slopes need within-level variation

A participant-specific slope for `x` is not estimable if `x` is constant within that participant. Likewise, an item-specific slope requires variation within every relevant item. The software therefore treats within-level variation as a design guard, not a warning to ignore.

For a scale random slope, the same principle applies in the log-scale equation. The predictor must also appear as a fixed scale effect so the random slope is a deviation around a declared population association. In the crossed joint model, all four random-slope declarations are checked independently.

## Conditional versus population prediction

For seen groups, empirical-Bayes latent effects can be used for conditional prediction. For unseen groups or items, those effects do not exist and prediction must revert to the population-level component unless a scientifically justified new-level mechanism is available.

This distinction matters in benchmarking. Performance on observed participants answers a different question from generalisation to new participants. Crossed designs add two mixed cases: new participants with known items, and known participants with new items.

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

## The next methodological priority

The crossed family now has explicit intercept-only, location-slope, scale-slope, and joint location+scale-slope structures. The next priority is therefore **validation depth and computational scalability**, not another random-effect term.

High-value follow-on work includes:

- systematic known-truth recovery across crossed incidence densities and replication levels;
- approximation-sensitivity checks against smaller problems that admit alternative integration strategies;
- sparse-Hessian or block-structured linear algebra for larger crossed designs;
- optimizer-start and covariance-boundary diagnostics;
- simulation-based guidance on when the joint 4D crossed blocks are estimable enough to justify interpretation.

Only after those checks should heavier-tailed crossed outcomes, richer distributional families, or still more general random-effect grammars be considered.

See the practical [model-selection guide](../../guides/model-selection.md) and the exact [Methods](../../methods/index.md) documentation.