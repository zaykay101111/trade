# Chronological regularization check

Research only: no odds, ROI, stakes, or evidence of beating bookmakers. Schedule observation times are reconstructed; result availability assumes +24h after scheduled start. Historical revisions are not verified. Validation is development data; repeated optimization can overfit it.

Fixed grid .001/.01/.1/1; minimize prior tuning-period RAW log loss, then refit on train+tune and fit sigmoid on separate calibration data. Objective: mean binary log loss + lambda * sum(standardized slope squared); intercept unpenalized. Same full features and imported +24h availability; no delay grid or feature removal. Compare selected policy with fixed .01, not a hindsight-best validation penalty. Previously inspected development folds, overlapping training, no independent confirmation. Weekly-block intervals exclude training/selection uncertainty and multiple-testing correction. No automatic promotion or change to training defaults; final holdout unscored.

Final holdout: NOT SCORED.

2022-23: selected lambda=0.1; neutral counts={'refit': 0, 'calibration': 0, 'validation': 2}
Tuning raw log loss: 0.001=0.650361; 0.01=0.643630; 0.1=0.639312; 1.0=0.664929
- fixed: calibrated log loss=0.647034; Brier=0.227182; raw log loss=0.647790
- selected: calibrated log loss=0.648646; Brier=0.227977; raw log loss=0.649199
Selected minus fixed: +0.001612; 95% block interval [-0.001283, +0.004137]

2023-24: selected lambda=0.1; neutral counts={'refit': 1, 'calibration': 1, 'validation': 4}
Tuning raw log loss: 0.001=0.669987; 0.01=0.665781; 0.1=0.659754; 1.0=0.665296
- fixed: calibrated log loss=0.609683; Brier=0.210956; raw log loss=0.611575
- selected: calibrated log loss=0.610485; Brier=0.211777; raw log loss=0.620882
Selected minus fixed: +0.000802; 95% block interval [-0.003941, +0.004986]

2024-25: selected lambda=0.01; neutral counts={'refit': 5, 'calibration': 1, 'validation': 5}
Tuning raw log loss: 0.001=0.603627; 0.01=0.602498; 0.1=0.614261; 1.0=0.653753
- fixed: calibrated log loss=0.607059; Brier=0.210083; raw log loss=0.607044
- selected: calibrated log loss=0.607059; Brier=0.210083; raw log loss=0.607044
Selected minus fixed: +0.000000; 95% block interval [+0.000000, +0.000000]

Pooled descriptive metrics:
- fixed: n=3690; log loss=0.621258; Brier=0.216074; raw log loss=0.622136
- selected: n=3690; log loss=0.622063; Brier=0.216613; raw log loss=0.625708

Negative selected-minus-fixed favors tuning. Calibration can offset shrinkage; judge both raw and calibrated results.
Do not expand the grid based on validation wins or automatically replace the baseline.
