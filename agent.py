from langgraph.pregel.remote import RemoteGraph
from langchain_openai import ChatOpenAI
from langgraph_supervisor import create_supervisor
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List, Optional
from langchain_core.runnables import RunnableConfig

load_dotenv()


class AgentsConfig(BaseModel):
    deployment_url: str
    """The URL of the LangGraph deployment"""
    agent_id: str
    """The ID of the agent to use"""


class GraphConfigPydantic(BaseModel):
    agents: List[AgentsConfig] = Field(
        default=[],
        metadata={"x_lg_ui_config": {"type": "agents"}},
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
    """
    Instantiate a list of RemoteGraph nodes based on the configuration.
    """
    return [RemoteGraph(a.agent_id, url=a.deployment_url) for a in cfg.agents]


def make_model(cfg: GraphConfigPydantic):
    """Instantiate the LLM for the supervisor based on the config."""
    return ChatOpenAI(model="gpt-4o")


def make_prompt(cfg: GraphConfigPydantic):
    """Build the system prompt, falling back to a sensible default."""
    return cfg.system_prompt or (
        "You are a supervisor AI overseeing a team of specialist agents. "
        "For each incoming user message, decide if it should be handled by one of your agents. "
        "If so, invoke the tool `delegate_to_<agent_id>(user_query)`—replacing `<agent_id>` with the agent’s name—"
        "to hand off control. Otherwise, answer the user yourself."
    )


def graph(config: RunnableConfig):

    cfg = GraphConfigPydantic(**config.get("configurable", {}))
    child_graphs = make_child_graphs(cfg)

    return create_supervisor(
        child_graphs,
        model=make_model(cfg),
        prompt=make_prompt(cfg),
        config_schema=GraphConfigPydantic,
        handoff_tool_prefix="delegate_to_",
    )
