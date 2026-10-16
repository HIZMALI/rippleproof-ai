# Publication and submission handoff — preparation only

The owner confirmed the personal copyright holder, intended account/repository
and intended Public visibility. These choices do not authorize publication.
Copyright © 2026 Mert Hızmalı. All rights reserved. No project LICENSE is added;
see [RIGHTS.md](../RIGHTS.md) and retained [third-party notices](../THIRD_PARTY_NOTICES.md).

| Human gate | Actual value/status |
| --- | --- |
| Phase 5A / 5B-1 preparation review | Accepted by owner; not publication permission |
| Personal copyright holder | Mert Hızmalı, explicitly declared by owner |
| Team / competition | MORVE, one human participant; Graph Hacks 2026 Track 1 |
| Intended account / repository | `hizmali/rippleproof-ai` |
| Intended visibility | Public; actual creation/publication NOT AUTHORIZED |
| Frozen source baseline | 514 files; ZIP SHA-256 `9d6677b8e1115289ac9039e065a7a670a15930f4af4426f1bcfe5a67514acbfe` |
| New publication tree | Separate baseline extraction; only RIGHTS, README, this checklist, release gates and submission draft changed; new external manifest/hash require review |
| GitHub CLI authentication | CLI absent in preparation environment; account `hizmali` NOT verified; browser sign-in is insufficient |
| Commit / remote / push | NOT AUTHORIZED; no initial commit or remote created |
| Source URL / signed-out check | PENDING publication and actual access check |
| README / graph / Cypher / disclosure | Present; linked below and in README |
| Real-provider acceptance | NOT EXECUTED; paid testing declined for now |
| Live internal-plan approval | NOT performed; requires separate human checkpoint |
| Authentic local video | Produced: 180 seconds, silent English captions; remote LLM acceptance explicitly unverified |
| Video hosting / accessible URL | PENDING separate authorization and signed-out playback check |
| Participant contribution / understanding | Participant must verify final disclosure and be able to explain implementation |
| Signed-in organizer form / receipt | NOT submitted; participant must inspect fields and separately authorize |

The external operator readiness report and manifest identify this exact changed
tree and its new ZIP SHA-256. They stay outside the archive to avoid a
self-referential archive hash. Never substitute the baseline hash for the new
publication hash. Historical reports retain the state and evidence at execution
time; they are not current publication consent.

After explicit approval of the NEW hash only: extract into a fresh empty folder,
validate every manifest member and secret exclusions, verify `gh api user --jq
.login` returns `hizmali`, inspect actual commit identity locally, then initialize
Git on main. Review staged files before a truthful current-time initial commit.
Creating the repository, adding its remote and pushing need explicit approval.
Do not retrodate commits or manufacture event-era history. The declared rights
holder does not establish a Git commit email or authorship history.

Do not publish `.git`, `.local`, `.venv`, `.env`, node_modules, caches, databases,
backups, private audit state, HAR, browser profiles or private recordings.
Localhost addresses are not public demo URLs. No data/volume removal is part of
the release procedure. Preserve all third-party notices unchanged.

- [README / setup](../README.md)
- [Architecture](ARCHITECTURE.md), [graph model](GRAPH_MODEL.md), [actual Cypher](CYPHER_AND_EVIDENCE.md)
- [Executed regression evidence](PHASE5B1_VERIFICATION.md), [release gates](PHASE5_RELEASE_GATES.md)
- [Agent evidence categories and authorization](AGENT_DEMO_GATE.md), [submission draft](SUBMISSION_TEXT.md)
