import logging

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

import env
from tools import get_tools
from utils.app_types import Agent, AgentYAML, GraphState
from utils.logger import log_message, log_progress, log_state


def init_agent(model_yaml: AgentYAML, directory: str) -> Agent:
    model_name = model_yaml["model"] if "model" in model_yaml else "openai/gpt-oss-20b"
    model = ChatOpenAI(
        api_key=lambda: env.endpoints["openrouter"]["api_key"],  # type: ignore
        base_url=env.endpoints["openrouter"]["base_url"],  # type: ignore
        model=model_name,  # type: ignore
    )
    tools = []
    tools_by_name = get_tools(directory)
    for tool in model_yaml["tools"]:
        tools.append(tools_by_name[tool])
    # if len(tools) > 0:
    #     model = model.bind_tools(tools)
    agent = create_agent(
        model=model,
        system_prompt=model_yaml["system_prompt"],
        tools=tools,
    )
    return {
        "identifier": model_yaml["identifier"],
        "model": agent,
        "model_name": model_name,
        # "system_prompt": model_yaml["system_prompt"],
        "prompt_template": model_yaml["prompt_template"]
        if "prompt_template" in model_yaml
        else "{prompt}",
    }


def call_llm(model: Agent, state: GraphState):
    log_progress(f"Calling LLM {model['identifier']} ({model['model_name']})")

    prompt = model["prompt_template"].format(**state.__dict__)
    response = model["model"].invoke(
        {"messages": [{"role": "user", "content": prompt}]}  # type: ignore[invalid-argument-type]
    )
    state.llm_response = response["messages"][-1].content  # type: ignore[union-attr]

    log_message(
        {
            "prompt": prompt,
            "response": list(
                map(
                    lambda m: {"type": m.type, "content": m.content},
                    response["messages"],  # type: ignore[not-subscriptable]
                )
            ),
        }
    )
    log_state(model["identifier"], state, str(response["messages"][-1].content))  # type: ignore[union-attr]
    log_progress(f"Received response from LLM {model['identifier']}")
    log_progress(f"LLM {model['identifier']} output state: {state}", logging.DEBUG)
    return state


# def build_graph(
#     name: str, save_graph_image: bool = False
# ) -> CompiledStateGraph[GraphState, None, GraphState, GraphState]:
#     path = f"{env.graph_path}/{name}.yaml"
#     graph = StateGraph(GraphState)
#     graph_yaml = yaml.safe_load(open(path, "r"))
#     log_graph(graph_yaml)

#     for node in graph_yaml["agents"]:
#         model = init_agent(directory="")
#         graph.add_node(
#             model["identifier"],
#             lambda state, model=model: call_llm(model, state),  # pyright: ignore
#         )
#     for node in graph_yaml["functions"]:
#         graph.add_node(node["identifier"], functions[node["function_name"]])

#     for edge in graph_yaml["edges"]:
#         source = edge["source"] if edge["source"] != "START" else START
#         if "target" in edge:
#             target = edge["target"] if edge["target"] != "END" else END
#             graph.add_edge(source, target)
#         elif "router" in edge:
#             router = list(
#                 filter(
#                     lambda x: x["identifier"] == edge["router"], graph_yaml["routers"]
#                 )
#             )
#             graph.add_conditional_edges(
#                 source,
#                 routers[router[0]["function_name"]],
#                 {
#                     key: value if value != "END" else END
#                     for key, value in edge["targets"].items()
#                 },
#             )

#     graph = graph.compile()

#     if save_graph_image:
#         with open("graph.png", "wb") as f:
#             f.write(graph.get_graph(xray=True).draw_mermaid_png())

#     return graph


# def run_graph(
#     graph: CompiledStateGraph[GraphState, None, GraphState, GraphState],
#     prompt: str,
#     print_messages: bool = False,
# ) -> WorkflowYAML:
#     message = HumanMessage(content=prompt)

#     state = graph.invoke(
#         GraphState(
#             messages=[message],
#             workflow=None,
#             static_check=None,
#             vulnerabilities=None,
#             judgement=None,
#             judge_score=None,
#             prompt=prompt,
#             syntax_retries_left=5,
#             if_retries_left=5,
#             vuln_retries_left=5,
#         ),
#         {"recursion_limit": 100},
#     )

#     if print_messages:
#         for m in state["messages"]:
#             m.pretty_print()

#     return state["workflow"]


# if __name__ == "__main__":
#     prompt = "Generate a GitHub Workflow named `Build PicView Avalonia on macOS` for a GitHub repository whose primary programming language is C#. This workflow will be triggered by multiple events: 1) The workflow would run whenever there is a push event to: a branch named dev. 2) The workflow would run whenever there is a pull_request event targeting: a branch named dev. The workflow has one job. The job id of the 1st job is `build`."
#     graph = build_graph("main", True)
#     # workflow = run_graph(graph, prompt)
#     # print(workflow)
