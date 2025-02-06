import asyncio
import io

from fastapi import FastAPI, File, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pdfminer.high_level import extract_text_to_fp
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings
import requests
import json
from io import StringIO
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 在文件开头添加超时设置
requests.adapters.DEFAULT_RETRIES = 3  # 增加重试次数

# 在文件开头添加环境变量设置
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'  # 禁用oneDNN优化

# 初始化组件
EMBED_MODEL = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
CHROMA_CLIENT = chromadb.PersistentClient(
    path="./chroma_db",
    settings=chromadb.Settings(anonymized_telemetry=False)
)
COLLECTION = CHROMA_CLIENT.get_or_create_collection("rag_docs")

logging.basicConfig(level=logging.INFO)

session = requests.Session()
retries = Retry(
    total=3,
    backoff_factor=0.1,
    status_forcelist=[500, 502, 503, 504]
)
session.mount('http://', HTTPAdapter(max_retries=retries))

app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:8080",  # 替换为你的客户端地址
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QuestionRequest(BaseModel):
    question: str

def extract_text(filepath):
    """改进的PDF文本提取方法"""
    output = StringIO()
    with open(filepath, 'rb') as file:
        extract_text_to_fp(file, output)
    return output.getvalue()


@app.post("/process_pdf/")
async def process_pdf(file: UploadFile = File(...)):
    """PDF处理全流程"""
    try:
        # 保存上传的文件
        file_path = f"temp_{file.filename}"
        with open(file_path, "wb") as f:
            f.write(await file.read())

        text = extract_text(file_path)

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=50
        )
        chunks = text_splitter.split_text(text)

        embeddings = EMBED_MODEL.encode(chunks)

        # 清空现有数据的正确方式
        existing_ids = COLLECTION.get()['ids']
        if existing_ids:
            COLLECTION.delete(ids=existing_ids)
        # 存入新数据
        ids = [str(i) for i in range(len(chunks))]
        COLLECTION.add(
            ids=ids,
            embeddings=embeddings.tolist(),
            documents=chunks
        )

        return {"message": f"PDF处理完成，已存储 {len(chunks)} 个文本块"}
    except Exception as e:
        return {"error": f"处理失败: {str(e)}"}

def stream_generator(response):
    full_answer = ""
    for line in response.iter_lines():
        try:
            chunk = json.loads(line)
            response_text = chunk.get("response", "")
            yield response_text
        except json.JSONDecodeError:
            logging.error("Ollama响应解析失败")

@app.post("/query_answer/")
async def query_answer(request: Request):
    """问答处理流程"""
    data = await request.json()
    question = data.get('question')

    try:
        logging.info(f"收到问题：{question}")
        # 生成问题嵌入
        query_embedding = EMBED_MODEL.encode([question]).tolist()

        # Chroma检索
        results = COLLECTION.query(
            query_embeddings=query_embedding,
            n_results=3
        )

        # 构建提示词
        context = "\n".join(results['documents'][0])
        prompt = f"""基于以下上下文：
        {context}

        问题：{question}
        请用中文给出详细回答："""

        # 调用Ollama，启用流式模式
        ollama_response = session.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "deepseek-r1:7b",
                "prompt": prompt,
                "stream": True
            },
            timeout=120,  # 延长到2分钟
            headers={'Connection': 'close'},  # 添加连接头
            stream=True
        )
        ollama_response.raise_for_status()  # 检查HTTP状态码

        return StreamingResponse(stream_generator(ollama_response))

    except Exception as e:
        return {"error": f"系统错误: {str(e)}"}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
