## Tools
In LangGraph, a ToolNode is a prebuilt node type that acts as a bridge between your graph and external tools (functions, APls, utilities).
- Normally in LangGraph you'd write a node function yourself: it takes in state and returns state.
- A ToolNode is a ready-made node that knows how to handle a list of LangChain tools.
- Its job: listen for tool calls from the LLM (like "call search()" or "get_weather()") and automatically route the request to the correct tool, then pass the tool's output back into the graph.

### Tools Condition
tools_condition is a prebuilt conditional edge function that helps your graph decide:
"Should the flow go to the ToolNode next, or back to the LLM?"