# Research Plan: Benchmarking LLM Agents for GitHub Actions Workflow Generation

## 1. Research Framing & Motivation

### 1.1 Problem Statement

Large Language Models are increasingly used as code-generation agents, yet there is no rigorous, reproducible benchmark for evaluating their ability to generate *correct, functional* CI/CD workflows—specifically GitHub Actions workflows. Existing code-generation benchmarks (HumanEval, SWE-bench, etc.) focus on general-purpose code, ignoring the declarative, event-driven, and infrastructure-coupled nature of CI/CD definitions.

### 1.2 Research Questions

| ID | Research Question |
|---|---|
| **RQ1** | How accurately can state-of-the-art LLM agents generate GitHub Actions workflows that are syntactically valid, semantically correct, and functionally complete? |
| **RQ2** | Which categories of workflow features (e.g., matrix builds, caching, secrets, reusable workflows) are most challenging for LLMs? |
| **RQ3** | How do different prompting strategies (zero-shot, few-shot, chain-of-thought, retrieval-augmented) affect generation quality? |
| **RQ4** | What is the correlation between static analysis pass rates and actual runtime correctness? |
| **RQ5** | How do models compare across different complexity tiers of workflow tasks? |

### 1.3 Contributions (Target)

1. **GHA-Bench**: An open-source, reproducible benchmark suite of synthetic repositories with ground-truth workflow specifications.
2. **A multi-dimensional evaluation framework** combining static analysis, runtime execution, and artifact/log validation.
3. **A large-scale empirical study** across multiple LLMs and prompting strategies.
4. **Actionable taxonomy** of failure modes in LLM-generated CI/CD workflows.

---

## 2. Benchmark Design: GHA-Bench

### 2.1 Design Principles

- **Isolation**: Each repository tests a controlled set of features; no confounding dependencies between test dimensions.
- **Determinism**: Workflows must produce deterministic, verifiable outputs (artifacts, exit codes, log patterns).
- **Coverage**: Systematic coverage of the GitHub Actions feature space (see taxonomy below).
- **Realism**: Tasks should mirror real-world usage patterns mined from open-source repositories.
- **Scalability**: The benchmark framework must support adding new tasks without re-engineering infrastructure.
- **Reproducibility**: Pinned action versions, containerized runners, seeded randomness.

### 2.2 Feature Taxonomy & Task Categories

Construct a **hierarchical taxonomy** of GitHub Actions features. Each leaf node becomes one or more benchmark tasks.

<details>
<summary><strong>Tier 1 — Foundational (Single-Feature Tasks)</strong></summary>

| Category | Feature | Example Task |
|---|---|---|
| **Triggers** | `push`, `pull_request` | Generate a workflow that runs on push to `main` only |
| **Triggers** | `schedule` (cron) | Generate a nightly build workflow |
| **Triggers** | `workflow_dispatch` with inputs | Generate a manually-triggered workflow with a string and choice input |
| **Triggers** | `repository_dispatch` | Trigger on a custom webhook event |
| **Triggers** | Path/branch filters | Run only when `src/**` files change |
| **Jobs** | Single job, single step | Run `echo "Hello World"` and verify log output |
| **Jobs** | Multiple steps with ordering | Run three sequential shell commands |
| **Jobs** | `runs-on` specific runner | Target `ubuntu-22.04` vs. `ubuntu-latest` |
| **Steps** | `run` (shell commands) | Execute a bash script inline |
| **Steps** | `uses` (action reference) | Use `actions/checkout@v4` |
| **Steps** | `with` (action inputs) | Pass parameters to an action |
| **Steps** | `working-directory` | Run commands in a subdirectory |
| **Environment** | `env` at workflow/job/step level | Set and use environment variables at each scope |
| **Environment** | `$GITHUB_OUTPUT` | Set step outputs using the new file-based syntax |
| **Environment** | `$GITHUB_ENV` | Set environment variables for subsequent steps |
| **Outputs** | Step outputs consumed by later steps | Chain output from step A to step B |

</details>

<details>
<summary><strong>Tier 2 — Intermediate (Multi-Feature Tasks)</strong></summary>

| Category | Feature | Example Task |
|---|---|---|
| **Job Dependencies** | `needs` keyword | Three jobs in a DAG: build → test → deploy |
| **Job Dependencies** | Conditional job execution | Run deploy only if test succeeds |
| **Matrix Strategy** | Basic matrix | Test across Node 18, 20, 22 |
| **Matrix Strategy** | Multi-dimensional matrix | OS × Language version matrix |
| **Matrix Strategy** | `include` / `exclude` | Add a specific combination; exclude another |
| **Matrix Strategy** | `fail-fast` and `max-parallel` | Control parallelism and failure behavior |
| **Conditionals** | `if` expressions | Skip a step based on branch name |
| **Conditionals** | Status functions (`success()`, `failure()`, `always()`) | Run cleanup step on failure only |
| **Conditionals** | Expression syntax with `github` context | Conditional on `github.event_name` |
| **Caching** | `actions/cache` | Cache `node_modules` with hash-based key |
| **Caching** | Restore keys / fallback | Implement cache fallback strategy |
| **Artifacts** | `actions/upload-artifact` / `download-artifact` | Upload build output, download in next job |
| **Artifacts** | Retention and naming | Set custom artifact retention days |
| **Services** | Service containers | Start a PostgreSQL service for integration tests |
| **Services** | Health checks and port mapping | Wait for Redis to be ready before running tests |
| **Permissions** | `permissions` key | Set minimal `contents: read` permissions |
| **Timeouts** | `timeout-minutes` | Set job and step-level timeouts |
| **Continue-on-error** | `continue-on-error` at step/job | Allow a linting step to fail without failing the job |
| **Defaults** | `defaults.run.shell`, `defaults.run.working-directory` | Set default shell to `bash` and default directory |

</details>

<details>
<summary><strong>Tier 3 — Advanced (Complex/Composed Tasks)</strong></summary>

| Category | Feature | Example Task |
|---|---|---|
| **Reusable Workflows** | `workflow_call` with inputs/outputs/secrets | Create a caller and callee workflow pair |
| **Composite Actions** | Local composite action | Define a local action in `.github/actions/` and invoke it |
| **Concurrency** | `concurrency` groups | Cancel in-progress runs on new push |
| **Concurrency** | `cancel-in-progress` | Implement branch-based concurrency groups |
| **Docker** | Container jobs (`container:`) | Run entire job inside a Docker container |
| **Docker** | Build and push Docker image | Build, tag, and push to GHCR |
| **Secrets** | `secrets` context | Use a secret in an environment variable (mock) |
| **Secrets** | Environment-scoped secrets | Deploy to staging vs. production environments |
| **Environments** | `environment` with protection rules | Reference a named environment with URL |
| **OIDC** | `id-token: write` permissions | Configure OIDC for cloud provider authentication |
| **Dynamic Matrix** | Matrix from prior job output | Generate matrix values dynamically from a JSON file |
| **Expressions** | Complex expressions | `fromJSON()`, `toJSON()`, `contains()`, `format()` |
| **Path-based Logic** | `dorny/paths-filter` or native `paths` | Conditionally run jobs based on changed files |
| **Multi-file** | Workflow + action + reusable workflow | Orchestrate multiple YAML files together |

</details>

<details>
<summary><strong>Tier 4 — End-to-End Realistic Scenarios</strong></summary>

| Scenario | Description |
|---|---|
| **Node.js CI Pipeline** | Lint → test (matrix: OS × Node version) → build → upload artifact → deploy |
| **Python Package Release** | Test → build wheel → publish to PyPI on tag push |
| **Monorepo CI** | Detect changed packages → run tests only for affected packages |
| **Terraform IaC** | `plan` on PR, `apply` on merge to main, with OIDC auth |
| **Docker Multi-arch** | Build multi-platform images using `docker/build-push-action` |
| **Release Automation** | Create GitHub Release with auto-generated changelog on tag |
| **Scheduled Maintenance** | Nightly dependency update check + issue creation |
| **Security Scanning** | CodeQL analysis + SARIF upload + PR comment |
| **Deployment Pipeline** | Staging → manual approval gate → production (using environments) |
| **Cross-repo Trigger** | Repository dispatch from repo A triggers workflow in repo B |

</details>

### 2.3 Task Specification Format

Each benchmark task is a self-contained directory with:

```
task-<id>/
├── README.md                    # Human-readable task description
├── prompt.md                    # Exact prompt given to the LLM
├── repo/                        # Synthetic repository contents
│   ├── src/                     # Source code (if needed)
│   ├── package.json / setup.py  # Language ecosystem files
│   ├── tests/                   # Test files (if needed)
│   └── .github/
│       └── actions/             # Pre-existing composite actions (if needed)
├── spec.yaml                    # Machine-readable task specification
├── oracle/                      # Ground-truth reference
│   └── .github/workflows/       # Reference workflow(s)
├── validation/
│   ├── static_checks.yaml       # Expected static analysis results
│   ├── runtime_checks.yaml      # Runtime assertions
│   └── validate.py              # Custom validation script
└── metadata.yaml                # Task metadata (tier, features, difficulty)
```

**`spec.yaml`** schema:

```yaml
task_id: "matrix-node-versions"
version: "1.0"
tier: 2
features_tested:
  - matrix_strategy
  - uses_action
  - node_setup
prompt_type: "natural_language"  # or "structured", "partial_completion"
expected_outputs:
  workflow_files:
    - path: ".github/workflows/ci.yml"
      required: true
  artifacts:
    - name: "test-results"
      content_checks:
        - type: "file_exists"
          path: "junit.xml"
  logs:
    - job: "test"
      step: "Run tests"
      patterns:
        - regex: "\\d+ passing"
        - must_not_contain: "FAILED"
  exit_codes:
    - job: "test"
      expected: 0
```

### 2.4 Prompt Design

Each task includes **multiple prompt variants** to support RQ3:

| Variant | Description |
|---|---|
| **NL-minimal** | Brief natural language description ("Create a CI workflow that tests on Node 18 and 20") |
| **NL-detailed** | Detailed specification with explicit requirements |
| **Structured** | Bulleted requirements list with constraints |
| **Partial** | Skeleton YAML with `# TODO` placeholders to fill in |
| **Conversational** | Multi-turn: initial prompt → clarification → refinement |

---

## 3. Evaluation Framework

### 3.1 Multi-Layer Evaluation Pipeline

```
┌─────────────────────────────────────────────────────────┐
│                    Generated Workflow                     │
└──────────┬──────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────┐    ┌──────────────────────────┐
│  L1: Syntactic        │    │  L2: Security / Lint     │
│  Validity             │    │  Analysis                │
│  ─────────────────    │    │  ──────────────────────  │
│  • YAML parse         │    │  • actionlint            │
│  • Schema validation  │    │  • Scorecard / Zizmor    │
│  • Key correctness    │    │  • Pin-to-SHA check      │
│                       │    │  • Permissions audit     │
└──────────┬────────────┘    └──────────┬───────────────┘
           │                            │
           ▼                            ▼
┌──────────────────────────────────────────────────────────┐
│  L3: Structural / Semantic Analysis                       │
│  ─────────────────────────────────────────────────────    │
│  • Feature presence check (does it USE a matrix?)         │
│  • Dependency graph validation (job DAG correctness)      │
│  • Trigger correctness                                    │
│  • Expression syntax validation                           │
└──────────┬───────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────┐
│  L4: Runtime Execution & Behavioral Validation            │
│  ─────────────────────────────────────────────────────    │
│  • Execute workflow via act or self-hosted runner          │
│  • Assert exit codes per job                              │
│  • Assert artifact existence and content                  │
│  • Assert log patterns (regex matching)                   │
│  • Assert job/step execution order                        │
│  • Assert matrix expansion (correct # of jobs)            │
│  • Assert service container interactions                  │
└──────────────────────────────────────────────────────────┘
```

### 3.2 Metrics

| Metric | Scope | Definition |
|---|---|---|
| **Syntax Pass Rate** | L1 | $\frac{\text{# workflows that parse as valid YAML + valid GHA schema}}{\text{total}}$ |
| **Lint Pass Rate** | L2 | $\frac{\text{# workflows with 0 actionlint errors}}{\text{total}}$ |
| **Security Score** | L2 | Mean security score from Zizmor/Scorecard (0–10 scale) |
| **Feature Recall** | L3 | $\frac{\text{# required features correctly implemented}}{\text{# required features specified}}$ |
| **Feature Precision** | L3 | $\frac{\text{# correctly implemented features}}{\text{# features present in generated workflow}}$ |
| **Structural F1** | L3 | Harmonic mean of Feature Recall and Precision |
| **Execution Pass Rate** | L4 | $\frac{\text{# workflows where all jobs exit with expected codes}}{\text{total}}$ |
| **Artifact Correctness** | L4 | $\frac{\text{# tasks with all artifact assertions passing}}{\text{# tasks with artifact assertions}}$ |
| **Log Assertion Rate** | L4 | $\frac{\text{# log pattern assertions passing}}{\text{total log assertions}}$ |
| **Full Pass Rate** | All | $\frac{\text{# tasks passing ALL layers}}{\text{total tasks}}$ |
| **Weighted Score** | All | Weighted composite: $S = w_1 \cdot L1 + w_2 \cdot L2 + w_3 \cdot L3 + w_4 \cdot L4$ |

### 3.3 Runtime Execution Infrastructure

**Option A: `nektos/act` (local execution)** — Preferred for reproducibility and cost.

- Pros: No GitHub API dependency, fast, free, deterministic.
- Cons: Incomplete feature parity with GitHub-hosted runners (some actions fail, no OIDC, limited services support).
- Mitigation: Maintain a compatibility matrix; tag tasks with `act-compatible: true/false`.

**Option B: GitHub-hosted runners via real repositories**

- Pros: Full feature parity.
- Cons: Rate limits, cost, slower, non-deterministic timing.
- Use selectively for Tier 3–4 tasks that require features `act` cannot emulate.

**Option C: Self-hosted runners in controlled VMs**

- Pros: Full control + reproducibility.
- Cons: Infrastructure overhead.

**Recommended**: Hybrid approach — `act` for Tiers 1–2 (~70% of tasks), GitHub-hosted for Tiers 3–4 with features requiring real infrastructure.

### 3.4 Ground Truth & Oracle Design

For each task, provide:

1. **Reference workflow(s)**: Human-authored, reviewed, tested.
2. **Assertion suite**: Decoupled from the reference implementation — validates *behavior*, not exact YAML match.
3. **Multiple valid solutions flag**: Some tasks accept multiple correct approaches; validation must be behavior-based, not diff-based.

---

## 4. Experimental Design

### 4.1 Independent Variables

| Variable | Values |
|---|---|
| **LLM Model** | GPT-4o, GPT-4.1, Claude Opus 4, Claude Sonnet 4, Gemini 2.5 Pro, DeepSeek-V3, Llama 4 Maverick, Codestral, (open-weight models for reproducibility) |
| **Prompting Strategy** | NL-minimal, NL-detailed, Structured, Partial, Few-shot (1, 3, 5 examples), CoT, RAG (with GHA docs) |
| **Temperature** | 0.0 (greedy), 0.2, 0.7 |
| **Task Tier** | 1, 2, 3, 4 |
| **Context Provision** | No repo context, file listing only, full repo context |

### 4.2 Dependent Variables

All metrics from §3.2.

### 4.3 Controls

- **Prompt phrasing**: Fixed across models (verbatim identical prompts).
- **API parameters**: Fixed `max_tokens`, `top_p`, `temperature` per experimental condition.
- **Evaluation environment**: Pinned Docker images, pinned action versions, pinned tool versions.
- **Repeated trials**: $n = 5$ generations per (model, prompt, task) triple at non-zero temperatures to measure variance.

### 4.4 Sample Size & Statistical Power

- Target: **≥100 tasks** across tiers (≈30 Tier 1, 30 Tier 2, 25 Tier 3, 15 Tier 4).
- With 8 models × 5 prompt strategies × 100 tasks × 5 trials = **20,000 generations** (for the full experiment; can subset).
- Use **mixed-effects logistic regression** for binary outcomes (pass/fail) with random effects for task and model.
- Report **95% confidence intervals** using bootstrap resampling.
- Effect sizes using **Cohen's $\kappa$** for inter-rater agreement and **Cliff's $\delta$** for ordinal comparisons.

### 4.5 Ablation Studies

1. **Prompt informativeness ablation**: Vary from minimal → detailed and measure Δ in pass rates.
2. **Context window ablation**: Vary repository context provided (none → file tree → full files).
3. **Few-shot scaling**: 0, 1, 3, 5 examples.
4. **Feature complexity**: Isolate per-feature difficulty by comparing single-feature tasks to multi-feature tasks containing the same feature.

---

## 5. Benchmark Validation (Meta-Evaluation)

A benchmark is only as good as its validity. This section is **critical for publication rigor**.

### 5.1 Content Validity

- **Feature coverage audit**: Map taxonomy against a sample of 10,000 real-world GHA workflows from GitHub (mine using BigQuery `githubarchive` or `ghs` dataset). Compute coverage of feature n-grams.
- **Expert review**: Have 3–5 DevOps/CI-CD practitioners review task specifications for realism (Likert scale + qualitative feedback).
- **Comparison to existing benchmarks**: Explicitly contrast with HumanEval, SWE-bench, DevBench, etc., highlighting what GHA-Bench covers that they don't.

### 5.2 Construct Validity

- **Metric convergence**: Do L1–L4 metrics correlate as expected? (L4 failures should be a superset of L1 failures.)
- **Discriminant validity**: Do different models produce statistically distinguishable scores? (If all models score the same, the benchmark lacks discrimination.)
- **Difficulty calibration**: Verify that Tier 1 < Tier 2 < Tier 3 < Tier 4 in average difficulty (measured empirically).

### 5.3 Criterion Validity

- **Human baseline**: Have 5+ experienced developers complete a subset of tasks (≥30 tasks). Their pass rates serve as a human ceiling.
- **Novice baseline**: Have 5 developers with <1 year experience complete the same subset. This calibrates difficulty.
- **Correlation with real-world performance**: If possible, correlate GHA-Bench scores with model performance on real open-source GHA contribution tasks.

### 5.4 Reliability

- **Test-retest reliability**: Run the same model on the same tasks at temperature 0 twice; assert determinism.
- **Inter-rater reliability for subjective judgments**: For any human-evaluated components, compute Cohen's $\kappa$ with $\kappa > 0.8$ required.
- **Evaluation determinism**: The validation pipeline itself must be deterministic — no flaky tests. Run the oracle against the reference solutions 10 times to confirm 100% pass rate.

### 5.5 Preventing Data Contamination

- **Novelty of tasks**: All repository names, variable names, and project structures are synthetic and unique (not copied from existing repos).
- **Temporal cutoff verification**: Check that reference solutions do not appear verbatim in Common Crawl / The Stack.
- **Canary strings**: Embed unique identifiers in prompts; search for them in model outputs to detect memorization.
- **Private holdout**: Maintain a private subset (20% of tasks) that is never publicly released, for re-evaluation.

---

## 6. Implementation Plan

### Phase 1: Foundation (Weeks 1–4)

| Week | Deliverable |
|---|---|
| 1 | Finalize taxonomy via literature review + mining real workflows |
| 2 | Design `spec.yaml` schema and validation framework architecture |
| 3 | Implement evaluation pipeline (L1–L3): YAML parser, schema validator, actionlint integration, structural checks |
| 4 | Implement L4 runtime execution harness using `act` with Docker |

### Phase 2: Benchmark Construction (Weeks 5–10)

| Week | Deliverable |
|---|---|
| 5–6 | Author Tier 1 tasks (30 tasks) with reference solutions + validation |
| 7–8 | Author Tier 2 tasks (30 tasks) |
| 9 | Author Tier 3 tasks (25 tasks) |
| 10 | Author Tier 4 tasks (15 tasks) + full integration test of all 100 tasks |

### Phase 3: Validation & Pilot (Weeks 11–13)

| Week | Deliverable |
|---|---|
| 11 | Expert review of tasks (recruit 3–5 reviewers); iterate on feedback |
| 12 | Human baseline study (recruit 10 developers via Prolific/Upwork) |
| 13 | Pilot run with 2 models to debug evaluation pipeline; fix flaky validations |

### Phase 4: Full Experiment (Weeks 14–17)

| Week | Deliverable |
|---|---|
| 14 | Run full experiment: all models × all prompt strategies (automated) |
| 15 | Aggregate results; compute all metrics with confidence intervals |
| 16 | Ablation studies and failure mode analysis |
| 17 | Statistical analysis; generate all figures and tables |

### Phase 5: Writing & Release (Weeks 18–22)

| Week | Deliverable |
|---|---|
| 18–20 | Write paper (see §8 for outline) |
| 21 | Internal review + revision |
| 22 | Open-source benchmark release + paper submission |

---

## 7. Threat Mitigation

| Threat | Type | Mitigation |
|---|---|---|
| `act` does not perfectly emulate GitHub runners | Construct | Maintain compatibility matrix; dual-run critical tasks on real GitHub |
| Tasks are too synthetic / not representative | External | Validate against mined real-world workflows; expert review |
| Data contamination in LLM training data | Internal | Synthetic/unique repos; canary strings; private holdout set |
| Flaky runtime tests | Reliability | 10× oracle self-test; deterministic seeds; retry with logging |
| Cost of API calls | Practical | Budget estimation upfront (~$2K–5K for 20K generations); use open-weight models where possible |
| Task difficulty not well-calibrated | Construct | Empirical difficulty from pilot + human baselines |
| Evaluation favors one "style" of correct solution | Construct | Behavior-based validation, not diff-based; multiple valid solutions |
| Models improve rapidly, benchmark becomes stale | External | Modular design for easy task addition; versioned releases |

---

## 8. Paper Outline

```
1. Introduction
   - Motivation: CI/CD generation is understudied
   - Gap: No functional benchmark for GHA workflows
   - Contributions (4 points from §1.3)

2. Background & Related Work
   - Code generation benchmarks (HumanEval, MBPP, SWE-bench, DevBench, ...)
   - CI/CD and GitHub Actions
   - LLMs for DevOps/infrastructure-as-code

3. GHA-Bench: Benchmark Design
   - Feature taxonomy (§2.2)
   - Task specification format (§2.3)
   - Prompt design (§2.4)
   - Benchmark validation (§5)

4. Evaluation Framework
   - Multi-layer pipeline (§3.1)
   - Metrics (§3.2)
   - Runtime infrastructure (§3.3)

5. Experimental Setup
   - Models, prompts, configurations (§4.1–4.3)
   - Human baselines (§5.3)

6. Results
   - RQ1: Overall accuracy (table: model × tier)
   - RQ2: Per-feature difficulty analysis (heatmap)
   - RQ3: Prompting strategy comparison (bar charts with CI)
   - RQ4: Static vs. runtime correlation (scatter + Spearman)
   - RQ5: Model comparison (radar charts, statistical tests)

7. Failure Mode Analysis
   - Taxonomy of errors (qualitative coding of failures)
   - Common anti-patterns
   - Case studies

8. Discussion
   - Implications for LLM-assisted DevOps
   - Benchmark limitations
   - Recommendations for model developers

9. Threats to Validity
   - Internal, external, construct, conclusion

10. Conclusion & Future Work
    - Summary of findings
    - Future: extend to GitLab CI, Azure Pipelines, etc.
```

---

## 9. Venue Targeting

| Venue | Fit | Deadline (typical) |
|---|---|---|
| **ICSE** (International Conference on Software Engineering) | Primary target — SE + empirical | ~Sep for May conf |
| **FSE / ESEC-FSE** (Foundations of Software Engineering) | Strong fit — tools + empirical | ~Mar for Nov conf |
| **ASE** (Automated Software Engineering) | Good fit — automation focus | ~May for Sep conf |
| **MSR** (Mining Software Repositories) | Good if emphasizing the mining/taxonomy | ~Feb for May conf |
| **ISSTA** (Software Testing and Analysis) | If emphasizing the testing/validation framework | ~Feb for Sep conf |
| **NeurIPS / ICML (Datasets & Benchmarks track)** | If emphasizing benchmark methodology | ~May/Jan |

---

## 10. Resource Requirements

| Resource | Estimate |
|---|---|
| LLM API costs | $3,000–$7,000 (depending on model mix and retry budget) |
| GitHub Actions minutes (for real-runner tasks) | ~2,000 minutes ≈ included in free tier or ~$80 |
| Compute for `act` execution | 8-core machine, 32GB RAM, 500GB SSD (local or cloud VM ~$200/month × 2 months) |
| Human participants (baselines) | 10 developers × 5 hours × $30/hr = $1,500 |
| Expert reviewers | 5 × $200 honorarium = $1,000 |
| **Total estimated budget** | **$6,000–$10,000** |

---

## 11. Artifacts & Open Science

To maximize impact and satisfy open-science expectations:

- [ ] Public GitHub repository with all tasks, evaluation scripts, and results
- [ ] Docker image for deterministic evaluation (pinned dependencies)
- [ ] Leaderboard website (auto-updated via CI)
- [ ] Preregistration of experimental hypotheses (e.g., on OSF)
- [ ] Raw results and analysis notebooks in a Zenodo archive with DOI
- [ ] Clear licensing (tasks: CC-BY-4.0; code: Apache-2.0)
- [ ] Datasheet for the benchmark (following Gebru et al.'s Datasheets for Datasets)

---

This plan provides the scaffolding for a rigorous, publishable benchmark. The key differentiators for reviewers will be: **(1)** the multi-layer evaluation that goes beyond syntax to runtime behavior, **(2)** the systematic feature taxonomy grounded in real-world usage, **(3)** the thorough meta-evaluation of the benchmark itself, and **(4)** the open, reproducible infrastructure.
