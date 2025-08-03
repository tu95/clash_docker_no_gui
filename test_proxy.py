#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Clash Docker 代理连通性测试工具
"""

import os
import sys
import subprocess
import time
import requests
import urllib3

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def print_status(message, status="INFO"):
    """打印状态信息"""
    emoji_map = {
        "INFO": "ℹ️",
        "SUCCESS": "✅", 
        "ERROR": "❌",
        "WARNING": "⚠️",
        "PROCESSING": "🔄"
    }
    emoji = emoji_map.get(status, "ℹ️")
    print(f"{emoji} {message}")

def run_command(command):
    """运行命令"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr

def test_proxy(wait_time=5):
    """测试代理连通性"""
    print_status("开始连通性测试...", "PROCESSING")
    time.sleep(wait_time)  # 等待服务完全启动
    
    # 测试网站列表
    test_sites = [
        {"name": "Google", "url": "https://www.google.com"},
        {"name": "YouTube", "url": "https://www.youtube.com"},
        {"name": "GitHub", "url": "https://github.com"}
    ]
    
    success_count = 0
    total_count = len(test_sites)
    
    print_status("通过代理测试网站连通性:", "INFO")
    
    for site in test_sites:
        try:
            # 使用session来避免影响全局设置
            session = requests.Session()
            # 使用HTTP代理，Clash的7890端口支持HTTP代理
            session.proxies = {
                'http': 'http://127.0.0.1:7890', 
                'https': 'http://127.0.0.1:7890'
            }
            # 禁用SSL验证，避免SSL握手问题
            session.verify = False
            
            response = session.get(site['url'], timeout=10)
            if response.status_code == 200:
                print_status(f"✅ {site['name']}: 连接成功 (HTTP {response.status_code})", "SUCCESS")
                success_count += 1
            else:
                print_status(f"⚠️ {site['name']}: 连接异常 (HTTP {response.status_code})", "WARNING")
        except Exception as e:
            print_status(f"❌ {site['name']}: 连接失败 - {str(e)}", "ERROR")
    
    # 测试直连（应该失败）
    print_status("测试直连（应该失败）:", "INFO")
    try:
        response = requests.get('https://www.google.com', timeout=5)
        print_status("⚠️ 直连Google成功，可能代理未生效", "WARNING")
    except Exception as e:
        print_status("✅ 直连Google失败（正常，证明代理生效）", "SUCCESS")
    
    # 总结
    if success_count == total_count:
        print_status(f"🎉 连通性测试完成！所有{total_count}个网站均可正常访问", "SUCCESS")
        return True
    elif success_count > 0:
        print_status(f"⚠️ 连通性测试完成！{success_count}/{total_count}个网站可访问", "WARNING")
        return True
    else:
        print_status("❌ 连通性测试失败！所有网站均无法访问", "ERROR")
        return False

def main():
    """主函数"""
    print("🔍 Clash Docker 代理连通性测试")
    print("=" * 40)
    
    # 检查clash容器是否运行
    print_status("检查容器状态...", "PROCESSING")
    success, output = run_command("docker ps --filter name=clash --format '{{.Status}}'")
    if not success or "Up" not in output:
        print_status("❌ Clash容器未启动", "ERROR")
        print_status("请先运行: python3 start_clash_docker.py", "INFO")
        sys.exit(1)
    
    print_status("✅ Clash容器运行正常", "SUCCESS")
    
    # 执行连通性测试
    test_proxy()

if __name__ == "__main__":
    main() 