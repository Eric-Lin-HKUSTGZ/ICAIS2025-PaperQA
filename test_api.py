#!/usr/bin/env python3
"""
API服务测试程序
用于测试文献问答API的流式响应
"""

import os
import sys
import json
import base64
import requests
import argparse
from pathlib import Path


def read_base64_from_txt(txt_path: str) -> str:
    """
    从txt文件中读取Base64编码的字符串。

    Args:
        txt_path: txt文件的路径。

    Returns:
        Base64 编码的字符串。
    """
    try:
        with open(txt_path, 'r', encoding='utf-8') as txt_file:
            base64_content = txt_file.read().strip()
        return base64_content
    except FileNotFoundError:
        print(f"❌ 错误：找不到文件 {txt_path}")
        return ""
    except Exception as e:
        print(f"❌ 错误：读取文件时出现问题 - {e}")
        return ""


def parse_sse_line(line: str) -> dict:
    """
    解析SSE数据行
    
    Args:
        line: SSE格式的数据行
        
    Returns:
        解析后的数据字典，如果解析失败返回None
    """
    line = line.strip()
    if not line:
        return None
    
    # 检查结束标记
    if line == "data: [DONE]" or line == "data: data: [DONE]":
        return {"done": True}
    
    # 检查是否是SSE数据行
    if line.startswith("data: "):
        data_str = line[6:]
        
        # 如果还有重复的 "data: " 前缀，再次移除
        if data_str.startswith("data: "):
            data_str = data_str[6:]
        
        try:
            data = json.loads(data_str)
            return data
        except json.JSONDecodeError:
            return None
    
    return None


def test_paper_qa_api(
    api_url: str,
    txt_path: str,
    query: str = "Please carefully analyze and explain the reinforcement learning training methods used in this article.",
    output_file: str = None,
    debug: bool = False
):
    """
    测试文献问答API
    
    Args:
        api_url: API端点URL
        txt_path: 包含base64编码的txt文件路径
        query: 查询字符串
        output_file: 输出文件路径（可选，如果提供则保存完整响应）
        debug: 是否启用调试模式
    """
    print(f"📄 测试文件: {txt_path}")
    print(f"🔗 API端点: {api_url}")
    print(f"❓ 查询: {query}")
    print("-" * 80)
    
    # 从txt文件读取base64内容
    print("📖 正在读取base64编码文件...")
    base64_content = read_base64_from_txt(txt_path)
    if not base64_content:
        print("❌ base64文件读取失败，退出测试")
        return
    
    print(f"✅ base64内容已读取，长度: {len(base64_content)} 字符")
    print("-" * 80)
    
    # 构建请求
    request_data = {
        "query": query,
        "pdf_content": base64_content
    }
    
    # 发送POST请求（流式响应）
    print("🚀 发送请求到API...")
    print("-" * 80)
    
    try:
        response = requests.post(
            api_url,
            json=request_data,
            stream=True,
            headers={
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
                "Cache-Control": "no-cache"
            },
            timeout=900  # 15分钟超时
        )
        
        response.raise_for_status()
        
        # 检查响应类型
        content_type = response.headers.get('Content-Type', '')
        if 'text/event-stream' not in content_type:
            print(f"⚠️ 警告: 响应Content-Type不是text/event-stream，而是: {content_type}")
        
        if debug:
            print(f"[DEBUG] 响应状态码: {response.status_code}")
            print(f"[DEBUG] 响应头 Content-Type: {response.headers.get('Content-Type', 'N/A')}")
        
        # 处理流式响应
        print("\n📥 开始接收流式响应:\n")
        print("=" * 80)
        
        full_content = ""
        chunk_count = 0
        line_count = 0
        
        buffer = ""
        done_received = False
        
        for chunk in response.iter_content(chunk_size=8192, decode_unicode=True):
            if not chunk:
                continue
            
            buffer += chunk
            
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                line = line.strip()
                
                if not line:
                    continue
                
                line_count += 1
                
                if debug and line_count <= 5:
                    print(f"[DEBUG] 行 {line_count}: {repr(line[:150])}")
                
                data = parse_sse_line(line)
                
                if data is None:
                    continue
                
                if data.get("done"):
                    print("\n" + "=" * 80)
                    print("✅ 响应完成")
                    done_received = True
                    break
                
                if "choices" in data and len(data["choices"]) > 0:
                    delta = data["choices"][0].get("delta", {})
                    content = delta.get("content", "")
                    
                    if content:
                        print(content, end='', flush=True)
                        full_content += content
                        chunk_count += 1
                
                if done_received:
                    break
        
        print(f"\n\n📊 统计信息:")
        print(f"  - 处理后的行数: {line_count}")
        print(f"  - 接收到的chunk数量: {chunk_count}")
        print(f"  - 总内容长度: {len(full_content)} 字符")
        
        # 保存完整响应到文件
        if output_file:
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(full_content)
                print(f"  - 完整响应已保存到: {output_file}")
            except Exception as e:
                print(f"  - ⚠️ 保存响应失败: {e}")
        
    except requests.exceptions.Timeout:
        print("\n❌ 请求超时（超过15分钟）")
    except requests.exceptions.ConnectionError as e:
        print(f"\n❌ 连接错误: {e}")
        print("   请确保API服务正在运行")
    except requests.exceptions.HTTPError as e:
        print(f"\n❌ HTTP错误: {e}")
        print(f"   状态码: {e.response.status_code if hasattr(e, 'response') else 'N/A'}")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        if debug:
            import traceback
            traceback.print_exc()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="测试文献问答API服务",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 使用默认查询测试
  python test_api.py --txt test.pdf.txt

  # 指定查询
  python test_api.py --txt test.pdf.txt --query "What are the main contributions of this paper?"

  # 使用中文查询
  python test_api.py --txt test.pdf.txt --query "这篇论文的主要贡献是什么？"

  # 指定API URL
  python test_api.py --txt test.pdf.txt --url http://localhost:3000/paper_qa

  # 保存响应到文件
  python test_api.py --txt test.pdf.txt --output answer_result.txt

  # 启用调试模式
  python test_api.py --txt test.pdf.txt --debug
        """
    )
    
    parser.add_argument(
        "--url",
        type=str,
        default="http://localhost:3000/paper_qa",
        help="API端点URL (默认: http://localhost:3000/paper_qa)"
    )
    
    parser.add_argument(
        "--txt",
        type=str,
        required=True,
        help="包含base64编码PDF的txt文件路径"
    )
    
    parser.add_argument(
        "--query",
        type=str,
        default="Please carefully analyze and explain the reinforcement learning training methods used in this article.",
        help="查询字符串"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        help="输出文件路径（可选，保存完整响应）"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="启用调试模式，显示原始SSE数据"
    )
    
    args = parser.parse_args()
    
    # 运行测试
    test_paper_qa_api(
        api_url=args.url,
        txt_path=args.txt,
        query=args.query,
        output_file=args.output,
        debug=args.debug
    )


if __name__ == "__main__":
    main()

