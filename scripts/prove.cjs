const fs = require('node:fs');
const {execFileSync} = require('node:child_process');
const {assert, equal, digest, sourceHash, invoke, read, rpc, receipt, receiptSummary, save} = require('./transport.cjs');
const {decodeReceipt} = require('./receipt-calldata.cjs');

const archive = 'https://files.pythonhosted.org/packages/81/c4/34e93fe5f5429d7570ec1fa436f1986fb1f00c3e0f43a589fe2bbcd22c3f/pytz-2025.2-py2.py3-none-any.whl';
const cases = [
  {label: 'gap', args: ['America/New_York', '2025-03-09T01:30:00', '2025-03-09T03:30:00']},
  {label: 'fold', args: ['America/New_York', '2025-11-02T01:15:00', '2025-11-02T01:45:00']},
  {label: 'half-hour', args: ['Australia/Lord_Howe', '2025-04-06T01:40:00', '2025-04-06T01:50:00']}
];

async function main() {
  const wallets = JSON.parse(process.env.CIVIL_ACCOUNTS || '[]');
  assert(wallets.length === 2 && wallets[0].address !== wallets[1].address, 'Two distinct wallets required');
  const args = cases.map(item => item.args);
  const answers = JSON.parse(execFileSync('python', ['scripts/reference.py'], {input: JSON.stringify(args)}));
  assert(equal(answers.map(answer => [answer.missing_seconds, answer.repeated_seconds, answer.utc_seconds]),
    [[3600, 0, 3600], [0, 1800, 3600], [0, 600, 1200]]), 'Unexpected reference projections');
  const archiveHash = digest(fs.readFileSync('.proof-journal/pytz.whl'));
  assert(await rpc('eth_chainId', []) === '0xf22f', 'StudioNet only');
  const code = fs.readFileSync('contracts/civil_fold.py');
  process.env.CIVIL_ACCOUNT = wallets[0].name;
  const deployment = await invoke('deploy', ['deploy', '--contract', 'contracts/civil_fold.py']);
  const deployed = await receipt('deploy', deployment, true);
  const contract = deployed.to_address || deployed.recipient;
  assert(/^0x[0-9a-f]{40}$/i.test(contract) && code.equals(Buffer.from(deployed.data.contract_code, 'base64')),
    'Deployed code mismatch');
  const report = {contract, deployment, revision: process.env.GITHUB_SHA, source_sha256: sourceHash,
    archive_sha256: archiveHash, trace: [], projections: {}};

  async function verify(label, raw, actor, args, error) {
    assert((raw.from_address || raw.sender).toLowerCase() === wallets[actor].address
      && (raw.to_address || raw.recipient).toLowerCase() === contract.toLowerCase(), 'Wrong receipt addresses');
    assert(equal(await decodeReceipt(raw), args), 'Wrong signed calldata');
    if (error) {
      const payload = Buffer.from(raw.consensus_data.leader_receipt[0].result, 'base64');
      assert(payload[0] === 1 && payload.subarray(1).toString() === error, 'Wrong expected rejection');
    }
    const projections = {};
    for (const item of cases) {
      const actual = await read(label + '-' + item.label, ['call', contract, 'get_projection', '--args', ...item.args]);
      assert(equal(actual, report.projections[item.label] || {}), 'Wrong published state at ' + item.label);
      projections[item.label] = actual;
    }
    report.trace.push({label, ...receiptSummary(raw), signer: wallets[actor].address, args, error: error || null, projections});
    save('progress', report);
  }

  async function publish(label, item, actor, expected, error) {
    process.env.CIVIL_ACCOUNT = wallets[actor].name;
    const hash = await invoke(label, ['write', contract, 'publish', '--args', ...item.args]);
    const raw = await receipt(label, hash, !error);
    if (!error) {
      const record = await read(label + '-new', ['call', contract, 'get_projection', '--args', ...item.args]);
      const [zone, start, end] = item.args;
      const {witness, ...projection} = record;
      assert(witness && equal(projection, {zone, start, end, source: archive, archive_sha256: archiveHash, ...expected}),
        'Civil preimage differs from the independent zoneinfo projection');
      const low = Date.parse(start + 'Z') / 1000 - 86400;
      const high = Date.parse(end + 'Z') / 1000 + 86400;
      assert(witness.initial[0] <= low && witness.changes.length === 1
        && low < witness.changes[0][0] && witness.changes[0][0] < high
        && witness.initial[1] === expected.branches[0].offset && witness.changes[0][1] === expected.branches[1].offset,
        'Offset transition witness differs');
      const checks = expected.utc_intervals.flatMap(([left, right]) => [[left, true], [right - 1, true], [right, false]]);
      for (const [index, [instant, valid]] of checks.entries()) {
        const allowed = await read(label + '-membership-' + index,
          ['call', contract, 'contains', '--args', ...item.args, String(instant)]);
        assert(allowed === valid, 'Half-open UTC membership differs');
      }
      report.projections[item.label] = record;
    }
    await verify(label, raw, actor, {method: 'publish', args: item.args}, error);
  }

  await verify('deploy', deployed, 0, {args: []});
  for (const [index, item] of cases.entries()) {
    await publish(item.label, item, (index + 1) % 2, answers[index]);
  }
  await publish('duplicate', cases[1], 0, null, 'Civil interval already published');
  assert(code.equals(Buffer.from(await rpc('gen_getContractCode', [contract]), 'base64')), 'Fresh code differs');
  save('verified', report);
  console.log(JSON.stringify({contract, deployment, cases: cases.map(item => item.label), receipts: report.trace.length}));
}

main().catch(error => { console.error(error); process.exitCode = 1; });
