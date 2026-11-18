# CivilFold

CivilFold turns a half-open local wall-clock interval into the exact union of UTC intervals that realize it. It preserves both occurrences when clocks move backward and marks skipped local seconds when clocks move forward. Downstream contracts can use the published UTC intervals as an execution guard.

Anyone can call `publish(zone, start, end)`. The input is an exact local timestamp in `YYYY-MM-DDTHH:MM:SS` form, without a zone suffix. The zone is `America/New_York` or `Australia/Lord_Howe`. Intervals may span up to 31 days within the supported 2000–2036 period.

The leader and each validator fetch the published pytz 2025.2 wheel, verify its SHA-256, decompress the bound TZif member, and parse the explicit 64-bit transitions. They compute the full inverse image by intersecting the requested local range with each offset segment. Consensus compares the complete transition witness, offset branches, UTC union, and local occurrence counts. Display-only file fields do not affect the projection.

`get_projection(zone, start, end)` returns the agreed result or an empty object. `contains(zone, start, end, utc_second)` evaluates the published half-open UTC union. The output includes the local segments with zero, one, or multiple occurrences, the number of skipped and repeated local seconds, and the total length of the UTC union. Local coordinates are seconds from the naive civil epoch. UTC coordinates are Unix seconds.

The contract uses the pinned release and explicit transition coverage. A later release or additional zone requires new deployment code. The stored projection is immutable for its exact request.

[Published pytz archive](https://pypi.org/project/pytz/2025.2/#files) · [IANA Time Zone Database](https://www.iana.org/time-zones) · [TZif specification](https://www.rfc-editor.org/rfc/rfc9636.html)

## Verification

```sh
mkdir -p .proof-journal
curl --fail 'https://files.pythonhosted.org/packages/81/c4/34e93fe5f5429d7570ec1fa436f1986fb1f00c3e0f43a589fe2bbcd22c3f/pytz-2025.2-py2.py3-none-any.whl' --output .proof-journal/pytz.whl
pip install -r requirements-dev.txt
genvm-lint download --version v0.2.16
genvm-lint check contracts/civil_fold.py
python -m pytest tests/direct -q
npm ci
node --test tests/rpc-preflight.test.cjs
```

The independent verifier uses standard-library ZIP extraction and `zoneinfo` to examine every UTC second in the proof cases. The StudioNet workflow checks a New York spring gap, a New York autumn fold, and a Lord Howe fold where the clocks change by 30 minutes. It verifies UTC membership at interval boundaries, exact signed calldata, the deployed source, and rejection of duplicate publication. Generic CLI receipt transport is reused under MIT.

[StudioNet proofs](proofs/README.md) · [Submission text](SUBMISSION.md).
