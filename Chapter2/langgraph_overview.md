# LangGraph

Goals:
- What is LangChain (recap)?
- What is langGraph?
- LangGraph vs LangChain?
- Why langGraph exists?
- Should we still use LangChain?


### What is LangChain (recap)?
LangChain is an open-source library designed to simplify the process of building
LLM based applications.
It provides modular building blocks that let you create sophisticated LLM-based workflows with ease.

LangChain consists of multiple components
-  Model components gives use a unified interface to interact with various LLM providers
- Prompts component helps you engineer prompts
- Retrievers component helps you fetch relevant documents from a vector store

But the biggest offering of LangChain is Chains.

What can you do with LangChain
- Simple conversational workflows like Chatbots, Text Summarizers
- Multistep workflows
- RAG applications
- Basic level agents

### Hiring a Backend Engineer Example:

Stages involved:
- Start
- Hiring Request
- Create JD
- JD Approval: No -> Create JD again
- Post JD
- Wait 7 Days
- Monitor Applications
- Enough Applications: No -> Modify JD -> Wait 48 hours
- Shortlist
- Schedule
- Conduct Interview
- Selected: No -> Regret Email
- Send Offer Letter
- Accepted: No -> Renegotiate
- Onboarding

### Why it is not a good choice to implement this workflow in LangChain (LangGraph vs LangChain)
1. Control flow complexity increases
    - Conditional Branches
    - Loops
    - Jumps

    This works fine with linear workflow, but as the complexity increases it becomes difficult to maintain it as the Glue code increases.

2. Handling State
    - Workflows often need to maintain shared state across multiple steps.
    - Managing state manually between LangChain components can become complicated.
    - LangGraph provides built-in state management, allowing nodes to read and update shared workflow state.

    Langchain is stateless and langgraph is stateful.

3. Event Driven Execution

    - Some workflows require execution based on events, such as incoming messages, database updates, or external triggers.
    - LangChain primarily focuses on composing LLM applications rather than managing complex event-driven workflows.
    - Dedicated workflow engines or event-driven architectures may be more suitable for these use cases.

4. Fault Tolerance
    - Production workflows need retries, error handling, timeouts, and recovery from failures.
    - Implementing these mechanisms manually in LangChain can increase complexity with glue code.
    - Workflow orchestration tools like Temporal or Prefect provide more robust execution and failure recovery capabilities.

    LangChain is not fault tolerance. Meanwhile LangGraph has concept of recovery since we have states.

5. Human in the Loop
    - Workflows may require human approval before executing critical actions.
    - Pausing execution, waiting for approval, and resuming from the same state requires additional implementation.
    - LangGraph supports interrupt-based workflows, making human approval processes easier to implement.

    LangChain does not have any mechanism to handle HITL. Meanwhile LangGraph has it and supports it using checkpoints with states.

6. Nested Workflows
    - Complex systems often contain workflows within workflows.
    - Managing nested chains and passing state between them can become difficult as complexity grows.
    - LangGraph supports subgraphs, while dedicated orchestration tools can provide structured workflow composition.

7. Observability
    - Debugging complex workflows requires tracking execution steps, state changes, errors, and performance.
    - Basic LangChain tracing may not be sufficient for monitoring complex, long-running workflows.
    - Tools such as LangSmith, OpenTelemetry, and Grafana can help provide deeper visibility into execution.

    In LanChain we can integrate LangSmith to trace the workflow, only problem is it traces only the langchain code not the glue code. Meanwhile the LangSmith with LangGraph works completely fine.

### What is LangGraph?
- LangGraph is an orchestration framework that enables you to build stateful, multi-step, and event-driven workflows using large language models (LLMs). It's ideal for designing both single-agent and multi-agent agentic Al applications.

- Think of LangGraph as a flowchart engine for LLMs — you define the steps (nodes), how they're connected (edges), and the logic that governs the transitions.
LangGraph takes care of state management, conditional branching, looping,
 pausing/resuming, and fault recovery — features essential for building robust,
production-grade Al systems.

### Why langgraph exists?
- To handle long running workflow.
- Better State Management.
- Complex Control Flow
- To provide Human-in-the-Loop.
- Better Fault Tolerance.
- Event-Driven Execution.
- Provides Nested Workflows.
- Provides Persistence.
- Better Observability.

### What to use when?
- Use LangChain when you're building simple, linear workflows — like a prompt chain, summarizer, or a basic retrieval system.
- Use LangGraph when your use case involves complex, non-linear workflows that need:
    - Conditional paths
    - Loops
    - Human-in-the-loop steps
    - Multi-agent coordination
    - Asynchronous or event-driven execution

### Should we still use LangChain?
- Yes. LangGraph is built on top of LangChain — it doesn't replace it.
- You'll still use LangChain components like:
    - LLMs (ChatOpenAI)
    - PromptTemplate
    - Retrievers
    - DocumentLoaders
    - Tools, etc.
    
    LangGraph handles workflow orchestration, while LangChain provides the building blocks for each step in that workflow.