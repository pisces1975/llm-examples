from openai import OpenAI
import streamlit as st
from streamlit_feedback import streamlit_feedback
import trubrics
from utilities.logger import LOG
from utilities.string_resource import get_running_state
from utilities.ConfigReader import ConfigReader
from utilities.db_driver import DBDriver
from utilities.query_util import ask_question, replace_links
from utilities.constants import CONST
import json
# from utilities.embedding_driver import embedding_FAISS

with st.sidebar:
    # openai_api_key = st.text_input("OpenAI API Key", key="feedback_api_key", type="password")
    # "[Get an OpenAI API key](https://platform.openai.com/account/api-keys)"
    # "[View the source code](https://github.com/streamlit/llm-examples/blob/main/pages/5_Chat_with_user_feedback.py)"
    # "[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/streamlit/llm-examples?quickstart=1)"
    user_id = st.text_input("员工号", type="default", help="请输入员工号")
    user_password = st.text_input("密码", type="password", help="请输入密码")    
    answer_limit = st.number_input("答案个数", min_value=1, max_value=15, value=8, step=1)
    options = [CONST.SEARCH_MODE_STR_ON, CONST.SEARCH_MODE_STR_OFF]
    summary_mode = st.radio("摘要模式", options)
    "[履约项目经验库](https://www.tapd.cn/36446663/markdown_wikis/show/#1136446663001004924)"

# st.title("📝 Chat with feedback (Trubrics)")
st.title("💬 小九AI")
st.caption("🚀 基于大模型技术和履约项目经验库的AI助手")
# """
# In this example, we're using [streamlit-feedback](https://github.com/trubrics/streamlit-feedback) and Trubrics to collect and store feedback
# from the user about the LLM responses.
# """

# openai_api_key = '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'


if "db" not in st.session_state:
    st.session_state['db'] = DBDriver()

# if "faiss" not in st.session_state:
#     st.session_state['faiss'] = embedding_FAISS()
    
if "user" not in st.session_state: 
    st.session_state["user"] = None
if "limit" not in st.session_state:
    st.session_state['limit'] = 8
if "password" not in st.session_state:
    st.session_state['password'] = None
if "mode" not in st.session_state:
    st.session_state['mode'] = CONST.SEARCH_MODE_MIX 

st.session_state["user"] = user_id
st.session_state['limit'] = answer_limit
st.session_state['password'] = user_password
st.session_state['mode'] = summary_mode

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "How can I help you? Leave feedback to help me improve!"}
    ]
if "response" not in st.session_state:
    st.session_state["response"] = None

messages = st.session_state.messages
for msg in messages:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input(placeholder="履约项目管理的基本原则是什么？"):
    messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    if not st.session_state['user']:
        st.info("请先输入用户名和密码登录")
        st.stop()

    # client = OpenAI(api_key=openai_api_key)
    # response = client.chat.completions.create(model="gpt-3.5-turbo", messages=messages)
    mode = CONST.SEARCH_MODE_MIX
    if st.session_state['mode'] == CONST.SEARCH_MODE_STR_ON:
        mode = CONST.SEARCH_MODE_SUMMARY

    LOG.debug(f"{get_running_state()} Start query ({st.session_state['user']}, {st.session_state['limit']}, {mode}): {prompt[:20]}")
    answer = ask_question(prompt, st.session_state['user'], st.session_state['limit'], mode)

    st.session_state["response"] = answer

    with st.chat_message("assistant"):
        # messages.append({"role": "assistant", "content": st.session_state["response"]})
        # st.write(st.session_state["response"])

        ans_list = answer
        for item in ans_list:
            if len(item['prefix']) > 2:
                content_string = f"{replace_links(item['prefix'])}: {replace_links(item['content'])}"                
            else:
                content_string = item['content']
            st.markdown(content_string)    
            st.divider()                
            messages.append({"role": "assistant", "content": content_string})

if st.session_state["response"]:
    feedback = streamlit_feedback(
        feedback_type="thumbs",
        optional_text_label="[Optional] Please provide an explanation",
        key=f"feedback_{len(messages)}",
    )
    # This app is logging feedback to Trubrics backend, but you can send it anywhere.
    # The return value of streamlit_feedback() is just a dict.
    # Configure your own account at https://trubrics.streamlit.app/
    if feedback and "TRUBRICS_EMAIL" in st.secrets:
        config = trubrics.init(
            email=st.secrets.TRUBRICS_EMAIL,
            password=st.secrets.TRUBRICS_PASSWORD,
        )
        collection = trubrics.collect(
            component_name="default",
            model="gpt",
            response=feedback,
            metadata={"chat": messages},
        )
        trubrics.save(config, collection)
        st.toast("Feedback recorded!", icon="📝")
