# 实现计划：会议录音智能总结系统

## 概述

本实现计划将设计文档转化为可执行的编码任务，采用增量开发方式，每个任务都建立在前一个任务的基础上。使用 Python FastAPI 作为后端框架，HTML/CSS/JavaScript 实现前端界面。

## 任务列表

- [x] 1. 项目初始化与基础架构
  - [x] 1.1 创建项目目录结构和基础文件
    - 创建 `src/`、`tests/`、`static/` 目录
    - 创建 `requirements.txt` 依赖文件
    - 创建 `config.yaml` 配置文件模板
    - _Requirements: 7.1, 7.2_
  
  - [x] 1.2 实现 ConfigManager 配置管理器
    - 实现 YAML 配置文件加载
    - 实现默认配置回退逻辑
    - 实现 `get_whisper_url()` 和 `get_claude_command()` 方法
    - _Requirements: 7.1, 7.2, 7.3, 7.4_
  
  - [x] 1.3 编写 ConfigManager 属性测试
    - **Property 9: 配置加载正确性**
    - **Property 10: 默认配置回退**
    - **Validates: Requirements 7.1, 7.2, 7.4**

- [x] 2. 数据模型与会话管理
  - [x] 2.1 实现数据模型类
    - 实现 `Session`、`Summary`、`ChatMessage` 数据类
    - 实现数据序列化和反序列化方法
    - _Requirements: 5.4, 6.1, 6.7_
  
  - [x] 2.2 实现 SessionManager 会话管理器
    - 实现 `create_session()`、`get_session()`、`update_session()`、`delete_session()` 方法
    - 实现会话内存存储
    - _Requirements: 5.4, 5.5_
  
  - [x] 2.3 编写会话管理属性测试
    - **Property 4: 会话历史保持**
    - **Property 5: 新会话清空历史**
    - **Property 6: 新总结为草稿状态**
    - **Validates: Requirements 5.4, 5.5, 6.1**

- [x] 3. 检查点 - 基础架构验证
  - 确保所有测试通过，如有问题请询问用户

- [ ] 4. 文件上传与验证服务
  - [x] 4.1 实现文件格式验证函数
    - 实现 `validate_audio_format()` 函数
    - 支持 mp3、wav、m4a 格式验证
    - _Requirements: 1.2, 1.3_
  
  - [x] 4.2 编写文件验证属性测试
    - **Property 1: 文件格式验证**
    - **Validates: Requirements 1.2**
  
  - [ ] 4.3 实现文件上传 API 端点
    - 实现 `POST /api/upload` 端点
    - 实现文件大小限制检查
    - 实现文件临时存储
    - _Requirements: 1.2, 1.3, 1.4, 1.5_

- [ ] 5. 转写服务集成
  - [ ] 5.1 实现 TranscriptionService 转写服务
    - 实现 `transcribe()` 方法调用 Whisper API
    - 实现 `check_health()` 健康检查方法
    - 使用 OpenAI 兼容的 `/v1/audio/transcriptions` 接口
    - _Requirements: 2.1, 2.2, 2.4, 2.5_
  
  - [ ] 5.2 实现健康检查 API 端点
    - 实现 `GET /api/health` 端点
    - 返回系统和 Whisper 服务状态
    - _Requirements: 8.1, 8.2, 8.3_
  
  - [ ] 5.3 编写转写服务单元测试
    - 测试 API 调用格式
    - 测试错误处理
    - _Requirements: 2.1, 2.2, 2.4_

- [ ] 6. 检查点 - 转写功能验证
  - 确保所有测试通过，如有问题请询问用户

- [ ] 7. 总结服务实现
  - [ ] 7.1 实现 SummaryService 总结服务
    - 实现 `generate_summary()` 方法调用 Claude CLI
    - 实现 `update_summary()` 方法处理修改请求
    - 实现总结 prompt 模板
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_
  
  - [ ] 7.2 实现总结版本管理
    - 实现版本号递增逻辑
    - 实现历史版本保存
    - 实现状态变更（draft -> final）
    - _Requirements: 6.1, 6.3, 6.5, 6.7_
  
  - [ ] 7.3 编写总结服务属性测试
    - **Property 2: Markdown 格式输出与导出**
    - **Property 7: 版本管理正确性**
    - **Property 8: 确认后状态变更**
    - **Validates: Requirements 3.5, 4.3, 6.3, 6.5, 6.7**

- [ ] 8. 对话服务实现
  - [ ] 8.1 实现 ChatService 对话服务
    - 实现 `chat()` 方法处理用户问答
    - 实现对话上下文构建（包含转写文本、总结、历史）
    - _Requirements: 5.1, 5.2, 5.3, 5.6, 5.7_
  
  - [ ] 8.2 实现对话 API 端点
    - 实现 `POST /api/chat` 端点
    - 支持 question 和 edit_request 两种消息类型
    - _Requirements: 5.2, 5.3, 6.2, 6.3, 6.4_
  
  - [ ] 8.3 编写对话服务属性测试
    - **Property 3: 对话上下文完整性**
    - **Validates: Requirements 5.2**

- [ ] 9. 确认生成与导出功能
  - [ ] 9.1 实现确认生成 API 端点
    - 实现 `POST /api/finalize` 端点
    - 实现状态变更为 final
    - _Requirements: 6.5, 6.6_
  
  - [ ] 9.2 实现下载 API 端点
    - 实现 `GET /api/download/{session_id}` 端点
    - 返回 Markdown 文件下载
    - _Requirements: 4.3_

- [ ] 10. 检查点 - 后端功能验证
  - 确保所有测试通过，如有问题请询问用户

- [ ] 11. 前端界面实现
  - [ ] 11.1 创建基础 HTML 页面结构
    - 创建 `static/index.html` 主页面
    - 实现响应式布局
    - 添加服务状态显示区域
    - _Requirements: 1.1, 8.3_
  
  - [ ] 11.2 实现文件上传组件
    - 实现拖拽上传功能
    - 实现文件格式验证提示
    - 实现上传进度显示
    - _Requirements: 1.1, 1.2, 1.3, 1.4_
  
  - [ ] 11.3 实现结果展示组件
    - 实现 Markdown 渲染显示
    - 实现原始转写文本折叠显示
    - 实现草稿/最终版本状态标识
    - _Requirements: 4.1, 4.2, 6.1_
  
  - [ ] 11.4 实现对话组件
    - 实现对话消息列表显示
    - 实现输入框和发送按钮
    - 实现加载状态显示
    - _Requirements: 5.1, 5.3, 5.6_
  
  - [ ] 11.5 实现操作按钮组件
    - 实现"确认生成"按钮
    - 实现"导出 Markdown"按钮
    - 实现"复制"按钮
    - _Requirements: 4.3, 4.4, 6.5, 6.6_

- [ ] 12. 前端与后端集成
  - [ ] 12.1 实现前端 API 调用逻辑
    - 实现文件上传 API 调用
    - 实现对话 API 调用
    - 实现确认生成和下载 API 调用
    - _Requirements: 1.5, 5.2, 6.5_
  
  - [ ] 12.2 实现错误处理和用户提示
    - 实现错误消息显示
    - 实现重试功能
    - _Requirements: 2.4, 3.6, 5.7, 8.4_
  
  - [ ] 12.3 配置静态文件服务
    - 配置 FastAPI 静态文件路由
    - 配置首页重定向
    - _Requirements: 1.1_

- [ ] 13. 最终检查点 - 完整功能验证
  - 确保所有测试通过
  - 验证完整的用户流程
  - 如有问题请询问用户

## 注意事项

- 每个任务都引用了具体的需求编号以便追溯
- 检查点任务用于验证阶段性成果
- 属性测试使用 Hypothesis 库，每个测试至少运行 100 次迭代
- 所有测试任务均为必需任务，确保代码质量
