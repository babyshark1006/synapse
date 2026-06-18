"""
download_pdf.py - 可靠下载 arXiv 论文

比 curl 更可靠:自动跟随重定向 + 格式校验
"""
import urllib.request
import os

# Transformer 论文的稳定链接(指定版本 v7)
url = "https://arxiv.org/pdf/1706.03762v7.pdf"
output_path = "data/papers/transformer.pdf"

# 下载
print(f"📥 正在下载:{url}")
try:
    urllib.request.urlretrieve(url, output_path)
    
    # 验证 1:文件大小
    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"📊 文件大小:{size_mb:.2f} MB")
    
    # 验证 2:PDF 格式校验(前几个字节应该是 %PDF)
    with open(output_path, 'rb') as f:
        header = f.read(5)
    
    if header.startswith(b'%PDF'):
        print(f"✅ 下载成功,这是一个合法 PDF 文件")
    else:
        print(f"⚠️ 警告:文件头不是 %PDF,实际是:{header}")
        print(f"   可能下载到了 HTML 错误页,请检查")
        
except Exception as e:
    print(f"❌ 下载失败:{e}")