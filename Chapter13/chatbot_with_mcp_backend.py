import os
import asyncio
import threading
import requests
import aiosqlite

from dotenv import load_dotenv
from typing import TypedDict, Annotated

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage
from langchain_core.tools import tool, BaseTool
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_mcp_adapters.client import MultiServerMCPClient

from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver


# ============================================================
# Environment
# ============================================================

load_dotenv()


# ============================================================
# Dedicated Async Event Loop
# ============================================================

_ASYNC_LOOP = asyncio.new_event_loop()

_ASYNC_THREAD = threading.Thread(
    target=_ASYNC_LOOP.run_forever,
    daemon=True,
)

_ASYNC_THREAD.start()


def _submit_async(coro):
    return asyncio.run_coroutine_threadsafe(
        coro,
        _ASYNC_LOOP,
    )


def run_async(coro):
    """
    Execute a coroutine on the dedicated async event loop
    and wait for its result.
    """

    return _submit_async(coro).result()


def submit_async_task(coro):
    """
    Submit a coroutine to the dedicated async event loop
    without blocking the caller.
    """

    return _submit_async(coro)


# ============================================================
# LLM
# ============================================================

llm = ChatOpenAI()


# ============================================================
# Tools
# ============================================================

# ------------------------------------------------------------
# DuckDuckGo Search
# ------------------------------------------------------------

search_tool = DuckDuckGoSearchRun(
    region="us-en",
)


@tool
def web_search(query: str) -> str:
    """
    Search the web for current information.
    """

    try:
        result = search_tool.invoke(query)

        if not result:
            return "No search results found."

        return result

    except Exception as e:
        # Do not crash the entire graph if the
        # external search service has a DNS/network issue.
        return (
            "Web search failed. "
            "Please answer using available knowledge if possible. "
            f"Error: {str(e)}"
        )


# ------------------------------------------------------------
# Stock Price
# ------------------------------------------------------------

@tool
def get_stock_price(symbol: str) -> dict:
    """
    Fetch the latest stock price for a stock symbol
    using Alpha Vantage.

    Examples:
        AAPL
        TSLA
        MSFT
    """

    api_key = os.getenv(
        "STOCK_MARKET_API_KEY"
    )

    if not api_key:
        return {
            "error": (
                "STOCK_MARKET_API_KEY "
                "is not configured."
            )
        }

    try:

        url = (
            "https://www.alphavantage.co/query"
            "?function=GLOBAL_QUOTE"
            f"&symbol={symbol}"
            f"&apikey={api_key}"
        )

        response = requests.get(
            url,
            timeout=15,
        )

        response.raise_for_status()

        return response.json()

    except requests.RequestException as e:

        return {
            "error": (
                f"Stock API request failed: {str(e)}"
            )
        }

    except Exception as e:

        return {
            "error": str(e)
        }


# ============================================================
# MCP
# ============================================================

client = MultiServerMCPClient(
    {
        "expense": {
            "transport": "http",
            "url": "https://asheesh.fastmcp.app/mcp",
            "headers": {
                "Authorization": (
                    f"Bearer "
                    f"{os.environ['FASTMCP_CLOUD_TOKEN']}"
                ),
            },
        }
    }
)


def load_mcp_tools() -> list[BaseTool]:

    try:

        return run_async(
            client.get_tools()
        )

    except Exception as e:

        print(
            f"Failed to load MCP tools: {e}"
        )

        return []


mcp_tools = load_mcp_tools()


# ============================================================
# All Tools
# ============================================================

tools = [
    web_search,
    get_stock_price,
    *mcp_tools,
]


# ============================================================
# LLM + Tools
# ============================================================

llm_with_tools = llm.bind_tools(
    tools
)


# ============================================================
# State
# ============================================================

class ChatState(TypedDict):

    messages: Annotated[
        list[BaseMessage],
        add_messages,
    ]


# ============================================================
# Chat Node
# ============================================================

async def chat_node(
    state: ChatState,
):

    messages = state["messages"]

    response = await llm_with_tools.ainvoke(
        messages
    )

    return {
        "messages": [
            response
        ]
    }


# ============================================================
# Tool Node
# ============================================================

tool_node = ToolNode(
    tools,
    handle_tool_errors=True,
)


# ============================================================
# Async SQLite Checkpointer
# ============================================================

async def _init_checkpointer():

    conn = await aiosqlite.connect(
        "chatbot.db"
    )

    return AsyncSqliteSaver(
        conn
    )


checkpointer = run_async(
    _init_checkpointer()
)


# ============================================================
# Graph
# ============================================================

graph = StateGraph(
    ChatState
)


# ------------------------------------------------------------
# Nodes
# ------------------------------------------------------------

graph.add_node(
    "chat_node",
    chat_node,
)

graph.add_node(
    "tools",
    tool_node,
)


# ------------------------------------------------------------
# START → chat_node
# ------------------------------------------------------------

graph.add_edge(
    START,
    "chat_node",
)


# ------------------------------------------------------------
# chat_node → tools OR END
# ------------------------------------------------------------

graph.add_conditional_edges(
    "chat_node",
    tools_condition,
)


# ------------------------------------------------------------
# tools → chat_node
# ------------------------------------------------------------

graph.add_edge(
    "tools",
    "chat_node",
)


# ------------------------------------------------------------
# Compile
# ------------------------------------------------------------

chatbot = graph.compile(
    checkpointer=checkpointer,
)


# ============================================================
# Retrieve All Threads
# ============================================================

async def _alist_threads():

    all_threads = set()

    async for checkpoint in checkpointer.alist(
        None
    ):

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


def retrieve_all_threads():

    return run_async(
        _alist_threads()
    )