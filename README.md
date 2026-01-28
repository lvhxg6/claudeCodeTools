# 会议录音智能总结系统

🎙️ 将会议录音自动转写为文字，并通过 AI 智能分析生成结构化的会议总结报告。

## 功能特性

- **音频上传**：支持拖拽上传，支持 mp3、wav、m4a 格式
- **语音转写**：集成本地 Whisper 服务，自动将音频转为文字
- **智能总结**：通过 Claude CLI 生成业务导向的会议总结
- **多轮对话**：支持追问和协作编辑总结内容
- **版本管理**：自动保存总结历史版本
- **导出功能**：支持导出 Markdown 格式文件

## 系统架构

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Web 前端      │────▶│  FastAPI 后端   │────▶│  Whisper 服务   │
│  (HTML/JS/CSS)  │     │                 │     │  (localhost:8765)│
└─────────────────┘     │                 │     └─────────────────┘
                        │                 │
                        │                 │────▶┌─────────────────┐
                        │                 │     │  Claude CLI     │
                        └─────────────────┘     └─────────────────┘
```

## 快速开始

### 前置条件

1. Python 3.10+
2. 本地 Whisper 服务（运行在 localhost:8765）
3. Claude CLI 已安装并配置

### 安装

```bash
# 克隆项目
git clone https://github.com/lvhxg6/claudeCodeTools.git
cd claudeCodeTools

# 安装依赖
pip install -r requirements.txt
```

### 启动

```bash
# 方式一：使用启动脚本
./start.sh

# 方式二：直接运行
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

启动后访问 http://localhost:8000

## 配置说明

编辑 `config.yaml` 文件：

```yaml
# Whisper 服务配置
whisper:
  url: "http://localhost:8765"  # Whisper 服务地址
  timeout: 300                   # 超时时间（秒）
  language: "zh"                 # 默认语言

# Claude CLI 配置
claude:
  command: "claude"              # Claude CLI 命令
  timeout: 120                   # 超时时间（秒）

# 服务器配置
server:
  host: "0.0.0.0"
  port: 8000
  upload_max_size: 100           # 上传文件大小限制（MB）
```

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/health` | GET | 健康检查 |
| `/api/upload` | POST | 上传音频文件 |
| `/api/chat` | POST | 对话/编辑请求 |
| `/api/finalize` | POST | 确认生成最终版本 |
| `/api/download/{session_id}` | GET | 下载 Markdown 文件 |

## 项目结构

```
.
├── src/
│   ├── main.py              # FastAPI 主应用
│   ├── config_manager.py    # 配置管理
│   ├── models.py            # 数据模型
│   ├── session_manager.py   # 会话管理
│   ├── audio_service.py     # 音频处理
│   ├── transcription_service.py  # 转写服务
│   ├── summary_service.py   # 总结服务
│   └── chat_service.py      # 对话服务
├── static/
│   ├── index.html           # 前端页面
│   └── app.js               # 前端逻辑
├── tests/
│   ├── unit/                # 单元测试
│   └── property/            # 属性测试
├── config.yaml              # 配置文件
├── requirements.txt         # 依赖列表
├── start.sh                 # 启动脚本
└── README.md
```

## 测试

```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行单元测试
python -m pytest tests/unit/ -v

# 运行属性测试
python -m pytest tests/property/ -v
```

## 使用流程

1. 打开浏览器访问 http://localhost:8000
2. 拖拽或点击上传音频文件
3. 等待转写和总结生成
4. 在对话区域提问或请求修改
5. 满意后点击"确认生成"
6. 导出 Markdown 文件

## 技术栈

- **后端**：Python, FastAPI, Uvicorn
- **前端**：HTML, CSS, JavaScript, Marked.js
- **测试**：Pytest, Hypothesis
- **外部服务**：Whisper API, Claude CLI

## License

MIT
