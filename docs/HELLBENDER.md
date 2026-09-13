# Hellbender training protocol

Verified against [Mizzou ITRSS Hellbender documentation](https://itrss-wiki.rnet.missouri.edu/pub/hpc/hellbender) on September 12, 2026 (America/Chicago).

## Cluster facts to check against your account

Hellbender serves UM research/teaching users; student access may require PI sponsorship. Confirm that your account and project are covered. SSH uses `hellbender-login.rnet.missouri.edu`; Open OnDemand is `https://ondemand.rnet.missouri.edu`. Off-campus access requires the documented key/VPN setup. Run computation on compute nodes, not login nodes. Use Globus or `hellbender-dtn-p1.rnet.missouri.edu` for transfers. The documented general and interactive partitions have maximum durations of two days and four hours respectively. Standard storage includes `/home/USERNAME/data`; cluster storage is not backed up by RSS. Check live limits with `scontrol show partition general`.

No cluster connection was made for this project. The following resource requests are our estimates for this workload.

## 1. Transfer project and normalized data

Use Globus, or from your Mac after replacing YOUR_SSO:

```bash
rsync -av --exclude='.venv' --exclude='__pycache__' --exclude='.pytest_cache' --exclude='runs' --exclude='*.egg-info' \
  "/Users/kylerzook2005/Documents/Personal Projects/Sports Betting Method/" \
  YOUR_SSO@hellbender-dtn-p1.rnet.missouri.edu:/home/YOUR_SSO/data/sports-method/
```

Create/choose the destination within your allocation first. Do not copy the Mac virtual environment to Linux. Transfer data locally before training; the batch training code has no network calls. Keep a second copy of raw data and final model artifacts.

## 2. Create the Linux environment on an allocated compute node

Log in:

```bash
ssh YOUR_SSO@hellbender-login.rnet.missouri.edu
salloc --partition=interactive --nodes=1 --ntasks=1 --cpus-per-task=4 --mem=8G --time=01:00:00
hostname
```

Confirm the hostname is a compute node. If the site's allocation leaves you in a login shell, use `srun --pty bash` inside the allocation and check again.

Find an available Python 3.12 module/environment using the site's module catalog (`module avail` / `module spider Python`); use the actual module name listed for your account. This project does not assume a particular module name.

On the compute node:

```bash
cd /home/YOUR_SSO/data/sports-method
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-tested.txt
python -m pip install --no-deps -e .
python -m pytest -q
bash scripts/smoke.sh
```

Python 3.12 is the tested interpreter family. requirements-tested.txt records the locally verified exact package versions; their Linux wheel/runtime compatibility still needs this smoke check. If software installation requires a different site-supported route, preserve the error output and use an RSS-supported environment. Do not substitute an unrecorded stack and compare runs as identical.

If compute nodes lack outbound package access, obtain a Linux Python 3.12 wheelhouse through an allowed transfer node or supported environment. Mac wheels are incompatible. Then install with `pip install --no-index --find-links WHEELHOUSE -r requirements-tested.txt`. Keep the resolved versions in the run manifest.

## 3. Build the real dataset interactively or in a batch job

The initial recommendation is one node, four CPUs, 8 GB memory. This is a small tabular model; no GPU or distributed training is requested. Start with a 100-game sample to check conversion, then build the full archive. Dataset building may take longer than fitting because it performs temporal joins.

```bash
sports build --data data/normalized/nba-v1 --config configs/first_model.json --out data/processed/nba-v1
sports report --path data/processed/nba-v1/audit.json
```

## 4. Submit training and validation

Return to a submission shell after environment setup. From the project root:

```bash
mkdir -p logs
sbatch slurm/train.sbatch data/processed/nba-v1 configs/first_model.json runs/nba-v1
```

The script requests four CPUs, 8 GB and one hour on general. It trains and evaluates development validation only. Output is logs/train-JOBID.out and .err. If your allocation needs an account, pass your actual `--account=ACCOUNT` to sbatch. No account is invented in the script.

## 5. Monitor the job and retrieve its report

```bash
squeue --me
sacct -j JOBID --format=JobID,State,Elapsed,AllocCPUS,MaxRSS,ExitCode
tail -n 60 logs/train-JOBID.out
tail -n 60 logs/train-JOBID.err
```

Look for COMPLETED with exit code 0:0. Pending is scheduling, not model failure. OUT_OF_MEMORY warrants checking MaxRSS/data size; TIMEOUT warrants reviewing elapsed time and progress. Preserve failed run directories.

Inspect runs/nba-v1/progress.json and trials.json while training, or use Open OnDemand's file viewer. Retrieve the validation PASTE_BACK.md through Globus/DTN and paste it into this chat. Do not send passwords or API keys.

## 6. Final test after validation review

Freeze on an allocated compute node:

```bash
sports freeze --run runs/nba-v1
```

Then submit from the project root:

```bash
sbatch slurm/test.sbatch runs/nba-v1 data/processed/nba-v1
```

Retrieve runs/nba-v1/test/PASTE_BACK.md. A completed job establishes computation success; the report determines what evidence, if any, supports the model.

