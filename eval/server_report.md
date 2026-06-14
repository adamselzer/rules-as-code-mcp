# Server robustness report

Every bad call must produce a clean, correctly-typed structured error -- never a crash, never an unauthorized result.

**Result: 9/9 failure cases handled cleanly.**

| Failure case | Error type | Handled cleanly |
|---|---|---|
| Screening scope tries a determination (privilege escalation) | `authorization_error` | ok |
| Screening scope tries to list verifications | `authorization_error` | ok |
| Screening scope tries to explain a determination | `authorization_error` | ok |
| Unsupported program (tool misuse) | `tool_misuse_error` | ok |
| Unknown determination id | `not_found_error` | ok |
| Empty household (semantic validation) | `input_validation_error` | ok |
| Negative income (domain constraint) | `input_validation_error` | ok |
| Household is not an object | `input_validation_error` | ok |
| Empty policy question | `input_validation_error` | ok |

## Structured responses

**Screening scope tries a determination (privilege escalation)**

```json
{"error": {"type": "authorization_error", "message": "This tool requires the 'caseworker' scope.", "recoverable": false, "hint": "Authenticate as a caseworker. Over HTTP, present a bearer token with the caseworker scope; over stdio, launch the server with RULES_MCP_ROLE=caseworker.", "details": {"required_scope": "caseworker", "granted_scopes": ["screening"]}}}
```

**Screening scope tries to list verifications**

```json
{"error": {"type": "authorization_error", "message": "This tool requires the 'caseworker' scope.", "recoverable": false, "hint": "Authenticate as a caseworker. Over HTTP, present a bearer token with the caseworker scope; over stdio, launch the server with RULES_MCP_ROLE=caseworker.", "details": {"required_scope": "caseworker", "granted_scopes": ["screening"]}}}
```

**Screening scope tries to explain a determination**

```json
{"error": {"type": "authorization_error", "message": "This tool requires the 'caseworker' scope.", "recoverable": false, "hint": "Authenticate as a caseworker. Over HTTP, present a bearer token with the caseworker scope; over stdio, launch the server with RULES_MCP_ROLE=caseworker.", "details": {"required_scope": "caseworker", "granted_scopes": ["screening"]}}}
```

**Unsupported program (tool misuse)**

```json
{"error": {"type": "tool_misuse_error", "message": "Program 'TANF' is not supported.", "recoverable": true, "hint": "Supported programs: ['SNAP']. This server determines SNAP.", "details": {"supported_programs": ["SNAP"]}}}
```

**Unknown determination id**

```json
{"error": {"type": "not_found_error", "message": "No determination found with id 'snap-does-not-exist'.", "recoverable": false, "hint": "Run check_program_eligibility first; use the determination_id it returns.", "details": {"known_count": 0}}}
```

**Empty household (semantic validation)**

```json
{"error": {"type": "input_validation_error", "message": "The household failed validation.", "recoverable": true, "hint": "Fix the listed fields and retry. Monetary fields must be non-negative numbers.", "details": {"validation_errors": [{"type": "too_short", "loc": ["members"], "msg": "List should have at least 1 item after validation, not 0", "ctx": {"field_type": "List", "min_length": 1, "actual_length": 0}}]}}}
```

**Negative income (domain constraint)**

```json
{"error": {"type": "input_validation_error", "message": "The household failed validation.", "recoverable": true, "hint": "Fix the listed fields and retry. Monetary fields must be non-negative numbers.", "details": {"validation_errors": [{"type": "greater_than_equal", "loc": ["income", 0, "monthly_amount"], "msg": "Input should be greater than or equal to 0", "ctx": {"ge": 0.0}}]}}}
```

**Household is not an object**

```json
{"error": {"type": "input_validation_error", "message": "The 'household' argument must be an object.", "recoverable": true, "hint": "Pass household as a JSON object with a 'members' array.", "details": {"received_type": "str"}}}
```

**Empty policy question**

```json
{"error": {"type": "input_validation_error", "message": "The 'question' argument must be a non-empty string.", "recoverable": true, "hint": "Pass a policy question, e.g. 'How is self-employment income counted?'", "details": {}}}
```
