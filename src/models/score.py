from dataclasses import dataclass, field
from typing import Any, cast

import env
from models.workflow import Workflow
from utils.app_types import SyntaxValidationOutput, Vulnerability, WorkflowYAML
from utils.client import Client
from utils.functional_test import FunctionalTestResult
from utils.lint import check_vulnerabilities, validate_workflow
from utils.scores import (
    calculate_bleu_score,
    calculate_meteor_score,
    extract_judge_score,
    make_judge_prompt,
)

client = Client(
    env.endpoints["openrouter"]["api_key"], env.endpoints["openrouter"]["base_url"]
)
model = "openai/gpt-oss-20b"


default_prompt_template = """
You are an expert DevOps engineer. Carefully evaluate whether the provided GitHub Actions workflow accurately and completely implements the requirements described in the accompanying prompt.

Please use the following Likert scale to rate how well the workflow fulfills the instructions (with 1 being the lowest and 5 being the highest):

1. Strongly Disagree – The workflow does not follow the instructions at all.
2. Disagree – The workflow follows the instructions in only a few aspects, with major omissions or errors.
3. Neutral – The workflow partially follows the instructions, but there are significant places where it falls short or deviates.
4. Agree – The workflow generally follows the instructions, with only minor issues or omissions.
5. Strongly Agree – The workflow fully and accurately implements all requirements described in the prompt.

**Instructions:**
- Do **not** allow the length, formatting, or verbosity of the response to affect your judgment.
- Assess only the accuracy and completeness of implementation relative to the prompt's requirements.
- First, clearly explain your reasoning, referencing specific aspects of the workflow and prompt as needed.
- Then, conclude with your rating in the following format:
    Therefore, I would rate the workflow with a score of **X out of 5**.

---

Here is the workflow:

{workflow_yaml}

Here is the prompt:

{description}
"""


async def run_judgement(
    judgement_prompt_template: str,
    workflow_prompt: str,
    generated_workflow: WorkflowYAML,
):
    judge_prompt = make_judge_prompt(
        judgement_prompt_template,
        description=workflow_prompt,
        workflow_yaml=generated_workflow,
    )

    judgement_text = await client.chat(
        model=model,
        messages=[
            {"role": "user", "content": judge_prompt},
        ],
    )

    score = extract_judge_score(judgement_text)

    if not score:
        judgement_text = await client.chat(
            model=model,
            messages=[
                {"role": "user", "content": judge_prompt},
            ],
        )
        score = extract_judge_score(judgement_text)
        if not score:
            raise ValueError("Failed to extract score from judgement")

    if not judgement_text:
        raise ValueError("Failed to generate judgement")

    return judgement_text, score


@dataclass
class Score:
    original_workflow: WorkflowYAML
    generated_workflow: WorkflowYAML

    judgement: str
    judge_score: float
    bleu_score: float
    meteor_score: float

    lint_valid: bool
    lint_output: list[SyntaxValidationOutput]
    vulnerabilities: list[Vulnerability]

    functional_test_success: bool
    functional_test_dryrun_success: bool
    functional_test_execution_success: bool
    functional_test_output: str
    functional_test_errors: str

    difficulty_tier: str
    difficulty_score: int

    graph_name: str
    workflow_id: int
    prompt_level: int
    prompt: str

    functional_test_skipped_jobs: list[str] = field(default_factory=list)
    functional_test_jobs_executed: list[str] = field(default_factory=list)
    functional_test_jobs_failed: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "original_workflow": self.original_workflow,
            "generated_workflow": self.generated_workflow,
            "judgement": self.judgement,
            "judge_score": self.judge_score,
            "bleu_score": self.bleu_score,
            "meteor_score": self.meteor_score,
            "lint_valid": self.lint_valid,
            "lint_output": self.lint_output,
            "vulnerabilities": self.vulnerabilities,
            "functional_test_success": self.functional_test_success,
            "functional_test_dryrun_success": self.functional_test_dryrun_success,
            "functional_test_execution_success": self.functional_test_execution_success,
            "functional_test_output": self.functional_test_output,
            "functional_test_errors": self.functional_test_errors,
            "functional_test_skipped_jobs": self.functional_test_skipped_jobs,
            "functional_test_jobs_executed": self.functional_test_jobs_executed,
            "functional_test_jobs_failed": self.functional_test_jobs_failed,
            "difficulty_tier": self.difficulty_tier,
            "difficulty_score": self.difficulty_score,
            "graph_name": self.graph_name,
            "workflow_id": self.workflow_id,
            "prompt_level": self.prompt_level,
            "prompt": self.prompt,
        }

    @classmethod
    async def new(
        cls,
        workflow: Workflow,
        generated_workflow: WorkflowYAML | None,
        prompt_level: int,
        graph_name: str,
        functional_result: FunctionalTestResult | None = None,
    ):
        workflow_yaml = generated_workflow or cast(WorkflowYAML, "")

        lint_results = validate_workflow(workflow_yaml)
        vulnerabilities = check_vulnerabilities(workflow_yaml)
        bleu_score = calculate_bleu_score(workflow_yaml, workflow.workflow)
        meteor_score = calculate_meteor_score(workflow_yaml, workflow.workflow)
        judgement, judge_score = await run_judgement(
            default_prompt_template,
            workflow.get_prompt(prompt_level),
            workflow_yaml,
        )

        if functional_result is None:
            functional_result = FunctionalTestResult(
                success=False,
                dryrun_success=False,
                execution_success=False,
                output="",
                errors="Functional test not run",
            )

        return cls(
            original_workflow=workflow.workflow,
            generated_workflow=workflow_yaml,
            judgement=judgement,
            judge_score=judge_score,
            bleu_score=bleu_score,
            meteor_score=meteor_score,
            lint_valid=lint_results["valid"],
            lint_output=lint_results["output"],
            vulnerabilities=vulnerabilities,
            functional_test_success=functional_result.success,
            functional_test_dryrun_success=functional_result.dryrun_success,
            functional_test_execution_success=functional_result.execution_success,
            functional_test_output=functional_result.output,
            functional_test_errors=functional_result.errors,
            functional_test_skipped_jobs=functional_result.skipped_jobs,
            functional_test_jobs_executed=functional_result.jobs_executed,
            functional_test_jobs_failed=functional_result.jobs_failed,
            difficulty_tier=workflow.difficulty_tier,
            difficulty_score=workflow.difficulty_score,
            graph_name=graph_name,
            workflow_id=workflow.id,
            prompt_level=prompt_level,
            prompt=workflow.get_prompt(prompt_level),
        )
