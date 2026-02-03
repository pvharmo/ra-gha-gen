import json
import re
from warnings import catch_warnings, simplefilter

import nltk
import polars as pl
import yaml
from nltk.translate.bleu_score import sentence_bleu
from nltk.translate.meteor_score import meteor_score

from utils.app_types import WorkflowYAML
from utils.formatting import extract_yaml
from utils.lint import detect_invalid_format, validate_workflow

nltk.download("punkt", quiet=True)
nltk.download("wordnet", quiet=True)


def make_judge_prompt(
    prompt_template: str, description: str, workflow_yaml: WorkflowYAML
) -> str:
    return prompt_template.format(description=description, workflow_yaml=workflow_yaml)


def calculate_bleu_score(reference: str | None, candidate: str | None) -> float:
    if candidate is None or reference is None or candidate == "" or reference == "":
        return 0.0

    try:
        i_reference = yaml.dump(yaml.safe_load(reference))
        i_candidate = yaml.dump(yaml.safe_load(candidate))

        i_reference = i_reference.strip().lower().split()
        i_candidate = i_candidate.strip().lower().split()

        with catch_warnings():
            simplefilter("ignore")
            score: float = sentence_bleu(  # pyright: ignore[reportAssignmentType]
                [i_reference], i_candidate, weights=(0.25, 0.25, 0.25, 0.25)
            )

        return score
    except Exception:
        return 0.0


def calculate_meteor_score(reference: str | None, candidate: str | None) -> float:
    if candidate is None or reference is None or candidate == "" or reference == "":
        return 0.0

    try:
        i_reference = yaml.dump(yaml.safe_load(reference))
        i_candidate = yaml.dump(yaml.safe_load(candidate))

        i_reference = i_reference.strip().lower().split()
        i_candidate = i_candidate.strip().lower().split()

        # Calculate METEOR score
        score = meteor_score([i_reference], i_candidate)

        return score
    except Exception:
        return 0.0


def extract_judge_score(text: str | None):
    if text is None:
        return None

    patterns = [
        r"\*{0,2}Overall Assessment\*{0,2}:\s*\*{0,2}(\d+(?:\.\d+)?)\s*out of\s*5\*{0,2}",  # "**Final score**: X out of 5"
        r"\*{0,2}Final Score\*{0,2}:\s*\*{0,2}(\d+(?:\.\d+)?)\s*out of\s*5\*{0,2}",  # "**Final score**: X out of 5"
        r"\*{0,2}Rating\*{0,2}:\s*\*{0,2}(\d+(?:\.\d+)?)\s*out of\s*5\*{0,2}",  # "Rating: X out of 5"
        r"\*{0,2}Score\*{0,2}:\s*\*{0,2}\s*(\d+(?:\.\d+)?)\s*out of\s*5\*{0,2}",  # "Score: X out of 5"
        r"score of\s*\*{0,2}(\d+(?:\.\d+)?)\*{0,2}\s*out of\s*5",  # "score of X out of 5"
        r"\*{0,2}(\d+(?:\.\d+)?)\s*out of\s*5\*{0,2}",  # "**X out of 5**"
        r"\*{0,2}Score\*{0,2}:\s*\*{0,2}(\d+(?:\.\d+)?)\s*\*{0,2}/\s*\*{0,2}5\*{0,2}",  # "Score: 3/5"
        r"\*{0,2}(\d+(?:\.\d+)?)\s*\*{0,2}/\s*\*{0,2}5\*{0,2}",  # "**x/5**"
        r"\*{0,2}Score\*{0,2}\n*\*{0,2}(\d+(?:\.\d+)?)\s*\*{0,2}",  # "### Score\nX"
        r"\*{0,2}Final score\*{0,2}:\s*\*{0,2}(\d+(?:\.\d+)?)\s*\*{0,2}\*{0,2}",  # "**Final score: X**",
    ]

    # Try each pattern
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return float(match.group(1))

    return None


def calculate_scores(reference: WorkflowYAML, llm_response: WorkflowYAML):
    # Extract YAML from responses
    candidate_yaml = extract_yaml(llm_response)

    # Calculate BLEU score
    bleu = calculate_bleu_score(reference, candidate_yaml)

    # Calculate METEOR score
    meteor = calculate_meteor_score(reference, candidate_yaml)

    # Validate action (lint check)
    lint_result = validate_workflow(candidate_yaml)
    lint_valid = lint_result.get("valid", False) if lint_result else False
    lint_output = json.dumps(lint_result.get("output", {})) if lint_result else "{}"

    invalid_format = detect_invalid_format(llm_response)

    return {
        "bleu": bleu,
        "meteor": meteor,
        "lint_valid": lint_valid,
        "lint_output": lint_output,
        "invalid_format": invalid_format,
    }


def print_scores(
    results_df: pl.DataFrame, save_dir: str | None = None, i: str | None = None
):
    avg_bleu = results_df["bleu_score"].mean()
    avg_meteor = results_df["meteor_score"].mean()
    lint_success_rate = results_df["lint_valid"].sum() / len(results_df)
    avg_judge_score = results_df["judge_score"].mean()

    print(f"Average BLEU score: {avg_bleu:.4f}")
    print(f"Average METEOR score: {avg_meteor:.4f}")
    print(f"Average Judge score: {avg_judge_score:.4f}")
    print(
        f"Lint success rate: {lint_success_rate:.4f} ({results_df['lint_valid'].sum()}/{len(results_df)})"
    )

    if save_dir:
        # Save results
        output_path = f"{save_dir}/scores{('-' + i) if i is not None else ''}.jsonl"
        results_df.write_ndjson(output_path)
        with open(
            f"{save_dir}/overview{('-' + i) if i is not None else ''}.json", "w+"
        ) as f:
            json.dump(
                {
                    "avg_bleu": f"{avg_bleu:.4f}",
                    "avg_meteor": f"{avg_meteor:.4f}",
                    "lint_success_rate": f"{lint_success_rate:.4f}",
                    "count": len(results_df),
                },
                f,
            )

        print(f"Scores saved to: {output_path}")
