# Benchmark Improvements

This document describes the enhancements made to the GitHub Actions workflow generation benchmark to increase difficulty and provide more meaningful evaluation metrics.

## Overview

The original benchmark was too simple - agents could easily succeed because:
1. Prompts were overly prescriptive (explicitly listed all workflow components)
2. No functional validation (workflows were never executed)
3. BLEU/METEOR measured surface-level similarity, not correctness
4. LLM judges may be lenient toward other LLMs' outputs

## Implemented Improvements

### 1. Difficulty Tiers

Workflows are now classified into three difficulty tiers based on computed complexity metrics:

| Tier | Criteria | Example |
|------|----------|---------|
| **Easy** | Score ≤ 2 | Simple CI that runs tests on push |
| **Medium** | Score 3-5 | Multi-platform build matrix with caching |
| **Hard** | Score > 5 | Reusable workflows, complex triggers, deployments |

**Scoring formula:**
```python
score = (
    cyclomatic_complexity
    + nb_jobs
    + nb_reusable_workflows * 3  # reusable workflows add significant complexity
    + (1 if nb_triggers > 1 else 0)  # multiple triggers add complexity
    + len([a for a in actions if "docker" in a.lower()])  # docker actions
)
```

**Implementation:** `src/models/workflow.py` - `difficulty_tier` and `difficulty_score` properties

### 2. Functional Testing with `act`

Workflows are now functionally tested using [act](https://github.com/nektos/act), a tool that runs GitHub Actions workflows locally using Docker.

#### Test Phases

| Phase | Command | What it validates |
|-------|---------|-------------------|
| Syntax | `actionlint` | YAML validity, action syntax (already implemented) |
| Dry-run | `act --dryrun` | Workflow graph resolution, step ordering |
| Mock execution | `act --secret MOCK=xxx` | Actual job execution with mock inputs |

#### Handling Reusable Workflows

Since `act` cannot resolve `.github/workflows/xxx.yml` references outside the test environment, jobs that use reusable workflows are:
1. Automatically detected and filtered out
2. Logged as `skipped_jobs` in the test results
3. The remaining jobs are still tested

#### Mock Environment

The functional test runner provides:
- Mock GitHub context (event payloads, repository info)
- Default mock secrets (GITHUB_TOKEN, NPM_TOKEN, etc.)
- Minimal repository structure for testing

**Implementation:** `src/utils/functional_test.py`

## New Score Fields

The `Score` model now includes:

```python
@dataclass
class Score:
    # ... existing fields ...
    
    # Functional test results
    functional_test_success: bool
    functional_test_dryrun_success: bool
    functional_test_execution_success: bool
    functional_test_output: str
    functional_test_errors: str
    functional_test_skipped_jobs: list[str]
    functional_test_jobs_executed: list[str]
    functional_test_jobs_failed: list[str]
    
    # Difficulty classification
    difficulty_tier: str  # "easy", "medium", "hard"
    difficulty_score: int
```

## Updated Benchmark Output

Results are now reported by tier:

```
============================================================
OVERALL RESULTS
============================================================
Average METEOR score: 0.4521
Average Judge score: 3.75
Lint success rate: 0.85 (85/100)
Functional test success rate: 0.62

============================================================
EASY TIER (25 workflows)
============================================================
...

============================================================
MEDIUM TIER (45 workflows)
============================================================
...

============================================================
HARD TIER (27 workflows)
============================================================
...
```

## Prerequisites

### Install `act`

```bash
curl -s https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash
```

### Docker

Docker must be installed and running for `act` to execute workflows.

## Files Modified/Created

| File | Changes |
|------|---------|
| `src/models/workflow.py` | Added `difficulty_tier` and `difficulty_score` properties |
| `src/models/score.py` | Added functional test fields, difficulty tier fields, updated `new()` |
| `src/utils/functional_test.py` | **NEW** - Mock execution with `act` |
| `src/utils/scores.py` | Added `suffix` param, functional test success rate reporting |
| `src/benchmarks/mp_benchmark.py` | Added functional tests, tier-based result grouping |
| `src/benchmarks/sm_benchmark.py` | Added functional tests, difficulty tier display |

## Future Improvements

Potential enhancements not yet implemented:

1. **Less prescriptive prompts** - Require agents to discover requirements from repository context rather than explicit instructions
2. **Deterministic validation** - Replace LLM-judge with structured checks for specific workflow properties
3. **Adversarial test cases** - Include vulnerability-prone patterns that agents must avoid
4. **Cross-validation** - Compare generated workflows against multiple reference implementations
