from textwrap import dedent

from functions import (
    extract_judge_score_function,
    extract_workflow_function,
    static_checker_function,
    vulnerability_scanner_function,
)
from graph import call_llm, init_agent
from utils.app_types import GraphState

# default_model = "qwen/qwen3-coder-next:exacto"
default_model = "z-ai/glm-4.7-flash"
# default_model = "openai/gpt-oss-120b:exacto"
default_retries = 5


class AgentsWorkflow:
    def __init__(self, directory: str):
        self.init_agents(directory)

    def init_agents(self, directory: str):
        self.generator_agent = init_agent(
            {
                "identifier": "generator_agent",
                "model": default_model,
                "system_prompt": dedent("""
                    You are an expert devops engineer. Please generate a YAML file based on the user's input below. No additional explanation is needed. The output format should be ```yaml <Workflow>```.
                    Use the following tools to gather information about the repository and its structure, as well as to find relevant code snippets that can help you generate the workflow:
                    - read_readme: Use this tool to read the content of the README.md file in the repository. It may contain important information about the project, its structure, and any specific instructions or requirements related to GitHub Actions workflows.
                    - read_contributing: Use this tool to read the content of the CONTRIBUTING.md file in the repository. This file may provide guidelines for contributing to the project, which can include information about the development process, coding standards, and any specific requirements for GitHub Actions workflows.
                    - list_directory: Use this tool to list the files and directories in the repository. This can help you understand the structure of the project and identify where relevant files are located.
                    - read_file: Use this tool to read the content of specific files in the repository. This can be useful for examining existing GitHub Actions workflows, configuration files, or any other relevant code that can inform the generation of the new workflow.
                    - file_search: Use this tool to search for specific keywords or patterns in the files in the repository. This can help you quickly find relevant code snippets, existing workflows, or any other information that can assist you in generating a workflow that meets the requirements described in the user's input.
                    """),
                "prompt_template": "{prompt}",
                "tools": [
                    "read_readme",
                    "read_contributing",
                    "list_directory",
                    "read_file",
                    "file_search",
                ],
            },
            directory,
        )
        self.generator_agent["model"].get_graph().draw_mermaid_png(
            output_file_path="generator_agent_graph.png"
        )

        self.judge_agent = init_agent(
            {
                "identifier": "judge_agent",
                "model": "openai/gpt-oss-120b",
                # "model": default_model,
                "system_prompt": "You are an expert DevOps engineer. Carefully evaluate whether the provided GitHub Actions workflow accurately and completely implements the requirements described in the accompanying prompt.",
                "prompt_template": dedent("""Please use the following Likert scale to rate how well the workflow fulfills the instructions (with 1 being the lowest and 5 being the highest):

                1. Strongly Disagree – The workflow does not follow the instructions at all.
                2. Disagree – The workflow follows the instructions in only a few aspects, with major omissions or errors.
                3. Neutral – The workflow partially follows the instructions, but there are significant places where it falls short or deviates.
                4. Agree – The workflow generally follows the instructions, with only minor issues or omissions.
                5. Strongly Agree – The workflow fully and accurately implements all requirements described in the prompt.

                **Instructions:**
                - Do **not** allow the length, formatting, or verbosity of the response to affect your judgment.
                - Assess only the accuracy and completeness of implementation relative to the prompt's requirements.
                - First, clearly explain your reasoning, referencing specific aspects of the workflow and prompt as needed.

                Then, conclude with your rating in the following format: Therefore, I would rate the workflow with a score of **X out of 5**.

                Here's the description of the workflow:
                {prompt}

                Here's the workflow:
                {workflow}"""),
                "tools": [
                    "read_readme",
                    "read_contributing",
                    "list_directory",
                    "read_file",
                    "file_search",
                ],
            },
            directory,
        )

        self.syntax_corrector_agent = init_agent(
            {
                "identifier": "syntax_corrector_agent",
                "model": default_model,
                "system_prompt": "You are an expert devops engineer. Please correct the YAML file generated by the generator tool. No additional explanation is needed. The output format should be ```yaml <Workflow>```.",
                "prompt_template": dedent("""Description:
                {prompt}
                Workflow:
                {workflow}
                Static analysis results:
                {static_check}"""),
                "tools": [],
            },
            directory,
        )

        self.judge_corrector_agent = init_agent(
            {
                "identifier": "judge_corrector_agent",
                "model": default_model,
                "system_prompt": "You are an expert devops engineer. Please correct the YAML file generated by the generator tool. No additional explanation is needed. The output format should be ```yaml <Workflow>```.",
                "prompt_template": dedent("""Description:
                {prompt}
                Workflow:
                {workflow}
                Judgement:
                {judgement}"""),
                "tools": [],
            },
            directory,
        )

        self.vulnerability_corrector_agent = init_agent(
            {
                "identifier": "vulnerability_corrector_agent",
                "model": default_model,
                "system_prompt": "You are an expert devops engineer. Please correct the YAML file generated by the generator tool. No additional explanation is needed. The output format should be ```yaml <Workflow>```.",
                "prompt_template": dedent("""Description:
                {prompt}
                Workflow:
                {workflow}
                Vulnerability analysis results:
                {vulnerabilities}"""),
                "tools": [],
            },
            directory,
        )

    def fix_syntax(self, state: GraphState):
        static_checker_function(state)

        while (
            state.static_check
            and not state.static_check["valid"]
            and state.syntax_retries_left > 0
        ):
            call_llm(self.syntax_corrector_agent, state)
            extract_workflow_function(state)
            static_checker_function(state)
            state.syntax_retries_left -= 1

    def fix_instruction_following(self, state: GraphState):
        call_llm(self.judge_agent, state)
        extract_judge_score_function(state)

        while state.judge_score and state.judge_score < 5 and state.if_retries_left > 0:
            call_llm(self.judge_corrector_agent, state)
            extract_workflow_function(state)
            call_llm(self.judge_agent, state)
            extract_judge_score_function(state)
            state.if_retries_left -= 1

    def fix_vulnerabilities(self, state: GraphState):
        vulnerability_scanner_function(state)

        while (
            state.vulnerabilities
            and len(state.vulnerabilities) > 0
            and state.vuln_retries_left > 0
        ):
            call_llm(self.vulnerability_corrector_agent, state)
            extract_workflow_function(state)
            vulnerability_scanner_function(state)
            state.vuln_retries_left -= 1

    def run(self, prompt):
        state = GraphState(
            workflow=None,
            llm_response=None,
            static_check=None,
            vulnerabilities=None,
            judgement=None,
            judge_score=None,
            prompt=prompt,
            syntax_retries_left=default_retries,
            if_retries_left=default_retries,
            vuln_retries_left=default_retries,
        )

        call_llm(self.generator_agent, state)
        extract_workflow_function(state)
        self.fix_syntax(state)
        self.fix_instruction_following(state)
        self.fix_vulnerabilities(state)

        return state.workflow
