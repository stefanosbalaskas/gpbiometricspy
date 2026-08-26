# Parity and validation

The initial semantic reference is the supplied `gpbiometrics 2.0.0` source release.

## Reference precedence

1. R implementation
2. R tests
3. Rd documentation
4. vignettes/examples
5. explanatory repository/site prose

## Completion criteria

The frozen 406-name export set is registered and implemented in Python. This is an **API and implementation freeze**, not a claim that every optional external package will return bit-identical numerical output across all library versions and platforms.

Deep parity is defended through translated fixtures, edge-path tests, retained R sources/tests, deterministic simulations, whole-package coverage, build/install tests, and explicit guardrails where the R implementation itself refuses unsupported inference.
