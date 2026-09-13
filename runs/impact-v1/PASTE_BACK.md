# Player-impact research comparison

Research only: no odds, ROI, stakes, or evidence of beating bookmakers. Schedule observation times are reconstructed; result availability assumes +24h after scheduled start. Historical revisions are not verified. Validation is development data; repeated optimization can overfit it.

RESEARCH CANDIDATE. Availability-extended model versus the same plus impact weights: for each listed player on a usable snapshot, mean minutes over the last 10 of their own games whose results were available before the cutoff, summed per declared status per side, home minus away, plus Out scoring and an unmatched-player indicator. Player logs joined to result availability by game id, so last night's minutes are excluded when not yet available. Statuses remain declared only; actual absence is never substituted. Reports were backfilled; development evidence only, repeated inspection risks overfitting. Primary contrast is impact minus availability-extended.

Listed-player match rate: 84.2% (45479 matched, 8562 unmatched).

- 2022-23: impact minus extended -0.003738; 95% block interval [-0.009305, +0.001849]  (includes zero)
- 2023-24: impact minus extended -0.003635; 95% block interval [-0.008864, +0.001269]  (includes zero)
- 2024-25: impact minus extended -0.008019; 95% block interval [-0.012761, -0.003580]  (excludes zero)

Pooled impact minus extended log loss: -0.005131

Development evidence only; adoption would require a new frozen release and prospective capture.
