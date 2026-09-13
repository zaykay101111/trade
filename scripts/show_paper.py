import argparse
import json
import sqlite3
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument("--ledger",required=True)
a=p.parse_args()
if not Path(a.ledger).is_file():raise FileNotFoundError(a.ledger)
db=sqlite3.connect("file:"+str(Path(a.ledger).resolve())+"?mode=ro",uri=True)
for game,issued,payload in db.execute("SELECT game_id,issued_at,payload FROM decisions ORDER BY issued_at DESC LIMIT 50"):
    print(json.dumps({"game_id":game,"issued_at":issued,**json.loads(payload)},indent=2))
db.close()

