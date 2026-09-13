#!/usr/bin/env bash
#SBATCH --job-name=nba-v1-test
#SBATCH --partition=general
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --output=logs/test-%j.out
#SBATCH --error=logs/test-%j.err
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?Submit from the project root}"
source .venv/bin/activate
export OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export OPENBLAS_NUM_THREADS=1
python -m sports_method.cli evaluate --run "${1:?run directory}" --dataset "${2:?dataset directory}" --split test

