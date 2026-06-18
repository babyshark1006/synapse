"""
test_pdf_read.py - 验证 pypdf 能读取 PDF

目的:用最少的代码,确认 pypdf 能打开 transformer.pdf 并提取文字
"""

from pypdf import PdfReader

# 打开 PDF 文件
pdf_path = "data/papers/transformer.pdf"
reader = PdfReader(pdf_path)

# 打印基础信息
print(f"📄 PDF 文件:{pdf_path}")
print(f"📊 总页数:{len(reader.pages)}")

# 读取第 1 页的文字
page1 = reader.pages[0]
text = page1.extract_text()

# 只打印前 500 个字符(避免刷屏)
print(f"\n📝 第 1 页前 500 字符:")
print("-" * 50)
print(text[:500])
print("-" * 50)

print(f"\n✅ pypdf 读取成功!")