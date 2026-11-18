# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *
from datetime import datetime
from hashlib import sha256
import json
import re
import zlib


WHEEL = ('https://files.pythonhosted.org/packages/81/c4/34e93fe5f5429d7570ec1fa436f1986fb1'
         'f00c3e0f43a589fe2bbcd22c3f/pytz-2025.2-py2.py3-none-any.whl')
WHEEL_SHA = '5ddf76296dd8c44c26eb8f4b6f35488f3ccbf6fbbd7adee0b7262d43f0ec2f00'
WHEEL_SIZE = 509225
ZONES = {
    'America/New_York': (178459, 1669, 3552, 'e9ed07d7bee0c76a9d442d091ef1f01668fee7c4f26014c0a868b19fe6c18a95'),
    'Australia/Lord_Howe': (309269, 893, 1846, 'a323c5433991a963eb497b7da4d1d09848bf3ef5f5d64d9c9649f388e4bab9df'),
}
EPOCH = datetime(1970, 1, 1)
DAY = 86400


def fail(reason):
    raise gl.vm.UserError(reason)


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


def civil_seconds(text):
    if not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}', text):
        fail('Expected a local timestamp with seconds and no offset')
    try:
        value = datetime.fromisoformat(text)
    except ValueError:
        fail('Invalid civil timestamp')
    if not datetime(2000, 1, 1) <= value <= datetime(2037, 1, 1):
        fail('Civil timestamp outside the supported years')
    delta = value - EPOCH
    return delta.days * DAY + delta.seconds


def request(zone, start, end):
    if zone not in ZONES:
        fail('Unsupported zone')
    first, last = civil_seconds(start), civil_seconds(end)
    if not 0 < last - first <= 31 * DAY:
        fail('Expected a positive interval of at most 31 days')
    return first, last, zone + '/' + start + '/' + end


def read_member(zone):
    response = gl.nondet.web.get(WHEEL)
    if response.status != 200 or len(response.body) != WHEEL_SIZE:
        fail('Time-zone archive unavailable')
    if sha256(response.body).hexdigest() != WHEEL_SHA:
        fail('Time-zone archive digest mismatch')
    offset, length, expected, digest = ZONES[zone]
    inflater = zlib.decompressobj(-15)
    try:
        member = inflater.decompress(response.body[offset:offset + length], expected + 1)
    except zlib.error:
        fail('Invalid compressed zone member')
    if not inflater.eof or inflater.unused_data or len(member) != expected or sha256(member).hexdigest() != digest:
        fail('Time-zone member digest mismatch')
    return member


def header(data, offset):
    if len(data) < offset + 44 or data[offset:offset + 5] not in (b'TZif2', b'TZif3'):
        fail('Expected a version 2 or 3 TZif header')
    ut, std, leap, times, kinds, chars = (
        int.from_bytes(data[at:at + 4], 'big') for at in range(offset + 20, offset + 44, 4)
    )
    if (leap != 0 or not 1 <= kinds <= 256 or not 1 <= times <= 4096 or not 1 <= chars <= 4096
            or ut not in (0, kinds) or std not in (0, kinds)):
        fail('Unsupported TZif block')
    return ut, std, times, kinds, chars


def transitions(data):
    ut, std, times, kinds, chars = header(data, 0)
    second = 44 + times * 5 + kinds * 6 + chars + std + ut
    ut, std, times, kinds, chars = header(data, second)
    start = second + 44
    indices = start + 8 * times
    types = indices + times
    names = types + 6 * kinds
    if len(data) < names + chars + std + ut:
        fail('Truncated TZif block')
    offsets = []
    for at in range(types, names, 6):
        offset = int.from_bytes(data[at:at + 4], 'big', signed=True)
        if not -DAY < offset < DAY or data[at + 4] not in (0, 1) or data[at + 5] >= chars:
            fail('Invalid TZif local time type')
        offsets.append(offset)
    result = []
    for i in range(times):
        at = start + 8 * i
        instant = int.from_bytes(data[at:at + 8], 'big', signed=True)
        index = data[indices + i]
        if index >= kinds or (result and instant <= result[-1][0]):
            fail('Invalid TZif transition order or type')
        result.append((instant, offsets[index]))
    return result


def project(table, start, end):
    low, high = start - DAY, end + DAY
    if table[0][0] > low or high > table[-1][0]:
        fail('Interval exceeds explicit transitions')
    initial = max(row for row in table if row[0] <= low)
    changes = [row for row in table if low < row[0] < high]
    buckets = [(low, initial[1]), *changes, (high, 0)]
    branches = []
    instants = []
    for (utc_begin, offset), (utc_end, _) in zip(buckets, buckets[1:]):
        civil_begin = max(start, utc_begin + offset)
        civil_end = min(end, utc_end + offset)
        if civil_begin >= civil_end:
            continue
        begin, finish = civil_begin - offset, civil_end - offset
        branches.append({'local': [civil_begin, civil_end], 'utc': [begin, finish], 'offset': offset})
        if instants and instants[-1][1] == begin:
            instants[-1][1] = finish
        else:
            instants.append([begin, finish])

    cuts = sorted({start, end, *(cut for branch in branches for cut in branch['local'])})
    pieces = []
    for left, right in zip(cuts, cuts[1:]):
        multiplicity = sum(branch['local'][0] <= left < branch['local'][1] for branch in branches)
        if pieces and pieces[-1][2] == multiplicity:
            pieces[-1][1] = right
        else:
            pieces.append([left, right, multiplicity])
    return {
        'witness': {'initial': list(initial), 'changes': [list(change) for change in changes]},
        'branches': branches, 'utc_intervals': instants, 'local_pieces': pieces,
        'missing_seconds': sum(b - a for a, b, n in pieces if n == 0),
        'repeated_seconds': sum(b - a for a, b, n in pieces if n >= 2),
        'utc_seconds': sum(b - a for a, b in instants)
    }


def observe(zone, start, end):
    def fetch():
        return project(transitions(read_member(zone)), start, end)

    def verify(proposal):
        try:
            independent = fetch()
        except gl.vm.UserError as error:
            return not isinstance(proposal, gl.vm.Return) and getattr(proposal, 'message', None) == error.message
        except Exception:
            return False
        return isinstance(proposal, gl.vm.Return) and encode(proposal.calldata) == encode(independent)

    return gl.vm.run_nondet_unsafe(fetch, verify)


class CivilFold(gl.Contract):
    projections: TreeMap[str, str]

    def __init__(self):
        pass

    @gl.public.write
    def publish(self, zone: str, start: str, end: str) -> None:
        first, last, key = request(zone, start, end)
        if key in self.projections:
            fail('Civil interval already published')
        result = observe(zone, first, last)
        self.projections[key] = encode({
            'zone': zone, 'start': start, 'end': end, 'source': WHEEL,
            'archive_sha256': WHEEL_SHA, 'tzif_sha256': ZONES[zone][3], **result
        })

    @gl.public.view
    def get_projection(self, zone: str, start: str, end: str) -> dict:
        _, _, key = request(zone, start, end)
        return json.loads(self.projections[key]) if key in self.projections else {}

    @gl.public.view
    def contains(self, zone: str, start: str, end: str, utc_second: int) -> bool:
        projection = self.get_projection(zone, start, end)
        if not projection:
            fail('Civil interval has not been published')
        return any(left <= utc_second < right for left, right in projection['utc_intervals'])
