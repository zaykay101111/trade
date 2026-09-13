import argparse
import json
import sys
from pathlib import Path
from .io import read_json

def main():
    parser=argparse.ArgumentParser(description="NBA first-model research and paper monitoring")
    sub=parser.add_subparsers(dest="command",required=True)
    p=sub.add_parser("regularize-free", help="Chronological four-value logistic penalty check")
    p.add_argument("--data", required=True);p.add_argument("--out", required=True)
    p=sub.add_parser("correct-venues", help="Apply six reviewed neutral-venue overrides into a new dataset")
    p.add_argument("--data", required=True);p.add_argument("--out", required=True)
    p=sub.add_parser("ablate-free", help="Leave-one-group-out logistic development checks")
    p.add_argument("--data", required=True);p.add_argument("--out", required=True)
    p=sub.add_parser("validate-free", help="Rolling development seasons and result-delay sensitivity")
    p.add_argument("--data", required=True);p.add_argument("--out", required=True)
    p.add_argument("--threads", type=int, default=2)
    p=sub.add_parser("train-free", help="Train offline statistics-only models; leave final season unscored")
    p.add_argument("--data", required=True);p.add_argument("--out", required=True)
    p.add_argument("--threads", type=int, default=2)
    p=sub.add_parser("demo");p.add_argument("--out",required=True);p.add_argument("--config",default="configs/first_model.json");p.add_argument("--games",type=int,default=1200)
    p=sub.add_parser("build");p.add_argument("--data",required=True);p.add_argument("--config",required=True);p.add_argument("--out",required=True)
    p=sub.add_parser("train");p.add_argument("--dataset",required=True);p.add_argument("--config",required=True);p.add_argument("--out",required=True)
    p=sub.add_parser("evaluate");p.add_argument("--run",required=True);p.add_argument("--dataset",required=True);p.add_argument("--split",choices=["validation","test"],required=True)
    p=sub.add_parser("freeze");p.add_argument("--run",required=True)
    p=sub.add_parser("report");p.add_argument("--path",required=True)
    p=sub.add_parser("plan-odds");p.add_argument("--games",required=True);p.add_argument("--out",required=True)
    p=sub.add_parser("fetch-odds");p.add_argument("--plan",required=True);p.add_argument("--out",required=True);p.add_argument("--execute",action="store_true");p.add_argument("--max-requests",type=int,default=0)
    p=sub.add_parser("normalize-odds");p.add_argument("--raw",required=True);p.add_argument("--mapping",required=True);p.add_argument("--out",required=True);p.add_argument("--config",default="configs/first_model.json")
    p=sub.add_parser("import-nba-results");p.add_argument("--raw",required=True);p.add_argument("--games",required=True);p.add_argument("--out",required=True)
    p=sub.add_parser("paper-issue");p.add_argument("--run",required=True);p.add_argument("--dataset",required=True);p.add_argument("--ledger",required=True)
    p=sub.add_parser("paper-check");p.add_argument("--ledger",required=True);p.add_argument("--game",required=True);p.add_argument("--price",type=float);p.add_argument("--available",action="store_true")
    p=sub.add_parser("paper-settle");p.add_argument("--ledger",required=True);p.add_argument("--game",required=True);p.add_argument("--outcome",choices=["win","loss","void"],required=True)
    p=sub.add_parser("monitor");p.add_argument("--ledger",required=True);p.add_argument("--out",required=True)
    args=parser.parse_args()
    try:
        result=dispatch(args)
        if result is not None:
            print(json.dumps(result,indent=2,default=str))
    except (ValueError,FileNotFoundError,FileExistsError,RuntimeError) as exc:
        print("ERROR: "+str(exc),file=sys.stderr);raise SystemExit(2)

def dispatch(a):
    if a.command=="regularize-free":
        from .free_regularize import regularize_free
        return regularize_free(a.data, a.out)
    if a.command=="correct-venues":
        from .venues import correct_venues
        return correct_venues(a.data, a.out)
    if a.command=="ablate-free":
        from .free_ablate import ablate_free
        return ablate_free(a.data, a.out)
    if a.command=="validate-free":
        from .free_validate import validate_free
        return validate_free(a.data, a.out, a.threads)
    if a.command=="train-free":
        from .free_train import fit_free
        return fit_free(a.data, a.out, a.threads)
    if a.command=="demo":
        from .demo import make_demo
        return make_demo(a.out,read_json(a.config),a.games)
    if a.command=="build":
        from .data import build
        return build(a.data,read_json(a.config),a.out)
    if a.command=="train":
        from .model import fit
        return fit(a.dataset,read_json(a.config),a.out)
    if a.command=="evaluate":
        from .evaluate import evaluate
        return evaluate(a.run,a.dataset,a.split)
    if a.command=="freeze":
        from .model import freeze
        freeze(a.run);return {"frozen":a.run}
    if a.command=="report":
        path=Path(a.path);print((path/"PASTE_BACK.md" if path.is_dir() else path).read_text());return None
    if a.command in ["plan-odds","fetch-odds","normalize-odds","import-nba-results"]:
        from . import providers
        if a.command=="plan-odds":return providers.plan_odds(a.games,a.out)
        if a.command=="fetch-odds":return providers.fetch_odds(a.plan,a.out,a.max_requests,a.execute)
        if a.command=="normalize-odds":return providers.normalize_odds(a.raw,a.mapping,a.out,read_json(a.config)["contract"])
        return providers.import_nba_results(a.raw,a.games,a.out)
    from . import paper
    if a.command=="paper-issue":return paper.issue(a.run,a.dataset,a.ledger)
    if a.command=="paper-check":return paper.record_check(a.ledger,a.game,a.price,a.available)
    if a.command=="paper-settle":return paper.settle(a.ledger,a.game,a.outcome)
    if a.command=="monitor":return paper.monitor(a.ledger,a.out)

if __name__=="__main__":
    main()
