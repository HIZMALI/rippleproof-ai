# Submission fields — draft, not submitted

**Project:** RippleProof AI

**Team:** MORVE (one human participant, Mert Hızmalı)

**Track:** Track 1: Agents That Act on Connected Data

**Short description:** Explain supplier-outage risk, test constrained recovery
plans, and retain human-reviewed decisions with verifiable graph evidence.

**Description:** RippleProof AI helps an operations planner trace a supplier outage
through shared parts, products, orders, inbound receipts and certifications in
FalkorDB. A deterministic Python engine allocates shared inventory, adjusts planned
arrivals, checks capacity and certificates on arrival, and compares baseline,
disruption and recovery with transparent gross additional cost. The React
workbench exposes original source edges, per-part constraints, genuine MCP traces
and a separate human review boundary. FalkorDB is the canonical source for both
operational facts and durable Decision/Evidence memory; disconnecting it prevents
the product from answering. Guided mode is deterministic and makes zero LLM calls.
The bounded real-provider orchestration is implemented and capability-gated, but
external LLM acceptance remains unexecuted pending separate authorization.

**Technology:** FalkorDB, parameterized Cypher, Python 3.12+, FastAPI, Pydantic,
official MCP SDK over stdio, bounded tool-calling coordinator, React, TypeScript,
Vite, TanStack Query, Zod, Cytoscape.js, Docker Compose and unprivileged Nginx.

**Measured demonstration:** On the fixed synthetic 145-node/291-relationship
operational dataset, the reference scenario covers 19/18/20 of 21 open orders
across baseline/disruption/mitigation. O-105/O-106 are newly at risk and restored;
the gross additional synthetic procurement cost is 1,364.00. These are model
results, not delivery guarantees, real quotations or savings. Actual Phase 5B-1
regression totals are 209 backend tests (79 integration), 51 component tests and
17 browser tests; see PHASE5B1_VERIFICATION.md. Prior isolated clean-install
evidence and its tested archive are in PHASE5A_VERIFICATION.md.

**Limitations:** Materials-only feasibility and deterministic greedy policies;
no global-optimality claim, real procurement, supplier contact, production identity
service or multi-writer transaction guarantee. The default demo is localhost.
Remote LLM verification has not been performed; paid testing is declined for now.
An authentic 180-second local silent English-captioned video is produced; hosting,
public source publication and submission remain separate authorization gates. Isolated automated approval records are not human
operator approvals.

**AI assistance:** OpenAI Codex assisted implementation, synthetic data, tests,
documentation and local verification during the event. The human participant must
review and understand the code, explain the graph/queries/architecture, verify
the disclosure and describe their actual contribution. Do not claim unobserved
human authorship or remote-provider evidence.

**Source-code URL:** PENDING — intended `hizmali/rippleproof-ai`; no repository
creation/publication authorized or public access verified. Do not submit a
prospective URL as an existing repository.

**Video URL:** PENDING — genuine local silent English-captioned recording exists;
separate upload permission and actual signed-out accessibility check required.

**Deployment/local setup:** Complete Docker local setup in README; no public
deployment is claimed. Localhost links in docs are local examples, not public URLs.

**Project rights:** Copyright © 2026 Mert Hızmalı. All rights reserved.
Personal holder explicitly declared by owner; no project open-source LICENSE.
Third-party licenses/notices remain intact.

**Rules checked:** [official rules](https://www.wemakedevs.org/hackathons/falkordb/rules)
and [event/Track 1](https://www.wemakedevs.org/hackathons/falkordb), checked 16 Oct
2026 Europe/Istanbul. Public source, README/setup/model, Cypher/algorithms, working
video, local setup or deployment, named track and AI disclosure are required.
The stated deadline is 18 Oct 2026 23:59 IST, equivalent to **21:29 Europe/Istanbul**.
Recheck the official panel before submission; no receipt or submission exists yet.
