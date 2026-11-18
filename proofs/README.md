# StudioNet proofs

Contract address 0x13ceE39267242815A048f7E099206F20c90a9344

All five receipts finalized with MAJORITY_AGREE. The independent zoneinfo verifier checked every UTC second in the three scenarios. Fresh reads verified the projected intervals, half-open membership, and state after duplicate rejection.

[Workflow](https://github.com/mohammadisina1988-jpg/civil-fold/actions/runs/44254434550) · [Verified reads](verified.json)

| Outcome | Explorer | Receipt | Agree / disagree / idle |
| --- | --- | --- | --- |
| Deployed interval projector | [Transaction](https://explorer-studio.genlayer.com/tx/0x1648a5edc4d37bc52da3004bb1e3438fc3beda9980fcb2ea594eb4309fa0722f) | [JSON](deploy-receipt.json) | 3 / 0 / 2 |
| Projected the New York spring gap | [Transaction](https://explorer-studio.genlayer.com/tx/0xff201f65bd0461e5ff3dee83c1d37597a132e7ec74062a9bc86a6c5d90ab1da9) | [JSON](gap-receipt.json) | 3 / 0 / 2 |
| Preserved both New York autumn occurrences | [Transaction](https://explorer-studio.genlayer.com/tx/0xfc029e0777cfc59a3149f68d9ad77716ff6d4d489d2218cd9ce0a7448ced57ff) | [JSON](fold-receipt.json) | 3 / 0 / 2 |
| Preserved both Lord Howe occurrences | [Transaction](https://explorer-studio.genlayer.com/tx/0xa12e6d128bd7bdaaf2ade7cf428f8b3c2e163d5df0c52b060b716412d0a4aebd) | [JSON](half-hour-receipt.json) | 3 / 0 / 2 |
| Rejected a duplicate publication | [Transaction](https://explorer-studio.genlayer.com/tx/0x24818560ab4791deb9fc1f8c53d844aad87539b19354767c5f4b645e66833158) | [JSON](duplicate-receipt.json) | 3 / 0 / 2 |

| Case | Skipped local seconds | Repeated local seconds | UTC intervals (half-open) |
| --- | ---: | ---: | --- |
| gap | 3600 | 0 | 2025-03-09T06:30:00Z to 2025-03-09T07:30:00Z |
| fold | 0 | 1800 | 2025-11-02T05:15:00Z to 2025-11-02T05:45:00Z<br>2025-11-02T06:15:00Z to 2025-11-02T06:45:00Z |
| half-hour | 0 | 600 | 2025-04-05T14:40:00Z to 2025-04-05T14:50:00Z<br>2025-04-05T15:10:00Z to 2025-04-05T15:20:00Z |

Source revision fd1e74eb94b9e5ab056f68796782a6c643b718f0

Contract SHA-256 9b639959708077a2edeaa3171caf996ba7a75f87b1d6e28c300854f27a778771

Archive SHA-256 5ddf76296dd8c44c26eb8f4b6f35488f3ccbf6fbbd7adee0b7262d43f0ec2f00
