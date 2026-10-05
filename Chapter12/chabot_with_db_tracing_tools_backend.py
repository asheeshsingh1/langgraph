import os
import sqlite3
import requests

from dotenv import load_dotenv
from typing import TypedDict, Annotated

from langchain_core.messages import BaseMessage
from langchain_core.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_google_genai import ChatGoogleGenerativeAI

from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.sqlite import SqliteSaver


# ============================================================
# Environment
# ============================================================

load_dotenv()


# ============================================================
# State
# ============================================================

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


# ============================================================
# LLM
# ============================================================

llm = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash"
)


# ============================================================
# Tools
# ============================================================

# ------------------------------------------------------------
# DuckDuckGo Search
# ------------------------------------------------------------

search_tool = DuckDuckGoSearchRun(
    region="us-en"
)


@tool
def web_search(query: str) -> str:
    """
    Search the web for current information.

    Use this tool when the user asks for information
    that may require a web search.
    """

    try:
        result = search_tool.invoke(query)

        if not result:
            return "No search results found."

        return result

    except Exception as e:
        # Important:
        # Don't allow a network/DNS failure to crash
        # the entire LangGraph execution.
        return (
            f"Web search failed. "
            f"Please answer using your existing knowledge if possible. "
            f"Error: {str(e)}"
        )


# ------------------------------------------------------------
# Calculator
# ------------------------------------------------------------

@tool
def calculator(
    first_num: float,
    second_num: float,
    operation: str
) -> dict:
    """
    Perform a basic arithmetic operation on two numbers.

    Supported operations:
    - add
    - sub
    - mul
    - div
    """

    try:

        if operation == "add":
            result = first_num + second_num

        elif operation == "sub":
            result = first_num - second_num

        elif operation == "mul":
            result = first_num * second_num

        elif operation == "div":

            if second_num == 0:
                return {
                    "error": "Division by zero is not allowed"
                }

            result = first_num / second_num

        else:
            return {
                "error": f"Unsupported operation '{operation}'"
            }

        return {
            "first_num": first_num,
            "second_num": second_num,
            "operation": operation,
            "result": result
        }

    except Exception as e:

        return {
            "error": str(e)
        }


# ------------------------------------------------------------
# Stock Price
# ------------------------------------------------------------

@tool
def get_stock_price(symbol: str) -> dict:
    """
    Fetch the latest stock price for a stock symbol
    using Alpha Vantage.

    Example:
        AAPL
        TSLA
        MSFT
    """

    api_key = os.getenv("STOCK_MARKET_API_KEY")

    if not api_key:
        return {
            "error": "STOCK_MARKET_API_KEY is not configured."
        }

    try:

        url = (
            "https://www.alphavantage.co/query"
            f"?function=GLOBAL_QUOTE"
            f"&symbol={symbol}"
            f"&apikey={api_key}"
        )

        response = requests.get(
            url,
            timeout=15
        )

        response.raise_for_status()

        data = response.json()

        return data

    except requests.RequestException as e:

        return {
            "error": f"Stock API request failed: {str(e)}"
        }

    except Exception as e:

        return {
            "error": str(e)
        }


# ============================================================
# Bind Tools
# ============================================================

tools = [
    web_search,
    get_stock_price,
    calculator,
]

llm_with_tools = llm.bind_tools(tools)


# ============================================================
# Chat Node
# ============================================================

def chat_node(state: ChatState):

    messages = state["messages"]

    response = llm_with_tools.invoke(messages)

    return {
        "messages": [response]
    }


# ============================================================
# Tool Node
# ============================================================

tool_node = ToolNode(
    tools,
    handle_tool_errors=True
)


# ============================================================
# Checkpointer
# ============================================================

conn = sqlite3.connect(
    database="chatbot.db",
    check_same_thread=False
)

checkpointer = SqliteSaver(
    conn=conn
)


# ============================================================
# Graph
# ============================================================

graph = StateGraph(ChatState)

# Nodes
graph.add_node(
    "chat_node",
    chat_node
)

graph.add_node(
    "tools",
    tool_node
)


# START → chat_node
graph.add_edge(
    START,
    "chat_node"
)


# chat_node → tools OR END
graph.add_conditional_edges(
    "chat_node",
    tools_condition
)


# tools → chat_node
graph.add_edge(
    "tools",
    "chat_node"
)


# Compile
chatbot = graph.compile(
    checkpointer=checkpointer
)


# ============================================================
# Retrieve Threads
# ============================================================

def retrieve_all_threads():

    all_threads = set()

    for checkpoint in checkpointer.list(None):

        thread_id = (
            checkpoint.config
            .get("configurable", {})
            .get("thread_id")
        )

        if thread_id:
            all_threads.add(
                str(thread_id)
            )

    return list(all_threads)