import asyncio
import threading
import os
import socketio
from aiohttp import web
import json
from db_operations import create_conversation, get_db_connection, insert_message, create_database, task_queue, database_worker
from vector_service import get_hs_code, search_hs_code_info, search_faq_info
from llm_config import create_agent_executor, llm, transcribe_base64
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.aiosqlite import AsyncSqliteSaver
from currency_db import get_currency_detail

systemPrompt = open("sysprompt.txt", "r").read()

# Initialize the agent executor
tools = [get_currency_detail, get_hs_code, search_hs_code_info, search_faq_info]
memory_instances = {}

async def run_agent_starting(data):
    thread_id = data['thread_id']
    language = data['language']
    conversation_id = create_conversation(thread_id)
    memory = AsyncSqliteSaver.from_conn_string(":memory:")
    config = {"configurable": {"thread_id": thread_id}}
    agent_executor = create_agent_executor(llm, tools, systemPrompt)
    memory_instances[thread_id] = agent_executor
    task_queue.put((insert_message, conversation_id, '', 'user', data.get("message", "Hello")))
    
    inputs = {
        "messages": [
            SystemMessage(content=systemPrompt.replace("REPLACE_LANGUAGE", language)),
            HumanMessage(content=data.get("message", "Hello"))
        ]
    }
    
    try:
        async for event in agent_executor.astream_events(inputs, version="v1", config=config):
            kind = event["event"]
            if kind == 'on_chat_model_end':
                print('response', {'kind': 'on_chat_model_end'})
            if kind == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                if content:
                    task_queue.put((insert_message, conversation_id, None, 'assistant', content))
                    print('response', {'kind': 'on_chat_model_stream', 'content': content})
            elif kind == "on_tool_start":
                print('response', {'kind': 'on_tool_start', 'name': event['name'], 'input': event['data'].get('input')})
            elif kind == "on_tool_end":
                print('response', {'kind': 'on_tool_end', 'name': event['name'], 'output': event['data'].get('output')})
    except:
        print('response', {'kind': 'on_chat_model_end'})

async def run_agent(data):
    thread_id = data['thread_id']
    message = data['message']
    ip_address = ''
    
    if thread_id not in memory_instances:
        return {'error': 'Thread ID not found'}, 404
    
    agent_executor = memory_instances[thread_id]
    config = {"configurable": {"thread_id": thread_id}}
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT conversation_id FROM conversations WHERE thread_id = ?", (thread_id,))
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        return {'error': 'Conversation not found'}, 404
    
    conversation_id = result[0]
    task_queue.put((insert_message, conversation_id, ip_address, 'user', message))
    
    if 'image' in data:
        beginning = transcribe_base64(data['image'])
        message = f'This is image transcript of image from user {beginning} ' + data.get('message')
        print(message)

    else:
        message = data.get("message")
    
    inputs = {"messages": [HumanMessage(content=message)]}

    async for event in agent_executor.astream_events(inputs, version="v2", config=config):
        kind = event["event"]
        if "prompt_token_count" in event:
            print(event["prompt_token_count"])

        if kind != 'on_chat_model_stream':
            print('response', {'kind': kind})
        if "on_tool" in kind:
            print(event["data"])
        if kind == "on_chat_model_stream":
            content = event["data"]["chunk"].content
            if content:
                task_queue.put((insert_message, conversation_id, None, 'assistant', content))
                print('response', {'kind': 'on_chat_model_stream', 'content': content})
    



async def init_app():
    thr_id = 123
    await run_agent_starting({
        'thread_id' : thr_id,
        'language' : 'indonesian'
    })
    await run_agent({
        'thread_id' : thr_id,
        'message' : 'a'
    })
    await run_agent({
        'thread_id' : thr_id,
        'message' : 'hanya membawa laptop 1k usd untuk pribadi, saya memiliki npwp'
    })
    pass

if __name__ == '__main__':
    create_database()
    threading.Thread(target=database_worker, daemon=True).start()
    asyncio.run(init_app())