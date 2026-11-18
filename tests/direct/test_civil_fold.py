from pathlib import Path
import re

import pytest

from scripts.reference import ARCHIVE, epoch, reference


SOURCE = 'https://files.pythonhosted.org/packages/81/c4/34e93fe5f5429d7570ec1fa436f1986fb1f00c3e0f43a589fe2bbcd22c3f/pytz-2025.2-py2.py3-none-any.whl'
WHEEL = Path(ARCHIVE).read_bytes()
GAP = ('America/New_York', '2025-03-09T01:30:00', '2025-03-09T03:30:00')
FOLD = ('America/New_York', '2025-11-02T01:15:00', '2025-11-02T01:45:00')
HALF_HOUR = ('Australia/Lord_Howe', '2025-04-06T01:40:00', '2025-04-06T01:50:00')
CASES = [
    (GAP, (3600, 0, 3600)),
    (FOLD, (0, 1800, 3600)),
    (HALF_HOUR, (0, 600, 1200)),
    (('America/New_York', '2025-03-09T02:20:00', '2025-03-09T02:30:00'), (600, 0, 0)),
    (('Australia/Lord_Howe', '2025-10-05T01:55:00', '2025-10-05T02:35:00'), (1800, 0, 600)),
]


def deploy(direct_deploy):
    return direct_deploy('contracts/civil_fold.py', sdk_version='v0.2.16')


def mock(vm, data=WHEEL, status=200):
    vm.clear_mocks()
    vm.mock_web(re.escape(SOURCE), {'status': status, 'body': data})


@pytest.mark.parametrize(('case', 'totals'), CASES)
def test_projection_matches_zoneinfo_by_the_second(direct_vm, direct_deploy, case, totals):
    contract = deploy(direct_deploy)
    mock(direct_vm)
    contract.publish(*case)
    result = contract.get_projection(*case)
    expected = reference(WHEEL, *case)
    assert {key: result[key] for key in expected} == expected
    assert tuple(result[key] for key in ('missing_seconds', 'repeated_seconds', 'utc_seconds')) == totals
    assert direct_vm.run_validator() is True
    for left, right in result['utc_intervals']:
        assert contract.contains(*case, left)
        assert contract.contains(*case, right - 1)
        assert not contract.contains(*case, right)


def test_fold_branches_and_intervening_time(direct_vm, direct_deploy, direct_bob):
    contract = deploy(direct_deploy)
    direct_vm.sender = direct_bob
    mock(direct_vm)
    contract.publish(*FOLD)
    assert contract.contains(*FOLD, epoch('2025-11-02T05:20:00'))
    assert not contract.contains(*FOLD, epoch('2025-11-02T06:00:00'))
    assert contract.contains(*FOLD, epoch('2025-11-02T06:20:00'))
    before = contract.get_projection(*FOLD)
    with direct_vm.expect_revert('Civil interval already published'):
        contract.publish(*FOLD)
    assert contract.get_projection(*FOLD) == before


def test_validator_rejects_dropped_multiplicity(direct_vm, direct_deploy):
    contract = deploy(direct_deploy)
    mock(direct_vm)
    contract.publish(*FOLD)
    record = contract.get_projection(*FOLD)
    metadata = {'zone', 'start', 'end', 'source', 'archive_sha256', 'tzif_sha256'}
    forged = {key: value for key, value in record.items() if key not in metadata}
    forged['local_pieces'] = [[epoch(FOLD[1]), epoch(FOLD[2]), 1]]
    assert direct_vm.run_validator(leader_result=forged) is False


@pytest.mark.parametrize(('data', 'status', 'reason'), [
    (b'error', 503, 'Time-zone archive unavailable'),
    (b'X' + WHEEL[1:], 200, 'Time-zone archive digest mismatch')
])
def test_bad_archive_never_publishes(direct_vm, direct_deploy, data, status, reason):
    contract = deploy(direct_deploy)
    mock(direct_vm, data, status)
    with direct_vm.expect_revert(reason):
        contract.publish(*FOLD)
    assert contract.get_projection(*FOLD) == {}
    mock(direct_vm)
    contract.publish(*FOLD)
    assert contract.get_projection(*FOLD)['repeated_seconds'] == 1800


@pytest.mark.parametrize(('args', 'reason'), [
    (('Europe/London', GAP[1], GAP[2]), 'Unsupported zone'),
    ((GAP[0], GAP[1] + 'Z', GAP[2]), 'Expected a local timestamp with seconds and no offset'),
    ((GAP[0], '2025-02-30T01:30:00', GAP[2]), 'Invalid civil timestamp'),
    ((GAP[0], GAP[2], GAP[1]), 'Expected a positive interval of at most 31 days'),
    ((GAP[0], '2040-03-09T01:30:00', '2040-03-09T03:30:00'), 'Civil timestamp outside the supported years')
])
def test_bad_request_rejects_before_fetch(direct_vm, direct_deploy, args, reason):
    contract = deploy(direct_deploy)
    with direct_vm.expect_revert(reason):
        contract.publish(*args)
