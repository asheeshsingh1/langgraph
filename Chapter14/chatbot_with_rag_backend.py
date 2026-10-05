import os
import asyncio
import tempfile
import threading
from typing import Annotated, Any, Dict, Optional, TypedDict

import aiosqlite
import requests
from dotenv import load_dotenv

from langchain_classic.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.vectorstores import FAISS

from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool, BaseTool, InjectedToolArg

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

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


# ============================================================
# PDF Retriever Store
# ============================================================

# Stores one retriever per chat thread.
#
# Example:
#
# {
#     "abc123": <FAISS retriever>,
#     "xyz456": <FAISS retriever>,
# }
#
_THREAD_RETRIEVERS: Dict[str, Any] = {}

_THREAD_METADATA: Dict[str, dict] = {}


# ============================================================
# Embeddings
# ============================================================

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small"
)


# ============================================================
# Retriever Helpers
# ============================================================

def _get_retriever(
    thread_id: Optional[str],
):
    """
    Fetch the retriever associated with a chat thread.
    """

    if not thread_id:
        return None

    return _THREAD_RETRIEVERS.get(
        str(thread_id)
    )


# ============================================================
# PDF Ingestion
# ============================================================

def ingest_pdf(
    file_bytes: bytes,
    thread_id: str,
    filename: Optional[str] = None,
) -> dict:
    """
    Build a FAISS retriever for the uploaded PDF
    and associate it with the current chat thread.

    Parameters
    ----------
    file_bytes:
        Raw PDF bytes.

    thread_id:
        LangGraph conversation/thread ID.

    filename:
        Original uploaded filename.

    Returns
    -------
    dict
        Metadata about the indexed document.
    """

    if not file_bytes:
        raise ValueError(
            "No bytes received for ingestion."
        )

    if not thread_id:
        raise ValueError(
            "thread_id is required for PDF ingestion."
        )

    thread_id = str(thread_id)

    temp_path = None

    try:

        # ----------------------------------------------------
        # Create temporary PDF
        # ----------------------------------------------------

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".pdf",
        ) as temp_file:

            temp_file.write(file_bytes)

            temp_path = temp_file.name

        # ----------------------------------------------------
        # Load PDF
        # ----------------------------------------------------

        loader = PyPDFLoader(
            temp_path
        )

        docs = loader.load()

        if not docs:
            raise ValueError(
                "No pages could be extracted from the PDF."
            )

        # ----------------------------------------------------
        # Split documents into chunks
        # ----------------------------------------------------

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=[
                "\n\n",
                "\n",
                " ",
                "",
            ],
        )

        chunks = splitter.split_documents(
            docs
        )

        if not chunks:
            raise ValueError(
                "No text chunks could be created from the PDF."
            )

        # ----------------------------------------------------
        # Build FAISS index
        # ----------------------------------------------------

        vector_store = FAISS.from_documents(
            chunks,
            embeddings,
        )

        # ----------------------------------------------------
        # Create retriever
        # ----------------------------------------------------

        retriever = vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={
                "k": 8,
            },
        )

        # ----------------------------------------------------
        # Store retriever for this thread
        # ----------------------------------------------------

        _THREAD_RETRIEVERS[
            thread_id
        ] = retriever

        # ----------------------------------------------------
        # Store document metadata
        # ----------------------------------------------------

        _THREAD_METADATA[
            thread_id
        ] = {
            "filename": (
                filename
                or os.path.basename(temp_path)
            ),
            "documents": len(docs),
            "chunks": len(chunks),
        }

        return {
            "filename": (
                filename
                or os.path.basename(temp_path)
            ),
            "documents": len(docs),
            "chunks": len(chunks),
        }

    finally:

        # ----------------------------------------------------
        # Remove temporary PDF
        # ----------------------------------------------------

        if temp_path:

            try:
                os.remove(temp_path)

            except OSError:
                pass


# ============================================================
# Async Helpers
# ============================================================

def _submit_async(coro):

    return asyncio.run_coroutine_threadsafe(
        coro,
        _ASYNC_LOOP,
    )


def run_async(coro):
    """
    Execute a coroutine on the dedicated event loop
    and wait for its result.
    """

    return _submit_async(
        coro
    ).result()


def submit_async_task(coro):
    """
    Submit a coroutine to the dedicated async event loop
    without blocking the caller.
    """

    return _submit_async(
        coro
    )


# ============================================================
# LLM
# ============================================================

llm = ChatOpenAI()


# ============================================================
# Tools
# ============================================================


# ============================================================
# DuckDuckGo Search
# ============================================================

search_tool = DuckDuckGoSearchRun(
    region="us-en",
)


@tool
def web_search(
    query: str,
) -> str:
    """
    Search the web for current information.

    Use this tool when the user asks about
    recent or current information that may not
    be available in the model's knowledge.
    """

    try:

        result = search_tool.invoke(
            query
        )

        if not result:
            return "No search results found."

        return result

    except Exception as e:

        return (
            "Web search failed. "
            "Please answer using available knowledge "
            "if possible. "
            f"Error: {str(e)}"
        )


# ============================================================
# Stock Price
# ============================================================

@tool
def get_stock_price(
    symbol: str,
) -> dict:
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
# RAG Tool
# ============================================================

@tool
def rag_tool(
    query: str,
    config: Annotated[
        RunnableConfig,
        InjectedToolArg,
    ],
) -> dict:
    """
    Search the currently uploaded PDF for information
    relevant to the user's question.

    The current LangGraph thread_id is injected automatically.
    The LLM does NOT need to provide thread_id.
    """

    # --------------------------------------------------------
    # Get current LangGraph thread ID
    # --------------------------------------------------------

    configurable = config.get(
        "configurable",
        {},
    )

    thread_id = configurable.get(
        "thread_id"
    )

    # --------------------------------------------------------
    # Validate thread ID
    # --------------------------------------------------------

    if not thread_id:

        return {
            "error": (
                "Unable to determine the current "
                "chat thread."
            ),
            "query": query,
        }

    thread_id = str(
        thread_id
    )

    # --------------------------------------------------------
    # Get retriever
    # --------------------------------------------------------

    retriever = _get_retriever(
        thread_id
    )

    if retriever is None:

        return {
            "error": (
                "No PDF is indexed for the current "
                "chat thread. Please upload a PDF first."
            ),
            "query": query,
            "thread_id": thread_id,
        }

    # --------------------------------------------------------
    # Retrieve relevant documents
    # --------------------------------------------------------

    try:

        documents = retriever.invoke(
            query
        )

        # ----------------------------------------------------
        # No results
        # ----------------------------------------------------

        if not documents:

            return {
                "query": query,
                "context": [],
                "metadata": [],
                "source_file": (
                    _THREAD_METADATA
                    .get(thread_id, {})
                    .get("filename")
                ),
                "message": (
                    "No relevant information was found "
                    "in the uploaded document."
                ),
            }

        # ----------------------------------------------------
        # Extract context
        # ----------------------------------------------------

        context = [
            doc.page_content
            for doc in documents
        ]

        # ----------------------------------------------------
        # Extract metadata
        # ----------------------------------------------------

        metadata = [
            doc.metadata
            for doc in documents
        ]

        # ----------------------------------------------------
        # Return RAG result
        # ----------------------------------------------------

        return {
            "query": query,
            "context": context,
            "metadata": metadata,
            "source_file": (
                _THREAD_METADATA
                .get(thread_id, {})
                .get("filename")
            ),
        }

    except Exception as e:

        return {
            "error": (
                f"Document retrieval failed: {str(e)}"
            ),
            "query": query,
            "thread_id": thread_id,
        }


# ============================================================
# MCP
# ============================================================

mcp_tools: list[BaseTool] = []


def _create_mcp_client():
    """
    Create the MCP client only when the required
    authentication token is available.
    """

    token = os.getenv(
        "FASTMCP_CLOUD_TOKEN"
    )

    if not token:

        print(
            "FASTMCP_CLOUD_TOKEN is not configured. "
            "Skipping MCP tools."
        )

        return None

    return MultiServerMCPClient(
        {
            "expense": {
                "transport": "http",
                "url": (
                    "https://asheesh.fastmcp.app/mcp"
                ),
                "headers": {
                    "Authorization": (
                        f"Bearer {token}"
                    ),
                },
            }
        }
    )


client = _create_mcp_client()


def load_mcp_tools() -> list[BaseTool]:
    """
    Load tools exposed by the MCP server.
    """

    if client is None:
        return []

    try:

        loaded_tools = run_async(
            client.get_tools()
        )

        print(
            f"Loaded {len(loaded_tools)} MCP tools."
        )

        return loaded_tools

    except Exception as e:

        print(
            f"Failed to load MCP tools: {e}"
        )

        return []


mcp_tools = load_mcp_tools()


# ============================================================
# All Tools
# ============================================================

tools: list[BaseTool] = [
    web_search,
    get_stock_price,
    rag_tool,
    *mcp_tools,
]


print(
    "Registered tools:",
    [
        getattr(
            tool_item,
            "name",
            str(tool_item),
        )
        for tool_item in tools
    ],
)


# ============================================================
# LLM With Tools
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

    messages = state[
        "messages"
    ]

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


# ============================================================
# Nodes
# ============================================================

graph.add_node(
    "chat_node",
    chat_node,
)

graph.add_node(
    "tools",
    tool_node,
)


# ============================================================
# START → chat_node
# ============================================================

graph.add_edge(
    START,
    "chat_node",
)


# ============================================================
# chat_node → tools OR END
# ============================================================

graph.add_conditional_edges(
    "chat_node",
    tools_condition,
)


# ============================================================
# tools → chat_node
# ============================================================

graph.add_edge(
    "tools",
    "chat_node",
)


# ============================================================
# Compile Graph
# ============================================================

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
            .get(
                "configurable",
                {},
            )
            .get(
                "thread_id"
            )
        )

        if thread_id:

            all_threads.add(
                str(thread_id)
            )

    return list(
        all_threads
    )


def retrieve_all_threads():

    return run_async(
        _alist_threads()
    )


# ============================================================
# Thread / Document Helpers
# ============================================================

def thread_has_document(
    thread_id: str,
) -> bool:

    return (
        str(thread_id)
        in _THREAD_RETRIEVERS
    )


def thread_document_metadata(
    thread_id: str,
) -> dict:

    return _THREAD_METADATA.get(
        str(thread_id),
        {},
    )