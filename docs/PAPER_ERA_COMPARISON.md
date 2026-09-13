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

| Model | Log loss | Brier | Accuracy | ECE |
|---|---|---|---|---|
| home rate | 0.680657 | 0.243781 | 57.89% | 0.0006 |
| Elo | 0.620445 | 0.215560 | 65.28% | 0.0335 |
| logistic (calibrated) | 0.621833 | 0.216284 | 64.96% | 0.0335 |
| logistic (raw) | 0.621066 | 0.215985 | 65.85% | 0.0422 |
| boosted | 0.627116 | 0.218531 | 65.28% | 0.0540 |

Their reported accuracies on this same season: LR 69.23%, RF 68.28%, SVM 68.28%,
MLP 68.02%. Our best is 65.85%, a gap of roughly 3.4 points against their
selected model.

Elo is the best model of ours on this season; logistic minus Elo is +0.001388
with interval [-0.008039, +0.010367], and boosted is worse still at +0.006671.
So in this season our engineered features add nothing over a plain rating
system, which makes the feature gap against the paper more credible, not less.

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

## Testing the feature hypothesis (finding 4 above): it does not hold

Their reported edge suggested box-score features carry information our
margin/rest/Elo set lacks. `sports compare-box` tests that directly: the same
eleven features versus the same set plus nine possession-adjusted differentials
(offensive, defensive and net rating, pace, effective FG%, turnover rate,
offensive rebound rate, free-throw rate, previous-season win rate), on the three
existing development folds, with the same lambda, calibration and fold shape.

Pooled over 3,690 development games:

| Feature set | Log loss | Brier | Accuracy |
|---|---|---|---|
| base (11) | 0.621258 | 0.216074 | 65.26% |
| extended (20) | 0.622048 | 0.216358 | 65.50% |

Extended minus base: **+0.000789 pooled — slightly worse.** Per fold: +0.001103,
-0.000095, +0.001360, and every 95% weekly-block interval includes zero.

Two readings, both worth recording:

1. **The features add nothing here.** Net rating and margin are close relatives,
   and Elo already absorbs opponent-adjusted strength, so the extra columns are
   largely redundant with what the base set encodes. Their apparent value in the
   paper is more plausibly selection - 69.23% was the best of four models on the
   season being reported - than information we were missing.
2. **Accuracy rose while log loss fell.** 65.26% to 65.50% accuracy alongside a
   worse probability score is the same lesson as the ECE finding, from the other
   direction: the metric you select on decides what you conclude. Selecting on
   accuracy here would have adopted a worse forecaster.

The base feature set is therefore retained unchanged, and the deployment release
frozen for 2026-27 stands. Nothing is promoted on the strength of development
folds that have been inspected this many times.

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

All figures above are from canonical local runs (`runs/paper-era-v1` and
`runs/paper-era-2017-18`, Python 3.12, xgboost 3.4.1).

Both were also run in a Linux sandbox (Python 3.11, xgboost 3.2.0) and compared. Home rate and Elo agreed exactly;
calibrated logistic agreed to 1e-9 on 2018/19 (0.6189004551 local vs 0.6189004541
sandbox) and to 3e-10 on 2017/18, both L-BFGS convergence noise; boosted moved by
3e-4 and 2e-4 respectively on the xgboost version change. Conclusions rest on the logistic and Elo comparison and
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
