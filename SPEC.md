# Project 4 — `rules-as-code-mcp`

**Pattern:** MCP server
**One line:** Deterministic eligibility logic — rules-as-code — exposed as MCP tools an agent can
call, so the model reasons but the **actual legal determination is made by auditable, tested,
cited code.**

This is the newest pattern and rising fastest, and for you it's also the keystone: it's the literal
embodiment of the deterministic/probabilistic boundary that wins these interviews, and it's the
"policy codification" layer you've argued is the highest-leverage, least-noticed place AI reshapes
government. Most candidates haven't touched MCP yet. That's the opening.

---

## Scope

**In scope**
- A small, well-tested **rules-as-code core**: implement one program properly (SNAP gross/net income
  test for a chosen state is a good target — real, bounded, verifiable), with versioning and a
  citation back to the policy section behind each rule.
- Expose it as an **MCP server** with a handful of clear tools (below).
- **Scoped permissions**: an anonymous *screening* role (no PII stored) vs. an authenticated
  *caseworker* role (full detail).
- Production hygiene: input validation, structured error handling, and tool descriptions clear enough
  that a model calls them correctly.
- **Composition**: also expose Project 2's policy RAG index as a `lookup_policy` tool, so one server
  offers both deterministic determination *and* cited policy lookup.
- A demonstration of a real MCP client (Claude Desktop / Claude Code) using the server end to end.

**Explicitly out of scope**
- The model never decides eligibility. The tools decide; the model orchestrates.

---

## The tools

Keep them few and sharp:

- `screen_programs(household)` → which programs the household likely qualifies for (anonymous-safe).
- `check_program_eligibility(program, household)` → a determination with the rule trace and the cited
  policy section(s) behind it.
- `list_required_verifications(program, case)` → documents needed to confirm eligibility.
- `explain_determination(determination_id)` → a plain trace of which rules fired and why.
- `lookup_policy(question)` → cited policy answer (delegates to Project 2's index).

Every determination tool returns **the result plus the rule trace plus the citation** — never a bare
yes/no. That's what makes it deployable in government.

---

## The hard parts (where production-readiness shows)

1. **Auditability by construction.** Each rule carries its policy citation and a version. A
   determination is reproducible and explainable, not a black box.
2. **Scoped permissions done right.** Screening must work without collecting PII; caseworker access is
   gated. Show the boundary in code and in the tool descriptions.
3. **Robustness to bad input.** Missing fields, wrong types, out-of-range values → clean structured
   errors, not stack traces. A model on the other end should be able to recover.
4. **Tool descriptions a model can actually use.** Half of MCP quality is writing tool schemas and
   descriptions so the model invokes them correctly. Treat this as a first-class deliverable.

---

## Architecture / repo structure

```
rules-as-code-mcp/
├── README.md
├── rules/
│   ├── snap.py                  # the rules-as-code core (one program, done well)
│   ├── citations.py             # rule → policy section mapping
│   ├── version.py               # ruleset versioning
│   └── tests/                   # exhaustive unit tests over the eligibility logic
├── server/
│   ├── main.py                  # MCP server: tool registration + dispatch
│   ├── tools.py                 # tool schemas + descriptions
│   ├── auth.py                  # screening vs caseworker scoping
│   └── errors.py                # structured error handling + validation
├── clients/
│   └── demo.md                  # how to connect Claude Desktop / Claude Code + sample transcript
├── eval/
│   ├── cases.json               # labeled eligibility cases (ground truth)
│   ├── run_eval.py              # tool correctness + robustness checks
│   └── report.md
└── pyproject.toml
```

## Tech stack

- The **MCP SDK** (Python) to implement the server; study and fork the official reference servers.
- The rules core is plain, heavily-tested Python — the point is that it's deterministic and auditable.
- Cite Anthropic's MCP launch/spec material in the README as the authoritative "what and why."

Pull the current MCP spec and SDK docs at build time — this ecosystem moves fast and the API surface
from even a few months ago may be stale.

---

## Evaluation

`eval/run_eval.py` reports:

- **Tool correctness** on a labeled set of eligibility cases (`cases.json`) spanning eligible,
  ineligible, and near-threshold households — does each determination match ground truth, and does it
  return the right citation?
- **Rule-trace correctness** — for each determination, did the *right* rules fire?
- **Robustness**: behavior under bad input, auth failure, and tool misuse — handled cleanly rather
  than crashing. List each failure case and show the structured response.
- **End-to-end client demo**: a real MCP client driving the server, captured in `clients/demo.md` —
  the server doing real work, with the failure cases handled, not ignored.

---

## README framing

This is where you state the thesis plainly: in government, "the model said so" is not a basis for
denying benefits. The model can read, reason, and orchestrate — but the determination itself is made
by versioned, tested, cited code that a caseworker (or an auditor, or a court) can inspect. That
boundary is what makes agentic AI deployable in the public sector at all. Then show the tools, the
permission model, and the eval.

## Interview one-liner

> "This is the deterministic core the agent hands the real decision to. The model orchestrates; the
> eligibility determination is auditable code with a citation to the manual and a version stamp. That
> boundary is the whole reason this is deployable in government — and exposing it over MCP is how the
> agent reaches it."

## Build order for Claude Code

1. `rules/snap.py` + `citations.py` + exhaustive `tests/` — get the core provably correct first.
2. `eval/cases.json` + `run_eval.py` against the core.
3. MCP server: tool schemas/descriptions, dispatch, validation, structured errors.
4. `auth.py` scoping (screening vs caseworker).
5. `lookup_policy` delegation to Project 2.
6. Real MCP client demo + `clients/demo.md` transcript.
