# NFL development: baselines versus regularized challenger

Research only: no odds, ROI, stakes, or evidence of beating bookmakers. Kickoff times were converted from US Eastern by us and schedule observation times are reconstructed, not provider timestamps. Result availability assumes kickoff plus 24h. Development folds may be inspected repeatedly and can be overfit; they are not confirmation.

Prespecified before any holdout use: the challenger advances only if its pooled DECIDED log loss beats the better of the two baselines across all three development folds AND the pooled paired difference has a 95% week-block interval excluding zero. Three-way log loss must not be worse. Meeting these criteria authorises one single scoring of the reserved 2025 season; it does not authorise deployment or any wager.

Games 6447 (ties 14); folds [2022, 2023, 2024]; 2025 reserved; 2026 prospective.

| fold | model | decided log loss | decided Brier | acc | 3-way log loss |
|---|---|---|---|---|---|
| 2022 | home_rate | 0.685636 | 0.246254 | 0.5613 | 0.728301 |
| 2022 | elo | 0.680398 | 0.241403 | 0.6097 | 0.723101 |
| 2022 | logistic | 0.652487 | 0.229875 | 0.6245 | 0.695397 |
| 2023 | home_rate | 0.687177 | 0.247020 | 0.5551 | 0.689299 |
| 2023 | elo | 0.675137 | 0.239390 | 0.6250 | 0.677259 |
| 2023 | logistic | 0.647153 | 0.227943 | 0.6176 | 0.649275 |
| 2024 | home_rate | 0.692756 | 0.249795 | 0.5331 | 0.695101 |
| 2024 | elo | 0.622441 | 0.217230 | 0.6507 | 0.624786 |
| 2024 | logistic | 0.632872 | 0.221402 | 0.6544 | 0.635217 |
| pooled | home_rate | 0.688534 | 0.247695 | 0.5498 | 0.704061 |
| pooled | elo | 0.659247 | 0.232642 | 0.6285 | 0.674847 |
| pooled | logistic | 0.644140 | 0.226394 | 0.6322 | 0.659777 |

- logistic minus home_rate: -0.044394; 95% week-block interval [-0.062161, -0.025827]  (excludes zero)
- logistic minus elo: -0.015107; 95% week-block interval [-0.030797, +0.000159]  (includes zero)

Advancement criteria met: **False** (stronger baseline: elo).
No holdout was read. No odds, stake or wager is involved.
