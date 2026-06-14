# Website blurb — rules-as-code-mcp

Drop-in copy for a portfolio page. A short paragraph plus highlight bullets.

---

## rules-as-code-mcp

The highest-leverage, least-noticed layer of AI in government is policy
codification: turning eligibility rules into auditable code. This project makes
that thesis literal. It implements the federal SNAP income test as deterministic,
tested, versioned code and exposes it to AI agents over the Model Context
Protocol, so a model can read and reason over a messy application while the actual
eligibility determination is made by code a caseworker or an auditor can inspect.
Every determination comes back with the rule trace and the policy citation behind
each rule, never a bare yes or no. It is the keystone of a four-project portfolio
on AI in the public benefits safety net, and it is the layer the other projects
hand the real decision to.

**Highlights**

- Deterministic SNAP eligibility core (FY2026 federal rules, Michigan categorical
  eligibility), with every dollar figure tied to a policy citation and a ruleset
  version.
- Exposed as five Model Context Protocol tools, with scoped permissions that
  separate anonymous screening from authenticated caseworker access.
- Every determination returns a result, a step-by-step rule trace, and a citation
  to 7 CFR or the state manual, so a decision is reproducible and explainable.
- Evaluated, not just demoed: 100% on 18 hand-labeled eligibility cases for
  decision, rule-trace, and citation correctness, and 9 of 9 failure cases handled
  with clean structured errors.
- Synthetic data only. PII is kept out of the model entirely and case detail is
  gated behind the caseworker scope.

---

*Voice note: I wrote this in a plain, finding-first register with the house style
from your other writing (no em dashes, no stock transitions, evidence over
decoration). Worth a final pass against the live aselzer.com voice before it goes
up, since I drafted from that style rather than the deployed site.*
