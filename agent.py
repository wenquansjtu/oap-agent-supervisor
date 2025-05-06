from langgraph.pregel.remote import RemoteGraph
from langgraph_supervisor.handoff import create_forward_message_tool
from langchain_openai import ChatOpenAI
from langgraph_supervisor import create_supervisor
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List, Optional

load_dotenv()


class AgentsConfig(BaseModel):
    deployment_url: str
    """The URL of the LangGraph deployment"""
    agent_id: str
    """The ID of the agent to use"""


class GraphConfigPydantic(BaseModel):
    agents: List[AgentsConfig] = Field(
        default=[],
        metadata={
            "x_lg_ui_config": {
                "type": "agents",
            }
        },
    )
    system_prompt: Optional[str] = Field(
        default=None,
        metadata={
            "x_lg_ui_config": {
                "type": "textarea",
                "placeholder": "Enter a system prompt...",
                "description": "The system prompt to use in all generations",
            }
        },
    )


def make_child_graphs(cfg: GraphConfigPydantic):
    return [
        RemoteGraph(deployment_url=agent.deployment_url, agent_id=agent.agent_id)
        for agent in cfg.agents
    ]


def make_prompt(cfg: GraphConfigPydantic):
    return cfg.system_prompt or (
        "You are a supervisor agent overseeing a team of specialist agents. "
        "For each user message, determine if it should be handled by one of your agents—"
        "if so, call the tool `delegate_to_<agent_id>()` with the user’s original question. "
        "If not, answer directly."
    )


supervisor_workflow = create_supervisor(
    agents=make_child_graphs,
    model=ChatOpenAI(model="gpt-4o"),
    prompt=make_prompt,
    config_schema=GraphConfigPydantic,
    handoff_tool_prefix="delegate_to_",
)

graph = supervisor_workflow.compile()
