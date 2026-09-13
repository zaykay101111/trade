#!/usr/bin/env bash
set -euo pipefail
# Run from project root with the environment activated.
demo_root="runs/smoke-$(date -u +%Y%m%dT%H%M%SZ)"
sports demo --out "$demo_root/raw"
sports build --data "$demo_root/raw" --config "$demo_root/raw/config.json" --out "$demo_root/dataset"
sports train --dataset "$demo_root/dataset" --config "$demo_root/raw/config.json" --out "$demo_root/model"
sports evaluate --run "$demo_root/model" --dataset "$demo_root/dataset" --split validation
sports freeze --run "$demo_root/model"
sports evaluate --run "$demo_root/model" --dataset "$demo_root/dataset" --split test
sports report --path "$demo_root/model/test"

