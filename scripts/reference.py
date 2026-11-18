"""Independent civil-time projection using stdlib zoneinfo and ZIP extraction."""
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
from zipfile import ZipFile
from zoneinfo import ZoneInfo
import json
import sys


ARCHIVE = '.proof-journal/pytz.whl'
WHEEL_SHA = '5ddf76296dd8c44c26eb8f4b6f35488f3ccbf6fbbd7adee0b7262d43f0ec2f00'


def epoch(text):
    return int(datetime.fromisoformat(text).replace(tzinfo=timezone.utc).timestamp())


def runs(values):
    result = []
    for coordinate, value in values:
        if result and result[-1][1] == coordinate and result[-1][2] == value:
            result[-1][1] += 1
        else:
            result.append([coordinate, coordinate + 1, value])
    return result


def reference(wheel, zone, start, end):
    assert sha256(wheel).hexdigest() == WHEEL_SHA
    with ZipFile(BytesIO(wheel)) as archive:
        binary = archive.read('pytz/zoneinfo/' + zone)
    tz = ZoneInfo.from_file(BytesIO(binary))
    first, last = epoch(start), epoch(end)
    assert 0 < last - first <= 86400
    accepted = []
    occurrence_count = [0] * (last - first)
    for candidate in range(first - 86400, last + 86400):
        instant = datetime.fromtimestamp(candidate, timezone.utc).astimezone(tz)
        naive = int(instant.replace(tzinfo=timezone.utc).timestamp())
        if first <= naive < last:
            accepted.append((candidate, int(instant.utcoffset().total_seconds())))
            occurrence_count[naive - first] += 1
    return {
        'tzif_sha256': sha256(binary).hexdigest(),
        'branches': [{'utc': [lo, hi], 'local': [lo + offset, hi + offset], 'offset': offset}
                     for lo, hi, offset in runs(accepted)],
        'utc_intervals': [[lo, hi] for lo, hi, _ in runs((i, 1) for i, _ in accepted)],
        'local_pieces': runs((first + i, count) for i, count in enumerate(occurrence_count)),
        'missing_seconds': occurrence_count.count(0),
        'repeated_seconds': sum(count >= 2 for count in occurrence_count),
        'utc_seconds': len(accepted)
    }


if __name__ == '__main__':
    with open(ARCHIVE, 'rb') as file:
        raw = file.read()
    print(json.dumps([reference(raw, *args) for args in json.load(sys.stdin)]))
