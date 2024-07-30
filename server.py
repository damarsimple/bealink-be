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

sio = socketio.AsyncServer(async_mode='aiohttp', cors_allowed_origins='*', max_http_buffer_size=10 * 1024)
app = web.Application(client_max_size=10 * 1024)
sio.attach(app)

# Create a directory for uploaded images
UPLOAD_DIR = "tmp"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# System prompt definition
systemPrompt = open("sysprompt.txt", "r").read()

# Initialize the agent executor
tools = [get_currency_detail, get_hs_code, search_hs_code_info, search_faq_info]
memory_instances = {}

@sio.event
async def connect(sid, environ):
    await sio.emit('response', {'data': 'Connected'}, room=sid)

@sio.event
async def run_agent_starting(sid, data):
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
                await sio.emit('response', {'kind': 'on_chat_model_end'}, room=sid)
            if kind == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                if content:
                    task_queue.put((insert_message, conversation_id, None, 'assistant', content))
                    await sio.emit('response', {'kind': 'on_chat_model_stream', 'content': content}, room=sid)
            elif kind == "on_tool_start":
                await sio.emit('response', {'kind': 'on_tool_start', 'name': event['name'], 'input': event['data'].get('input')}, room=sid)
            elif kind == "on_tool_end":
                await sio.emit('response', {'kind': 'on_tool_end', 'name': event['name'], 'output': event['data'].get('output')}, room=sid)
    except:
        await sio.emit('response', {'kind': 'on_chat_model_end'}, room=sid)

@sio.event
async def run_agent(sid, data):
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
            await sio.emit('response', {'kind': kind}, room=sid)
        if "on_tool" in kind:
            print(event["data"])
        if kind == "on_chat_model_stream":
            content = event["data"]["chunk"].content
            if content:
                task_queue.put((insert_message, conversation_id, None, 'assistant', content))
                await sio.emit('response', {'kind': 'on_chat_model_stream', 'content': content}, room=sid)

# Upload handler
async def upload_handler(request):
    reader = await request.multipart()
    
    # Get the file field from the request
    field = await reader.next()
    assert field.name == 'image'
    
    # Get the filename of the uploaded file
    filename = field.filename
    
    # Create the file path
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    # Save the uploaded file
    size = 0
    with open(file_path, 'wb') as f:
        while True:
            chunk = await field.read_chunk()
            if not chunk:
                break
            size += len(chunk)
            if size > 10 * 1024 * 1024: # Limit size to 10 MB
                return web.Response(status=413, text='File size limit exceeded')
            f.write(chunk)
    
    # Return the file URL
    return web.Response(text=json.dumps({'image_url': file_path}), content_type='application/json', headers={
        'Access-Control-Allow-Origin' : '*'
    })

# HEAD request handler
async def upload_handler_head(request):
    return web.Response(status=200, headers={
        'Access-Control-Allow-Origin': '*',
        'Content-Type': 'application/json'
    })

# Add the upload routes
app.router.add_post('/upload', upload_handler)
app.router.add_head('/upload', upload_handler_head)

async def init_app():
    return app

if __name__ == '__main__':
    create_database()
    threading.Thread(target=database_worker, daemon=True).start()
    web.run_app(init_app())