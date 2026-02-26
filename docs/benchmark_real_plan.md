To make functional testing meaningful (and fast), you want repositories that are (a) representative of real CI/CD needs, (b) safe and deterministic to run in an evaluation harness, and (c) cheap in runtime. A good approach is to define **hard filters** (must-pass), then **scoring/ranking** (to pick a small, diverse set).

## 1) Hard filters: “must be runnable, safe, and comparable”

### A. Can run without privileged credentials
Keep repos whose CI can succeed on a fork/PR **without secrets**:

- No required `secrets.*` for the “main” CI path (tests/lint/build).
- No required access to private registries, private submodules, or paid services.
- Avoid workflows that require:
  - signing keys, publishing tokens, deployment credentials
  - GitHub Environments with required reviewers
  - self-hosted runners behind a firewall

**Why:** Your benchmark should evaluate workflow generation, not secret provisioning.

### B. Hosted-runner compatible
Require that the repo can run on GitHub-hosted runners:

- Uses `runs-on: ubuntu-latest` / `windows-latest` / `macos-latest` (at least one)
- No `runs-on: self-hosted` needed for core CI
- No GPU-only assumptions

### C. Deterministic and low-flake test suite
Pick repos with stable CI:

- Low failure rate on default branch over recent runs
- No “nightly-only” behavior for basic tests
- Avoid tests that depend on timing, network instability, or external APIs

**Practical heuristic:** check recent CI runs and require something like “$\ge 95\%$ success rate” on the default branch for the job(s) you’ll exercise.

### D. Reasonable runtime and resource footprint
Set explicit caps:

- Median runtime under a threshold, e.g. **$\le 5$–$10$ minutes** for the targeted workflow path
- No very large Docker builds, giant integration suites, or multi-arch builds as the *main* CI signal
- Avoid monorepos where any CI run fan-outs to dozens/hundreds of jobs

### E. Clean licensing and reproducible dependencies
- OSI-approved license (MIT/Apache-2.0/BSD, etc.)
- Builds/tests don’t require non-redistributable artifacts
- Dependency install is straightforward (e.g., `npm ci`, `pip install -r`, `go test ./...`)

---

## 2) Relevance filters: “will exercise real workflow-generation skills”

### A. Contains CI-relevant “ground truth” tasks
Choose repos that naturally require common CI steps, so prompts map to real workflows:

- Install dependencies
- Lint/format
- Run unit tests
- Build artifacts
- Cache dependencies
- Upload test reports/artifacts

This creates realistic prompts like “add caching”, “split lint vs test”, “matrix by language version”, “upload coverage”, etc.

### B. Uses common ecosystems (for generality)
Aim for a small set that covers popular stacks:

- Node.js, Python, Go, Java, Rust, .NET (pick 3–6 total)
- Optional: one repo that needs Docker, one that is docs-only, one that is a CLI library, etc.

### C. “Workflow complexity without being expensive”
You want workflows that are non-trivial but not slow. Look for:

- Version matrix (e.g., Python 3.10–3.12, Node 18/20)
- OS matrix (maybe just Ubuntu + one other)
- Caching (pip/npm/go build cache)
- Artifact upload
- Basic concurrency/cancel-in-progress behavior

Avoid:
- multi-stage release pipelines
- deployments
- long integration environments

---

## 3) Security and containment criteria (important for running untrusted generated workflows)

If you’re going to run agent-generated YAML, treat it as adversarial.

### A. Repo should be safe to run in a sandboxed evaluation setup
- Prefer repos where “normal CI” doesn’t require elevated permissions
- Avoid repos that legitimately need:
  - `permissions: write-all`
  - `pull_request_target` usage
  - writing to repo contents/releases/packages

### B. Enforce minimal token permissions in evaluation
Even if the repo is safe, your benchmark harness should enforce constraints (and you can prefer repos that don’t break under them):

- `permissions: contents: read`
- Disallow `pull_request_target`
- Disallow workflow modifications that request broad permissions

Repos whose CI fundamentally needs write permissions (e.g., auto-format PRs, auto-commit) are usually poor benchmark targets unless you explicitly want that category.

---

## 4) Ranking/scoring to pick “a few” repos

After hard filtering, score candidates across dimensions and select a **diverse top set** (stratified sampling). Example scoring dimensions:

| Dimension | What to measure | Why it matters |
|---|---|---|
| Runtime | median job duration | cost |
| Flakiness | failure rate excluding code changes | signal quality |
| Complexity | matrix size, caching, artifacts | discriminates agents |
| Ecosystem | language/toolchain diversity | generalization |
| Maintenance | recent commits/releases | avoids bitrot |
| Dependency cost | install time, large downloads | cost + reliability |
| Security posture | minimal permissions, no secrets | safe functional testing |

Then pick, for example, **6–12 repos**: 1–2 per ecosystem, mixing “simple” and “moderately complex”.

---

## 5) Concrete repository selection heuristics (actionable)

### Quick “keep” heuristics
- Has a working CI workflow already (you can mine it to design prompts), but your evaluation still runs the agent-generated one.
- Default CI can run on PRs from forks without secrets.
- Typical CI finishes in under 10 minutes.
- Uses standard test commands (`pytest`, `npm test`, `go test`, `mvn test`, etc.).
- Recent activity within the last 6–12 months.

### Quick “drop” heuristics
- Needs cloud credentials, integration services, or private resources to pass.
- Regularly flaky (timeouts, network calls, rate limits).
- Very large monorepo or requires heavy build tooling.
- Requires self-hosted runners.
- CI depends on `pull_request_target` or high-permission tokens.

---

<details>
<summary>How to operationalize this filtering (data sources + automation ideas)</summary>

### A. Mine runtime and flakiness from GitHub APIs
- Use GitHub Actions runs API to compute:
  - median duration per workflow/job
  - success rate over last $N$ runs (e.g., $N = 50$)
- Exclude runs triggered by schedules if they’re noisier than PR/push.

### B. Detect “needs secrets” and risky patterns statically
Parse existing workflows in the repo to flag:
- `secrets.` usage
- `pull_request_target`
- `permissions: write-all` or broad scopes
- `uses:` actions that are unpinned to a SHA (optional, but relevant)
- `runs-on: self-hosted`

### C. Detect “expensive patterns”
- Docker build/push steps
- Large matrices (e.g., $\gt 6$ combinations)
- Integration services (databases, browsers, k8s) unless you want that class

### D. Create repository “profiles” and stratify
Compute a profile like:
- language ecosystem
- expected install + test time
- complexity score
Then select a balanced subset instead of just “fastest”.

</details>

---

## 6) Recommended minimal target set composition

If you truly only want “a few”, I’d pick something like **8 repos**:

- 2 repos with very standard unit-test CI (fast, baseline)
- 3 repos with caching + matrix versions (moderate complexity)
- 1 repo requiring artifacts upload (e.g., build output or coverage)
- 1 repo with OS matrix (Ubuntu + Windows or macOS)
- 1 repo with a lightweight containerized service (optional, if you want to test `services:`)

This gives you functional coverage without turning evaluation into a full CI farm.

---

If you tell me your intended prompt categories (e.g., “add caching”, “add matrix”, “tighten permissions”, “upload coverage”, “pin actions”), I can propose a concrete scoring formula and a repository sampling plan that matches those tasks.
