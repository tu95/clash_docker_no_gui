# Clash Docker 一键启动工具

一个简单的Clash + YACD Docker部署工具，通过订阅链接一键启动。

## 文件说明

- `docker-compose.yml` - Docker服务配置
- `clash_docker.py` - 一键启动脚本
- `uninstall.py` - 一键卸载脚本

## 使用方法

### 1. 安装依赖

```bash
# 安装Python依赖
pip3 install pyyaml

# 或者使用apt安装
apt update && apt install -y python3-yaml
```

### 2. 准备配置文件

将你的Clash配置文件重命名为 `config.yaml` 并放在当前目录：

```bash
# 例如从ClashX Pro导出配置后重命名
mv ~/Downloads/clash_config.yaml config.yaml
```

### 3. 一键启动

```bash
# 直接启动
python3 clash_docker.py

# 查看代理状态
python3 clash_docker.py status
```

### 3. 访问服务

- **YACD管理界面**: http://服务器IP:8080
- **代理端口**: 7890 (混合代理), 7891 (SOCKS5)
- **API密钥**: dler

## 管理命令

```bash
# 查看服务状态
docker compose ps

# 查看日志
docker compose logs clash

# 停止服务
docker compose down

# 重启服务
docker compose restart

## 卸载

```bash
# 一键卸载
python3 uninstall.py
```

## 功能特点

✅ **一键启动**: 直接导入config.yaml文件启动  
✅ **自动获取**: 自动获取服务器IP和代理状态  
✅ **一键卸载**: 完全清理Docker环境  
✅ **自动过滤**: 自动过滤Auto - UrlTest  
✅ **Docker适配**: 自动适配Docker环境  
✅ **代理测试**: 自动测试代理连接  
✅ **中文界面**: 完整的中文提示  

## 注意事项

1. 确保Docker和Docker Compose已安装
2. 确保config.yaml文件格式正确
3. 配置文件必须是Clash YAML格式
4. 支持各种代理类型：ss、ssr、vmess、trojan等
5. 需要安装requests库：`pip3 install requests` 