# open-agent-supervisor

A supervisor agent for the LangGraph Open Agent Platform. This project leverages the built in LangGraph supervisor agent to orchestrate specialist agents via their [RemoteGraph](https://langchain-ai.github.io/langgraph/reference/remote_graph/).

## Features

*   **Dynamic Agent Delegation:** The supervisor can decide whether to handle a user query itself or delegate it to a configured specialist agent.
*   **Configurable Agents:** Easily define and configure multiple child agents, selecting from the list of existing agents you have deployed.
*   **Customizable System Prompt:** Tailor the supervisor's behavior and instructions using a configurable system prompt, with a sensible default provided.

## How it Works

The supervisor operates based on a system prompt that instructs it on how to manage incoming user messages. It can either:
1.  Answer the user directly.
2.  Delegate the query to a specialist agent by invoking a tool in the format `delegate_to_<agent_name>(user_query)`.

The user sees all messages and tool calls, ensuring transparency in the conversation flow.

## Configuration

The supervisor and its child agents are configured using Pydantic models defined in `agent.py`.

### `AgentsConfig`
Defines the configuration for each child agent:
-   `deployment_url`: The URL of the LangGraph deployment for the child agent.
-   `agent_id`: The ID of the child agent.
-   `name`: A user-friendly name for the child agent. This name is sanitized (spaces replaced with underscores, special characters removed) to be used in tool names.

### `GraphConfigPydantic`
Defines the overall configuration for the supervisor graph:
-   `agents`: A list of `AgentsConfig` objects, defining all the child agents the supervisor can delegate to.
-   `system_prompt`: An optional custom system prompt for the supervisor. If not provided, a default prompt is used, guiding the supervisor on its role and how to delegate tasks.

## Core Components (`agent.py`)

*   **`DEFAULT_SUPERVISOR_PROMPT`**: A constant string providing the default system prompt for the supervisor.
*   **`AgentsConfig(BaseModel)`**: Pydantic model for configuring individual child agents.
*   **`GraphConfigPydantic(BaseModel)`**: Pydantic model for the overall graph configuration, including the list of agents and the system prompt.
*   **`make_child_graphs(cfg: GraphConfigPydantic)`**:
    *   Takes the graph configuration as input.
    *   Instantiates `RemoteGraph` objects for each configured child agent.
    *   Sanitizes agent names (replaces spaces with underscores, removes characters like `<`, `>`, `|`, `\`, `/`) to ensure they are valid tool names.
*   **`make_model(cfg: GraphConfigPydantic)`**:
    *   Instantiates the Language Model (LLM) for the supervisor.
    *   Currently configured to use `ChatOpenAI` with the "gpt-4o" model.
*   **`make_prompt(cfg: GraphConfigPydantic)`**:
    *   Builds the system prompt for the supervisor.
    *   Uses the `system_prompt` from the configuration if provided, otherwise falls back to `DEFAULT_SUPERVISOR_PROMPT`.
*   **`graph(config: RunnableConfig)`**:
    *   The main function that constructs the LangGraph supervisor.
    *   Retrieves the configuration using `config.get("configurable", {})`.
    *   Calls `make_child_graphs` to create the child agent nodes.
    *   Uses `create_supervisor` from `langgraph_supervisor` to assemble the supervisor graph, passing in:
        *   The child graphs.
        *   The supervisor model (from `make_model`).
        *   The system prompt (from `make_prompt`).
        *   The Pydantic schema for configuration (`GraphConfigPydantic`).
        *   A prefix for handoff tools (`delegate_to_`).
        *   The output mode (`full_history`).
