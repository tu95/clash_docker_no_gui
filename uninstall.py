#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Clash Docker 一键卸载工具
"""

import os
import sys
import subprocess
import shutil
import glob

def run(cmd):
    """运行命令"""
    try:
        subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError:
        return False

def print_status(msg, status="INFO"):
    emoji = {"INFO": "ℹ️", "SUCCESS": "✅", "ERROR": "❌", "WARNING": "⚠️", "PROCESSING": "🔄"}
    print(f"{emoji.get(status, 'ℹ️')} {msg}")

def main():
    print("🗑️  Clash Docker 一键卸载")
    print("=" * 30)
    
    # 确认卸载
    print_status("将删除以下内容:", "WARNING")
    print("  • Docker容器: clash, yacd")
    print("  • Docker镜像: dreamacro/clash, haishanh/yacd")
    print("  • 配置文件: config/, Country.mmdb")
    print("  • 网络和卷")
    
    if input("\n确认卸载? (输入 yes): ").lower() != 'yes':
        print_status("取消卸载", "INFO")
        return
    
    print("\n开始卸载...")
    
    # 停止服务
    print_status("停止Docker服务...", "PROCESSING")
    run("docker compose down")
    
    # 删除容器
    print_status("删除容器...", "PROCESSING")
    for container in ["clash", "yacd"]:
        if run(f"docker rm -f {container}"):
            print_status(f"已删除容器: {container}", "SUCCESS")
    
    # 删除镜像
    print_status("删除镜像...", "PROCESSING")
    for image in ["dreamacro/clash:latest", "haishanh/yacd:latest"]:
        if run(f"docker rmi {image}"):
            print_status(f"已删除镜像: {image}", "SUCCESS")
    
    # 删除文件
    print_status("删除文件...", "PROCESSING")
    files_to_remove = [
        "config",
        "Country.mmdb", 
        "clash-linux-amd64-v1.18.0"
    ]
    
    for item in files_to_remove:
        if os.path.exists(item):
            try:
                if os.path.isdir(item):
                    shutil.rmtree(item)
                else:
                    os.remove(item)
                print_status(f"已删除: {item}", "SUCCESS")
            except Exception as e:
                print_status(f"删除失败: {item} - {e}", "WARNING")
    
    # 删除备份文件
    for backup_file in glob.glob("config/config.yaml.backup.*"):
        try:
            os.remove(backup_file)
            print_status(f"已删除备份: {backup_file}", "SUCCESS")
        except:
            pass
    
    # 清理Docker
    print_status("清理Docker...", "PROCESSING")
    run("docker system prune -f")
    run("docker volume prune -f")
    run("docker network prune -f")
    
    print("\n🎉 卸载完成!")
    print("💡 如需重新安装，运行: python3 clash_docker.py")

if __name__ == "__main__":
    main() 