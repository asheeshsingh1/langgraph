from importlib import metadata

import streamlit as st
from chatbot_backend import chatbot
from langchain_core.messages import HumanMessage, AIMessage

CONFIG = {"configurable":{"thread_id":"thread-1"}}

if "message_history" not in st.session_state:
    st.session_state["message_history"] = []


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


    # response = chatbot.invoke({"messages":[HumanMessage(content=user_input)]},config=CONFIG)
    # ai_message = response["messages"][-1].content
    # st.session_state["message_history"].append(
    #     {
    #         "role":"ai",
    #         "message":ai_message
    #     }
    # )
    # with st.chat_message("ai"):
    #         st.write(ai_message)

    # Will use streaming instead os static message.
    with st.chat_message("ai"):
            ai_message = st.write_stream(
                message_chunk.content for message_chunk,_ in chatbot.stream(
                    {"messages":[HumanMessage(content=user_input)]},
                    config=CONFIG,
                    stream_mode="messages"
                )
            )

    st.session_state["message_history"].append(
        {
            "role":"ai",
            "message":ai_message
        }
    )