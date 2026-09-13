"""Reviewed historical venue overrides, never inferred from outcomes."""
import csv
import json
import shutil
from pathlib import Path
from .io import digest, now, write_json, new_dir

# Sources establish location. Treating international/Cup venues as neutral is
# our consistent modeling convention, not a claim of zero crowd advantage.
CORRECTIONS = {
    '0022200439': ('Mexico City, Mexico', 'https://pr.nba.com/nba-mexico-city-game-to-return-with-regular-season-matchup-featuring-san-antonio-spurs-and-miami-heat-on-dec-17/'),
    '0022200678': ('Paris', 'https://www.nba.com/news/bulls-pistons-to-play-regular-season-game-in-paris'),
    '0022300172': ('Mexico City', 'https://www.nba.com/game/atl-vs-orl-0022300172'),
    '0022301229': ('Las Vegas', 'https://www.nba.com/news/2023-in-season-tournament-debut-official-release'),
    '0022301230': ('Las Vegas', 'https://www.nba.com/news/2023-in-season-tournament-debut-official-release'),
    '0022300527': ('Paris', 'https://www.nba.com/cavaliers/photos/photogallery-bkncle-240111'),
}


def correct_venues(data, out):
    data, out = Path(data).resolve(), Path(out).resolve()
    if out.exists():
        raise FileExistsError(f'Output exists: {out}')
    if data in out.parents:
        raise ValueError('Output must not be inside source dataset')
    with (data/'games.csv').open(newline='') as f:
        reader = csv.DictReader(f)
        fields, rows = reader.fieldnames, list(reader)
    ids = [r['game_id'] for r in rows]
    if len(set(ids)) != len(ids) or not set(CORRECTIONS).issubset(ids):
        raise ValueError('Need unique IDs and all six reviewed games')
    hashes = {name: digest(data/name) for name in ('games.csv', 'results.csv')}
    cached = {}
    raw_hashes = {}
    for filename in ('schedule-2022-23.json', 'schedule-2023-24.json'):
        path = data/'raw'/filename
        raw_hashes[filename] = digest(path)
        for r in json.loads(path.read_text()):
            gid = str(r.get('gameId', '')).zfill(10)
            if gid in CORRECTIONS:
                if gid in cached:
                    raise ValueError('Duplicate reviewed ID in raw cache')
                cached[gid] = r
    audit = []
    for row in rows:
        gid = row['game_id']
        if gid not in CORRECTIONS:
            continue
        city, url = CORRECTIONS[gid]
        raw = cached.get(gid, {})
        if raw.get('arenaCity') != city or raw.get('isNeutral') is not False:
            raise ValueError(f'Unexpected raw venue/flag for {gid}; review required')
        if row['is_neutral'].lower() != 'false':
            raise ValueError(f'Expected uncorrected false flag for {gid}')
        if row['home_id'] != str(raw['homeTeam_teamId']) or row['away_id'] != str(raw['awayTeam_teamId']):
            raise ValueError(f'Team identity mismatch for {gid}')
        row['is_neutral'] = 'True'
        audit.append({'game_id': gid, 'before': False, 'after': True, 'arena_city': city,
                      'arena_name': raw.get('arenaName'), 'source': url})
    new_dir(out)
    with (out/'games.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)
    shutil.copy2(data/'results.csv', out/'results.csv')
    shutil.copytree(data/'raw', out/'raw')
    if (data/'manifest.json').exists():
        shutil.copy2(data/'manifest.json', out/'upstream_manifest.json')
    manifest = {'created_at': now(), 'source_dataset': str(data), 'rows': len(rows),
                'corrections': audit, 'source_sha256': hashes, 'reviewed_raw_sha256': raw_hashes,
                'output_sha256': {n:digest(out/n) for n in hashes},
                'warning': 'Venue-only overrides; no score or timestamp revisions. International and Cup semifinal venues treated as neutral. Austin regional home games and temporary home bases retain source flags. Not an exhaustive venue/home-advantage model. Final holdout rows unchanged and unscored.'}
    write_json(out/'manifest.json', manifest)
    if any(digest(data/n) != sha for n,sha in hashes.items()):
        raise RuntimeError('Source changed during correction')
    return {'data': str(out), 'games': len(rows), 'corrected': len(audit), 'results_unchanged': digest(out/'results.csv') == hashes['results.csv']}
