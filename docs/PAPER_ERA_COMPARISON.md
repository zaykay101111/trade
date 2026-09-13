# External comparison: Walsh & Joshi (arXiv:2303.06021v2)

"Machine learning for sports betting: should model selection be based on accuracy
or calibration?" Trains LR/RF/SVM/MLP on NBA 2014/15-2017/18, then simulates
betting on 2018/19 using Westgate CLOSING moneylines obtained from
sportsbookreviewsonline, with Kelly staking. Headline: the calibration-selected
model returns far more than the accuracy-selected one.

## What they report

- Test season 2017/18 accuracy: LR 69.23%, RF 68.28%, SVM 68.28%, MLP 68.02%.
- Test season 2017/18 classwise-ECE: SVM 3.49%, RF 4.06%, LR 5.64%, MLP 5.71%.
- Betting season 2018/19: ROI only. No accuracy, calibration, log loss or Brier
  is reported for the season the conclusions rest on.
- Features: FG, 3P, FT%, ORB, DRB, BLK, PF, AST%, STL%, DRB%, BPM and previous
  season record.

## What we ran

Dataset `data/normalized/nba-paper-era-v2`: the same five seasons, 6,150 games,
1,230 per season, built from nba_api ScheduleLeagueV2. Scores come from the
cached schedule JSON; equivalence with the LeagueGameFinder team logs used
elsewhere was verified on nba-v3 at 7,230/7,230 games with zero mismatches.

The frozen candidate recipe was applied unchanged via `sports replicate-external`,
with our usual fold shape, on two evaluation seasons: their betting season
(2018/19) and their test season (2017/18), the latter for a like-for-like
accuracy comparison.

### Their betting season, 2018/19 (n=1,230)

| Model | Log loss | Brier | Accuracy | ECE |
|---|---|---|---|---|
| home rate | 0.676087 | 0.241516 | 59.27% | 0.0103 |
| Elo | 0.620843 | 0.215670 | 65.69% | 0.0391 |
| logistic (calibrated) | 0.618900 | 0.214425 | 65.20% | 0.0523 |
| logistic (raw) | 0.614883 | 0.212967 | 66.18% | 0.0470 |
| boosted | 0.620616 | 0.215332 | 64.72% | 0.0481 |

Logistic minus Elo: -0.001943, 95% weekly-block interval [-0.009094, +0.005335].
**Includes zero: no confirmed advantage over Elo in this era**, unlike the
2025-26 holdout (-0.008525, interval excluded zero) and pooled 2022-25
development (-0.0088). All models beat the constant home rate decisively
(logistic -0.057186, interval [-0.085804, -0.028518]).

### Their test season, 2017/18 (n=1,230)

Our accuracy 64.96% calibrated, 65.85% raw; Elo 65.28%. Their reported 69.23%.

## What we learned

**1. ECE alone selects the useless model.** On both seasons the constant home-rate
predictor has the LOWEST calibration error of any model we ran (0.0103 in
2018/19; 0.0006 in 2017/18) while being by far the worst forecaster. A constant
equal to the base rate is perfectly calibrated and has zero discrimination. This
is the exact failure the paper patches with a "platykurtic" constraint on bin
weights that the authors themselves call "somewhat arbitrary". Our numbers show
quantitatively why that patch was necessary, and that it is treating a symptom.

The principled version of the paper's thesis is a strictly proper scoring rule.
Log loss decomposes into calibration plus refinement, so selecting on it
penalizes miscalibration AND rewards discrimination, with no ad-hoc constraint
and no binning choice. This project already selects on log loss; the paper is an
argument for what we do, not a reason to change it. We now also report ECE and
classwise-ECE purely for comparability with this literature.

**2. Their headline is not established by their own statistics.** Reported
significance is p=0.153 across strategies and p=0.053 for one strategy at a 10%
threshold. The abstract (+34.69% vs -35.17%) and the body (110.42% vs 2.98%)
disagree depending on aggregation. The best case, 902% ROI, is full-Kelly on one
season; full Kelly on estimated probabilities is known over-betting and its
outcome distribution is extremely skewed. One season, one book, one realisation.

**3. Closing odds cannot support the claim.** The closing line is the sharpest
price of the day and already contains injury and lineup news that neither their
features nor ours observe. Betting into it retrospectively says nothing about
whether that price was available when a decision was made. This is the same
reason this project refuses to substitute closing odds for prediction-cutoff
odds.

**4. Their accuracy edge is plausibly real and worth pursuing.** Even discounting
that 69.23% is the maximum of four models on the season being reported, a 3-4
point gap over our 65-66% is larger than the ~1.3 point standard error of a
single season. The likely source is their feature set: shooting splits,
rebounding rates, BPM and previous-season record, versus our margin/Elo/rest
inputs. All of those are available free from nba_api. This is the strongest
concrete modelling lead to come out of the comparison.

**5. The eras differ materially.** Home win rate was 58.4% across 2014-2019
versus roughly 55% across 2020-2026, and the constant baseline is correspondingly
stronger in the older era (accuracy 59.27% in 2018/19). Our edge over Elo is
weaker there. Cross-era results are context, not replication.

**6. Calibration cost us slightly in both eras.** Raw logistic beat calibrated
logistic on 2018/19 (0.614883 vs 0.618900) and on the 2025-26 holdout (0.605870
vs 0.606802). Fitting a sigmoid on a half-season slice appears to add more noise
than it removes. Worth investigating in development; it does not change any
frozen result.


**7. Boosted trees are indistinguishable from Elo in this era.** Boosted minus Elo
is -0.000228 with interval [-0.008546, +0.007300] - effectively zero, consistent
with the 2025-26 holdout where the same comparison also spanned zero. Across two
untouched eras, the gradient-boosted challenger has never separated from a fixed
Elo rating. That is a reason to keep it strictly secondary.

## Reproducing

```bash
python scripts/results_from_schedule.py --data data/normalized/nba-paper-era-v2
sports replicate-external --data data/normalized/nba-paper-era-v2 \
  --out runs/paper-era-v1 --threads 2 --label "Walsh & Joshi era 2014-15..2018-19"
sports replicate-external --data data/normalized/nba-paper-era-v2 \
  --out runs/paper-era-2017-18 --threads 2 --label "paper test season 2017-18" \
  --start 2014-07-01 --train-end 2016-07-01 --tune-end 2017-01-01 \
  --calibration-end 2017-07-01 --evaluation-end 2018-07-01
```

All figures above are from the canonical local run (`runs/paper-era-v1`,
Python 3.12, xgboost 3.4.1), except the 2017/18 accuracy comparison, which used a
Linux sandbox (Python 3.11, xgboost 3.2.0) and reports a logistic figure.

The two environments were compared directly. Home rate and Elo agreed exactly;
calibrated logistic agreed to 1e-9 (0.6189004551 local vs 0.6189004541 sandbox,
L-BFGS convergence noise); boosted moved by 3e-4 (0.620616 vs 0.620910) on the
xgboost version change. Conclusions rest on the logistic and Elo comparison and
are unaffected.

## Data note

`data/normalized/nba-paper-era` (first attempt) contains only 1,230 games and
should not be used: four of the five seasons carry `postponedStatus='A'` on every
row, including all 1,230 completed regular-season games, while 2018/19 uses 'N'.
This is the same legacy provider coding that cost 2021-22 and 2023-24 earlier,
verified season by season before `--include-postponed` was used for the corrected
`nba-paper-era-v2`. It remains a targeted, evidenced exception, not a default.

`isNeutral` is false for all 6,150 rows in this era, although London and Mexico
City games were played in it. The provider flag is unusable here, so the `neutral`
feature is constant zero for the whole era and contributes nothing. Venue
corrections were NOT auto-applied: relabelling would need the same reviewed,
source-cited treatment as venues.py, and ablations put the neutral flag's
contribution near zero anyway.
