import polars as pl

import env
from models.workflow import Workflow

data = pl.read_ndjson(
    "/var/home/jonathan/Documents/ulaval/maitrise/fse/results/sota/scores-0.jsonl"
)

invalids = (
    data.filter(~pl.col("lint_valid"))
    .filter(pl.col("judge_score") > 0)
    .filter(pl.col("augment_meteor_score") == 1)
).sample(fraction=1, seed=37, shuffle=True)


invalids = (
    invalids.group_by(pl.col("judge_score"))
    .head(20)
    .rename({"stats": "stats_temp"})
    .unnest("info")
    .drop("stats")
    .unnest("stats_temp")
    .drop(
        [
            "content_right",
            "user_right",
            "repository_name_right",
            "tokens_count_right",
            "text",
            "llm_response",
            "bleu_score",
            "meteor_score",
            "lint_valid",
            "lint_output",
            "is_infinite_loop",
            "judgement",
            "level",
            "prompt",
            "answer",
            "judge_score",
            "name",
            "augment_meteor_score",
            "content_at_model_training",
        ]
    )
    .rename(
        {
            "level5": "prompt_level3",
            "user": "repository_owner",
            "level1": "prompt_level1",
            "level2": "prompt_level2",
            "NumofTriggers": "nb_triggers",
            "Triggers": "triggers",
            "NumofJobs": "nb_jobs",
            "NumofActions": "nb_actions",
            "Actions": "actions",
            "Actions_details": "actions_details",
            "NumofReusableWfs": "nb_reusable_workflows",
            "ReusableWfs": "reusable_workflows",
            "NumofSteps": "nb_steps",
            "CyclomaticComplexity": "cyclomatic_complexity",
            "content": "file_content",
        }
    )
)

# print(
#     invalids.group_by("judge_score")
#     .mean()
#     .sort("judge_score")
#     .select(["judge_score", "tokens_count"])
# )

invalids.write_ndjson(env.dataset_path + "/invalids.jsonl")

Workflow.load("invalids")
