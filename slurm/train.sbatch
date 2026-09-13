#!/usr/bin/env bash
#SBATCH --job-name=nba-v1-train
#SBATCH --partition=general
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=01:00:00
#SBATCH --output=logs/train-%j.out
#SBATCH --error=logs/train-%j.err
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?Submit from the project root}"
source .venv/bin/activate
export OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
dataset="${1:?Pass dataset directory}"
config="${2:?Pass config JSON}"
run="${3:?Pass new output directory}"
python -m sports_method.cli train --dataset "$dataset" --config "$config" --out "$run"
python -m sports_method.cli evaluate --run "$run" --dataset "$dataset" --split validation

