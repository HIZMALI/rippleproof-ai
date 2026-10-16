# RippleProof AI — final release gates (Track 1)

**Status notation:** PASS = executed/verified with evidence, PENDING = not yet executed, BLOCKED = requires operator authorization, FAIL = demonstrated defect. Never treat a planned step as PASS.

| Gate | Acceptance proof | Owner | Current status at handoff |
| --- | --- | --- | --- |
| Local graph persists | Actual FalkorDB reconnect, counts and fingerprint | Codex | PASS Phase 5A; full snapshot equal, isolated restart/recreation equal |
| Deterministic simulation | Same real graph, 19 → 18 → 20, gross 1,364.00 synthetic units | Codex | PASS Phase 5A; complete JSON equal |
| Certificate reasoning | S-09 eligible for P-22; S-10 lacks C-02; S-10 eligible for P-12 | Codex | PASS real API/browser/integration |
| Genuine MCP | Independent SDK stdio client and six constrained tools | Codex | PASS Phase 5A clean install; all six called |
| Real LLM | Controlled paid run, model_requests > 0, actual MCP tools, grounded trace | Operator + Codex | NOT EXECUTED; paid testing declined for now; separate authorization/credentials required |
| Guided truth | UI labels deterministic MCP walkthrough; model_requests 0 | Codex | PASS Phase 5A; separate disabled remote-agent gate |
| Persistent internal decision | Graph-linked Evidence/Decision survives restart and same-key replay | Codex | PASS Phase 5A in **isolated graph**, live approvals 0 |
| Manual human live approval | Real operator reviews read-only preview and approves INTERNAL record | Operator | PENDING, optional demo path; never auto-approve |
| Backend test matrix | Host + Docker suites and real FalkorDB integration | Codex | PASS Phase 5B-1: 209 host / 209 Docker; 79 integration tests |
| Browser/quality tests | Vitest, Chromium E2E, mobile+tablet, axe scan, build, lint | Codex | PASS 51 Vitest / 17 E2E; four-width additional gate scans |
| Public safe content | Separate source export, notice retention, known-value/pattern and history scan | Codex + operator | Automated audit PASS; final human content/rights review pending |
| Clean new-machine install | Fresh isolated Compose project + new graph + seed/migrate + browser walkthrough | Codex | PASS twice; Docker source-only install on current machine, not another physical machine |
| Public repository | Accessible source and complete README/schema/Cypher | Operator | BLOCKED by publication authorization |
| Demo video | Authentic capture with accessible public/unlisted URL | Operator | Local 180s silent English-captioned video verified; hosting/upload/access check pending authorization |
| Track and disclosure | Track 1 name, AI assistance disclosure, accurate qualifications | Operator | PENDING submission |
| Organizer submission | Required form fields accepted before 18 Oct 2026 21:29 TRT; receipt saved | Operator | PENDING |

## Project claims to preserve
- “FalkorDB is the canonical store for operational graph facts and persisted decisions.”
- “Each supply-plan recommendation is tied to verifiable supplier → part → product → order and certificate evidence.”
- “19/18/20 are **orders materially covered by deadline in a synthetic scenario**, not guaranteed delivered orders.”
- “1,364.00 is **gross additional synthetic procurement cost**; not profit, confirmed savings, or a real monetary quote.”
- “The optional remediation proposal does not order inventory, contact vendors or reserve stock.”
- “The optimization uses a documented greedy heuristic; no global optimality claim.”
- “Guided MCP follows a deterministic script and uses zero remote LLM calls. Only externally executed model evidence may be called a real AI agent run.”

## Highest-risk public-readiness issues
1. A public code snapshot accidentally includes local `.git`, `.venv`, `.local`, `node_modules`, raw logs or developer credentials. Do NOT upload the original ZIP wholesale.
2. A localhost-only deployment is mistaken for a public URL. Complete local setup + real video is allowed under the official rules; prefer this if hardening cannot be finished safely.
3. Owner declares Mert Hızmalı the personal copyright holder. Keep All Rights Reserved with no project LICENSE, retain third-party obligations, and obtain explicit publication permission.
4. Real-provider status not accepted in production: resolve honestly before describing it as demonstrated.
5. User must understand/explain architecture and AI-assisted contributions under organizer rules.

Latest implementation evidence: [Phase 5B-1 verification](PHASE5B1_VERIFICATION.md).
Prior isolated installation evidence: [Phase 5A verification](PHASE5A_VERIFICATION.md).
Intended repository is `hizmali/rippleproof-ai`, Public; creation/commit/remote/push
remain unauthorized. The separately hashed publication tree needs final approval.
Prepared source candidate is local and unpublished. A controlled model simulator
using real graph tools passed; this does not satisfy the blocked remote LLM gate.
