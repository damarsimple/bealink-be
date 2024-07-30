import base64
from vertexai.generative_models import HarmBlockThreshold, HarmCategory
from langchain.tools import tool
from langchain_google_vertexai import ChatVertexAI, VertexAIEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.aiosqlite import AsyncSqliteSaver

from langgraph.prebuilt import create_react_agent

# LLM Configuration
llm = ChatVertexAI(
    model="gemini-1.5-pro",
    temperature=0,
    max_tokens=4096,
    max_retries=6,
    stop=None,
    streaming=True,
    safety_settings={
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH
    }
)

def create_agent_executor(llm, tools, systemPrompt):
    memory = AsyncSqliteSaver.from_conn_string(":memory:")
    config = {"configurable": {"thread_id": 'default_thread'}}
    agent_executor = create_react_agent(llm, tools, checkpointer=memory)
    return agent_executor

llm_image = ChatVertexAI(model="gemini-pro-vision")

def encode_image(image_path):
    """Getting the base64 string"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")
    
def transcribe_base64(fpath):
    
    message = HumanMessage(
        content=[
            {"type": "text", "text": "Extract data from this image, might be receipt in which case focus on items name and price!"},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encode_image(fpath)}"}},
        ]
    )
    return llm_image.invoke([message]).content
