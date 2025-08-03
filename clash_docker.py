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
            # 测试API连接 - 使用服务器IP
            response = requests.get(
                "http://117.72.118.25:9090/proxies",
                headers={"Authorization": "Bearer dler"},
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
    print_status("获取代理状态...", "PROCESSING")
    
    # 获取服务器IP
    server_ip = get_server_ip()
    
    # 获取代理信息
    proxy_info = get_proxy_info()
    
    if proxy_info:
        print("\n📊 代理状态:")
        print("=" * 50)
        
        for group_name, info in proxy_info.items():
            current = info.get('now', 'Unknown')
            all_proxies = info.get('all', [])
            
            print(f"🔗 {group_name}:")
            print(f"   当前选择: {current}")
            print(f"   可用代理: {len(all_proxies)} 个")
            
            # 显示前5个代理
            if all_proxies:
                print("   代理列表:")
                for i, proxy in enumerate(all_proxies[:5]):
                    print(f"     {i+1}. {proxy}")
                if len(all_proxies) > 5:
                    print(f"     ... 还有 {len(all_proxies) - 5} 个")
            print()
    else:
        print("\n⚠️  代理信息获取失败")
        print("可能的原因:")
        print("  • Clash服务还在启动中")
        print("  • API端口未就绪")
        print("  • 配置文件有问题")
        print("建议:")
        print("  • 等待几分钟后重试: python3 clash_docker.py status")
        print("  • 查看日志: docker compose logs clash")
    
    if server_ip:
        print("🌐 访问信息:")
        print("=" * 50)
        print(f"YACD管理界面: http://{server_ip}:8080")
        print(f"代理端口: {server_ip}:7890 (HTTP/SOCKS5)")
        print(f"API端口: {server_ip}:9090")
        print(f"API密钥: dler")

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

def create_docker_config(config):
    """创建Docker环境配置"""
    # 设置Docker环境需要的配置
    config['port'] = 7890
    config['socks-port'] = 7891
    config['mixed-port'] = 7890
    config['allow-lan'] = True
    config['mode'] = 'Rule'
    config['log-level'] = 'info'
    config['external-controller'] = '0.0.0.0:9090'
    config['secret'] = 'dler'
    
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
            session.proxies = {'http': 'http://127.0.0.1:7890', 'https': 'http://127.0.0.1:7890'}
            
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
    print("🚀 Clash Docker 一键启动工具")
    print("============================")
    
    # 检查命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        show_proxy_status()
        print("\n" + "="*50)
        test_proxy(wait_time=2)  # status命令使用较短的等待时间
        return
    
    # 配置文件路径
    config_file = "config.yaml"
    
    # 检查配置文件是否存在
    if not os.path.exists(config_file):
        print_status(f"配置文件不存在: {config_file}", "ERROR")
        print_status("请将Clash配置文件重命名为 'config.yaml' 并放在当前目录", "INFO")
        sys.exit(1)
    
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
    
    # 测试代理
    test_proxy()
    
    print("\n🎉 启动完成！")
    
    # 显示代理状态
    show_proxy_status()
    
    print("\n💡 管理命令:")
    print("   查看状态: python3 clash_docker.py status")
    print("   查看日志: docker compose logs clash")
    print("   停止服务: docker compose down")
    print("   重启服务: docker compose restart")

if __name__ == "__main__":
    main() 