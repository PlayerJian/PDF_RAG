import hashlib

from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Milvus

# 加载 PDF 文档
loader = PyPDFLoader('E:/Users/Python-菅荣孝简历.pdf')
documents = loader.load()
text_splitter = CharacterTextSplitter(
                                    separator="；",
                                    chunk_size=400,
                                    chunk_overlap=10,
                                    length_function=len,
                                    is_separator_regex=True)
docs = text_splitter.split_documents(documents)

# 创建向量数据库
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
# milvus集合名称
collection_name = "pdf_test"
# 连接到本地 Milvus 服务
vectorstore = Milvus(
    embedding_function=embeddings,
    collection_name=collection_name,  # 可以根据需要修改集合名称
    connection_args={"host": "172.27.9.40", "port": "19530"},  # 本地 Milvus 服务的地址和端口
    drop_old = False,
    auto_id = True
)

vectorstore.add_documents(docs)
print('存储完成')

# 定义查询内容
query = "年龄"
# 执行查询，返回相关的 2 条记录
results = vectorstore.similarity_search(query, k=2)
# 输出查询结果
for i, result in enumerate(results, start=1):
    print(f"第 {i} 条记录：")
    print(result.page_content)
    print("-" * 50)