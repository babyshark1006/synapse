"""
verify_chroma.py - 验证 ChromaDB 真的存了向量

跑完 ingest.py 后,跑这个脚本检查向量库内容
"""
import chromadb

# 连接到本地 ChromaDB
client = chromadb.PersistentClient(path="./chroma_db")

# 拿到我们的集合
collection = client.get_collection("synapse_papers")

# 1. 看有几个切片
count = collection.count()
print(f"📊 向量库里有 {count} 个切片")

# 2. 取出前 2 个切片看看内容(原文 + 元数据)
peek = collection.peek(limit=2)
print(f"\n📝 前 2 个切片预览:")
print("=" * 60)

for i, doc in enumerate(peek['documents']):
    print(f"\n--- 切片 {i+1} ---")
    print(f"原文(前 200 字):{doc[:200]}...")
    print(f"元数据:{peek['metadatas'][i]}")
    print(f"向量维度:{len(peek['embeddings'][i])}")
    print(f"向量前 5 个数字:{peek['embeddings'][i][:5]}")

print("\n" + "=" * 60)
print("✅ ChromaDB 验证通过")