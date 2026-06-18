"""
verify_multi_papers.py - 验证多论文索引正确性
"""
import chromadb
from collections import Counter

client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_collection("synapse_papers")

total = collection.count()
print(f"📊 切片总数:{total}")

all_data = collection.get(include=['metadatas'])
metadatas = all_data['metadatas']

file_counter = Counter(m.get('file_name', 'unknown') for m in metadatas)

print(f"\n📚 按论文分组:")
print("=" * 50)
for filename, count in sorted(file_counter.items()):
    percentage = count / total * 100
    print(f"  {filename:30s} {count:4d} 切片 ({percentage:.1f}%)")
print("=" * 50)

expected = {"transformer.pdf", "rag.pdf", "react.pdf"}
actual = set(file_counter.keys())

if expected == actual:
    print(f"\n✅ 3 篇论文全部成功索引")
else:
    missing = expected - actual
    if missing:
        print(f"\n❌ 缺失论文:{missing}")

print(f"\n📖 每篇论文的页码范围")
print("=" * 50)
for paper in sorted(actual):
    pages = [int(m['page_label']) for m in metadatas 
             if m.get('file_name') == paper and m.get('page_label', '').isdigit()]
    if pages:
        print(f"  {paper:30s} 第 {min(pages)}-{max(pages)} 页 (共 {len(set(pages))} 页)")