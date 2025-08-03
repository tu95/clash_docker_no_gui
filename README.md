# Clash Docker 一键启动工具

适用于linux服务器无gui图形页面环境。通过docker启动Clash + YACD控制面板来管理代理clash，为本机设置代理。

## 使用步骤

### 1. 安装依赖
```bash
pip3 install pyyaml requests
```

### 2. 准备配置文件
将Clash配置文件（.yaml或.yml格式）放在当前目录：
```bash
mv ~/Downloads/clash_config.yaml ./config.yaml
```

### 3. 一键启动
```bash
python3 start_clash_docker.py
```

### 4. 测试和使用
```bash
# 测试代理连通性
python3 test_proxy.py

# 查看API密钥
cat clash_secret.txt

# 查看代理状态
python3 show_secret.py
```

### 5. 访问服务
在yacd输入API Base URL和Secret
- **YACD管理界面**: http://服务器IP:8080
- **代理端口**: http://127.0.0.1:7890 (HTTP/SOCKS5)
- **API端口**: http://127.0.0.1:9090

### 6. 卸载服务
```bash
python3 uninstall.py
```

## 代理使用

### 命令行使用
```bash
# HTTP代理
curl --proxy http://127.0.0.1:7890 http://httpbin.org/ip

# 设置环境变量
export http_proxy=http://127.0.0.1:7890
export https_proxy=http://127.0.0.1:7890
```

### 浏览器配置
- **代理地址**: 127.0.0.1
- **代理端口**: 7890
- **代理类型**: HTTP/SOCKS5

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
```

## 文件说明

- `start_clash_docker.py` - 一键启动脚本
- `test_proxy.py` - 代理测试脚本
- `uninstall.py` - 卸载脚本
- `config/config.yaml` - Clash配置文件
- `clash_secret.txt` - API密钥文件

