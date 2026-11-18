# CivilFold — Consensus civil-time interval projection

**Category** Builder → Intelligent Contracts

CivilFold turns a local wall-clock interval into its exact half-open UTC union. The leader and validators independently fetch the published pytz archive, verify its digest, decompress a TZif member, and parse the explicit time-zone transitions. They compare the full projection, including offset branches and the number of UTC occurrences of each local segment. Other contracts can query membership in the published union. StudioNet verified a New York spring gap, a New York autumn fold, and a Lord Howe fold where the clock moves back by 30 minutes. An independent zoneinfo verifier checked every UTC second and the workflow verified the boundary reads. All five receipts finalized with MAJORITY_AGREE. The deployment uses two zones and the pinned 2025.2 release.

- [GenLayer contract](contracts/civil_fold.py)
- [StudioNet deployment](https://explorer-studio.genlayer.com/tx/0x1648a5edc4d37bc52da3004bb1e3438fc3beda9980fcb2ea594eb4309fa0722f)
- [Lord Howe fold](https://explorer-studio.genlayer.com/tx/0xa12e6d128bd7bdaaf2ade7cf428f8b3c2e163d5df0c52b060b716412d0a4aebd)
- [Receipts and verified state](proofs/README.md)
