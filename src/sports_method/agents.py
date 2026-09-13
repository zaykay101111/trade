"""Boundary for later multi-agent integration around the shared pipeline.

Agents may ANNOTATE. They may not FORECAST.

The risk this module exists to remove is specific: a persuasive agent argument
nudging a probability or a stake, producing a number no frozen model would have
produced and no replay could reproduce. That is not a policy we can enforce by
writing it in a document, so the data structure enforces it — an annotation is
a separate, additive artifact that names its sources, and nothing here can
reach into a recorded forecast.

Permitted:
  evidence   a sourced claim, every source carrying a URL and a retrieval time
  quality    a data-quality flag against a named artifact
  scenario   a labelled what-if that is never mixed into the issued forecast
  narrative  an explanation of an existing number

Forbidden by construction: any field that could be read as a probability, a
stake, or an odds figure. `annotate()` rejects those keys outright rather than
trusting a convention.

Adoption gate: an agent contribution is adopted only if it produces a MEASURED
improvement on the pipeline's own metrics — the same paired, interval-based
comparison every other candidate faces. Agreement between agents is not
evidence, and neither is fluency.
"""
import json
import re
from pathlib import Path

from .io import now, write_json

KINDS = ("evidence", "quality", "scenario", "narrative")
# Anything that could be mistaken for a forecast or a bet size.
FORBIDDEN = re.compile(
    r"(^|_)(p|prob|probability|odds|price|stake|kelly|ev|edge|wager|bet)($|_)",
    re.IGNORECASE)


def _check_payload(body):
    for key in body:
        if FORBIDDEN.search(str(key)):
            raise ValueError(
                f"Agent annotations may not carry forecast or stake fields: {key!r}")


def annotate(store, *, kind, subject, body, sources, agent, adopted=False):
    """Append one annotation. Never touches a forecast record.

    `subject` names the artifact the annotation is ABOUT (a game id, a run
    directory, a dataset). `sources` must be non-empty and every source needs a
    url and a retrieved_at, so an unsourced assertion cannot be stored.
    """
    if kind not in KINDS:
        raise ValueError(f"Unknown annotation kind {kind!r}; allowed: {KINDS}")
    if not isinstance(body, dict):
        raise ValueError("Annotation body must be a mapping")
    _check_payload(body)
    if not sources:
        raise ValueError("Every annotation must cite at least one source")
    for source in sources:
        if not source.get("url") or not source.get("retrieved_at"):
            raise ValueError("Each source needs a url and a retrieved_at")
    if adopted:
        raise ValueError(
            "Adoption requires a measured improvement recorded by the evaluation "
            "pipeline; it cannot be asserted when writing an annotation")
    record = {"at": now(), "agent": str(agent), "kind": kind, "subject": str(subject),
              "body": body, "sources": list(sources), "adopted": False}
    store = Path(store)
    store.parent.mkdir(parents=True, exist_ok=True)
    with store.open("a") as stream:
        stream.write(json.dumps(record, allow_nan=False)+"\n")
    return record


def read(store):
    path = Path(store)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def summarise(store, out=None):
    """Counts by kind and agent. Descriptive; adopts nothing."""
    records = read(store)
    by_kind, by_agent = {}, {}
    for record in records:
        by_kind[record["kind"]] = by_kind.get(record["kind"], 0)+1
        by_agent[record["agent"]] = by_agent.get(record["agent"], 0)+1
    report = {"created_at": now(), "annotations": len(records), "by_kind": by_kind,
              "by_agent": by_agent, "adopted": sum(r["adopted"] for r in records),
              "note": "Annotations never alter a forecast, a probability or a stake. "
                      "Adoption requires a measured improvement on the pipeline's own "
                      "paired metrics."}
    if out is not None:
        write_json(Path(out)/"agent_annotations.json", report)
    return report
