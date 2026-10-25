"""Plan one finite calendar expansion without writing or regenerating lessons."""
import argparse
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

LANGUAGES = {'javascript', 'python', 'sql'}


def plan(content_root, batch_day):
    root = Path(content_root)
    ledger = json.loads((root / 'maintenance.json').read_text())
    records = ledger['batches']
    previous = next((record for record in records if record['run_date'] == batch_day.isoformat()), None)
    if previous:
        return {'status': 'already-recorded', 'batch': previous,
                'next_action': 'Verify deployment; do not add another source batch.'}
    if (batch_day < date.fromisoformat(ledger['program_start'])
            or batch_day > date.fromisoformat(ledger['program_end'])
            or len(records) >= ledger['total_batches']):
        return {'status': 'closed', 'next_action': 'No expansion is authorized for this date.'}
    by_day = {}
    for path in root.glob('*/*.json'):
        item = json.loads(path.read_text())
        if path.parent.name != item['language'] or path.stem != item['date']:
            raise ValueError('Lesson path does not match its language/date')
        by_day.setdefault(date.fromisoformat(item['date']), set()).add(item['language'])
    if not by_day or any(languages != LANGUAGES for languages in by_day.values()):
        raise ValueError('Every existing date must contain all three language tracks')
    first, last = min(by_day), max(by_day)
    width = ledger['days_per_direction']
    if width != 3 or ledger['total_batches'] != 30:
        raise ValueError('Unexpected program scope; review before expanding')
    older = [(first - timedelta(days=offset)).isoformat() for offset in range(width, 0, -1)]
    forward = [(last + timedelta(days=offset)).isoformat() for offset in range(1, width + 1)]
    return {'status': 'new-batch', 'run_date': batch_day.isoformat(), 'older_dates': older,
            'forward_dates': forward, 'lesson_count': (len(older) + len(forward)) * len(LANGUAGES),
            'languages': sorted(LANGUAGES), 'source_batches_remaining': ledger['total_batches'] - len(records)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--date', type=date.fromisoformat,
                        default=datetime.now(ZoneInfo('America/New_York')).date())
    parser.add_argument('--content-root', type=Path,
                        default=Path(__file__).resolve().parents[1] / 'authentic_dynamics/content/coding')
    args = parser.parse_args()
    print(json.dumps(plan(args.content_root, args.date), indent=2))
