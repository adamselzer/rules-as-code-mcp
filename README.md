# rules-as-code-mcp

Deterministic SNAP eligibility logic, exposed as auditable [Model Context
Protocol](https://modelcontextprotocol.io) tools. An AI agent can read, reason,
and orchestrate, but the eligibility determination itself is made by versioned,
tested, cited code that a caseworker, an auditor, or a court can inspect.

This is the keystone of a four-project portfolio on AI in the public benefits
safety net. It is the layer the other three projects hand the actual legal
decision to.

> In government, "the model said so" is not a basis for denying someone food or
> medical coverage. The boundary between what a model decides and what code
> decides is the whole reason agentic AI is deployable in the public sector. This
> project puts that boundary on the table and exposes it over MCP.

## What it does

A household's facts go in. A determination comes out, and it is never a bare
yes/no. Every determination carries:

- the **decision** (eligible / ineligible),
- the **rule trace**: each rule that fired, what it saw, and what it concluded,
- a **policy citation** behind every rule (7 CFR, USDA FNS, or the Michigan
  Bridges Eligibility Manual),
- the **ruleset version** and the policy effective dates it was computed under,
- a reproducible **determination id** (a hash of the inputs, not a random id, so
  re-running the same case reproduces the same id).

It implements the federal SNAP financial eligibility test for the 48 contiguous
states and DC (FY2026 figures), with Michigan's broad-based categorical
eligibility applied as a state option.

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

pytest                              # 83 unit tests over the rules core and server
python eval/run_eval.py             # determination correctness (writes eval/report.md)
python eval/run_server_eval.py      # server robustness (writes eval/server_report.md)
python clients/demo_client.py       # drive the server over stdio (writes a transcript)
```

To wire the server into Claude Desktop or Claude Code, see
[`clients/demo.md`](clients/demo.md). A captured end-to-end transcript is in
[`clients/demo_transcript.md`](clients/demo_transcript.md).

## The tools

Few and sharp. Three require the caseworker scope; two are anonymous-safe.

| Tool | Scope | Returns |
|---|---|---|
| `screen_programs(household)` | screening | Coarse "likely eligible" signal across SNAP and a simplified Medicaid income screen. Not a determination; stores nothing. |
| `check_program_eligibility(program, household)` | caseworker | A full SNAP determination: decision + rule trace + citations + version. |
| `list_required_verifications(program, household)` | caseworker | The documents a caseworker must verify, derived from the facts the household presents. |
| `explain_determination(determination_id)` | caseworker | A plain, step-by-step trace of a prior determination by id. |
| `lookup_policy(question)` | screening | Cited policy answer. Currently an honest stub with a seam to the `policy-manual-rag` index. |

## Architecture

```
rules-as-code-mcp/
├── rules/                     # the deterministic core (no MCP, no network)
│   ├── constants.py           # FY2026 figures, derived from the poverty guidelines
│   ├── citations.py           # rule_id -> policy citation (enforced by tests)
│   ├── version.py             # ruleset version + effective dates
│   ├── models.py              # pydantic domain models (also the validation layer)
│   ├── snap.py                # the determination engine + net-income calculation
│   ├── programs.py            # cross-program screening + verification requirements
│   └── tests/                 # 63 unit tests over the logic
├── server/                    # the MCP boundary
│   ├── main.py                # FastMCP tool registration + error translation
│   ├── tools.py               # pure, scope-aware tool logic
│   ├── auth.py                # screening vs caseworker scope resolution
│   ├── errors.py              # structured, recoverable tool errors
│   ├── store.py               # determination cache for explain_determination
│   └── tests/                 # 20 unit tests over scope + errors
├── clients/                   # real MCP client demo + captured transcript
└── eval/                      # labeled cases + the two eval harnesses
```

The dependency arrow points one way: `server/` imports `rules/`, never the
reverse. The core has no idea it is being served over MCP, which is what keeps it
testable in isolation and reusable by the other portfolio projects (the
`benefits-intake-agent` imports this core directly or calls it over MCP).

## How the rule logic works

For a household with no elderly or disabled member, eligibility is two income
tests with deductions in between:

1. **Asset test.** Waived under Michigan's broad-based categorical eligibility.
2. **Gross income test.** Gross monthly income at or below 130% of the federal
   poverty guideline (200% under BBCE). Households with an elderly (60+) or
   disabled member are exempt from this test.
3. **Net income test.** After the statutory deductions (20% of earned income, the
   standard deduction, dependent care, child support paid, medical expenses over
   $35 for elderly/disabled members, and the excess shelter deduction), net income
   must be at or below 100% of poverty.

The excess shelter deduction is capped at $744/month, except for households with
an elderly or disabled member, where it is uncapped. All FY2026 dollar figures
live in one file, [`rules/constants.py`](rules/constants.py), each tied to a
citation. The income limits are the published USDA standards, independently
reproduced in the tests by deriving them from the 2025 HHS poverty guidelines.

When the FY2027 COLA is published, `constants.py` and `version.py` change. The
logic in `snap.py` does not. That separation is the point of rules-as-code.

## The scope boundary

Two scopes, resolved from the request context and never from a model-supplied
argument, so a model cannot escalate its own privileges:

- **screening** (anonymous): coarse signals, no PII collected or stored.
- **caseworker** (authenticated): full determinations, verifications, and stored
  explanations.

Over stdio the role comes from the `RULES_MCP_ROLE` environment variable; over
streamable-http it comes from the OAuth bearer token. The domain models carry no
names, SSNs, or addresses (only ages and flags), which is what lets anonymous
screening exist at all.

## Evaluation

Evaluation is the deliverable, not the demo. Two harnesses, both runnable as CI
gates with `--check`.

**Determination correctness** ([`eval/run_eval.py`](eval/run_eval.py), 18 hand-derived
labeled cases spanning eligible / ineligible / near-threshold / elderly /
deduction-edge / asset-waived):

| Metric | Result |
|---|---|
| Decision accuracy | 100% (18/18) |
| Rule-trace correctness (right rules fired) | 100% (18/18) |
| Citation correctness (right citation present) | 100% (18/18) |
| Net-income spot checks | 100% |
| Input-robustness (malformed input rejected) | 100% (7/7) |

**Server robustness** ([`eval/run_server_eval.py`](eval/run_server_eval.py)): 9/9
failure cases (privilege escalation, unsupported program, unknown id, malformed
and out-of-range input) return a clean, correctly-typed, recoverable structured
error. None crash; none leak an unauthorized result. The full failure-case table
with each structured response is in [`eval/server_report.md`](eval/server_report.md).

The labeled cases were derived by hand from 7 CFR 273.9 and the FY2026 standards,
independently of the implementation, so the eval is a real check rather than a
restatement of the code.

## Synthetic data only, never real PII

Every household this project touches is synthetic and illustrative. Handling
applicant data correctly is a hard requirement (you cannot touch real benefits
data) and a core public-sector competency, so the design keeps PII out of the
domain model entirely and gates all case detail behind the caseworker scope.

## How it composes with the rest of the portfolio

- `benefits-intake-agent` (the agent) calls `check_program_eligibility` here
  rather than reasoning about eligibility itself. The model extracts messy facts;
  this code makes the call.
- `policy-manual-rag` (the RAG index) is what `lookup_policy` will delegate to, so
  one server offers both deterministic determination and cited policy lookup.

Each repo also runs standalone.

## What I would do differently at production scale

- **Real rule sourcing.** The FY2026 figures are hand-entered from USDA and CBPP
  and verified against the poverty guidelines. At scale these would be ingested
  from the authoritative releases with a review step, and older rulesets would be
  retained so any past determination stays reproducible.
- **More than the financial test.** SNAP has work requirements, categorical and
  immigration rules, and state variation this does not model. The architecture
  (one program, fully cited, versioned) is built to extend to those rather than to
  hide them.
- **Production auth.** The scope model is real, but the HTTP token table is a
  demonstration stand-in for an identity provider, and over stdio the role is an
  environment variable. A deployment would issue and validate scoped tokens
  through the agency's IdP.
- **Persistence and audit.** The determination store is process-local. Production
  needs durable storage with retention and an audit log of who asked for what.

## Sources

- MCP: [specification](https://modelcontextprotocol.io/specification) (2025-11-25),
  [Python SDK](https://github.com/modelcontextprotocol/python-sdk) (`mcp` 1.27).
- SNAP: [7 CFR 273.9](https://www.ecfr.gov/current/title-7/part-273/section-273.9),
  [USDA FNS FY2026 COLA](https://www.fns.usda.gov/snap/allotment/COLA),
  [CBPP SNAP eligibility guide](https://www.cbpp.org/research/food-assistance/a-quick-guide-to-snap-eligibility-and-benefits),
  Michigan [BEM 213](https://dhhs.michigan.gov/OLMWEB/EX/BP/Public/BEM/213.pdf) (FAP categorical eligibility).
