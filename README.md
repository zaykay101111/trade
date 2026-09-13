# Sports Betting Method — first model

A runnable NBA regular-season moneyline research scaffold. It trains a market-residual XGBoost model, an offset logistic comparator, and separate calibration transforms. It evaluates chronological holdouts and issues **paper** decisions. It never places bets.

**Start with [START_HERE.md](docs/START_HERE.md).** The local `.venv` is installed and a synthetic training/evaluation run has been verified. Real NBA and bookmaker data are not bundled and no real market performance is established.

## Documents

- [Download list and schemas](docs/DATASETS.md)
- [Training protocol and model architecture](docs/TRAINING.md)
- [Mizzou Hellbender instructions](docs/HELLBENDER.md)
- [Monitoring and interpreting results](docs/MONITORING.md)
- [Implementation status and limitations](docs/STATUS.md)

## Quick check

From this directory:

```bash
source .venv/bin/activate
python -m pytest -q
bash scripts/smoke.sh
```

The smoke command creates a new `runs/smoke-TIMESTAMP/` directory. Its synthetic numbers are only software checks.

Every historical evaluation produces `PASTE_BACK.md`. Read or copy it with:

```bash
sports report --path runs/YOUR_RUN/validation
```

On macOS, append `| pbcopy` to copy the report to the clipboard.

## Layout

```text
configs/             Experiment and policy configuration
data/templates/      Canonical CSV headers
data/raw/            Unmodified provider downloads
data/normalized/     Audited canonical records
data/processed/      Features, exclusion records, source hashes
src/sports_method/   Data, learners, evaluation, policy, paper ledger, adapters
slurm/               CPU training and final-test batch jobs
scripts/             Smoke run and optional NBA downloader
tests/               Leakage, probability, accounting and schema checks
runs/                Models, manifests, learning curves, evaluation reports
logs/                Slurm stdout/stderr
docs/                Download, training and monitoring protocols
```

