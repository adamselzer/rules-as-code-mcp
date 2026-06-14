# Portfolio notes — rules-as-code-mcp

A plain-language account of what this project is and the judgment behind it.

## Pattern

**MCP (Model Context Protocol).** A server that exposes deterministic eligibility
logic as tools an AI agent can call. This is the newest of the four FDE build
patterns and the one fewest candidates have touched.

## Concept demonstrated

Exposing a deterministic, auditable, versioned decision core to AI agents over
MCP, and drawing the line between what the model is allowed to decide (nothing,
when it comes to eligibility) and what the code decides (everything). That
boundary is what makes agentic AI deployable in government at all. The model
reads, reasons, and orchestrates; the determination is made by tested code that
returns a rule trace and a policy citation every time.

## Why it matters in this domain

A hallucinated eligibility answer is not an embarrassment, it is a wrongful denial
of food or medical coverage. Agencies, auditors, and courts can review code and
cited rules. They cannot review a model's hidden reasoning. So the question an FDE
faces in the public sector is not "can the model get it right often enough," it is
"where does the model stop and the inspectable code start." This project answers
that by construction: there is no path through it where a model's judgment becomes
a determination.

## Key design decisions and tradeoffs

1. **A separate deterministic core, with MCP only at the edge.** The rules live in
   `rules/` with no MCP and no network; `server/` is a thin boundary that imports
   the core. *Rejected:* implementing eligibility inside the MCP tool handlers.
   That would have been fewer files, but it would have tangled protocol concerns
   with legal logic and made the core untestable in isolation and unusable by the
   sibling agent project. The one-way dependency is what lets the same core be
   imported directly or called over MCP.

2. **Constants derived from the poverty guidelines, separated from logic.** Every
   FY2026 dollar figure sits in one file, each tied to a citation, and the tests
   reproduce the published income limits by deriving them from the 2025 poverty
   guidelines. *Rejected:* scattering thresholds through the rule code as literals.
   Pulling them into one versioned file means the annual COLA is a data change, not
   a logic change, and the independent derivation catches a typo that would
   otherwise silently shift an eligibility line.

3. **Reproducible determination ids (a hash of the inputs), not random uuids.**
   Re-running the same case under the same ruleset yields the same id. *Rejected:* a
   random id per call. The hash makes the id itself an audit artifact and lets the
   eval and the explain tool work without a database in the loop.

4. **Scope resolved from the request context, never from a tool argument.** A model
   cannot ask to be a caseworker; the scope comes from the transport (an OAuth
   token over HTTP, an environment role over stdio). *Rejected:* passing a role or
   token as a tool parameter. That would have been trivially testable but would
   have handed privilege escalation to the very model the boundary exists to
   contain.

5. **An honest stub for `lookup_policy`, not a plausible fake.** The policy lookup
   tool returns an explicit "not yet connected" placeholder rather than an invented
   answer, with a seam to the `policy-manual-rag` index. *Rejected:* a hardcoded
   sample answer to make the demo look complete. Fabricating a policy answer is
   precisely the failure this project exists to prevent, so faking it here would
   contradict the thesis.

## How it's evaluated

Two harnesses, both runnable as CI gates.

- **Determination correctness:** 18 labeled cases derived by hand from 7 CFR 273.9
  and the FY2026 standards, independently of the code, spanning eligible,
  ineligible, near-threshold, elderly/disabled, deduction-edge, and asset-waived
  households. The harness checks four things per case: the decision, that the right
  rules fired, that the right citation is present, and (where pinned) the computed
  net income. Headline result: 100% on all four, plus 7/7 on malformed-input
  rejection.
- **Server robustness:** 9 failure cases (privilege escalation, unsupported
  program, unknown determination id, malformed and out-of-range input). Headline
  result: 9/9 return a clean, correctly-typed, recoverable structured error. None
  crash; none leak an unauthorized result.

The metrics are chosen to match the stake. Decision accuracy is table stakes;
rule-trace and citation correctness are what make a determination defensible; and
the robustness suite is the safety case for putting a model on the other end of
these tools.

## What I would do differently at production scale

- Ingest the rule figures from the authoritative USDA releases with a review step,
  and retain old rulesets so any past determination stays reproducible.
- Model the parts of SNAP this omits (work requirements, categorical and
  immigration rules, state variation). The architecture is built to extend to them
  rather than to paper over them.
- Replace the demonstration token table with the agency's identity provider, and
  the process-local determination store with durable storage plus an audit log of
  who requested what.
- Wire `lookup_policy` to the real retrieval index so one server offers both
  determination and cited policy lookup.
