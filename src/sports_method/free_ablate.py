"""Predeclared leave-one-group-out logistic development experiments."""
from pathlib import Path
import platform
import numpy as np
import pandas as pd
from .free_data import FEATURES, load_games, build_features
from .free_train import partition, metrics, paired_interval, WARNING
from .free_validate import YEARS, fold_boundaries
from .model import fit_logistic, predict_logistic, fit_calibration, calibrate
from .io import new_dir, write_json, digest, code_hash, now

GROUPS = {
    "scoring": ["margin_diff", "scored_diff", "allowed_diff"],
    "recent_wins": ["win_rate_diff"],
    "history_count": ["history_count_diff"],
    "rest": ["home_rest", "away_rest", "home_b2b", "away_b2b"],
    "elo": ["elo_diff"],
    "neutral": ["neutral"],
}


def variants():
    return {"full": list(FEATURES), **{
        "without_"+name: [f for f in FEATURES if f not in group]
        for name, group in GROUPS.items()}}


def fit_variant(combined, cal, val, columns, *, l2=.01):
    """Refit scaler/coefficients and calibration, never zero trained columns."""
    if not columns or not set(columns).issubset(FEATURES) or len(set(columns)) != len(columns):
        raise ValueError("Invalid ablation feature list")
    model = fit_logistic(combined[columns].to_numpy(), combined.y.to_numpy(), np.full(len(combined), .5), l2=l2)
    def predict(frame):
        return predict_logistic(model, frame[columns].to_numpy(), np.full(len(frame), .5))
    c = fit_calibration(predict(cal), cal.y.to_numpy())
    raw = predict(val)
    return {"features": columns, "logistic": model, "calibrator": c, "l2": l2}, raw, calibrate(raw, c)


def ablate_free(data, out):
    data = Path(data)
    if Path(out).exists():
        raise FileExistsError(f"Output exists: {out}; choose a new directory")
    raw = load_games(data)
    dev = raw[raw.decision_at < pd.Timestamp('2025-07-01', tz='UTC')].copy()
    features = build_features(dev)
    out = new_dir(out)
    features.to_csv(out/'development_features.csv', index=False)
    protocol = ("Seven fixed logistic variants across three chronological development seasons. "
        "Remove one group at a time, refit scaler/coefficients and sigmoid calibration. "
        "Imported availability is unchanged (assumed +24h); no additional delay. "
        "Positive ablated-minus-full log-loss difference favors keeping the group. "
        "These are previously inspected development seasons; intervals are descriptive, "
        "not corrected for multiple comparisons and exclude training/selection uncertainty. "
        "Folds share training history; pooled metrics are descriptive. No automatic feature removal. "
        "Scoring columns are removed together because margin=scored-allowed. "
        "This measures conditional predictive contribution, not causal importance. "
        "Removing neutral removes only the direct input, not venue effects embedded in historical Elo.")
    report = {"created_at": now(), "warning": WARNING, "protocol": protocol,
        "final_holdout": "NOT SCORED", "groups": GROUPS, "variants": variants(),
        "folds": {}, "pooled": {}, "code_sha256": code_hash(),
        "data_sha256": {f: digest(data/f) for f in ('games.csv', 'results.csv')},
        "versions": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__}}
    pooled = {name: [] for name in variants()}
    completed = 0
    for year in YEARS:
        season = f'{year}-{str(year+1)[-2:]}'
        parts = partition(features, fold_boundaries(year))
        combined = pd.concat([parts['train'], parts['tune']])
        cal, val = parts['calibration'], parts['validation']
        fold = {"boundaries": fold_boundaries(year), "split_counts": {k:len(v) for k,v in parts.items()},
                "constant_training_features": [c for c in FEATURES if combined[c].nunique() <= 1], "variants": {}}
        report['folds'][season] = fold
        full_p = full_raw = None
        for name, columns in variants().items():
            bundle, raw_p, p = fit_variant(combined, cal, val, columns)
            if name == 'full':
                full_p, full_raw = p, raw_p
            child = new_dir(out/f'{season}-{name}')
            write_json(child/'bundle.json', {**bundle, "boundaries": fold['boundaries'],
                "code_sha256": report['code_sha256'], "data_sha256": report['data_sha256']})
            pred = val[['game_id', 'decision_at', 'y']].copy()
            pred['p_raw'], pred['p'] = raw_p, p
            pred.to_csv(child/'validation_predictions.csv', index=False)
            pooled[name].append(pred)
            fold['variants'][name] = {"metrics": metrics(val.y, p), "raw_metrics": metrics(val.y, raw_p),
                "vs_full": paired_interval(val, p, full_p),
                "raw_log_loss_change": metrics(val.y, raw_p)['log_loss']-metrics(val.y, full_raw)['log_loss'],
                "mean_absolute_probability_change": float(np.abs(p-full_p).mean())}
            completed += 1
            write_json(out/'progress.json', {"completed": completed, "total": 21, "last_completed": child.name})
        print(f"Completed {season}: 7 logistic variants", flush=True)
    baseline = pd.concat(pooled['full'], ignore_index=True)
    if baseline.game_id.duplicated().any():
        raise ValueError('Overlapping validation games')
    for name, frames in pooled.items():
        frame = pd.concat(frames, ignore_index=True)
        if not frame[['game_id','decision_at','y']].equals(baseline[['game_id','decision_at','y']]):
            raise ValueError('Variants must evaluate identical games and outcomes')
        m = metrics(frame.y, frame.p)
        report['pooled'][name] = {"games": len(frame), "metrics": m,
            "raw_metrics": metrics(frame.y, frame.p_raw),
            "log_loss_change_vs_full": m['log_loss']-metrics(baseline.y, baseline.p)['log_loss'],
            "seasons_removal_hurts": sum(f['variants'][name]['vs_full']['difference'] > 1e-10 for f in report['folds'].values())}
    write_json(out/'report.json', report)
    lines = ['# Logistic feature-ablation report', '', WARNING, '', protocol,
             '', 'Final holdout: NOT SCORED.', '', 'Pooled development results (3,690 games for complete NBA input):']
    for name, r in report['pooled'].items():
        m = r['metrics']
        lines.append(f"- {name}: n={r['games']}; log loss={m['log_loss']:.6f}; Brier={m['brier']:.6f}; change vs full={r['log_loss_change_vs_full']:+.6f}; removal hurts in {r['seasons_removal_hurts']}/3 seasons")
    lines.extend(['', 'Per-season ablated-minus-full log-loss differences; positive favors keeping group:'])
    for season, fold in report['folds'].items():
        lines.append(f"- {season}: constant training inputs={fold['constant_training_features']}")
        for name, r in fold['variants'].items():
            if name == 'full':
                continue
            ci = r['vs_full']
            lines.append(f"  {name}: {ci['difference']:+.6f}; 95% weekly-block interval [{ci['ci95'][0]:+.6f}, {ci['ci95'][1]:+.6f}]; raw change={r['raw_log_loss_change']:+.6f}")
    lines.extend(['', 'Do not treat an interval containing zero as proof of no contribution.',
                  'No combined subset is selected or tested by this command. Each child saves a refitted model and predictions.'])
    (out/'PASTE_BACK.md').write_text('\n'.join(lines)+'\n')
    return {"run": str(out), "completed": completed, "final_holdout": "NOT SCORED",
            "report_command": f'sports report --path "{out}"'}
