# Open Agent Platform Supervisor

This project leverages the pre-built [LangGraph Supervisor](https://github.com/langchain-ai/langgraph-supervisor-py) agent to orchestrate specialist agents via a [RemoteGraph](https://langchain-ai.github.io/langgraph/reference/remote_graph/).

## Features

*   **Dynamic Agent Delegation:** The supervisor can decide whether to handle a user query itself or delegate it to a configured specialist agent.
*   **Configurable Agents:** Easily define and configure multiple child agents, selecting from the list of existing agents you have deployed and configured in [Open Agent Platform](https://github.com/langchain-ai/open-agent-platform) (OAP).
*   **Customizable System Prompt:** Tailor the supervisor's behavior and instructions using a configurable system prompt, with a sensible default provided.

## Deployments

### Local

To run the supervisor locally, 

1. Clone this repo

```bash
gh repo clone langchain-ai/open-agent-supervisor
```

2. Copy the `.env.example` file into `.env`, and set your environment variables
     
   *We default to OpenAI to provide the underlying supervisor agent LLM*

```bash
cp .env.example .env
```

4. Install the in-memory LangGraph command line package

```bash
pip install -U "langgraph-cli[inmem]"
```

4. Run the LangGraph server locally

```bash
langgraph dev
```

For more info, see our [LangGraph CLI docs](https://langchain-ai.github.io/langgraph/cloud/reference/cli/#dev)

### OAP

> [!IMPORTANT]
> **Prerequisites**: Have at least one supervisor deployed to your instance of LangGraph Platform (LGP) that matches or extends the base implementation provided in this repo

To add a supervisor agent to the platform: 
1. Navigate to the `Agents` tab in the left menu bar
2. Create and agent and select the graph deployed to your LGP instance described in the prerequisites above
3. Give your supervisor a name, description, an optional system prompt if you'd like to modify it and select the agents that it will orchestrate (note -  these agents will need to already be deployed in your LGP instance and configured in Open Agent Platform)

## How it Works

The supervisor operates based on a system prompt that instructs it on how to manage incoming user messages. It can either:
1.  Answer the user directly.
2.  Delegate the query to a specialist agent by invoking a tool in the format `delegate_to_<agent_name>(user_query)`.

The user sees all messages and and optionally all tool calls, ensuring transparency in the conversation flow.
