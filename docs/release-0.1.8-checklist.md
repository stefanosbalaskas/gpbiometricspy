# 0.1.8 qualification checklist

This page mirrors the release-specific qualification record for the 0.1.8 stable-freeze candidate.

- qualified pre-freeze source: `a75eb1d73791213e6e830ff94975f632455632e2`;
- 406/406 frozen R exports implemented, 0 pending;
- 12/12 OS × Python 3.11–3.14 lanes green;
- 874/874 tests;
- 15,612/15,612 statements = 100.00%;
- 7,315/7,334 raw branches = 99.7409%;
- 19 reviewed structural arcs;
- 0 unexpected / 0 stale / 0 unaudited branch debt;
- 7,334/7,334 audited branch accounting;
- STEP authorized evidence complete with restricted rows retained locally;
- ENCoDE deferred;
- no clinical SpO₂ validation claim;
- no fabricated 0.1.8 Zenodo version DOI.

## Remaining publication gates

- [ ] exact stable-freeze PR head passes every required workflow family;
- [ ] release-identity and distribution checks pass on that exact head;
- [ ] PR is merged only on a pinned unchanged head;
- [ ] resulting exact `main` passes every protected stable-release gate;
- [ ] immutable `v0.1.8` is created from that exact qualified commit;
- [ ] canonical GitHub Release assets and SHA256 sums are verified;
- [ ] protected PyPI Trusted Publishing succeeds from the canonical artifact;
- [ ] fresh public-index consumer installation succeeds;
- [ ] any 0.1.8 Zenodo version DOI is recorded only after genuine independent verification.
