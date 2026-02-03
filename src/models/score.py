from dataclasses import dataclass

import env
from models.workflow import Workflow
from utils.app_types import SyntaxValidationOutput, Vulnerability, WorkflowYAML
from utils.client import Client
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

    graph_name: str
    workflow_id: int
    prompt_level: int
    prompt: str

    @classmethod
    async def new(
        cls,
        workflow: Workflow,
        generated_workflow: WorkflowYAML,
        prompt_level: int,
        graph_name: str,
    ):
        lint_results = validate_workflow(generated_workflow)
        vulnerabilities = check_vulnerabilities(generated_workflow)
        bleu_score = calculate_bleu_score(generated_workflow, workflow.workflow)
        meteor_score = calculate_meteor_score(generated_workflow, workflow.workflow)
        judgement, judge_score = await run_judgement(
            default_prompt_template,
            workflow.get_prompt(prompt_level),
            generated_workflow,
        )
        return cls(
            original_workflow=workflow.workflow,
            generated_workflow=generated_workflow,
            judgement=judgement,
            judge_score=judge_score,
            bleu_score=bleu_score,
            meteor_score=meteor_score,
            lint_valid=lint_results["valid"],
            lint_output=lint_results["output"],
            vulnerabilities=vulnerabilities,
            graph_name=graph_name,
            workflow_id=workflow.id,
            prompt_level=prompt_level,
            prompt=workflow.get_prompt(prompt_level),
        )
