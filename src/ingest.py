"""
ingest.py - PDF → 向量库的索引脚本

功能:
    读取 data/papers/ 下的 PDF,切片 + embedding + 存入 ChromaDB
    这是 RAG 系统的"索引阶段"(建立知识库)

使用:
    python src/ingest.py
    
输出:
    ./chroma_db/ 目录下生成向量数据库
    
设计决策:
    - 切片大小:512 token(业界 baseline)
    - 切片重叠:50 token(保留上下文连贯)
    - Embedding 模型:text-embedding-3-small(便宜 + 够用)
    - 向量库:ChromaDB 本地模式(零运维)
"""

# ========================================
# 第 1 部分:导入工具库
# ========================================
import os
from dotenv import load_dotenv

# LlamaIndex 核心组件
from llama_index.core import (
    VectorStoreIndex,           # 索引对象(存向量 + 支持查询)
    SimpleDirectoryReader,       # 读目录里的文件
    StorageContext,              # 管理存储位置
    Settings,                    # 全局配置
)
from llama_index.core.node_parser import SentenceSplitter  # 切片器
from llama_index.embeddings.openai import OpenAIEmbedding  # OpenAI 向量化
from llama_index.vector_stores.chroma import ChromaVectorStore  # ChromaDB 适配器

# ChromaDB 本体
import chromadb


# ========================================
# 第 2 部分:加载配置
# ========================================
# 读取 .env 里的 API key
load_dotenv()

# 确认 OpenAI key 存在(Embedding 需要)
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("❌ 缺少 OPENAI_API_KEY,请检查 .env")

# 路径配置
PDF_DIR = "data/papers"           # PDF 存放目录
CHROMA_DIR = "./chroma_db"        # 向量库存放目录
COLLECTION_NAME = "synapse_papers"  # 向量库里的"集合"名(类似表名)


# ========================================
# 第 3 部分:配置 LlamaIndex 的全局参数
# ========================================
# 💡 这里设置 embedding 模型,全局生效
# 所有切片都会用这个模型转向量
Settings.embed_model = OpenAIEmbedding(
    model="text-embedding-3-small",  # 模型名
    embed_batch_size=100              # 批量处理 100 个,省 API 调用次数
)

# 💡 配置切片器
# chunk_size=512:每段 512 token
# chunk_overlap=50:相邻段重叠 50 token(保留上下文)
Settings.node_parser = SentenceSplitter(
    chunk_size=512,
    chunk_overlap=50
)


# ========================================
# 第 4 部分:核心函数 —— ingest 流程
# ========================================
def ingest_pdfs():
    """
    主索引函数:读 PDF → 切片 → embedding → 存 ChromaDB
    """
    
    # --- 第 1 步:读取 PDF 文件 ---
    print(f"\n📂 开始读取 {PDF_DIR}/ 目录下的 PDF...")
    
    reader = SimpleDirectoryReader(
        input_dir=PDF_DIR,
        required_exts=[".pdf"]  # 只处理 PDF 文件
    )
    documents = reader.load_data()
    
    print(f"✅ 成功读取 {len(documents)} 个文档片段")
    # 💡 注意:LlamaIndex 会自动把多页 PDF 拆成多个 document
    # 每页通常是一个 document,所以数字可能比 PDF 数量多
    
    
    # --- 第 2 步:初始化 ChromaDB ---
    print(f"\n🗄️  初始化 ChromaDB (存储在 {CHROMA_DIR}/)...")
    
    # 创建/连接本地 ChromaDB
    chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
    
    # 获取或创建集合(collection,类似数据库里的"表")
    # 如果集合已存在,这里会复用(不会重复创建)
    chroma_collection = chroma_client.get_or_create_collection(
        name=COLLECTION_NAME
    )
    
    # 把 ChromaDB 包装成 LlamaIndex 能用的格式
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    
    print(f"✅ ChromaDB 就绪,集合名:{COLLECTION_NAME}")
    
    
    # --- 第 3 步:建立索引(这一步会调 OpenAI API,需要钱 💰) ---
    print(f"\n🔄 开始切片 + embedding + 存储...")
    print(f"   这一步会调用 OpenAI API,预计耗时 30-60 秒")
    print(f"   预计成本:< $0.01(这篇论文)")
    
    # 💡 这一行是整个脚本的核心
    # LlamaIndex 会自动完成:切片 → embedding → 存入 ChromaDB
    index = VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        show_progress=True  # 显示进度条
    )
    
    print(f"\n✅ 索引建立完成!")
    
    
    # --- 第 4 步:报告结果 ---
    # 查询 ChromaDB 里实际存了多少条
    count = chroma_collection.count()
    
    print(f"\n" + "=" * 50)
    print(f"📊 索引报告")
    print(f"=" * 50)
    print(f"原始文档数:{len(documents)}")
    print(f"向量数据库里的切片数:{count}")
    print(f"向量维度:1536(OpenAI text-embedding-3-small)")
    print(f"存储位置:{CHROMA_DIR}/")
    print(f"=" * 50)
    
    return index


# ========================================
# 第 5 部分:主程序入口
# ========================================
if __name__ == "__main__":
    print("=" * 50)
    print("🧠 Synapse - PDF 索引脚本")
    print("=" * 50)
    
    try:
        ingest_pdfs()
        print("\n🎉 Ingest 成功!可以进入 Step 5(检索测试)")
    except Exception as e:
        print(f"\n❌ Ingest 失败:{e}")
        raise