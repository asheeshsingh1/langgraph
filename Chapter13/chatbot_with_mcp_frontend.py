import queue
import uuid

import streamlit as st

from chatbot_with_mcp_backend import (
    chatbot,
    retrieve_all_threads,
    submit_async_task,
    run_async,
)

from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    AIMessageChunk,
    ToolMessage,
)


# ============================================================
# Page configuration
# ============================================================

st.set_page_config(
    page_title="LangGraph MCP Chatbot",
    page_icon="🤖",
    layout="wide",
)


# ============================================================
# Helpers
# ============================================================

def extract_text(content):

    if isinstance(content, str):
        return content

    if isinstance(content, list):

        text = ""

        for block in content:

            if isinstance(block, dict):

                if block.get("type") == "text":

                    text += block.get(
                        "text",
                        "",
                    )

        return text

    return str(content)


# ============================================================
# Thread utilities
# ============================================================

def generate_thread_id():

    return str(
        uuid.uuid4()
    )


def add_thread(thread_id):

    if thread_id not in st.session_state[
        "chat_threads"
    ]:

        st.session_state[
            "chat_threads"
        ].append(
            thread_id
        )


# ============================================================
# Reset chat
# ============================================================

def reset_chat():

    thread_id = generate_thread_id()

    st.session_state[
        "thread_id"
    ] = thread_id

    add_thread(
        thread_id
    )

    st.session_state[
        "message_history"
    ] = []


# ============================================================
# Load conversation from LangGraph
# ============================================================

async def _get_conversation(thread_id):

    state = await chatbot.aget_state(
        config={
            "configurable": {
                "thread_id": thread_id
            }
        }
    )

    return state.values.get(
        "messages",
        []
    )


def load_conversation(thread_id):

    messages = run_async(
        _get_conversation(
            thread_id
        )
    )

    visible_messages = []

    for msg in messages:

        # ====================================================
        # USER
        # ====================================================

        if isinstance(
            msg,
            HumanMessage,
        ):

            content = extract_text(
                msg.content
            )

            if content:

                visible_messages.append(
                    {
                        "role": "user",
                        "content": content,
                    }
                )


        # ====================================================
        # AI
        # ====================================================

        elif isinstance(
            msg,
            AIMessage,
        ):

            # Ignore tool-call AI messages
            if getattr(
                msg,
                "tool_calls",
                None,
            ):
                continue

            content = extract_text(
                msg.content
            )

            if not content:
                continue

            visible_messages.append(
                {
                    "role": "assistant",
                    "content": content,
                }
            )


        # ====================================================
        # TOOL
        # ====================================================

        elif isinstance(
            msg,
            ToolMessage,
        ):

            # Tool messages are internal.
            continue


    return visible_messages


# ============================================================
# Session state
# ============================================================

if "thread_id" not in st.session_state:

    st.session_state[
        "thread_id"
    ] = generate_thread_id()


if "chat_threads" not in st.session_state:

    st.session_state[
        "chat_threads"
    ] = retrieve_all_threads()


if "message_history" not in st.session_state:

    st.session_state[
        "message_history"
    ] = load_conversation(
        st.session_state[
            "thread_id"
        ]
    )


add_thread(
    st.session_state[
        "thread_id"
    ]
)


# ============================================================
# Sidebar
# ============================================================

st.sidebar.title(
    "LangGraph MCP Chatbot"
)


if st.sidebar.button(
    "New Chat"
):

    reset_chat()

    st.rerun()


st.sidebar.header(
    "My Conversations"
)


for thread_id in st.session_state[
    "chat_threads"
][::-1]:

    if st.sidebar.button(
        str(thread_id),
        key=f"thread_{thread_id}",
    ):

        st.session_state[
            "thread_id"
        ] = thread_id

        st.session_state[
            "message_history"
        ] = load_conversation(
            thread_id
        )

        st.rerun()


# ============================================================
# Render conversation history
# ============================================================

for message in st.session_state[
    "message_history"
]:

    with st.chat_message(
        message["role"]
    ):

        st.markdown(
            message["content"]
        )


# ============================================================
# Chat input
# ============================================================

user_input = st.chat_input(
    "Ask anything"
)


# ============================================================
# New message
# ============================================================

if user_input:

    # --------------------------------------------------------
    # IMPORTANT
    #
    # Do NOT append the user message to message_history here.
    #
    # LangGraph/SQLite will become the source of truth.
    # --------------------------------------------------------

    # --------------------------------------------------------
    # Render current user message ONCE
    # --------------------------------------------------------

    with st.chat_message(
        "user"
    ):

        st.markdown(
            user_input
        )


    # ========================================================
    # LangSmith configuration
    # ========================================================

    thread_id = str(
        st.session_state[
            "thread_id"
        ]
    )

    CONFIG = {

        "configurable": {

            "thread_id": thread_id,

        },

        "metadata": {

            "application": (
                "langgraph-mcp-chatbot"
            ),

            "environment": (
                "development"
            ),

            "thread_id": thread_id,

        },

        "tags": [

            "langgraph",
            "mcp",
            "chatbot",
            "tools",

        ],

        "run_name": (
            "LangGraph MCP Chat"
        ),

    }


    # ========================================================
    # Assistant
    # ========================================================

    with st.chat_message(
        "assistant"
    ):

        status_holder = {
            "box": None
        }


        # ----------------------------------------------------
        # Async stream
        # ----------------------------------------------------

        def ai_only_stream():

            event_queue = queue.Queue()


            async def run_stream():

                try:

                    async for (
                        message_chunk,
                        metadata,
                    ) in chatbot.astream(

                        {
                            "messages": [
                                HumanMessage(
                                    content=user_input
                                )
                            ]
                        },

                        config=CONFIG,

                        stream_mode="messages",

                    ):

                        event_queue.put(
                            (
                                "message",
                                message_chunk,
                                metadata,
                            )
                        )


                except Exception as exc:

                    event_queue.put(
                        (
                            "error",
                            exc,
                            None,
                        )
                    )


                finally:

                    event_queue.put(
                        (
                            "done",
                            None,
                            None,
                        )
                    )


            submit_async_task(
                run_stream()
            )


            # ------------------------------------------------
            # Consume events
            # ------------------------------------------------

            while True:

                event = event_queue.get()

                event_type = event[0]


                # ============================================
                # Done
                # ============================================

                if event_type == "done":

                    break


                # ============================================
                # Error
                # ============================================

                if event_type == "error":

                    raise event[1]


                message_chunk = event[1]


                # ============================================
                # Tool
                # ============================================

                if isinstance(
                    message_chunk,
                    ToolMessage,
                ):

                    tool_name = getattr(
                        message_chunk,
                        "name",
                        "tool",
                    )


                    if status_holder[
                        "box"
                    ] is None:

                        status_holder[
                            "box"
                        ] = st.status(

                            f"🔧 Using `{tool_name}`...",

                            expanded=True,

                        )

                    else:

                        status_holder[
                            "box"
                        ].update(

                            label=(
                                f"🔧 Using `{tool_name}`..."
                            ),

                            state="running",

                            expanded=True,

                        )


                    # Never render tool output
                    continue


                # ============================================
                # AI
                # ============================================

                if isinstance(
                    message_chunk,
                    (
                        AIMessage,
                        AIMessageChunk,
                    ),
                ):

                    # Ignore tool-call messages
                    if getattr(
                        message_chunk,
                        "tool_calls",
                        None,
                    ):

                        continue


                    text = extract_text(
                        getattr(
                            message_chunk,
                            "content",
                            "",
                        )
                    )


                    # Ignore empty chunks
                    if not text:

                        continue


                    yield text


        # ----------------------------------------------------
        # Stream
        # ----------------------------------------------------

        try:

            ai_message = st.write_stream(
                ai_only_stream()
            )

        except Exception as e:

            st.error(
                f"Something went wrong: {e}"
            )

            ai_message = ""


        # ----------------------------------------------------
        # Complete tool status
        # ----------------------------------------------------

        if status_holder[
            "box"
        ] is not None:

            status_holder[
                "box"
            ].update(

                label="✅ Tool finished",

                state="complete",

                expanded=False,

            )


    # ========================================================
    # IMPORTANT
    #
    # DO NOT manually append the response to
    # message_history.
    #
    # Instead reload the conversation from LangGraph.
    # ========================================================

    st.session_state[
        "message_history"
    ] = load_conversation(
        thread_id
    )