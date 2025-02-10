import zlib
import json

import uvicorn
from fastapi import FastAPI, Response, Body, UploadFile, File
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma, Milvus
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain_community.llms import Ollama
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain_core.messages import HumanMessage, AIMessage
from sse_starlette.sse import EventSourceResponse
from langchain.prompts import PromptTemplate  # 导入 PromptTemplate 类

app = FastAPI()

# 创建向量数据库
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
# 连接到本地 Milvus 服务
vectorstore = Milvus(
    embedding_function=embeddings,
    collection_name="test2",  # 可以根据需要修改集合名称
    connection_args={"host": "172.27.9.40", "port": "19530"},  # 本地 Milvus 服务的地址和端口
    drop_old = True,
    auto_id = True
)

# 初始化大模型，开启流式处理
llm = Ollama(
    model="deepseek-r1:7b"
)

# 初始化记忆
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

# 自定义 prompt 模板
custom_prompt_template = """以下是与用户的对话历史：
{chat_history}
请根据以上对话历史和以下相关文档回答用户的问题：
{context}
用户的问题是：{question}
如果用户的问题在相关文档中没有体现，那你就回答不知道
"""

# 创建自定义的 PromptTemplate 实例
PROMPT = PromptTemplate(
    input_variables=["chat_history", "context", "question"],
    template=custom_prompt_template
)

# 创建问答链，设置合理的请求结果数量，并使用自定义的 prompt 模板
qa = ConversationalRetrievalChain.from_llm(
    llm,
    vectorstore.as_retriever(search_kwargs={"k": 5}),  # 设置请求结果数量为 2
    memory=memory,
    combine_docs_chain_kwargs={"prompt": PROMPT}  # 使用自定义的 prompt 模板
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
    full_answer = ""
    # 解压缩对话历史
    memory.chat_memory.messages = decompress_history(compressed_chat_history)

    # 创建一个生成器来流式输出结果
    async for chunk in qa.astream(question):
        answer_chunk = chunk.get("answer", "")
        print(answer_chunk+"**", end="", flush=True)
        if answer_chunk:
            yield answer_chunk

    # 压缩对话历史
    compressed_chat_history = compress_history(memory.chat_memory.messages)


@app.post("/process_pdf/")
async def process_pdf(file: UploadFile = File(...)):
    """PDF处理全流程"""
    try:
        # 保存上传的文件
        file_path = f"temp_{file.filename}"
        with open(file_path, "wb") as f:
            f.write(await file.read())

        loader = PyPDFLoader(file_path)
        documents = loader.load()
        text_splitter = CharacterTextSplitter(
            separator="。",
            chunk_size=100,
            chunk_overlap=10,
            length_function=len,
            is_separator_regex=True)
        docs = text_splitter.split_documents(documents)
        vectorstore.add_documents(docs)

        return {"message": f"PDF处理完成，已存储"}
    except Exception as e:
        return {"error": f"处理失败: {str(e)}"}


@app.post("/ask")
async def ask_question(question: str = Body(embed=True)):  # 确保传入的是字符串类型的问题
    return EventSourceResponse(generate_response(question))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)