import asyncio
import multiprocessing
import os
import shutil

import polars as pl

import env
from main import AgentsWorkflow
from models.score import Score
from models.workflow import Workflow
from tools import set_base_path
from utils.app_types import WorkflowYAML
from utils.functional_test import run_functional_test
from utils.logger import init_state_logger, log_progress, log_score
from utils.scores import print_scores

mocked_wf = WorkflowYAML("""name: MySQL Schema Dump (Laravel)
on: [ push, pull_request ]
jobs:
    schema-dump:
        strategy:
            matrix:
                operating-system:
                    - ubuntu-22.04
                php-version:
                    - '8.5'
        name: php ${{ matrix.php-version }} on ${{ matrix.operating-system }}
        runs-on: ${{ matrix.operating-system }}
        services:
            mysql:
                image: mysql:8.0
                env:
                    MYSQL_ALLOW_EMPTY_PASSWORD: yes
                    MYSQL_DATABASE: unit3d
                ports:
                    - 3306:3306
                options: --health-cmd="mysqladmin ping" --health-interval=10s --health-timeout=5s --health-retries=3
            redis:
                image: redis:7.2.1
                ports:
                    - 6379:6379
                options: >-
                    --health-cmd "redis-cli ping"
                    --health-interval 10s
                    --health-timeout 5s
                    --health-retries 5
        steps:
            -   name: Checkout
                uses: actions/checkout@v6
                with:
                    fetch-depth: 0
            -   name: Setup PHP ${{ matrix.php-version }}
                uses: shivammathur/setup-php@v2
                with:
                    php-version: ${{ matrix.php-version }}
                    extensions: curl, dom, gd, libxml, mbstring, zip, mysql, xml, intl, bcmath, redis-phpredis/phpredis@6.0.1
                    ini-values: error_reporting=E_ALL
                    coverage: none
                    tools: composer:v2
                env:
                    REDIS_CONFIGURE_OPTS: --enable-redis
            -   name: Install Composer Dependencies
                env:
                    COMPOSER_AUTH: ${{ secrets.COMPOSER_AUTH }}
                run: composer install --no-ansi --no-interaction --no-scripts --no-progress --prefer-dist
            -   name: Prepare The Laravel Environment
                run: cp .env.example .env
            -   name: Generate Application Key
                run: php artisan key:generate
            -   name: Clear Application Cache
                run: php artisan optimize:clear
            -   name: Run Migrations
                run: php artisan migrate --force --schema-path=database/schema/mysql-schema-new.sql
                env:
                    DB_CONNECTION: mysql
                    DB_HOST: 127.0.0.1
                    DB_PORT: ${{ job.services.mysql.ports['3306'] }}
                    DB_DATABASE: unit3d
                    DB_USERNAME: root
                    DB_PASSWORD: null
            -   name: Run Schema Dump
                run: php artisan schema:dump --path=database/schema/mysql-schema-new.sql
                env:
                    DB_CONNECTION: mysql
                    DB_HOST: 127.0.0.1
                    DB_PORT: ${{ job.services.mysql.ports['3306'] }}
                    DB_DATABASE: unit3d
                    DB_USERNAME: root
                    DB_PASSWORD: null
            -   name: Check if schema has changed
                id: diff
                run: |
                    if [ -f database/schema/mysql-schema.sql ] && diff -q database/schema/mysql-schema.sql database/schema/mysql-schema-new.sql > /dev/null; then
                      echo "No changes detected in schema"
                      echo "has_changes=false" >> $GITHUB_OUTPUT
                    else
                      echo "Changes detected in schema"
                      echo "has_changes=true" >> $GITHUB_OUTPUT
                    fi
            -   name: Update Schema
                if: steps.diff.outputs.has_changes == 'true'
                run: |
                  cp database/schema/mysql-schema-new.sql database/schema/mysql-schema.sql
                  rm database/schema/mysql-schema-new.sql
            -   name: Commit Schema Changes
                if: steps.diff.outputs.has_changes == 'true'
                uses: stefanzweifel/git-auto-commit-action@v7
                with:
                    commit_message: "automation: update schema dump"
                    commit_user_name: unit3d-bot
                    commit_user_email: unit3d_gh_bot@protonmail.com
                    commit_author: unit3d-bot <unit3d_gh_bot@protonmail.com>

""")


def pool_task(workflow: Workflow):
    shutil.move(
        f"{env.repositories_path}/{workflow.repository_name}/.github/workflows/{workflow.file_name}",
        f"{env.repositories_path}/workflows/{workflow.repository_name}/{workflow.file_name}",
    )
    set_base_path(f"{env.repositories_path}/{workflow.repository_name}")
    init_state_logger(workflow.id, log_to_term=True)
    agents_workflow = AgentsWorkflow(
        f"{env.repositories_path}/{workflow.repository_name}"
    )
    prompt_level = 1
    prompt = workflow.get_prompt(1)
    generated_workflow = mocked_wf
    # generated_workflow = agents_workflow.run(prompt)

    log_progress("Running functional test...")
    functional_result = asyncio.run(
        run_functional_test(
            generated_workflow or "",
            event_type=workflow.triggers[0] if workflow.triggers else "push",
            repository_path=f"{env.repositories_path}/{workflow.repository_name}",
        )
    )
    log_progress("Functional tests completed")

    score: Score = asyncio.run(
        Score.new(workflow, generated_workflow, prompt_level, "main", functional_result)
    )
    log_score(score)
    shutil.move(
        f"{env.repositories_path}/workflows/{workflow.repository_name}/{workflow.file_name}",
        f"{env.repositories_path}/{workflow.repository_name}/.github/workflows/{workflow.file_name}",
    )
    return score


def print_scores_by_tier(scores: list[Score], save_dir: str):
    data = pl.DataFrame(
        [s.to_dict() for s in scores], infer_schema_length=len(scores), strict=False
    )

    print("\n" + "=" * 60)
    print("OVERALL RESULTS")
    print("=" * 60)
    print_scores(data, save_dir, suffix="_overall")

    for tier in ["easy", "medium", "hard"]:
        tier_scores = [s for s in scores if s.difficulty_tier == tier]
        if tier_scores:
            tier_data = pl.DataFrame(
                [s.to_dict() for s in tier_scores],
                infer_schema_length=len(tier_scores),
                strict=False,
            )
            print("\n" + "=" * 60)
            print(f"{tier.upper()} TIER ({len(tier_scores)} workflows)")
            print("=" * 60)
            print_scores(tier_data, save_dir, suffix=f"_{tier}")


if __name__ == "__main__":
    workflows = Workflow.load("invalids")
    workflows = workflows[:1]
    scores = []
    # for workflow in workflows:
    #     results = pool_task(workflow)
    #     scores.append(results)
    with multiprocessing.Pool(processes=100) as pool:
        results = pool.map(pool_task, workflows)
        scores = list(results)

    print_scores_by_tier(scores, env.results_path)

    for filename in os.listdir(env.tmp_path):
        os.remove(os.path.join(env.tmp_path, filename))
