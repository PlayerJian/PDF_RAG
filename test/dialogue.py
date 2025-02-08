import zlib
import json

import uvicorn
from fastapi import FastAPI, Response, Body
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain_community.llms import Ollama
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain_core.messages import HumanMessage, AIMessage
from sse_starlette.sse import EventSourceResponse

app = FastAPI()

# 加载 PDF 文档
loader = PyPDFLoader('E:/Users/Python-菅荣孝简历.pdf')
documents = loader.load()
text_splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=0)
docs = text_splitter.split_documents(documents)

# 创建向量数据库
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
vectorstore = Chroma.from_documents(docs, embeddings)

# 初始化大模型，开启流式处理
llm = Ollama(
    model="deepseek-r1:8b"
)

# 初始化记忆
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

# 创建问答链，设置合理的请求结果数量
qa = ConversationalRetrievalChain.from_llm(
    llm,
    vectorstore.as_retriever(search_kwargs={"k": 2
                                            }),  # 设置请求结果数量为 2
    memory=memory
)

# 用于存储压缩后的对话历史
compressed_chat_history = None

# 辅助函数：解压缩并转换聊天历史
def decompress_history(compressed_history):
    if compressed_history:
        decompressed_history = zlib.decompress(compressed_history)
        decoded_history = decompressed_history.decode('utf-8')
        serialized_messages = json.loads(decoded_history)
        messages = []
        for msg in serialized_messages:
            if msg["type"] == "HumanMessage":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["type"] == "AIMessage":
                messages.append(AIMessage(content=msg["content"]))
        return messages
    return []

# 辅助函数：压缩聊天历史
def compress_history(messages):
    serialized_history = json.dumps([{"type": type(msg).__name__, "content": msg.content} for msg in messages]).encode('utf-8')
    return zlib.compress(serialized_history)

async def generate_response(question):
    global compressed_chat_history
    # 解压缩对话历史
    memory.chat_memory.messages = decompress_history(compressed_chat_history)

    # 创建一个生成器来流式输出结果
    async for chunk in qa.astream(question):
        answer_chunk = chunk.get("answer", "")
        if answer_chunk:
            yield {"data": answer_chunk}

    # 压缩对话历史
    compressed_chat_history = compress_history(memory.chat_memory.messages)

app = FastAPI()

@app.post("/ask")
async def ask_question(question: str = Body(embed=True)):  # 确保传入的是字符串类型的问题
    return EventSourceResponse(generate_response(question))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)