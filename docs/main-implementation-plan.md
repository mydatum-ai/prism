implement it as **two monorepos**: `prism` for the open-core runtime, and `prism-enterprise` for the private intelligence and commercial extensions.

local referrence: 
1. prism is in "C:\Users\john_\Desktop\prism"
2. prism-enterprise is in "C:\Users\john_\Desktop\prism-enterprise"


## Target repo layout

```text
mydatum-ai/
├── prism                 # public
└── prism-enterprise      # private
```

## Phase-by-phase plan

### Phase 0 — Foundation

**prism**

```text
prism/
├── apps/
│   └── gateway/
├── packages/
│   ├── compiler/
│   ├── detectors/
│   ├── transformers/
│   ├── policy-runtime/
│   ├── vault-core/
│   ├── rehydration/
│   ├── evaluation/
│   └── sdk-python/
├── examples/
├── docs/
├── docker/
└── tests/
```

Build:

```text
FastAPI gateway
Pydantic schemas
pytest setup
ruff/mypy
Docker Compose
basic README
```

**prism-enterprise**

```text
prism-enterprise/
├── packages/
│   ├── semantic-engine/
│   ├── semantic-graph/
│   ├── domain-packs/
│   ├── optimizer/
│   ├── enterprise-vault/
│   └── eval-enterprise/
├── docs-private/
└── tests/
```

Build only skeleton interfaces first.

---

### Phase 1 — Public transformation MVP

**Goal:** transform → store mapping → rehydrate.

In `prism` build:

```text
POST /v1/transform
POST /v1/rehydrate
POST /v1/chat/mock
```

Implement:

```text
email detector
phone detector
simple name detector
invoice detector
token generator
in-memory vault
basic rehydration
audit event object
```

Example:

```text
John Smith → PERSON_1
john@email.com → EMAIL_1
INV-1001 → INVOICE_1
```

Completion:

```text
Unit tests pass
Can transform and rehydrate one prompt
No external LLM required yet
```

---

### Phase 2 — Mapping Vault

**Goal:** secure short-term memory.

In `prism`:

```text
packages/vault-core/
```

Implement:

```text
Vault interface
InMemoryVault
RedisVault
TTL expiry
tenant_id/app_id/session_id
mapping metadata
safe failure when expired
```

In `prism-enterprise` later:

```text
EnterpriseVault
KMS-backed encryption
high availability
```

Completion:

```text
Mappings expire
Rehydration fails closed
Vault never exposes mapping externally
```

---

### Phase 3 — Policy Runtime

**Goal:** policies decide transformation.

In `prism`:

```text
packages/policy-runtime/
```

Implement YAML rules:

```yaml
domain: pulse
rules:
  - entity_type: person
    role: resident
    action: tokenize
    token_prefix: RESIDENT

  - entity_type: email
    action: tokenize
    token_prefix: EMAIL

  - entity_type: money
    action: preserve
```

Support actions:

```text
preserve
tokenize
mask
generalize
abstract
block
```

Completion:

```text
Same prompt transforms differently under different policies
Policy version appears in audit event
```

---

### Phase 4 — Gateway + Provider adapter

**Goal:** Prism becomes usable as an AI proxy.

In `prism/apps/gateway`:

```text
POST /v1/chat/completions
POST /v1/responses optional later
```

Provider adapters:

```text
MockProvider
OpenAIProvider
```

Flow:

```text
request → transform → provider → rehydrate → response
```

Completion:

```text
Pulse can call Prism instead of OpenAI directly
OpenAI-compatible endpoint works
```

---

### Phase 5 — Evaluation Core

**Goal:** prove the engine works.

In `prism/packages/evaluation`:

Build:

```text
dataset loader
test runner
leakage scanner
rehydration validator
basic semantic comparator
JSON report
markdown report
CLI command: prism eval
```

Metrics:

```text
identity_leakage_score
rehydration_accuracy
transformation_correctness
quality_delta
latency_overhead
```

Public datasets:

```text
datasets/synthetic_pii
datasets/pulse_sample
datasets/customer_support
```

Completion:

```text
Can run benchmark against raw, redacted, tokenized, prism-transformed prompts
Produces report
```

---

### Phase 6 — Enterprise plugin loading

**Goal:** make private repo plug into public repo cleanly.

In `prism` define interfaces:

```python
SemanticAnalyzer
SemanticGraphBuilder
TransformationOptimizer
DomainPack
EnterpriseVault
AdvancedEvaluator
```

Plugin loading via config:

```env
PRISM_SEMANTIC_ANALYZER=prism_enterprise.semantic.Engine
PRISM_DOMAIN_PACKS=pulse,logsentry
```

Rule:

```text
prism never imports prism_enterprise directly
prism-enterprise depends on prism
```

Completion:

```text
Community edition runs without enterprise
Enterprise edition auto-loads private implementations
```

---

### Phase 7 — Local SLM semantic engine

In `prism-enterprise/packages/semantic-engine`:

Build:

```text
Ollama connector
JSON-only extraction prompt
Qwen/Llama/Gemma model support
entity role classifier
sensitivity classifier
recommendation generator
```

Output:

```json
{
  "entities": [
    {
      "text": "Maria Santos",
      "type": "person",
      "role": "public_official",
      "sensitivity": "medium",
      "recommendation": "generalize",
      "confidence": 0.92
    }
  ]
}
```

Completion:

```text
SLM recommends only
Policy still decides
```

---

### Phase 8 — Semantic Graph

In `prism-enterprise/packages/semantic-graph`:

Build:

```text
entity nodes
relationship edges
role inference
context extraction
graph-to-transformation hints
```

Example:

```text
Juan Dela Cruz → resident
12 Rizal Street → private residence
reported_flooding_at relationship
```

Completion:

```text
Transformation can preserve relationships, not just entities
```

---

### Phase 9 — Domain Packs

In `prism-enterprise/packages/domain-packs`:

Start with:

```text
pulse
logsentry
customer_support
```

Pulse pack:

```text
resident names → AFFECTED_RESIDENT
reporter names → REPORTER
public officials → PUBLIC_OFFICIAL
private addresses → private residence in same barangay
barangay/city/province → preserve
money/counts/dates → preserve
```

LogSentry pack:

```text
API keys → block
JWTs → tokenize
private IPs → tokenize
CVE IDs → preserve
timestamps → preserve
usernames → tokenize
```

Completion:

```text
Real MyDatum apps can use domain-specific policies
```

---

### Phase 10 — Enterprise evaluation

In `prism-enterprise/packages/eval-enterprise`:

Build:

```text
golden datasets
semantic retention scorer
LLM-as-judge optional
expert-labelled expected outputs
domain benchmark reports
optimizer feedback loop
```

Target report:

```text
Pulse dataset:
semantic retention: 95%+
identity leakage: <1%
rehydration accuracy: 99%+
quality delta: <10%
```

Completion:

```text
Can prove Prism is better than simple redaction/tokenization
```

---

### Phase 11 — Dashboard

In `prism-enterprise`:

Build later, not first.

```text
tenant dashboard
policy editor
transformation viewer
audit search
evaluation reports
leakage dashboard
semantic retention dashboard
```

Completion:

```text
Enterprise user can manage policies and inspect transformations
```

---

## Build order recommendation

```text
1. prism foundation
2. public transformation MVP
3. mapping vault
4. policy runtime
5. gateway + OpenAI adapter
6. evaluation core
7. enterprise plugin loading
8. local SLM semantic engine
9. semantic graph
10. Pulse domain pack
11. LogSentry domain pack
12. enterprise evaluation
13. dashboard
```

## Best rule to follow

Build this first:

```text
Transform → Vault → LLM → Rehydrate → Evaluate
```

Everything else is secondary.
