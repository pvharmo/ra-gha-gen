import polars as pl

import env

paths = [
    # "base/Qwen2.5-Coder-7B-Instruct",
    "base/Qwen2.5-Coder-3B-Instruct",
    # "sft/Qwen2.5-Coder-7B-Instruct/50000/checkpoint-18750",
    "sft/Qwen2.5-Coder-3B-Instruct/50000/checkpoint-18750",
    "grpo_lint_meteor_4_False-50000_checkpoint-18750/Qwen2.5-Coder-3B-Instruct/0_4000/checkpoint-12000",
    # "sota",
    "codellama",
]

merged_data = pl.read_ndjson(f"{env.previous_results_path}/sota/scores-0.jsonl").select(
    pl.col(
        "id",
        "prompt",
        "answer",
        "llm_response",
        "repository_id",
        "name",
        "file_name",
        "level",
        "lint_valid",
        "lint_output",
        "meteor_score",
        "judge_score",
        "is_infinite_loop",
        "tokens_count",
        "stats",
    )
)

for path in paths:
    try:
        data = pl.read_ndjson(f"{env.previous_results_path}/{path}/scores-0.jsonl")
    except FileNotFoundError:
        data = pl.read_ndjson(f"{env.previous_results_path}/{path}/scores.jsonl")

    data = data.select(
        pl.col(
            "id",
            "prompt",
            "answer",
            "llm_response",
            "repository_id",
            "name",
            "file_name",
            "level",
            "lint_valid",
            "lint_output",
            "meteor_score",
            "judge_score",
            "is_infinite_loop",
            "tokens_count",
            "stats",
        )
    )

    if merged_data is None:
        merged_data = data
    else:
        merged_data = pl.concat([merged_data, data])

count = (
    merged_data.filter(~pl.col("is_infinite_loop") & ~pl.col("lint_valid"))
    .group_by(
        [
            "id",
            "level",
            "name",
            "file_name",
        ]
    )
    .len()
    .filter(pl.col("len") > 4)
    .join(
        merged_data,
        on=[
            "id",
            "level",
            "name",
            "file_name",
        ],
        how="inner",
    )
    .unique()
)

pl.Config.set_tbl_rows(1000)
print(
    count.sort(["name", "file_name", "level", "judge_score"]).select(
        ["name", "file_name", "level", "judge_score", "tokens_count"]
    )
)

count.write_ndjson("hard.jsonl")
