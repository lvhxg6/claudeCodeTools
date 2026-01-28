#!/bin/bash

# 会议录音智能总结系统启动脚本
# Meeting Summary System Startup Script

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 显示 Banner
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║${NC}        🎙️  会议录音智能总结系统                        ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}        Meeting Summary System                          ${BLUE}║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 检查 Python
print_info "检查 Python 环境..."
if ! command -v python &> /dev/null; then
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    else
        print_error "未找到 Python，请先安装 Python 3.10+"
        exit 1
    fi
else
    PYTHON_CMD="python"
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2)
print_success "Python 版本: $PYTHON_VERSION"

# 检查依赖
print_info "检查依赖..."
if ! $PYTHON_CMD -c "import fastapi" &> /dev/null; then
    print_warning "依赖未安装，正在安装..."
    $PYTHON_CMD -m pip install -r requirements.txt
    print_success "依赖安装完成"
else
    print_success "依赖已安装"
fi

# 检查配置文件
if [ ! -f "config.yaml" ]; then
    print_warning "配置文件不存在，使用默认配置"
fi

# 从配置文件读取端口（如果存在）
PORT=8000
HOST="0.0.0.0"
if [ -f "config.yaml" ]; then
    CONFIG_PORT=$(grep -A2 "^server:" config.yaml | grep "port:" | awk '{print $2}' | tr -d '\r')
    CONFIG_HOST=$(grep -A2 "^server:" config.yaml | grep "host:" | awk '{print $2}' | tr -d '"' | tr -d '\r')
    if [ -n "$CONFIG_PORT" ]; then
        PORT=$CONFIG_PORT
    fi
    if [ -n "$CONFIG_HOST" ]; then
        HOST=$CONFIG_HOST
    fi
fi

# 检查端口是否被占用
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    print_warning "端口 $PORT 已被占用"
    read -p "是否终止占用进程? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        lsof -ti:$PORT | xargs kill -9 2>/dev/null || true
        print_success "已终止占用进程"
    else
        print_error "请手动释放端口 $PORT 后重试"
        exit 1
    fi
fi

# 检查 Whisper 服务
print_info "检查 Whisper 服务..."
WHISPER_URL="http://localhost:8765"
if [ -f "config.yaml" ]; then
    CONFIG_WHISPER=$(grep -A2 "^whisper:" config.yaml | grep "url:" | awk '{print $2}' | tr -d '"' | tr -d '\r')
    if [ -n "$CONFIG_WHISPER" ]; then
        WHISPER_URL=$CONFIG_WHISPER
    fi
fi

if curl -s --connect-timeout 2 "$WHISPER_URL/health" > /dev/null 2>&1; then
    print_success "Whisper 服务可用: $WHISPER_URL"
else
    print_warning "Whisper 服务不可用: $WHISPER_URL"
    print_warning "请确保 Whisper 服务已启动"
fi

# 检查 Claude CLI
print_info "检查 Claude CLI..."
if command -v claude &> /dev/null; then
    print_success "Claude CLI 已安装"
else
    print_warning "Claude CLI 未找到，总结功能可能不可用"
fi

echo ""
print_info "启动服务..."
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  🌐 访问地址: ${GREEN}http://localhost:$PORT${NC}"
echo -e "  📖 API 文档: ${GREEN}http://localhost:$PORT/docs${NC}"
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  按 ${YELLOW}Ctrl+C${NC} 停止服务"
echo ""

# 启动服务
$PYTHON_CMD -m uvicorn src.main:app --host "$HOST" --port "$PORT" --reload
