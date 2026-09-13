"""Small predeclared chronological penalty selection experiment."""
from pathlib import Path
import numpy as np
import pandas as pd
from .free_data import FEATURES, load_games, build_features
from .free_train import partition, metrics, paired_interval, WARNING
from .free_validate import YEARS, fold_boundaries
from .free_ablate import fit_variant
from .model import fit_logistic, predict_logistic
from .io import new_dir, write_json, code_hash, digest, now

PENALTIES = (.001, .01, .1, 1.)


def select_penalty(train, tune):
    trials = []
    for l2 in PENALTIES:
        model = fit_logistic(train[FEATURES].to_numpy(), train.y.to_numpy(), np.full(len(train), .5), l2=l2)
        p = predict_logistic(model, tune[FEATURES].to_numpy(), np.full(len(tune), .5))
        trials.append({'l2': l2, 'tune_log_loss': metrics(tune.y, p)['log_loss']})
    # Exact ties prefer stronger shrinkage. No validation/calibration labels here.
    return min(trials, key=lambda r: (r['tune_log_loss'], -r['l2']))['l2'], trials


def regularize_free(data, out):
    data = Path(data)
    if Path(out).exists():
        raise FileExistsError(f'Output exists: {out}')
    raw = load_games(data)
    dev = raw[raw.decision_at < pd.Timestamp('2025-07-01', tz='UTC')].copy()
    features = build_features(dev)
    out = new_dir(out)
    features.to_csv(out/'development_features.csv', index=False)
    protocol = ('Fixed grid .001/.01/.1/1; minimize prior tuning-period RAW log loss, '
        'then refit on train+tune and fit sigmoid on separate calibration data. '
        'Objective: mean binary log loss + lambda * sum(standardized slope squared); intercept unpenalized. '
        'Same full features and imported +24h availability; no delay grid or feature removal. '
        'Compare selected policy with fixed .01, not a hindsight-best validation penalty. '
        'Previously inspected development folds, overlapping training, no independent confirmation. '
        'Weekly-block intervals exclude training/selection uncertainty and multiple-testing correction. '
        'No automatic promotion or change to training defaults; final holdout unscored.')
    report = {'created_at': now(), 'warning': WARNING, 'protocol': protocol,
              'grid': PENALTIES, 'folds': {}, 'pooled': {}, 'final_holdout': 'NOT SCORED',
              'code_sha256': code_hash(), 'data_sha256': {n:digest(data/n) for n in ('games.csv','results.csv')}}
    pooled = {'fixed': [], 'selected': []}
    for year in YEARS:
        season = f'{year}-{str(year+1)[-2:]}'
        parts = partition(features, fold_boundaries(year))
        selected, trials = select_penalty(parts['train'], parts['tune'])
        combined = pd.concat([parts['train'], parts['tune']])
        cal, val = parts['calibration'], parts['validation']
        fold = {'selected_l2': selected, 'trials': trials, 'boundaries': fold_boundaries(year),
                'split_counts': {k:len(v) for k,v in parts.items()}, 'models': {},
                'neutral_counts': {'refit': int(combined.neutral.sum()), 'calibration': int(cal.neutral.sum()), 'validation': int(val.neutral.sum())}}
        report['folds'][season] = fold
        predictions = {}
        for name, l2 in (('fixed', .01), ('selected', selected)):
            bundle, raw_p, p = fit_variant(combined, cal, val, FEATURES, l2=l2)
            child = new_dir(out/f'{season}-{name}')
            write_json(child/'bundle.json', {**bundle, 'boundaries': fold['boundaries'],
                'code_sha256': report['code_sha256'], 'data_sha256': report['data_sha256']})
            pred = val[['game_id','decision_at','y']].copy()
            pred['p_raw'], pred['p'] = raw_p, p
            pred.to_csv(child/'validation_predictions.csv', index=False)
            pooled[name].append(pred); predictions[name] = p
            fold['models'][name] = {'l2': l2, 'metrics': metrics(val.y, p), 'raw_metrics': metrics(val.y, raw_p),
                                    'calibrator': bundle['calibrator'],
                                    'standardized_slope_norm': float(np.linalg.norm(bundle['logistic']['coef'][1:]))}
        fold['selected_minus_fixed'] = paired_interval(val, predictions['selected'], predictions['fixed'])
        write_json(out/'progress.json', {'completed_folds': len(report['folds']), 'total_folds': 3})
        print(f'{season}: selected lambda={selected}', flush=True)
    base = pd.concat(pooled['fixed'], ignore_index=True)
    if base.game_id.duplicated().any():
        raise ValueError('Overlapping validation games')
    for name, frames in pooled.items():
        frame = pd.concat(frames, ignore_index=True)
        if not frame[['game_id','decision_at','y']].equals(base[['game_id','decision_at','y']]):
            raise ValueError('Comparators must score identical games')
        report['pooled'][name] = {'games': len(frame), 'metrics': metrics(frame.y, frame.p), 'raw_metrics': metrics(frame.y, frame.p_raw)}
    write_json(out/'report.json', report)
    lines = ['# Chronological regularization check', '', WARNING, '', protocol, '', 'Final holdout: NOT SCORED.', '']
    for season, fold in report['folds'].items():
        lines.append(f"{season}: selected lambda={fold['selected_l2']}; neutral counts={fold['neutral_counts']}")
        lines.append('Tuning raw log loss: ' + '; '.join(f"{t['l2']}={t['tune_log_loss']:.6f}" for t in fold['trials']))
        for name,r in fold['models'].items():
            lines.append(f"- {name}: calibrated log loss={r['metrics']['log_loss']:.6f}; Brier={r['metrics']['brier']:.6f}; raw log loss={r['raw_metrics']['log_loss']:.6f}")
        ci = fold['selected_minus_fixed']
        lines.extend([f"Selected minus fixed: {ci['difference']:+.6f}; 95% block interval [{ci['ci95'][0]:+.6f}, {ci['ci95'][1]:+.6f}]", ''])
    lines.append('Pooled descriptive metrics:')
    for name,r in report['pooled'].items():
        lines.append(f"- {name}: n={r['games']}; log loss={r['metrics']['log_loss']:.6f}; Brier={r['metrics']['brier']:.6f}; raw log loss={r['raw_metrics']['log_loss']:.6f}")
    lines.extend(['', 'Negative selected-minus-fixed favors tuning. Calibration can offset shrinkage; judge both raw and calibrated results.',
                  'Do not expand the grid based on validation wins or automatically replace the baseline.'])
    (out/'PASTE_BACK.md').write_text('\n'.join(lines)+'\n')
    return {'run': str(out), 'completed_folds': 3, 'final_holdout': 'NOT SCORED', 'report_command': f'sports report --path "{out}"'}
