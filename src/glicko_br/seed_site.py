"""Preserva os resultados do site publicado na primeira carga do banco."""
from __future__ import annotations

import argparse
import json
from urllib.request import urlopen

from .database import connect, initialise, store_match

SITE_DATA = 'https://andremes.github.io/FUTRanking/data/ranking.json'


def import_snapshot(database, payload: dict) -> int:
    matches = payload.get('matches')
    if not isinstance(matches, list) or not matches:
        raise ValueError('O snapshot publicado não contém resultados; carga inicial interrompida.')
    for match in matches:
        store_match(database, {
            'external_id': match['external_id'], 'played_at': match['played_at'],
            'competition': match['competition'], 'matchday': str(match.get('matchday') or ''),
            'stage': match.get('stage') or '', 'group_name': match.get('group_name') or '',
            'home_team': match['home_team'], 'away_team': match['away_team'],
            'home_crest': match.get('home_crest') or '', 'away_crest': match.get('away_crest') or '',
            'home_goals': str(match['home_goals']), 'away_goals': str(match['away_goals']),
        })
    database.commit()
    return len(matches)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', required=True)
    args = parser.parse_args()
    with urlopen(SITE_DATA, timeout=30) as response:
        payload = json.load(response)
    database = connect(args.database)
    initialise(database)
    print(f'{import_snapshot(database, payload)} resultados preservados do site publicado.')


if __name__ == '__main__':
    main()

