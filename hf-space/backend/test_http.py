import os
import asyncio
from dotenv import load_dotenv

try:
    from ddgs.ddgs_async import DDGS
except ImportError:
    print("错误: 找不到 ddgs 库。请确保您已运行 'pip install ddgs'")
    exit()

# 这一部分模仿您的应用启动，加载环境变量
print("--- 正在加载 .env 文件 ---")
load_dotenv()
http_proxy = os.getenv('HTTP_PROXY')
https_proxy = os.getenv('HTTPS_PROXY')
print(f"读取到的 HTTP_PROXY: {http_proxy}")
print(f"读取到的 HTTPS_PROXY: {https_proxy}")
print("--------------------------\n")

if not http_proxy:
    print("警告: .env 文件中未找到 HTTP_PROXY 设置。")

async def run_test():
    """
    一个独立的异步函数，用于测试 ddgs 的联网搜索功能。
    """
    query = "what is the weather in new york today?"
    print(f"--- 准备使用 ddgs 执行搜索: '{query}' ---")
    
    try:
        # 我们直接使用 ddgs 库，它会自动读取环境变量中的代理
        # 我们设置一个20秒的超时以防永久等待
        async with DDGS(timeout=20) as ddgs:
            # 异步迭代获取结果
            results = [r async for r in ddgs.text(query, max_results=3)]
            
        print("\n--- ✅ 搜索成功！---\n")
        if results:
            print("获取到以下结果:")
            for i, result in enumerate(results, 1):
                print(f"{i}. {result.get('title')}")
                print(f"   Link: {result.get('href')}\n")
        else:
            print("搜索执行完毕，但 DuckDuckGo 未返回任何结果。")
    
    except Exception as e:
        print(f"\n--- ❌ 搜索失败！ ---\n")
        print(f"错误类型: {type(e).__name__}")
        print(f"错误详情: {e}")
        print("\n--- 请重点检查 ---")
        print("1. 您的代理客户端 (如 Clash, V2RayN, etc.) 是否正在运行？")
        print("2. 代理客户端的日志 (Log) 中，是否有关于拦截或拒绝来自 'Python' 或 'ddgs' 请求的记录？")
        print("3. 您的代理模式是否正确？（例如，是否需要开启 TUN 模式才能代理来自终端的流量）")
        print("4. 您的代理服务器是否需要用户名和密码认证？")

if __name__ == "__main__":
    # 运行这个异步测试函数
    asyncio.run(run_test())