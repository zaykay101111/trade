# Final holdout evaluation (one use, odds-free)

Research only: no odds, ROI, stakes, or evidence of beating bookmakers. Schedule observation times are reconstructed; result availability assumes +24h after scheduled start. Historical revisions are not verified. Validation is development data; repeated optimization can overfit it.

This record is the single agreed test of the frozen candidate on 2025-26.
2025-26 is now development data and cannot back any later fresh-holdout claim.

Frozen candidate: logistic regression, all eleven features, lambda=0.01, sigmoid calibration
Boundaries (exclusive UTC): start 2020-07-01; train 2024-07-01; tune 2025-01-01; calibration 2025-07-01; holdout 2026-07-01
Split counts: {'train': 4770, 'tune': 471, 'calibration': 749, 'holdout': 1230}
Labels excluded at fitting cutoffs: 10
Code sha256: 13a835fd5f0dded149732a105e2a8f369b9b210ac8709e673b23c1271fb745a6
Data sha256: {'games.csv': '32d3037da5088ea9a726a2fc561b7fcb8a2230bef3007742f3602449df691d73', 'results.csv': '62e88041b0d981f0bb1307144fd6a0dcf616a4fefae8b3f2ed36997b088e97e2', 'manifest.json': '4abaa63ebf6c6df0878974701f432646e9a212dc76ac121a5a1df318c72f2bf0'}

## Primary (confirmatory)
- Calibrated logistic log loss: 0.606802
- Logistic minus Elo: -0.008525; 95% block interval [-0.016040, -0.001502]
- Interval excludes zero.

## Secondary (pre-specified, descriptive)
- home_rate: log loss=0.687205; Brier=0.247035; accuracy=55.45%
- elo: log loss=0.615328; Brier=0.212253; accuracy=67.72%
- logistic: log loss=0.606802; Brier=0.209140; accuracy=67.80%
- boosted: log loss=0.609174; Brier=0.210161; accuracy=67.80%
- logistic_raw: log loss=0.605870; Brier=0.208912; accuracy=67.64%
- boosted_raw: log loss=0.609899; Brier=0.210427; accuracy=67.97%
- logistic_minus_home_rate: -0.080402; 95% block interval [-0.112684, -0.043242]
- boosted_minus_elo: -0.006154; 95% block interval [-0.016133, +0.003319]
- Holdout calibration diagnostic (intercept/slope, reported not applied): elo=-0.082/0.880; logistic=+0.078/0.887; boosted=+0.064/0.949

Reliability bins: count / mean predicted / observed
- elo: 5 / 0.079 / 0.000; 39 / 0.175 / 0.103; 80 / 0.248 / 0.287; 160 / 0.355 / 0.331; 159 / 0.449 / 0.415; 177 / 0.554 / 0.548; 206 / 0.651 / 0.660; 214 / 0.751 / 0.710; 150 / 0.846 / 0.793; 40 / 0.922 / 0.800
- logistic: 10 / 0.072 / 0.100; 74 / 0.159 / 0.162; 112 / 0.255 / 0.277; 140 / 0.353 / 0.393; 192 / 0.448 / 0.464; 186 / 0.553 / 0.618; 187 / 0.650 / 0.636; 165 / 0.747 / 0.745; 132 / 0.848 / 0.841; 32 / 0.927 / 0.812
- boosted: 40 / 0.185 / 0.200; 139 / 0.247 / 0.230; 164 / 0.355 / 0.329; 203 / 0.453 / 0.507; 191 / 0.551 / 0.644; 146 / 0.643 / 0.637; 165 / 0.757 / 0.739; 182 / 0.831 / 0.808

## Exploratory (not confirmatory, not multiplicity-corrected)

Monthly log loss:
- 2025-10, n=76: home_rate=0.6820; elo=0.6560; logistic=0.6553; boosted=0.6391
- 2025-11, n=221: home_rate=0.6868; elo=0.6060; logistic=0.5941; boosted=0.5914
- 2025-12, n=197: home_rate=0.6918; elo=0.7129; logistic=0.7010; boosted=0.7004
- 2026-01, n=232: home_rate=0.6860; elo=0.6710; logistic=0.6748; boosted=0.6721
- 2026-02, n=167: home_rate=0.7046; elo=0.6335; logistic=0.6078; boosted=0.6133
- 2026-03, n=239: home_rate=0.6778; elo=0.5138; logistic=0.5106; boosted=0.5231
- 2026-04, n=98: home_rate=0.6792; elo=0.4937; logistic=0.4804; boosted=0.4966
Neutral-site subset: n=5 (too few for inference).
Extra result-availability delay scenarios (refit and recalibrated under delay):
- +24h: home_rate=0.687205; elo=0.616404; logistic=0.609478; boosted=0.612598
  change vs baseline: home_rate=+0.000000; elo=+0.001077; logistic=+0.002676; boosted=+0.003424
- +48h: home_rate=0.687206; elo=0.616597; logistic=0.609856; boosted=0.610109
  change vs baseline: home_rate=+0.000001; elo=+0.001269; logistic=+0.003053; boosted=+0.000935

Intervals exclude training and model-selection uncertainty and are not corrected
for the development experiments already performed. No ROI, stake sizing, executable
price or market edge is demonstrated or implied by anything above.
Saved-model replay maximum absolute difference: 0.00e+00.
Full metrics: report.json. Model and provenance: bundle.json, freeze.json, HOLDOUT_CONSUMED.json.
