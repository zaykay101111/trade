# Verification record

Verified locally on September 12, 2026, using Python 3.12 and the versions in requirements-tested.txt.

- 18 automated tests passed.
- Shell syntax checks passed for the smoke and Slurm scripts.
- Python compilation checks passed for the package and helper scripts.
- A complete synthetic run generated 1,200 games, admitted 1,167 after history requirements, trained both learners, calibrated them, evaluated validation, froze the bundle, and evaluated 179 final-test games.
- Both market-evidence flags remain false for synthetic data by construction.
- Final verified example report: ../runs/smoke-20260913T014941Z/model/test/PASTE_BACK.md.

Tests include future-result invariance, future/stale quote rejection, schedule leakage, duplicate identities, paired probability arithmetic, away-side haircut, open exposure, calibration monotonicity, frozen-model tamper detection, delayed-price isolation, and paper settlement/check accounting.

Not verified: real vendor downloads with credentials, real NBA model performance, live-feed scheduling, Hellbender environment installation or Slurm execution. The optional NBA download script is based on the documented client interface and has not made a real data request here.
