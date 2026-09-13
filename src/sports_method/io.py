import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone

def read_json(path):
    return json.loads(Path(path).read_text())

def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def code_hash():
    h = hashlib.sha256()
    for path in sorted(Path(__file__).parent.glob("*.py")):
        h.update(path.name.encode())
        h.update(path.read_bytes())
    return h.hexdigest()

# Modules that determine a forecast given a schedule and a fitted bundle. A
# change here changes what a deployed forecast means; a change anywhere else in
# the package does not, and must not halt a season of collection.
FORECAST_SURFACE = ("free_data.py", "model.py", "collect.py", "io.py")


def forecast_surface_hash():
    h = hashlib.sha256()
    for name in FORECAST_SURFACE:
        path = Path(__file__).parent/name
        h.update(name.encode())
        h.update(path.read_bytes())
    return h.hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()

def new_dir(path):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=False)
    return path

