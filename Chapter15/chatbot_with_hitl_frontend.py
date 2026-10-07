import queue
import uuid
import streamlit as st
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    HumanMessage,
    ToolMessage,
)


from chatbot_with_hitl_backend import (
    chatbot,
    ingest_pdf,
    retrieve_all_threads,
    thread_document_metadata,
    run_async,
    submit_async_task,
    get_pending_interrupt,
    resume_chat,
)

# ============================================================

# Page Configuration

# ============================================================


st.set_page_config(
    page_title="LangGraph HITL Chatbot",
    page_icon="📚",
    layout="wide",
)


# ============================================================

# Utilities

# ============================================================


def generate_thread_id():

    return str(uuid.uuid4())


def extract_text(content):
    """

    Extract text from LangChain message content.



    Supports:

    - str

    - list[dict]

    - other content types

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
                        "",
                    )

        return text

    return str(content)


# ============================================================

# Thread Utilities

# ============================================================


def add_thread(thread_id):

    thread_id = str(thread_id)

    if thread_id not in st.session_state["chat_threads"]:

        st.session_state["chat_threads"].append(thread_id)


def reset_chat():

    thread_id = generate_thread_id()

    st.session_state["pending_approval"] = None

    st.session_state["thread_id"] = thread_id

    add_thread(thread_id)


# ============================================================

# Async Conversation Loader

# ============================================================


async def _load_conversation_async(thread_id):

    state = await chatbot.aget_state(
        config={"configurable": {"thread_id": str(thread_id)}}
    )

    return state.values.get("messages", [])


def load_conversation(thread_id):

    return run_async(_load_conversation_async(thread_id))


# ============================================================

# Convert LangGraph Messages -> UI Messages

# ============================================================


def get_visible_messages(thread_id):

    messages = load_conversation(thread_id)

    visible_messages = []

    for message in messages:

        # ====================================================

        # HUMAN MESSAGE

        # ====================================================

        if isinstance(
            message,
            HumanMessage,
        ):

            content = extract_text(message.content)

            if content:

                visible_messages.append(
                    {
                        "role": "user",
                        "content": content,
                    }
                )

            continue

        # ====================================================

        # AI MESSAGE

        # ====================================================

        if isinstance(
            message,
            AIMessage,
        ):

            # ------------------------------------------------

            # Ignore AI messages whose purpose was only

            # requesting a tool.

            # ------------------------------------------------

            if getattr(
                message,
                "tool_calls",
                None,
            ):

                continue

            content = extract_text(message.content)

            # ------------------------------------------------

            # Ignore empty AI messages.

            # ------------------------------------------------

            if not content:

                continue

            visible_messages.append(
                {
                    "role": "assistant",
                    "content": content,
                }
            )

            continue

        # ====================================================

        # TOOL MESSAGE

        # ====================================================

        if isinstance(
            message,
            ToolMessage,
        ):

            # ------------------------------------------------

            # Tool results are internal LangGraph messages.

            #

            # Do NOT display these in chat history.

            # ------------------------------------------------

            continue

    return visible_messages


# ============================================================

# Session State Initialization

# ============================================================


if "thread_id" not in st.session_state:

    st.session_state["thread_id"] = generate_thread_id()


if "chat_threads" not in st.session_state:

    st.session_state["chat_threads"] = retrieve_all_threads()


if "ingested_docs" not in st.session_state:

    st.session_state["ingested_docs"] = {}


if "pending_approval" not in st.session_state:

    st.session_state["pending_approval"] = None


# Make sure current thread exists

add_thread(st.session_state["thread_id"])


# ============================================================

# Current Thread

# ============================================================


thread_key = str(st.session_state["thread_id"])


# Restore any persisted HITL request for this thread.
pending_approval = get_pending_interrupt(thread_key)

st.session_state["pending_approval"] = pending_approval


thread_docs = st.session_state["ingested_docs"].setdefault(
    thread_key,
    {},
)


# ============================================================

# Sidebar

# ============================================================


st.sidebar.title("LangGraph Chatbot")


st.sidebar.markdown(f"**Thread ID:** `{thread_key}`")


# ============================================================

# New Chat

# ============================================================


if st.sidebar.button(
    "New Chat",
    use_container_width=True,
):

    reset_chat()

    st.rerun()


# ============================================================

# Current Document

# ============================================================


if thread_docs:

    latest_doc = list(thread_docs.values())[-1]

    st.sidebar.success(
        f"Using `{latest_doc.get('filename')}` "
        f"({latest_doc.get('chunks')} chunks "
        f"from {latest_doc.get('documents')} pages)"
    )


else:

    st.sidebar.info("No PDF indexed yet.")


# ============================================================

# PDF Upload

# ============================================================


uploaded_pdf = st.sidebar.file_uploader(
    "Upload a PDF for this chat",
    type=["pdf"],
)


if uploaded_pdf:

    if uploaded_pdf.name in thread_docs:

        st.sidebar.info(f"`{uploaded_pdf.name}` " "already processed for this chat.")

    else:

        with st.sidebar.status(
            "Indexing PDF...",
            expanded=True,
        ) as status_box:

            try:

                summary = ingest_pdf(
                    uploaded_pdf.getvalue(),
                    thread_id=thread_key,
                    filename=uploaded_pdf.name,
                )

                thread_docs[uploaded_pdf.name] = summary

                status_box.update(
                    label="✅ PDF indexed",
                    state="complete",
                    expanded=False,
                )

            except Exception as exc:

                status_box.update(
                    label="❌ PDF indexing failed",
                    state="error",
                    expanded=True,
                )

                st.sidebar.error(str(exc))


# ============================================================

# Past Conversations

# ============================================================


st.sidebar.subheader("Past conversations")


threads = st.session_state["chat_threads"][::-1]


if not threads:

    st.sidebar.write("No past conversations yet.")


else:

    for thread_id in threads:

        if st.sidebar.button(
            str(thread_id),
            key=f"side-thread-{thread_id}",
            use_container_width=True,
        ):

            st.session_state["thread_id"] = str(thread_id)

            st.session_state["ingested_docs"].setdefault(
                str(thread_id),
                {},
            )

            # ------------------------------------------------

            # IMPORTANT

            #

            # Immediately rerun so the new thread is rendered

            # from the beginning of the script.

            # ------------------------------------------------

            st.rerun()


# ============================================================

# Main UI

# ============================================================


st.title("Multi Utility Chatbot")


# ============================================================

# Load Conversation From LangGraph

# ============================================================


message_history = get_visible_messages(thread_key)


# ============================================================

# Render Existing Conversation

# ============================================================


for message in message_history:

    with st.chat_message(message["role"]):

        st.markdown(message["content"])


# ============================================================

# Document Metadata

# ============================================================


doc_meta = thread_document_metadata(thread_key)


if doc_meta:

    st.caption(
        f"📄 Document indexed: "
        f"{doc_meta.get('filename')} "
        f"(chunks: {doc_meta.get('chunks')}, "
        f"pages: {doc_meta.get('documents')})"
    )


# ============================================================
# Human-in-the-Loop Email Approval
# ============================================================

pending_approval = st.session_state.get("pending_approval")

if pending_approval:
    if pending_approval.get("type") == "email_confirmation":
        st.warning("⏸️ Email approval required before sending")

        st.markdown(
            pending_approval.get(
                "message",
                "Please review the email before sending.",
            )
        )

        col1, col2 = st.columns(2)

        with col1:
            st.text_input(
                "To",
                value=pending_approval.get("to", ""),
                disabled=True,
            )

        with col2:
            st.text_input(
                "Subject",
                value=pending_approval.get("subject", ""),
                disabled=True,
            )

        st.text_area(
            "Email body",
            value=pending_approval.get("content", ""),
            height=220,
            disabled=True,
        )

        approve_col, reject_col = st.columns(2)

        with approve_col:
            approve_email = st.button(
                "✅ Send Email",
                type="primary",
                use_container_width=True,
            )

        with reject_col:
            reject_email = st.button(
                "❌ Cancel",
                use_container_width=True,
            )

        if approve_email:
            with st.spinner("Sending email..."):
                resume_chat(
                    thread_key,
                    approved=True,
                )

            st.session_state["pending_approval"] = None

            st.rerun()

        if reject_email:
            with st.spinner("Cancelling email..."):
                resume_chat(
                    thread_key,
                    approved=False,
                )

            st.session_state["pending_approval"] = None

            st.rerun()

    else:
        st.warning(
            "A human approval request is waiting, "
            "but its format is not supported by this UI."
        )


# ============================================================
# Chat Input
# ============================================================


user_input = st.chat_input(
    "Ask about your document or use tools",
    disabled=bool(pending_approval),
)

if user_input:

    # ========================================================

    # Render USER message

    #

    # DO NOT add it to session_state.

    # LangGraph will persist it.

    # ========================================================

    with st.chat_message("user"):

        st.markdown(user_input)

    # ========================================================

    # LangSmith / LangGraph Config

    # ========================================================

    CONFIG = {
        "configurable": {
            "thread_id": thread_key,
        },
        "metadata": {
            "application": ("langgraph-hitl-chatbot"),
            "environment": ("development"),
            "thread_id": thread_key,
        },
        "tags": [
            "langgraph",
            "rag",
            "pdf",
            "chatbot",
            "tools",
            "hitl"
        ],
        "run_name": ("LangGraph Chatbot HITL"),
    }

    # ========================================================

    # Assistant Message

    # ========================================================

    with st.chat_message("assistant"):

        status_holder = {"box": None}

        # ====================================================

        # Async LangGraph Stream

        # ====================================================

        def ai_only_stream():

            event_queue = queue.Queue()

            async def run_stream():

                try:

                    async for (
                        message_chunk,
                        metadata,
                    ) in chatbot.astream(
                        {"messages": [HumanMessage(content=user_input)]},
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

            # ------------------------------------------------

            # Run async graph on backend event loop

            # ------------------------------------------------

            submit_async_task(run_stream())

            # ------------------------------------------------

            # Consume events synchronously so Streamlit can

            # update the UI.

            # ------------------------------------------------

            while True:

                event_type, message_chunk, metadata = event_queue.get()

                # ============================================

                # Finished

                # ============================================

                if event_type == "done":

                    break

                # ============================================

                # Error

                # ============================================

                if event_type == "error":

                    raise message_chunk

                # ============================================

                # Tool Message

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

                    if status_holder["box"] is None:

                        status_holder["box"] = st.status(
                            f"🔧 Using `{tool_name}`...",
                            expanded=True,
                        )

                    else:

                        status_holder["box"].update(
                            label=(f"🔧 Using `{tool_name}`..."),
                            state="running",
                            expanded=True,
                        )

                    # ----------------------------------------

                    # Never display tool output.

                    # ----------------------------------------

                    continue

                # ============================================

                # AI Message / AI Message Chunk

                # ============================================

                if isinstance(
                    message_chunk,
                    (
                        AIMessage,
                        AIMessageChunk,
                    ),
                ):

                    # ----------------------------------------

                    # Ignore AI tool-call messages.

                    # ----------------------------------------

                    if getattr(
                        message_chunk,
                        "tool_calls",
                        None,
                    ):

                        continue

                    # ----------------------------------------

                    # Extract text.

                    # ----------------------------------------

                    text = extract_text(
                        getattr(
                            message_chunk,
                            "content",
                            "",
                        )
                    )

                    # ----------------------------------------

                    # Ignore empty chunks.

                    # ----------------------------------------

                    if not text:

                        continue

                    yield text

        # ====================================================

        # Stream response into Streamlit

        # ====================================================

        try:

            ai_message = st.write_stream(ai_only_stream())

        except Exception as exc:

            st.error(f"Something went wrong: {exc}")

            ai_message = ""

        # ====================================================

        # Check for a pending HITL interrupt.
        pending_approval = get_pending_interrupt(thread_key)

        if pending_approval:
            st.session_state["pending_approval"] = pending_approval

            st.rerun()

        # Finish Tool Status

        # ====================================================

        if status_holder["box"] is not None:

            status_holder["box"].update(
                label="✅ Tool finished",
                state="complete",
                expanded=False,
            )

    # ========================================================

    # IMPORTANT

    #

    # DO NOT:

    #

    # st.session_state["message_history"].append(...)

    #

    # The response is already persisted by LangGraph.

    # ========================================================
