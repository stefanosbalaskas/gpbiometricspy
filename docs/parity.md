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

At the stable `0.1.0` freeze every export was directly referenced by Python tests, the complete suite passed on Linux/Windows/macOS across Python 3.11–3.14, and coverage exceeded the 90% release gate.

## Independent deep-parity evidence

Development after `0.1.0` adds a second evidence layer under `reference/golden/`: the frozen R implementation and Python port independently generate deterministic outputs for numerical physiology/QC families, then a separate comparator applies explicit tolerances. This prevents a Python-only test suite from being mistaken for cross-runtime numerical evidence.

Optional backend behavior is tested separately because HeartPy, BioSPPy, pyHRV, NeuroKit2, MNE, pylsl and pyxdf can change independently of the frozen R reference.
