#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
显示当前Clash API密钥
"""

import yaml
import os
def show_ip_port():
    """显示clash的公网IP和端口"""
    import requests
    
    # 检查密钥文件是否存在
    secret_path = "clash_secret.txt"
    if not os.path.exists(secret_path):
        print("❌ 密钥文件不存在，请先启动Clash")
        print("💡 运行: python3 start_clash_docker.py")
        return
    
    try:
        # 获取公网IP
        try:
            response = requests.get("https://ifconfig.me", timeout=5)
            public_ip = response.text.strip()
        except:
            try:
                response = requests.get("https://icanhazip.com", timeout=5)
                public_ip = response.text.strip()
            except:
                public_ip = "服务器IP"
        
        # 读取密钥
        with open(secret_path, 'r') as f:
            secret = f.read().strip()
        
        print(f"🌐 http://127.0.0.1:9090")
        print(f"🔑 {secret}")
        
    except Exception as e:
        print(f"❌ 读取失败: {e}")

def show_secret():
    """显示API密钥"""
    secret_path = "clash_secret.txt"
    
    if not os.path.exists(secret_path):
        print("❌ 密钥文件不存在，请先启动Clash")
        print("💡 运行: python3 start_clash_docker.py")
        return
    
    try:
        with open(secret_path, 'r') as f:
            secret = f.read().strip()
        
        print("🔑 Clash API 密钥")
        print("=" * 50)
        print(f"密钥: {secret}")
        print("=" * 50)
        print("💡 使用方式:")
        print("  • 在API请求头中添加: Authorization: Bearer {密钥}")
        print("  • 在YACD中配置API密钥")
        print("  • 在Clash客户端中配置API密钥")
        
    except Exception as e:
        print(f"❌ 读取密钥文件失败: {e}")

if __name__ == "__main__":
    show_ip_port()
    # show_secret() 