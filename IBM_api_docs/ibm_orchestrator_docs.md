# Creating agents - IBM watsonx Orchestrate ADK
With the ADK, you can create native agents, external agents, and external watsonx Assistants agents. Each of these agent types requires its own set of configurations. Use YAML, JSON, or Python files to create your agents for watsonx Orchestrate.

Native Agents
-------------

Native agents are built with and imported to the watsonx Orchestrate platform. They have the capability of following a set of instructions that tell the agent how it should respond to a user request. The overall integrated prompting structure of the agent can be modified by using the `style` attribute. To learn more about agent styles, see [Agent styles](#agent-styles). Native agents have `collaborators` which are other agents, whether they be native agents, external agents, or external assistants, that this agent can communicate with to solve a users request. The native agent’s `description` provides a user-facing description of the agent for the agent management UI and helps the agent decide when to consume this agent as a collaborator when it is added to the agent’s collaborator list. Provide well-crafted descriptions for your agents. These descriptions are used by supervisor agents to determine how to route user requests. For more information, see [Writing descriptions for agents](about:blank/getting_started/guidelines#writing-descriptions-for-agents).

### Chat with documents

Native agents support the chat with documents feature, so you send a document in the agent chat and ask questions about it in the same thread. To enable this feature, configure the following parameters:



* Parameter: enabled
  * Type: boolean
  * Description: Enables or disables the Chat with Documents feature. Default is false.
* Parameter: citations
  * Type: object
  * Description: Contains the citations_shown parameter, which controls the maximum number of citations displayed during the interaction.


### Providing access to context variables

Context variables enrich the information an agent sees about the user it interacts with. They enhance flexibility and personalization, helping agents deliver more relevant responses and orchestrate complex workflows across authenticated user sessions. To enable access to specific context variables:

1.  Set `context_access_enabled` to `true`.
2.  Define the list of variables your agent can access in the `context_variables` schema.
3.  Add instructions to guide how your agent should use each variable. Wrap each variable in curly braces `{}`.


|Variable     |Description                                                                  |
|-------------|-----------------------------------------------------------------------------|
|wxo_user_name|The user name of the authenticated watsonx Orchestrate user.                 |
|wxo_email_id |The email address associated with the authenticated watsonx Orchestrate user.|
|wxo_tenant_id|The unique identifier for the tenant the user belongs to.                    |


### Agent styles

Agent styles dictate how the agents will follow instructions and the way that the agents behaves. Currently, you can choose from three available styles:

*   [Default (`default`)](#default-style)
*   [ReAct (`react`)](#react-style)
*   [Plan-Act (`planner`)](#plan-act-style).

#### Default style

The **Default** (`default`) style is a streamlined, tool-centric reasoning mode ideal for straightforward tasks. It relies on the LLM’s prompt-driven decision-making to decide which tool to use, how to use it, and when to respond. This style is excellent when the logic is mostly linear, like retrieving a report or checking a ticket, because the agent uses the LLM’s intrinsic capabilities to orchestrate tool calls on the fly. It is ideal for:

*   Single-step or lightly sequential tasks
*   Scenarios where flexibility and adaptability are needed
*   Tasks that might require multiple tools but don’t need strict sequencing

**Behavior**

*   Iteratively prompts the LLM to:
    *   Identify which tool or collaborator agent to invoke
    *   Determine what inputs to use
    *   Decide whether to call more tool or finalize a response
*   Continues the prompting loop as needed, until it gathers sufficient context for a final answer.

**Tool Compatibilty**

*   Python tools
*   OpenAPI tools
*   MCP tools

**Example use cases:**

*   Extract information from the web or from a system
*   Check the status of a task or ticket
*   Perform tasks that require well-defined steps

#### ReAct style

The **ReAct** (`react`) style (Reasoning and Acting) is an iterative loop where the agent thinks, acts, and observes continuously. It’s designed for complex or ambiguous problems where each outcome influences the next action. Inspired by the [ReAct methodology](https://arxiv.org/abs/2210.03629), this pattern surfaces the agent’s [chain of thought](https://www.ibm.com/think/topics/chain-of-thoughts), supporting validation, step-by-step reasoning, and interactive confirmation. A ReAct agent breaks the task into smaller parts, and starts reasoning through each step before taking an action and deciding on which tools to use. The agent then adjusts its actions based on what it learns along the way, and it might ask the user for confirmation to continue working on the given task. It is ideal for:

*   Exploratory or research-intensive tasks
*   Scenarios requiring iterative validation or hypothesis testing
*   Tasks with unclear or evolving requirements
*   Situations where transparent reasoning and reflection are valuable

**Behavior**

*   **Think**: Assess the user’s request and decide on a tool, collaborator, or reasoning step.
*   **Act**: Execute the tool or collaborator.
*   **Observe**: Evaluate the outcome and adjust reasoning.
*   Repeat until the goal is achieved.

**Tool Compatibilty**

*   Knowledge-intensive tools
*   Data-intensive tools
*   Collaborator agents

**Example use cases**

*   Coding an application or tool by generating code snippets or refactoring existing code
*   Answering complex questions by searchig the web, synthesizing information, and citing sources
*   Handling support tickets that require complex interactions with users

#### Plan-Act style

The **Plan-Act** (`planner`) style agent emphasizes upfront planning followed by stepwise execution. Initially, the agent uses the LLM to create a structured action plan, a sequence of tasks to execute, with all the tools and collaborator agents to invoke. Once the plan is in place, it carries out each step in order. This approach supports dynamic replanning if unexpected changes occur, leveraging the agent’s oversight over multi-step workflows. A `planner` style agent is capable of customizing the response output. By default, the `planner` style generates a summary of the tasks planned and executed by the planner agent if you don’t provide a custom response output. It is ideal for:

*   Multi-step, structured workflows
*   Business processes needing transparency and traceability
*   Automations involving multiple domains or collaborator agents

**Tool Compatibility**

*   Python tools
*   OpenAPI tools
*   MCP tools
*   Collaborator agents

**Example use cases:**

*   Creating structured reports
*   Agents that use multiple tools (for example, search, calculator, code execution) and need to combine results
*   Drafting contracts, policies, or compliance checklists

##### Customizing the response output with the Plan-Act agent

To customize the output, you can define either a `structured_output` field or a `custom_join_tool` field, as follows:

The `structured_output` defines the schema of how the data should be returned from the agent. The `custom_join_tool` is a normal Python tool that dictates how the output of the agent shuld look like, giving you total control of how the output looks instead of being generated by the LLM. You can see the following example of a `custom_join_tool`:

```
from typing import Dict, List, Any
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission

@tool(permission=ToolPermission.READ_ONLY, kind=PythonToolKind.join_tool)
def format_task_results(original_query: str, task_results: Dict[str, Any], messages: List[Dict[str, Any]]) -> str:
    """
    Format the results from various tasks executed by a planner agent into a cohesive response.
    
    Args:
        original_query (str): The initial query submitted by the user.
        task_results (Dict[str, Any]): A dictionary containing the outcomes of each task executed within the agent's plan.
        messages (List[Dict[str, Any]]): The history of messages in the current conversation.
        
    Returns:
        str: A formatted string containing the consolidated results.
    """
    # Create a summary header
    output = f"## Results for: {original_query}\n\n"
    
    # Add each task result in a structured format
    for task_name, result in task_results.items():
        output += f"### {task_name}\n"
        
        # Handle different result types appropriately
        if isinstance(result, dict):
            # Pretty format dictionaries
            output += "```json\n"
            output += json.dumps(result, indent=2)
            output += "\n```\n\n"
        elif isinstance(result, list):
            # Format lists as bullet points
            output += "\n".join([f"- {item}" for item in result])
            output += "\n\n"
        else:
            # Plain text for other types
            output += f"{result}\n\n"
    
    # Add a summary section
    output += "## Summary\n"
    output += f"Completed {len(task_results)} tasks related to your query about {original_query.lower()}.\n"
    
    return output

```


### Guidelines

You can configure the guidelines for your agent. A guideline includes a name, condition, action, and associated tool. To set up guidelines, add a guidelines section and define each guideline with the following fields:



* Parameter: display_name
  * type: string
  * Description: The display name of the guideline.
* Parameter: condition
  * type: string
  * Description: The condition for this guideline.
* Parameter: action
  * type: string
  * Description: The action your agent takes when the condition is met.
* Parameter: tool
  * type: string
  * Description: The unique identifier of the tool that is associated with this guideline.Note:Use the tool name as its unique identifier.


### Welcome message

The welcome message is the first message users see when they start interacting with your agent. You can personalize this message to match your agent’s purpose. To configure it, define the `welcome_content` schema in your agent file using the following fields:



* Parameter: welcome_message
  * type: string
  * Description: The welcome message.
* Parameter: description
  * type: string
  * Description: The welcome message description.
* Parameter: is_default_message
  * type: boolean
  * Description: (Optional) Set to true  to make this message the default welcome message.


**Example:**

### Starter prompts

Starter prompts are predefined messages that help users begin a conversation with your agent. You can configure these prompts in the `starter_prompts` section of your agent file. Start by defining whether these prompts are the default set. Then, for each prompt, configure the following fields:


|Parameter|Type  |Description                        |
|---------|------|-----------------------------------|
|id       |string|A unique identifier for the prompt.|
|title    |string|The title of the prompt.           |
|subtitle |string|The subtitle of the prompt.        |
|prompt   |string|The prompt shown to the user.      |
|state    |string|The current state of the prompt.   |


**Example:**

External Agents
---------------

External agents are built outside watsonx Orchestrate and can be used as collaborators for native agents.

### provider: external\_chat

The external chat provider can be used to integrate agents from an external provider such as BeeAI, Langgraph, or CrewAI that a user hosts themselves, for example in Code Engine. The documentation for this API spec can be found on the [watsonx-orchestrate-developer-toolkit](https://github.com/watson-developer-cloud/watsonx-orchestrate-developer-toolkit/tree/main/external_agent). A reference Langgraph external agent can be found [here](https://github.com/watson-developer-cloud/watsonx-orchestrate-developer-toolkit/tree/main/external_agent/examples/langgraph_python). Provide well-crafted descriptions for your agents. These descriptions are used by supervisor agents to determine how to route user requests. For more information, see [Writing descriptions for agents](about:blank/getting_started/guidelines#writing-descriptions-for-agents).

### provider: wx.ai

It is also possible to integrate with agents built using watsonx.ai’s [agent builder platform](https://www.ibm.com/products/watsonx-ai/ai-agent-development). For more information, please see Registering agents from watsonx.ai [here](https://www.ibm.com/docs/en/watsonx/watson-orchestrate/current?topic=agent-managing-agents-in-ai-chat#registering-agents-from-watsonxai). However, rather than using the api, simply fill out the following yaml file and import your agent. Provide well-crafted descriptions for your agents. These descriptions are used by supervisor agents to determine how to route user requests. For more information, see [Writing descriptions for agents](about:blank/getting_started/guidelines#writing-descriptions-for-agents).

### provider: salesforce

To register an agent built within Salesforce Agent Force as an external agent:

1.  Follow the **Getting Started Guide** for the Agent API. For more information, see [Getting Started Guide](https://developer.salesforce.com/docs/einstein/genai/guide/agent-api-get-started.html).

![getting-started-salesforce.png](https://mintlify.s3.us-west-1.amazonaws.com/ibm-2e3153bf/assets/salesforce/getting-started-salesforce.png)

1.  On the create a token page, you find the following information, which will be the same across all your SalesForce agents in the instance:

*   Your `api_url`, it always be [https://api.salesforce.com/einstein/ai-agent/v1](https://api.salesforce.com/einstein/ai-agent/v1).
*   Under `auth_config`, your `token` will be the `CONSUMER_SECRET` referenced in the guide.
*   Under `chat_params`.
    *   Your `client_id` will be the `CONSUMER_KEY`.
    *   Your `domain_url` will be the `DOMAIN_URL`.
    *   Optionally, you can specify a list of display types to pass to orchestrate as a comma-separated string.

1.  Provide well-crafted descriptions for your agents. These descriptions are used by supervisor agents to determine how to route user requests. For more information, see [Writing descriptions for agents](about:blank/getting_started/guidelines#writing-descriptions-for-agents).
2.  Lastly, under `chat_params` you need to specify your `agent_id`. This can be found by hovering over one of your agents and either right-clicking and copying the URL, or by manually writing it based on hover text. In the following example, the agent\_id is `0XxfJ0000001d8zSAA`.

![agent-selection-salesforce.png](https://mintlify.s3.us-west-1.amazonaws.com/ibm-2e3153bf/assets/salesforce/agent-selection-salesforce.png)

External watsonx Assistants agents
----------------------------------

To register assistants from watsonx Assistant, you need to obtain the following information:

*   `service_instance_url`
*   `api_key`
*   `assistant_id`
*   `environment_id`

To retrieve your assistant ID:

1.  Navigate to the settings on the actions page and open the settings.

![actions_page.png](https://mintlify.s3.us-west-1.amazonaws.com/ibm-2e3153bf/assets/assistant/actions-page.png)

1.  On the farthest right tab, select Upload/Download, and click the **Download** button.

![actions-page.png](https://mintlify.s3.us-west-1.amazonaws.com/ibm-2e3153bf/assets/assistant/settings.png)

1.  Locate your `environment_id` and `assistant_id` in the output JSON.

![environment-id.png](https://mintlify.s3.us-west-1.amazonaws.com/ibm-2e3153bf/assets/assistant/environment-id.png)

### IBM Cloud

On IBM Cloud, your `service_instance_url` and `api_key` can be found on the page where you launch your assistant’s tooling UI. ![ibmcloud-service-keys.png](https://mintlify.s3.us-west-1.amazonaws.com/ibm-2e3153bf/assets/assistant/ibmcloud-service-keys.png) Provide well-crafted descriptions for your agents. These descriptions are used by supervisor agents to determine how to route user requests. For more information, see [Writing descriptions for agents](about:blank/getting_started/guidelines#writing-descriptions-for-agents).

### AWS

Provide well-crafted descriptions for your agents. These descriptions are used by supervisor agents to determine how to route user requests. For more information, see [Writing descriptions for agents](about:blank/getting_started/guidelines#writing-descriptions-for-agents).

External agents as collaborator agents
--------------------------------------

You can use external agents that follow the A2A protocol as collaborators for native agents. To do this, set `provider` to `external_chat`/`A2A`/`0.2.1` as show below. Make sure to write clear, well-crafted descriptions for your agents. Supervisor agents rely on these descriptions to route user requests effectively. For more information, see [Writing descriptions for agents](about:blank/getting_started/guidelines#writing-descriptions-for-agents).

### Providing access to context variables

Context variables enrich the information an agent sees about the user it interacts with. They enhance flexibility and personalization, helping agents deliver more relevant responses and orchestrate complex workflows across authenticated user sessions. To enable access to specific context variables:

1.  Set `context_access_enabled` to `true`.
2.  Define the list of variables your agent can access in the `context_variables` schema.
3.  Add instructions to guide how your agent should use each variable. Wrap each variable in curly braces `{}`.


|Variable     |Description                                                                  |
|-------------|-----------------------------------------------------------------------------|
|wxo_user_name|The user name of the authenticated watsonx Orchestrate user.                 |
|wxo_email_id |The email address associated with the authenticated watsonx Orchestrate user.|
|wxo_tenant_id|The unique identifier for the tenant the user belongs to.                    |






# Creating agents - IBM watsonx Orchestrate ADK
With the ADK, you can create native agents, external agents, and external watsonx Assistants agents. Each of these agent types requires its own set of configurations. Use YAML, JSON, or Python files to create your agents for watsonx Orchestrate.

Native Agents
-------------

Native agents are built with and imported to the watsonx Orchestrate platform. They have the capability of following a set of instructions that tell the agent how it should respond to a user request. The overall integrated prompting structure of the agent can be modified by using the `style` attribute. To learn more about agent styles, see [Agent styles](#agent-styles). Native agents have `collaborators` which are other agents, whether they be native agents, external agents, or external assistants, that this agent can communicate with to solve a users request. The native agent’s `description` provides a user-facing description of the agent for the agent management UI and helps the agent decide when to consume this agent as a collaborator when it is added to the agent’s collaborator list. Provide well-crafted descriptions for your agents. These descriptions are used by supervisor agents to determine how to route user requests. For more information, see [Writing descriptions for agents](about:blank/getting_started/guidelines#writing-descriptions-for-agents).

### Chat with documents

Native agents support the chat with documents feature, so you send a document in the agent chat and ask questions about it in the same thread. To enable this feature, configure the following parameters:



* Parameter: enabled
  * Type: boolean
  * Description: Enables or disables the Chat with Documents feature. Default is false.
* Parameter: citations
  * Type: object
  * Description: Contains the citations_shown parameter, which controls the maximum number of citations displayed during the interaction.


### Providing access to context variables

Context variables enrich the information an agent sees about the user it interacts with. They enhance flexibility and personalization, helping agents deliver more relevant responses and orchestrate complex workflows across authenticated user sessions. To enable access to specific context variables:

1.  Set `context_access_enabled` to `true`.
2.  Define the list of variables your agent can access in the `context_variables` schema.
3.  Add instructions to guide how your agent should use each variable. Wrap each variable in curly braces `{}`.


|Variable     |Description                                                                  |
|-------------|-----------------------------------------------------------------------------|
|wxo_user_name|The user name of the authenticated watsonx Orchestrate user.                 |
|wxo_email_id |The email address associated with the authenticated watsonx Orchestrate user.|
|wxo_tenant_id|The unique identifier for the tenant the user belongs to.                    |


### Agent styles

Agent styles dictate how the agents will follow instructions and the way that the agents behaves. Currently, you can choose from three available styles:

*   [Default (`default`)](#default-style)
*   [ReAct (`react`)](#react-style)
*   [Plan-Act (`planner`)](#plan-act-style).

#### Default style

The **Default** (`default`) style is a streamlined, tool-centric reasoning mode ideal for straightforward tasks. It relies on the LLM’s prompt-driven decision-making to decide which tool to use, how to use it, and when to respond. This style is excellent when the logic is mostly linear, like retrieving a report or checking a ticket, because the agent uses the LLM’s intrinsic capabilities to orchestrate tool calls on the fly. It is ideal for:

*   Single-step or lightly sequential tasks
*   Scenarios where flexibility and adaptability are needed
*   Tasks that might require multiple tools but don’t need strict sequencing

**Behavior**

*   Iteratively prompts the LLM to:
    *   Identify which tool or collaborator agent to invoke
    *   Determine what inputs to use
    *   Decide whether to call more tool or finalize a response
*   Continues the prompting loop as needed, until it gathers sufficient context for a final answer.

**Tool Compatibilty**

*   Python tools
*   OpenAPI tools
*   MCP tools

**Example use cases:**

*   Extract information from the web or from a system
*   Check the status of a task or ticket
*   Perform tasks that require well-defined steps

#### ReAct style

The **ReAct** (`react`) style (Reasoning and Acting) is an iterative loop where the agent thinks, acts, and observes continuously. It’s designed for complex or ambiguous problems where each outcome influences the next action. Inspired by the [ReAct methodology](https://arxiv.org/abs/2210.03629), this pattern surfaces the agent’s [chain of thought](https://www.ibm.com/think/topics/chain-of-thoughts), supporting validation, step-by-step reasoning, and interactive confirmation. A ReAct agent breaks the task into smaller parts, and starts reasoning through each step before taking an action and deciding on which tools to use. The agent then adjusts its actions based on what it learns along the way, and it might ask the user for confirmation to continue working on the given task. It is ideal for:

*   Exploratory or research-intensive tasks
*   Scenarios requiring iterative validation or hypothesis testing
*   Tasks with unclear or evolving requirements
*   Situations where transparent reasoning and reflection are valuable

**Behavior**

*   **Think**: Assess the user’s request and decide on a tool, collaborator, or reasoning step.
*   **Act**: Execute the tool or collaborator.
*   **Observe**: Evaluate the outcome and adjust reasoning.
*   Repeat until the goal is achieved.

**Tool Compatibilty**

*   Knowledge-intensive tools
*   Data-intensive tools
*   Collaborator agents

**Example use cases**

*   Coding an application or tool by generating code snippets or refactoring existing code
*   Answering complex questions by searchig the web, synthesizing information, and citing sources
*   Handling support tickets that require complex interactions with users

#### Plan-Act style

The **Plan-Act** (`planner`) style agent emphasizes upfront planning followed by stepwise execution. Initially, the agent uses the LLM to create a structured action plan, a sequence of tasks to execute, with all the tools and collaborator agents to invoke. Once the plan is in place, it carries out each step in order. This approach supports dynamic replanning if unexpected changes occur, leveraging the agent’s oversight over multi-step workflows. A `planner` style agent is capable of customizing the response output. By default, the `planner` style generates a summary of the tasks planned and executed by the planner agent if you don’t provide a custom response output. It is ideal for:

*   Multi-step, structured workflows
*   Business processes needing transparency and traceability
*   Automations involving multiple domains or collaborator agents

**Tool Compatibility**

*   Python tools
*   OpenAPI tools
*   MCP tools
*   Collaborator agents

**Example use cases:**

*   Creating structured reports
*   Agents that use multiple tools (for example, search, calculator, code execution) and need to combine results
*   Drafting contracts, policies, or compliance checklists

##### Customizing the response output with the Plan-Act agent

To customize the output, you can define either a `structured_output` field or a `custom_join_tool` field, as follows:

The `structured_output` defines the schema of how the data should be returned from the agent. The `custom_join_tool` is a normal Python tool that dictates how the output of the agent shuld look like, giving you total control of how the output looks instead of being generated by the LLM. You can see the following example of a `custom_join_tool`:

```
from typing import Dict, List, Any
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission

@tool(permission=ToolPermission.READ_ONLY, kind=PythonToolKind.join_tool)
def format_task_results(original_query: str, task_results: Dict[str, Any], messages: List[Dict[str, Any]]) -> str:
    """
    Format the results from various tasks executed by a planner agent into a cohesive response.
    
    Args:
        original_query (str): The initial query submitted by the user.
        task_results (Dict[str, Any]): A dictionary containing the outcomes of each task executed within the agent's plan.
        messages (List[Dict[str, Any]]): The history of messages in the current conversation.
        
    Returns:
        str: A formatted string containing the consolidated results.
    """
    # Create a summary header
    output = f"## Results for: {original_query}\n\n"
    
    # Add each task result in a structured format
    for task_name, result in task_results.items():
        output += f"### {task_name}\n"
        
        # Handle different result types appropriately
        if isinstance(result, dict):
            # Pretty format dictionaries
            output += "```json\n"
            output += json.dumps(result, indent=2)
            output += "\n```\n\n"
        elif isinstance(result, list):
            # Format lists as bullet points
            output += "\n".join([f"- {item}" for item in result])
            output += "\n\n"
        else:
            # Plain text for other types
            output += f"{result}\n\n"
    
    # Add a summary section
    output += "## Summary\n"
    output += f"Completed {len(task_results)} tasks related to your query about {original_query.lower()}.\n"
    
    return output

```


### Guidelines

You can configure the guidelines for your agent. A guideline includes a name, condition, action, and associated tool. To set up guidelines, add a guidelines section and define each guideline with the following fields:



* Parameter: display_name
  * type: string
  * Description: The display name of the guideline.
* Parameter: condition
  * type: string
  * Description: The condition for this guideline.
* Parameter: action
  * type: string
  * Description: The action your agent takes when the condition is met.
* Parameter: tool
  * type: string
  * Description: The unique identifier of the tool that is associated with this guideline.Note:Use the tool name as its unique identifier.


### Welcome message

The welcome message is the first message users see when they start interacting with your agent. You can personalize this message to match your agent’s purpose. To configure it, define the `welcome_content` schema in your agent file using the following fields:



* Parameter: welcome_message
  * type: string
  * Description: The welcome message.
* Parameter: description
  * type: string
  * Description: The welcome message description.
* Parameter: is_default_message
  * type: boolean
  * Description: (Optional) Set to true  to make this message the default welcome message.


**Example:**

### Starter prompts

Starter prompts are predefined messages that help users begin a conversation with your agent. You can configure these prompts in the `starter_prompts` section of your agent file. Start by defining whether these prompts are the default set. Then, for each prompt, configure the following fields:


|Parameter|Type  |Description                        |
|---------|------|-----------------------------------|
|id       |string|A unique identifier for the prompt.|
|title    |string|The title of the prompt.           |
|subtitle |string|The subtitle of the prompt.        |
|prompt   |string|The prompt shown to the user.      |
|state    |string|The current state of the prompt.   |


**Example:**

External Agents
---------------

External agents are built outside watsonx Orchestrate and can be used as collaborators for native agents.

### provider: external\_chat

The external chat provider can be used to integrate agents from an external provider such as BeeAI, Langgraph, or CrewAI that a user hosts themselves, for example in Code Engine. The documentation for this API spec can be found on the [watsonx-orchestrate-developer-toolkit](https://github.com/watson-developer-cloud/watsonx-orchestrate-developer-toolkit/tree/main/external_agent). A reference Langgraph external agent can be found [here](https://github.com/watson-developer-cloud/watsonx-orchestrate-developer-toolkit/tree/main/external_agent/examples/langgraph_python). Provide well-crafted descriptions for your agents. These descriptions are used by supervisor agents to determine how to route user requests. For more information, see [Writing descriptions for agents](about:blank/getting_started/guidelines#writing-descriptions-for-agents).

### provider: wx.ai

It is also possible to integrate with agents built using watsonx.ai’s [agent builder platform](https://www.ibm.com/products/watsonx-ai/ai-agent-development). For more information, please see Registering agents from watsonx.ai [here](https://www.ibm.com/docs/en/watsonx/watson-orchestrate/current?topic=agent-managing-agents-in-ai-chat#registering-agents-from-watsonxai). However, rather than using the api, simply fill out the following yaml file and import your agent. Provide well-crafted descriptions for your agents. These descriptions are used by supervisor agents to determine how to route user requests. For more information, see [Writing descriptions for agents](about:blank/getting_started/guidelines#writing-descriptions-for-agents).

### provider: salesforce

To register an agent built within Salesforce Agent Force as an external agent:

1.  Follow the **Getting Started Guide** for the Agent API. For more information, see [Getting Started Guide](https://developer.salesforce.com/docs/einstein/genai/guide/agent-api-get-started.html).

![getting-started-salesforce.png](https://mintlify.s3.us-west-1.amazonaws.com/ibm-2e3153bf/assets/salesforce/getting-started-salesforce.png)

1.  On the create a token page, you find the following information, which will be the same across all your SalesForce agents in the instance:

*   Your `api_url`, it always be [https://api.salesforce.com/einstein/ai-agent/v1](https://api.salesforce.com/einstein/ai-agent/v1).
*   Under `auth_config`, your `token` will be the `CONSUMER_SECRET` referenced in the guide.
*   Under `chat_params`.
    *   Your `client_id` will be the `CONSUMER_KEY`.
    *   Your `domain_url` will be the `DOMAIN_URL`.
    *   Optionally, you can specify a list of display types to pass to orchestrate as a comma-separated string.

1.  Provide well-crafted descriptions for your agents. These descriptions are used by supervisor agents to determine how to route user requests. For more information, see [Writing descriptions for agents](about:blank/getting_started/guidelines#writing-descriptions-for-agents).
2.  Lastly, under `chat_params` you need to specify your `agent_id`. This can be found by hovering over one of your agents and either right-clicking and copying the URL, or by manually writing it based on hover text. In the following example, the agent\_id is `0XxfJ0000001d8zSAA`.

![agent-selection-salesforce.png](https://mintlify.s3.us-west-1.amazonaws.com/ibm-2e3153bf/assets/salesforce/agent-selection-salesforce.png)

External watsonx Assistants agents
----------------------------------

To register assistants from watsonx Assistant, you need to obtain the following information:

*   `service_instance_url`
*   `api_key`
*   `assistant_id`
*   `environment_id`

To retrieve your assistant ID:

1.  Navigate to the settings on the actions page and open the settings.

![actions_page.png](https://mintlify.s3.us-west-1.amazonaws.com/ibm-2e3153bf/assets/assistant/actions-page.png)

1.  On the farthest right tab, select Upload/Download, and click the **Download** button.

![actions-page.png](https://mintlify.s3.us-west-1.amazonaws.com/ibm-2e3153bf/assets/assistant/settings.png)

1.  Locate your `environment_id` and `assistant_id` in the output JSON.

![environment-id.png](https://mintlify.s3.us-west-1.amazonaws.com/ibm-2e3153bf/assets/assistant/environment-id.png)

### IBM Cloud

On IBM Cloud, your `service_instance_url` and `api_key` can be found on the page where you launch your assistant’s tooling UI. ![ibmcloud-service-keys.png](https://mintlify.s3.us-west-1.amazonaws.com/ibm-2e3153bf/assets/assistant/ibmcloud-service-keys.png) Provide well-crafted descriptions for your agents. These descriptions are used by supervisor agents to determine how to route user requests. For more information, see [Writing descriptions for agents](about:blank/getting_started/guidelines#writing-descriptions-for-agents).

### AWS

Provide well-crafted descriptions for your agents. These descriptions are used by supervisor agents to determine how to route user requests. For more information, see [Writing descriptions for agents](about:blank/getting_started/guidelines#writing-descriptions-for-agents).

External agents as collaborator agents
--------------------------------------

You can use external agents that follow the A2A protocol as collaborators for native agents. To do this, set `provider` to `external_chat`/`A2A`/`0.2.1` as show below. Make sure to write clear, well-crafted descriptions for your agents. Supervisor agents rely on these descriptions to route user requests effectively. For more information, see [Writing descriptions for agents](about:blank/getting_started/guidelines#writing-descriptions-for-agents).

### Providing access to context variables

Context variables enrich the information an agent sees about the user it interacts with. They enhance flexibility and personalization, helping agents deliver more relevant responses and orchestrate complex workflows across authenticated user sessions. To enable access to specific context variables:

1.  Set `context_access_enabled` to `true`.
2.  Define the list of variables your agent can access in the `context_variables` schema.
3.  Add instructions to guide how your agent should use each variable. Wrap each variable in curly braces `{}`.


|Variable     |Description                                                                  |
|-------------|-----------------------------------------------------------------------------|
|wxo_user_name|The user name of the authenticated watsonx Orchestrate user.                 |
|wxo_email_id |The email address associated with the authenticated watsonx Orchestrate user.|
|wxo_tenant_id|The unique identifier for the tenant the user belongs to.                    |

