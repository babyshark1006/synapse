"""
download_arxiv.py - 通用 arXiv 论文下载工具

功能:
    输入 arXiv ID + 输出文件名,自动下载 PDF 并验证格式
    
使用方法:
    1. 命令行参数模式:
       python tests/download_arxiv.py 2005.11401 rag.pdf
    
    2. 直接修改文件底部的列表批量下载

设计决策:
    - 用 urllib(自动跟随重定向,比 curl 可靠)
    - 下载后立即验证 PDF 格式(GIGO 防御)
    - 支持单篇 + 批量两种模式
"""

import urllib.request
import os
import sys


def download_arxiv_paper(arxiv_id: str, output_filename: str, output_dir: str = "data/papers") -> bool:
    """
    下载 arXiv 论文
    
    参数:
        arxiv_id: arXiv ID,如 "1706.03762"
        output_filename: 保存的文件名,如 "transformer.pdf"
        output_dir: 保存目录,默认 data/papers/
    
    返回:
        True = 成功,False = 失败
    """
    
    # arXiv 的 PDF URL 格式
    url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    output_path = os.path.join(output_dir, output_filename)
    
    # 如果文件已存在,跳过(避免重复下载)
    if os.path.exists(output_path):
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"⏭️  {output_filename} 已存在 ({size_mb:.2f} MB),跳过下载")
        return True
    
    # 下载
    print(f"\n📥 正在下载:{arxiv_id} → {output_filename}")
    print(f"   URL: {url}")
    
    try:
        urllib.request.urlretrieve(url, output_path)
        
        # 验证 1:文件大小
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        
        # 验证 2:PDF 格式(GIGO 防御)
        with open(output_path, 'rb') as f:
            header = f.read(5)
        
        if not header.startswith(b'%PDF'):
            print(f"   ❌ 文件头不是 %PDF,实际:{header}")
            print(f"   可能是 HTML 错误页,删除...")
            os.remove(output_path)
            return False
        
        print(f"   ✅ 下载成功:{size_mb:.2f} MB")
        return True
        
    except Exception as e:
        print(f"   ❌ 下载失败:{e}")
        # 清理可能的损坏文件
        if os.path.exists(output_path):
            os.remove(output_path)
        return False


# ========================================
# 主程序
# ========================================
if __name__ == "__main__":
    # 模式 1:命令行参数(下载单篇)
    if len(sys.argv) == 3:
        arxiv_id = sys.argv[1]
        output_filename = sys.argv[2]
        download_arxiv_paper(arxiv_id, output_filename)
    
    # 模式 2:批量下载(默认 Part 3 的 3 篇论文)
    else:
        print("=" * 60)
        print("🧠 Synapse - 批量下载 Part 3 论文")
        print("=" * 60)
        
        # Part 3 要下载的论文列表
        papers = [
            ("1706.03762", "transformer.pdf"),    # Transformer (已有)
            ("2005.11401", "rag.pdf"),            # RAG 原论文
            ("2210.03629", "react.pdf"),          # ReAct
        ]
        
        # 逐个下载
        success_count = 0
        for arxiv_id, filename in papers:
            if download_arxiv_paper(arxiv_id, filename):
                success_count += 1
        
        # 报告
        print("\n" + "=" * 60)
        print(f"📊 下载报告:{success_count}/{len(papers)} 成功")
        print("=" * 60)
        
        # 列出 data/papers/ 里所有 PDF
        print(f"\n📂 当前 data/papers/ 目录:")
        for f in sorted(os.listdir("data/papers")):
            if f.endswith(".pdf"):
                size_mb = os.path.getsize(f"data/papers/{f}") / (1024 * 1024)
                print(f"   - {f} ({size_mb:.2f} MB)")