#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Clash Docker 一键启动工具
直接导入config.yaml文件启动Clash + YACD
支持自动获取服务器代理
"""

import os
import sys
import yaml
import subprocess
import time
import requests
import json
import zipfile
import tempfile
import secrets
import string

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

def get_server_ip():
    """获取服务器公网IP"""
    try:
        # 尝试多个IP查询服务
        services = [
            "https://api.ipify.org",
            "https://ifconfig.me",
            "https://icanhazip.com",
            "https://ipinfo.io/ip"
        ]
        
        for service in services:
            try:
                response = requests.get(service, timeout=5, proxies={'http': None, 'https': None})
                if response.status_code == 200:
                    ip = response.text.strip()
                    print_status(f"服务器IP: {ip}", "SUCCESS")
                    return ip
            except:
                continue
        
        print_status("无法获取服务器IP", "WARNING")
        return None
    except Exception as e:
        print_status(f"获取IP失败: {e}", "WARNING")
        return None

def get_proxy_info():
    """获取代理信息"""
    # 等待API端口准备就绪
    max_retries = 10
    for i in range(max_retries):
        try:
            # 从本地文件读取密钥
            secret = load_secret_from_file()
            if not secret:
                secret = 'dler'  # 如果读取失败，使用默认值
            
            # 测试API连接 - 使用本地地址
            response = requests.get(
                "http://127.0.0.1:9090/proxies",
                headers={"Authorization": f"Bearer {secret}"},
                timeout=3
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # 获取代理组信息
                proxy_groups = {}
                for name, info in data.get('proxies', {}).items():
                    if info.get('type') == 'Selector':
                        proxy_groups[name] = {
                            'now': info.get('now'),
                            'all': info.get('all', [])
                        }
                
                return proxy_groups
            else:
                print_status(f"API响应错误: {response.status_code}", "WARNING")
                return None
                
        except requests.exceptions.ConnectionError:
            if i < max_retries - 1:
                print_status(f"等待API端口准备就绪... ({i+1}/{max_retries})", "PROCESSING")
                time.sleep(2)
            else:
                print_status("API端口连接超时，Clash可能还在启动中", "WARNING")
                return None
        except Exception as e:
            print_status(f"获取代理信息失败: {e}", "ERROR")
            return None
    
    return None

def show_proxy_status():
    """显示代理状态"""
    print_status("检查容器状态...", "PROCESSING")
    
    # 检查clash容器是否运行
    success, output = run_command("docker ps --filter name=clash --format '{{.Status}}'")
    if not success or "Up" not in output:
        print_status("❌ Clash容器未启动", "ERROR")
        print_status("请先运行: python3 start_clash_docker.py", "INFO")
        sys.exit(1)
    
    print_status("✅ Clash容器运行正常", "SUCCESS")
    print_status("获取代理状态...", "PROCESSING")
    
    # 获取服务器IP
    server_ip = get_server_ip()
    
    # 获取代理信息
    proxy_info = get_proxy_info()
    
    if proxy_info:
        print("\n📊 代理统计:")
        print("=" * 50)
        
        total_groups = len(proxy_info)
        total_proxies = sum(len(info.get('all', [])) for info in proxy_info.values())
        
        print(f"🔗 代理组数量: {total_groups}")
        print(f"📡 总代理数量: {total_proxies}")
        
        for group_name, info in proxy_info.items():
            current = info.get('now', 'Unknown')
            all_proxies = info.get('all', [])
            print(f"   • {group_name}: {len(all_proxies)} 个代理 (当前: {current})")
    else:
        print("\n⚠️  代理信息获取失败")
        print("可能的原因:")
        print("  • Clash服务还在启动中")
        print("  • API端口未就绪")
        print("  • 配置文件有问题")
        print("建议:")
        print("  • 等待几分钟后重试: python3 test_proxy.py")
        print("  • 查看日志: docker compose logs clash")
    
    # 读取生成的密钥
    secret = load_secret_from_file()
    if not secret:
        secret = 'dler'
    
    if server_ip:
        print("🌐 访问信息:")
        print("=" * 50)
        print(f"YACD管理界面: http://{server_ip}:8080")
        print(f"----- 在yacd页面中输入URL还有API密钥 -----")
        print(f"API端口: http://127.0.0.1:9090")
        print(f"API密钥: {secret}")
        print(f"使用代理：http://127.0.0.1:7890")
        print("设置终端代理：")
        print(f"export http_proxy=http://127.0.0.1:7890")
        print(f"export https_proxy=http://127.0.0.1:7890")

def load_config(file_path):
    """加载配置文件"""
    print_status(f"正在读取配置文件: {file_path}", "PROCESSING")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        if not config:
            print_status("配置文件为空", "ERROR")
            return None
            
        if 'proxies' not in config:
            print_status("配置文件中没有找到proxies节点", "ERROR")
            print_status(f"配置文件包含的键: {list(config.keys())}", "INFO")
            return None
            
        print_status(f"发现 {len(config.get('proxies', []))} 个代理节点", "SUCCESS")
        return config
        
    except FileNotFoundError:
        print_status(f"配置文件不存在: {file_path}", "ERROR")
        return None
    except yaml.YAMLError as e:
        print_status(f"YAML解析失败: {e}", "ERROR")
        return None
    except Exception as e:
        print_status(f"读取文件失败: {e}", "ERROR")
        return None

def generate_random_secret(length=64):
    """生成随机密钥"""
    characters = string.ascii_letters + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))

def save_secret_to_file(secret):
    """保存密钥到本地文件"""
    try:
        with open("clash_secret.txt", 'w') as f:
            f.write(secret)
        print_status("API密钥已保存到: clash_secret.txt", "SUCCESS")
        return True
    except Exception as e:
        print_status(f"保存密钥失败: {e}", "ERROR")
        return False

def load_secret_from_file():
    """从本地文件读取密钥"""
    try:
        if os.path.exists("clash_secret.txt"):
            with open("clash_secret.txt", 'r') as f:
                return f.read().strip()
        return None
    except:
        return None

def create_docker_config(config):
    """创建Docker环境配置"""
    # 检查是否已有密钥文件
    secret = load_secret_from_file()
    if not secret:
        # 生成新的随机密钥
        secret = generate_random_secret()
        # 保存到文件
        save_secret_to_file(secret)
    else:
        print_status("使用已存在的API密钥", "INFO")
    
    # 设置Docker环境需要的配置
    config['port'] = 7890
    config['socks-port'] = 7891
    config['mixed-port'] = 7890
    config['allow-lan'] = True
    config['mode'] = 'Rule'
    config['log-level'] = 'info'
    config['external-controller'] = '0.0.0.0:9090'
    # 强制使用本地文件中的密钥，覆盖原始配置中的secret
    config['secret'] = secret
    
    # 添加DNS配置
    config['dns'] = {
        'enable': True,
        'listen': '0.0.0.0:53',
        'default-nameserver': [
            '223.5.5.5',
            '119.29.29.29'
        ],
        'nameserver': [
            'https://doh.pub/dns-query',
            'https://dns.alidns.com/dns-query'
        ],
        'fallback': [
            'https://doh.pub/dns-query',
            'https://dns.alidns.com/dns-query'
        ],
        'fallback-filter': {
            'geoip': True,
            'ipcidr': [
                '240.0.0.0/4',
                '0.0.0.0/32'
            ]
        }
    }
    
    # 过滤Auto - UrlTest
    if 'proxy-groups' in config:
        for group in config['proxy-groups']:
            if isinstance(group, dict) and 'proxies' in group:
                if isinstance(group['proxies'], list):
                    group['proxies'] = [
                        proxy for proxy in group['proxies'] 
                        if 'Auto - UrlTest' not in str(proxy)
                    ]
                if 'all' in group and isinstance(group['all'], list):
                    group['all'] = [
                        proxy for proxy in group['all'] 
                        if 'Auto - UrlTest' not in str(proxy)
                    ]
    
    # 过滤proxies中的Auto - UrlTest
    if 'proxies' in config:
        config['proxies'] = [
            proxy for proxy in config['proxies']
            if isinstance(proxy, dict) and 'Auto - UrlTest' not in proxy.get('name', '')
        ]
    
    # 移除不兼容的高级功能
    if 'script' in config:
        del config['script']
    if 'rule-providers' in config:
        del config['rule-providers']
    
    # 创建简化的rules
    config['rules'] = [
        'DOMAIN-SUFFIX,google.com,Proxy',
        'DOMAIN-SUFFIX,facebook.com,Proxy',
        'DOMAIN-SUFFIX,youtube.com,Proxy',
        'DOMAIN-SUFFIX,twitter.com,Proxy',
        'DOMAIN-SUFFIX,instagram.com,Proxy',
        'DOMAIN-SUFFIX,github.com,Proxy',
        'DOMAIN-SUFFIX,githubusercontent.com,Proxy',
        'DOMAIN-SUFFIX,netflix.com,Proxy',
        'DOMAIN-SUFFIX,spotify.com,Proxy',
        'DOMAIN-SUFFIX,telegram.org,Proxy',
        'DOMAIN-SUFFIX,whatsapp.com,Proxy',
        'DOMAIN-SUFFIX,amazon.com,Proxy',
        'DOMAIN-SUFFIX,cloudflare.com,Proxy',
        'DOMAIN-SUFFIX,baidu.com,DIRECT',
        'DOMAIN-SUFFIX,qq.com,DIRECT',
        'DOMAIN-SUFFIX,taobao.com,DIRECT',
        'DOMAIN-SUFFIX,jd.com,DIRECT',
        'DOMAIN-SUFFIX,163.com,DIRECT',
        'DOMAIN-SUFFIX,126.com,DIRECT',
        'DOMAIN-SUFFIX,sina.com.cn,DIRECT',
        'DOMAIN-SUFFIX,weibo.com,DIRECT',
        'DOMAIN-SUFFIX,alipay.com,DIRECT',
        'DOMAIN-SUFFIX,wechat.com,DIRECT',
        'DOMAIN-SUFFIX,tencent.com,DIRECT',
        'DOMAIN-SUFFIX,alibaba.com,DIRECT',
        'DOMAIN-SUFFIX,aliyun.com,DIRECT',
        'DOMAIN-SUFFIX,tencent.com,DIRECT',
        'DOMAIN-SUFFIX,qq.com,DIRECT',
        'DOMAIN-SUFFIX,weixin.qq.com,DIRECT',
        'DOMAIN-SUFFIX,wechat.com,DIRECT',
        'DOMAIN-SUFFIX,weibo.com,DIRECT',
        'DOMAIN-SUFFIX,sina.com.cn,DIRECT',
        'DOMAIN-SUFFIX,163.com,DIRECT',
        'DOMAIN-SUFFIX,126.com,DIRECT',
        'DOMAIN-SUFFIX,baidu.com,DIRECT',
        'DOMAIN-SUFFIX,taobao.com,DIRECT',
        'DOMAIN-SUFFIX,jd.com,DIRECT',
        'DOMAIN-SUFFIX,tmall.com,DIRECT',
        'DOMAIN-SUFFIX,alipay.com,DIRECT',
        'DOMAIN-SUFFIX,alibaba.com,DIRECT',
        'DOMAIN-SUFFIX,aliyun.com,DIRECT',
        'DOMAIN-SUFFIX,tencent.com,DIRECT',
        'DOMAIN-SUFFIX,qq.com,DIRECT',
        'DOMAIN-SUFFIX,weixin.qq.com,DIRECT',
        'DOMAIN-SUFFIX,wechat.com,DIRECT',
        'DOMAIN-SUFFIX,weibo.com,DIRECT',
        'DOMAIN-SUFFIX,sina.com.cn,DIRECT',
        'DOMAIN-SUFFIX,163.com,DIRECT',
        'DOMAIN-SUFFIX,126.com,DIRECT',
        'DOMAIN-SUFFIX,baidu.com,DIRECT',
        'DOMAIN-SUFFIX,taobao.com,DIRECT',
        'DOMAIN-SUFFIX,jd.com,DIRECT',
        'DOMAIN-SUFFIX,tmall.com,DIRECT',
        'DOMAIN-SUFFIX,alipay.com,DIRECT',
        'DOMAIN-SUFFIX,alibaba.com,DIRECT',
        'DOMAIN-SUFFIX,aliyun.com,DIRECT',
        'GEOIP,CN,DIRECT',
        'MATCH,Proxy'
    ]
    
    return config

def download_country_mmdb():
    """下载Country.mmdb文件"""
    print_status("正在下载Country.mmdb文件...", "PROCESSING")
    
    # Country.mmdb下载地址 - 使用release版本
    
    mmdb_url = "https://github.com/Dreamacro/maxmind-geoip/releases/latest/download/Country.mmdb"
    github_mirror_url = "https://gh-proxy.com/https://github.com/Dreamacro/maxmind-geoip/releases/latest/download/Country.mmdb"
    mmdb_file = "Country.mmdb"
    
    try:
        # 直接下载Country.mmdb文件
        print_status(f"下载Country.mmdb文件:{github_mirror_url}", "PROCESSING")
        response = requests.get(github_mirror_url, timeout=30)
        response.raise_for_status()
        
        # 保存文件到当前目录
        target_path = mmdb_file
        with open(target_path, 'wb') as f:
            f.write(response.content)
        
        print_status(f"Country.mmdb文件已下载到: {target_path}", "SUCCESS")
        return True
                
    except requests.exceptions.RequestException as e:
        print_status(f"下载失败: {e}", "ERROR")
        return False
    except zipfile.BadZipFile:
        print_status("下载的文件不是有效的zip格式", "ERROR")
        return False
    except Exception as e:
        print_status(f"处理文件失败: {e}", "ERROR")
        return False

def save_config(config, file_path):
    """保存配置到文件"""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        print_status(f"配置已保存到: {file_path}", "SUCCESS")
        return True
    except Exception as e:
        print_status(f"保存配置失败: {e}", "ERROR")
        return False

def run_command(command):
    """运行命令"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr

def start_services():
    """启动Docker服务"""
    print_status("正在启动Docker服务...", "PROCESSING")
    
    # 停止现有服务
    run_command("docker compose down")
    
    # 检查Country.mmdb文件是否存在
    mmdb_path = "Country.mmdb"
    if not os.path.exists(mmdb_path):
        print_status("Country.mmdb文件不存在，尝试下载...", "WARNING")
        if not download_country_mmdb():
            print_status("Country.mmdb下载失败，继续启动服务...", "WARNING")
    
    # 启动服务
    success, output = run_command("docker compose up -d")
    if not success:
        print_status(f"启动服务失败: {output}", "ERROR")
        return False
    
    # 如果Country.mmdb文件存在，复制到容器中
    if os.path.exists(mmdb_path):
        print_status("正在将Country.mmdb文件复制到容器中...", "PROCESSING")
        # 先确保容器内的目录存在
        run_command("docker exec clash mkdir -p /root/.config/clash")
        # 复制文件到容器
        success, output = run_command(f"docker cp {mmdb_path} clash:/root/.config/clash/")
        if success:
            print_status("Country.mmdb文件已成功复制到容器", "SUCCESS")
            # 重启clash容器以加载新的Country.mmdb文件
            print_status("重启clash容器以加载Country.mmdb...", "PROCESSING")
            run_command("docker restart clash")
        else:
            print_status(f"复制Country.mmdb到容器失败: {output}", "WARNING")
    
    print_status("Docker服务启动成功", "SUCCESS")
    return True

def check_service_status():
    """检查服务状态"""
    print_status("检查服务状态...", "PROCESSING")
    
    success, output = run_command("docker compose ps")
    if not success:
        print_status(f"检查服务状态失败: {output}", "ERROR")
        return False
    
    if "Up" in output:
        print_status("服务运行正常", "SUCCESS")
        print(output)
        return True
    else:
        print_status("服务未正常运行", "ERROR")
        return False



def get_yaml_files():
    """获取当前目录下所有的.yaml文件"""
    yaml_files = []
    for file in os.listdir('.'):
        if file.endswith('.yaml') or file.endswith('.yml') and file != 'docker-compose.yml':
            yaml_files.append(file)
    return sorted(yaml_files)

def select_config_file():
    """选择配置文件"""
    yaml_files = get_yaml_files()
    
    if not yaml_files:
        print_status("当前目录下没有找到.yaml或.yml文件", "ERROR")
        print_status("请将Clash配置文件放在当前目录", "INFO")
        sys.exit(1)
    
    if len(yaml_files) == 1:
        print_status(f"发现配置文件: {yaml_files[0]}", "SUCCESS")
        return yaml_files[0]
    
    # 多个文件时让用户选择
    print_status(f"发现 {len(yaml_files)} 个配置文件:", "INFO")
    print("=" * 50)
    for i, file in enumerate(yaml_files, 1):
        print(f"  {i}. {file}")
    print("=" * 50)
    
    while True:
        try:
            choice = input(f"请选择配置文件 (1-{len(yaml_files)}): ").strip()
            choice_num = int(choice)
            if 1 <= choice_num <= len(yaml_files):
                selected_file = yaml_files[choice_num - 1]
                print_status(f"已选择: {selected_file}", "SUCCESS")
                return selected_file
            else:
                print_status(f"请输入 1-{len(yaml_files)} 之间的数字", "WARNING")
        except ValueError:
            print_status("请输入有效的数字", "WARNING")

def main():
    """主函数"""
    print("🚀 Clash Docker 一键启动工具")
    print("============================")
    
    # 检查命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        show_proxy_status()
        print("\n" + "="*50)
        # 调用独立的测试脚本
        os.system("python3 test_proxy.py")
        return
    
    # 选择配置文件
    config_file = select_config_file()
    
    # 加载配置文件
    config = load_config(config_file)
    if not config:
        sys.exit(1)
    
    # 创建Docker配置
    config = create_docker_config(config)
    
    # 保存配置
    if not save_config(config, "config/config.yaml"):
        sys.exit(1)
    
    # 启动服务
    if not start_services():
        sys.exit(1)
    
    # 检查服务状态
    if not check_service_status():
        sys.exit(1)
    
    print("\n🎉 启动完成！")
    
    # 获取服务器IP用于显示访问信息
    server_ip = get_server_ip()
    
    # 读取生成的密钥
    secret = load_secret_from_file()
    if not secret:
        secret = 'dler'
    
    print("\n🌐 访问信息:")
    print("=" * 50)
    if server_ip:
        print(f"YACD管理界面: http://{server_ip}:8080")
        print(f"代理端口: {server_ip}:7890 (HTTP/SOCKS5)")
    else:
        print("YACD管理界面: http://服务器IP:8080")
        print("代理端口: 服务器IP:7890 (HTTP/SOCKS5)")

    print("=" * 50)
    print("\n")
    print("在yacd页面中输入URL还有API密钥:")
    print("API端口: http://127.0.0.1:9090")
    print(f"API密钥: {secret}")
        
    print("\n💡 查看密码: python3 show_secret.py")
    print("\n💡 测试连通性: python3 test_proxy.py")
    print("\n💡 卸载服务: python3 uninstall.py")

if __name__ == "__main__":
    main() 