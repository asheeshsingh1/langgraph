import uuid
import streamlit as st
from chatbot_with_db_backend import chatbot, retrieve_all_threads
from langchain_core.messages import HumanMessage, AIMessage

# Helper
def extract_text(content):
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text = ""

        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    text += block.get("text", "")

        return text

    return str(content)

# Utils
def generate_thread_id():
    thread_id = uuid.uuid4()
    return thread_id

def reset_chat():
    thread_id = generate_thread_id()
    st.session_state["thread_id"] = thread_id
    add_thread(st.session_state["thread_id"])
    st.session_state["message_history"] = []

def add_thread(thread_id):
    if thread_id not in st.session_state["chat_threads"]:
        st.session_state["chat_threads"].append(thread_id)

def load_conversation(thread_id):
    state = chatbot.get_state(config={'configurable': {'thread_id': thread_id}})
    # Check if messages key exists in state values, return empty list if not
    return state.values.get('messages', [])


# Message history injected in session state
if "message_history" not in st.session_state:
    st.session_state["message_history"] = []

if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = generate_thread_id()

if 'chat_threads' not in st.session_state:
    st.session_state['chat_threads'] = retrieve_all_threads()

add_thread(st.session_state["thread_id"])



# Configuration
CONFIG = {"configurable":{"thread_id":st.session_state["thread_id"]}}

# Sidebar UI
st.sidebar.title("Langgraph Chatbot")

if st.sidebar.button("New Chat"):
    reset_chat()

st.sidebar.header("My Conversation")

for thread in st.session_state["chat_threads"][::-1]:
    if st.sidebar.button(str(thread)):
        st.session_state['thread_id'] = thread
        messages = load_conversation(thread)

        temp_messages = []

        for msg in messages:
            if isinstance(msg, HumanMessage):
                role='user'
            else:
                role='assistant'
            temp_messages.append({'role': role, 'message': extract_text(msg.content)})

        st.session_state['message_history'] = temp_messages


# Chatbot UI
for message in st.session_state["message_history"]:
    with st.chat_message(message["role"]):
        st.write(message['message'])

user_input = st.chat_input("Ask anything")

if user_input:
    st.session_state["message_history"].append(
        {
            "role":"human",
            "message":user_input
        }
    )
    with st.chat_message("human"):
        st.write(user_input)

    # Will use streaming instead os static message.
    with st.chat_message("ai"):
        def ai_only_stream():
            for message_chunk, _ in chatbot.stream(
                {"messages": [HumanMessage(content=user_input)]},
                config=CONFIG,
                stream_mode="messages"
            ):
                if isinstance(message_chunk, AIMessage):
                    yield extract_text(message_chunk.content)
        ai_message = st.write_stream(ai_only_stream())

    st.session_state["message_history"].append(
        {
            "role":"ai",
            "message":ai_message
        }
    )