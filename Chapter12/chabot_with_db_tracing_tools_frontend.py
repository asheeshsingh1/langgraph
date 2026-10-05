import uuid

import streamlit as st

from chabot_with_db_tracing_tools_backend import (
    chatbot,
    retrieve_all_threads
)

from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    AIMessageChunk,
    ToolMessage,
)


# ============================================================
# Helper Functions
# ============================================================

def extract_text(content):
    """
    Extract textual content from LangChain message content.
    """

    if isinstance(content, str):
        return content

    if isinstance(content, list):

        text = ""

        for block in content:

            if isinstance(block, dict):

                if block.get("type") == "text":

                    text += block.get(
                        "text",
                        ""
                    )

        return text

    return str(content)


# ============================================================
# Thread Utilities
# ============================================================

def generate_thread_id():

    return str(
        uuid.uuid4()
    )


def add_thread(thread_id):

    if thread_id not in st.session_state["chat_threads"]:

        st.session_state["chat_threads"].append(
            thread_id
        )


def reset_chat():

    thread_id = generate_thread_id()

    st.session_state["thread_id"] = thread_id

    add_thread(thread_id)

    st.session_state["message_history"] = []


# ============================================================
# Load Conversation
# ============================================================

def load_conversation(thread_id):

    state = chatbot.get_state(
        config={
            "configurable": {
                "thread_id": thread_id
            }
        }
    )

    messages = state.values.get(
        "messages",
        []
    )

    visible_messages = []

    for msg in messages:

        # ----------------------------------------------------
        # User message
        # ----------------------------------------------------

        if isinstance(msg, HumanMessage):

            content = extract_text(
                msg.content
            )

            if content:

                visible_messages.append(
                    {
                        "role": "user",
                        "message": content
                    }
                )

        # ----------------------------------------------------
        # AI message
        # ----------------------------------------------------

        elif isinstance(
            msg,
            (AIMessage, AIMessageChunk)
        ):

            # Ignore AI messages that only contain
            # tool calls.
            if getattr(
                msg,
                "tool_calls",
                None
            ):
                continue

            content = extract_text(
                msg.content
            )

            if content:

                visible_messages.append(
                    {
                        "role": "assistant",
                        "message": content
                    }
                )

        # ----------------------------------------------------
        # ToolMessage
        # ----------------------------------------------------

        elif isinstance(
            msg,
            ToolMessage
        ):

            # NEVER display tool output directly
            # to the user.
            continue

    return visible_messages


# ============================================================
# Session State
# ============================================================

if "message_history" not in st.session_state:

    st.session_state["message_history"] = []


if "thread_id" not in st.session_state:

    st.session_state["thread_id"] = (
        generate_thread_id()
    )


if "chat_threads" not in st.session_state:

    st.session_state["chat_threads"] = (
        retrieve_all_threads()
    )


add_thread(
    st.session_state["thread_id"]
)


# ============================================================
# LangSmith Configuration
# ============================================================

CONFIG = {

    "configurable": {

        "thread_id": str(
            st.session_state["thread_id"]
        )

    },

    "metadata": {

        "application": "langgraph-chatbot",

        "environment": "development",

        "thread_id": str(
            st.session_state["thread_id"]
        )

    },

    "tags": [

        "langgraph",

        "chatbot",

        "tools"

    ],

    "run_name": "Langgraph Chatbot Stream"

}


# ============================================================
# Sidebar
# ============================================================

st.sidebar.title(
    "Langgraph Chatbot"
)


# ------------------------------------------------------------
# New Chat
# ------------------------------------------------------------

if st.sidebar.button(
    "New Chat"
):

    reset_chat()

    st.rerun()


# ------------------------------------------------------------
# Conversations
# ------------------------------------------------------------

st.sidebar.header(
    "My Conversations"
)


for thread in st.session_state[
    "chat_threads"
][::-1]:

    if st.sidebar.button(
        str(thread),
        key=f"thread_{thread}"
    ):

        st.session_state[
            "thread_id"
        ] = thread

        st.session_state[
            "message_history"
        ] = load_conversation(
            thread
        )

        st.rerun()


# ============================================================
# Display Existing Messages
# ============================================================

for message in st.session_state[
    "message_history"
]:

    with st.chat_message(
        message["role"]
    ):

        st.write(
            message["message"]
        )


# ============================================================
# Chat Input
# ============================================================

user_input = st.chat_input(
    "Ask anything"
)


# ============================================================
# Process User Message
# ============================================================

if user_input:

    # --------------------------------------------------------
    # Add user message to local history
    # --------------------------------------------------------

    st.session_state[
        "message_history"
    ].append(
        {
            "role": "user",
            "message": user_input
        }
    )


    # --------------------------------------------------------
    # Display user message
    # --------------------------------------------------------

    with st.chat_message("user"):

        st.write(
            user_input
        )


    # --------------------------------------------------------
    # AI response
    # --------------------------------------------------------

    with st.chat_message("assistant"):

        status_holder = {
            "box": None
        }


        def ai_only_stream():

            try:

                for message_chunk, metadata in chatbot.stream(

                    {
                        "messages": [
                            HumanMessage(
                                content=user_input
                            )
                        ]
                    },

                    config=CONFIG,

                    stream_mode="messages"

                ):

                    # ========================================
                    # Tool Message
                    # ========================================

                    if isinstance(
                        message_chunk,
                        ToolMessage
                    ):

                        tool_name = getattr(
                            message_chunk,
                            "name",
                            "tool"
                        )


                        if status_holder[
                            "box"
                        ] is None:

                            status_holder[
                                "box"
                            ] = st.status(

                                f"🔧 Using `{tool_name}`...",

                                expanded=True

                            )

                        else:

                            status_holder[
                                "box"
                            ].update(

                                label=(
                                    f"🔧 Using `{tool_name}`..."
                                ),

                                state="running",

                                expanded=True

                            )

                        # IMPORTANT:
                        # Do not yield ToolMessage content.
                        continue


                    # ========================================
                    # AI Message / AI Message Chunk
                    # ========================================

                    if isinstance(

                        message_chunk,

                        (
                            AIMessage,
                            AIMessageChunk
                        )

                    ):

                        # Ignore AI messages that are
                        # only making tool calls.
                        if getattr(
                            message_chunk,
                            "tool_calls",
                            None
                        ):
                            continue


                        text = extract_text(
                            message_chunk.content
                        )


                        # IMPORTANT:
                        # Don't create empty AI bubbles.
                        if text:

                            yield text


            except Exception as e:

                st.error(
                    f"Something went wrong: {str(e)}"
                )

                return


        # ----------------------------------------------------
        # Stream response
        # ----------------------------------------------------

        try:

            ai_message = st.write_stream(
                ai_only_stream()
            )

        finally:

            # ------------------------------------------------
            # Complete tool status
            # ------------------------------------------------

            if status_holder["box"] is not None:

                status_holder[
                    "box"
                ].update(

                    label="✅ Tool finished",

                    state="complete",

                    expanded=False

                )


    # ========================================================
    # Save Final AI Response
    # ========================================================

    if ai_message:

        st.session_state[
            "message_history"
        ].append(

            {
                "role": "assistant",
                "message": ai_message
            }

        )