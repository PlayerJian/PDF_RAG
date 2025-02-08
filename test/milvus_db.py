from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Milvus

# 加载 PDF 文档
loader = PyPDFLoader('E:/Users/Python-简历.pdf')
documents = loader.load()
text_splitter = CharacterTextSplitter(
                                    separator="；",
                                    chunk_size=400,
                                    chunk_overlap=0,
                                    length_function=len,
                                    is_separator_regex=True)
docs = text_splitter.split_documents(documents)

# 创建向量数据库
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# 连接到本地 Milvus 服务
vectorstore = Milvus(
    embedding_function=embeddings,
    collection_name="pdf_test",  # 可以根据需要修改集合名称
    connection_args={"host": "", "port": "19530"},  # 本地 Milvus 服务的地址和端口
    drop_old = True,
    auto_id = True
)
vectorstore.add_documents(docs)

print('完成')