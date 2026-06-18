"""
test_env.py - 环境验证脚本

目的:
    验证 Synapse 项目所需的两个核心 API 是否能正常工作。
    - Claude API(用于生成答案)
    - OpenAI Embedding API(用于文本向量化)

使用:
    在 synapse 根目录下运行:
        python tests/test_env.py

预期结果:
    ✅ Claude API OK
    ✅ OpenAI Embedding OK
"""

# ========================================
# 第 1 部分:导入工具库
# ========================================
# os:用来读取系统环境变量
import os

# dotenv:用来加载 .env 文件里的 key 到环境变量里
from dotenv import load_dotenv

# anthropic 和 openai:两个 API 的官方客户端
from anthropic import Anthropic
from openai import OpenAI


# ========================================
# 第 2 部分:加载 .env 文件
# ========================================
# load_dotenv() 会自动找到项目根目录的 .env 文件,读取里面的 key
load_dotenv()

# 从环境变量里读出 API key
# 如果 .env 没配置或者读不到,这两个变量会是 None
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

# 检查 key 是否存在,如果不存在就报错退出
# 这是一个"防御性编程"的好习惯:早失败、给清楚的错误提示
if not ANTHROPIC_KEY:
    print("❌ 错误:没找到 ANTHROPIC_API_KEY。请检查 .env 文件。")
    exit(1)
if not OPENAI_KEY:
    print("❌ 错误:没找到 OPENAI_API_KEY。请检查 .env 文件。")
    exit(1)


# ========================================
# 第 3 部分:测试 Claude API
# ========================================
def test_claude():
    """测试 Claude API 能不能正常回话。"""
    print("\n🧪 测试 Claude API...")
    
    try:
        # 💡 创建 Claude 客户端(用 .env 里的 key)
        client = Anthropic(api_key=ANTHROPIC_KEY)
        
        # 💡 发一个最简单的请求:给 Claude 一句话,让它回一句
        # max_tokens=50:限制回答长度,省 token
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=50,
            messages=[
                {"role": "user", "content": "用一句话介绍你自己。"}
            ]
        )
        
        # 拿出 Claude 的回答内容
        reply = response.content[0].text
        
        # 打印成功信息
        print(f"✅ Claude API OK")
        print(f"   回复:{reply}")
        return True
        
    except Exception as e:
        # 如果任何一步出错,打印错误信息
        print(f"❌ Claude API 失败:{e}")
        return False


# ========================================
# 第 4 部分:测试 OpenAI Embedding API
# ========================================
def test_openai_embedding():
    """测试 OpenAI Embedding API 能不能返回向量。"""
    print("\n🧪 测试 OpenAI Embedding API...")
    
    try:
        # 💡 创建 OpenAI 客户端
        client = OpenAI(api_key=OPENAI_KEY)
        
        # 💡 让它把一句话变成向量(embedding)
        # model:用最新的小模型,便宜够用
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input="Attention is all you need."
        )
        
        # 拿出向量(是一个很长的数字列表)
        embedding = response.data[0].embedding
        
        # 打印成功信息 + 向量长度(让你看到它返回了什么)
        print(f"✅ OpenAI Embedding OK")
        print(f"   向量维度:{len(embedding)}(前 5 个数字:{embedding[:5]})")
        return True
        
    except Exception as e:
        print(f"❌ OpenAI Embedding 失败:{e}")
        return False


# ========================================
# 第 5 部分:主程序入口
# ========================================
if __name__ == "__main__":
    # 这是 Python 脚本的标准入口写法
    # 当你运行 "python tests/test_env.py" 时,这段代码才会执行
    
    print("=" * 50)
    print("🧪 Synapse 环境验证脚本")
    print("=" * 50)
    
    # 分别测试两个 API
    claude_ok = test_claude()
    openai_ok = test_openai_embedding()
    
    # 汇总结果
    print("\n" + "=" * 50)
    if claude_ok and openai_ok:
        print("🎉 所有 API 验证通过!可以进入 Day 2。")
    else:
        print("⚠️ 部分 API 失败,请检查上面的错误信息。")
    print("=" * 50)