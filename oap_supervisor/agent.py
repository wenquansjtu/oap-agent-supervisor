from langgraph.graph import StateGraph
from langgraph.pregel.remote import RemoteGraph
from langchain_openai import ChatOpenAI
from langgraph_supervisor import create_supervisor
from pydantic import BaseModel, Field
import uuid
from typing import List, Optional
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt.chat_agent_executor import AgentState

# This system prompt is ALWAYS included at the bottom of the message.
UNEDITABLE_SYSTEM_PROMPT = """\nYou can invoke sub-agents by calling tools in this format:
`delegate_to_<name>(user_query)`--replacing <name> with the agent's name--
to hand off control. Otherwise, answer the user yourself.

The user will see all messages and tool calls produced in the conversation, 
along with all returned from the sub-agents. With this in mind, ensure you 
never repeat any information already presented to the user.
"""

DEFAULT_SUPERVISOR_PROMPT = """You are a supervisor AI overseeing a team of specialist agents. 
For each incoming user message, decide if it should be handled by one of your agents. 
"""


class AgentsConfig(BaseModel):
    deployment_url: str
    """The URL of the LangGraph deployment"""
    agent_id: str
    """The ID of the agent to use"""
    name: str
    """The name of the agent"""


class GraphConfigPydantic(BaseModel):
    agents: List[AgentsConfig] = Field(
        default=[],
        metadata={"x_oap_ui_config": {"type": "agents"}},
    )
    system_prompt: Optional[str] = Field(
        default=DEFAULT_SUPERVISOR_PROMPT,
        metadata={
            "x_oap_ui_config": {
                "type": "textarea",
                "placeholder": "Enter a system prompt...",
                "description": f"The system prompt to use in all generations. The following prompt will always be included at the end of the system prompt:\n---{UNEDITABLE_SYSTEM_PROMPT}---",
                "default": DEFAULT_SUPERVISOR_PROMPT,
            }
        },
    )


def make_child_graphs(cfg: GraphConfigPydantic, access_token: Optional[str] = None):
    """
    Instantiate a list of RemoteGraph nodes based on the configuration.

    Args:
        cfg: The configuration for the graph
        access_token: The Supabase access token for authentication, can be None

    Returns:
        A list of RemoteGraph instances
    """
    import re

    def sanitize_name(name):
        # Replace spaces with underscores
        sanitized = name.replace(" ", "_")
        # Remove any other disallowed characters (<, >, |, \, /)
        sanitized = re.sub(r"[<|\\/>]", "", sanitized)
        return sanitized

    # If no agents in config, return empty list
    if not cfg.agents:
        return []

    # If access_token is None, create headers without token
    headers = {}
    if access_token:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "x-supabase-access-token": access_token,
        }

    def create_remote_graph_wrapper(agent: AgentsConfig):
        remote_graph = RemoteGraph(
            agent.agent_id,
            url=agent.deployment_url,
            name=sanitize_name(agent.name),
            headers=headers,
        )

        async def remote_graph_wrapper(state):
            # Ensure we overwrite the thread ID so that sub-agents do NOT inherit
            # the thread ID, and thus the config from the parent/previous run.
            thread_id = str(uuid.uuid4())
            return await remote_graph.ainvoke(
                state, {"configurable": {"thread_id": thread_id}}
            )

        workflow = (
            StateGraph(AgentState)
            .add_node("remote_graph", remote_graph_wrapper)
            .add_edge("__start__", "remote_graph")
        )

        return workflow.compile(name=sanitize_name(agent.name))

    return [create_remote_graph_wrapper(a) for a in cfg.agents]


def make_model(cfg: GraphConfigPydantic):
    """Instantiate the LLM for the supervisor based on the config."""
    return ChatOpenAI(model="gpt-4o")


def make_prompt(cfg: GraphConfigPydantic):
    """Build the system prompt, falling back to a sensible default."""
    return cfg.system_prompt + UNEDITABLE_SYSTEM_PROMPT


def graph(config: RunnableConfig):
    cfg = GraphConfigPydantic(**config.get("configurable", {}))
    supabase_access_token = config.get("configurable", {}).get(
        "x-supabase-access-token"
    )

    # Pass the token to make_child_graphs, which now handles None values
    child_graphs = make_child_graphs(cfg, supabase_access_token)

    return create_supervisor(
        child_graphs,
        model=make_model(cfg),
        prompt=make_prompt(cfg),
        config_schema=GraphConfigPydantic,
        handoff_tool_prefix="delegate_to_",
        output_mode="full_history",
    )
