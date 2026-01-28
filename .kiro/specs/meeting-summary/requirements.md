# 需求文档

## 简介

会议录音智能总结系统是一个工作提效工具，用于将会议录音自动转写为文字，并通过 AI 智能分析生成结构化的会议总结报告。系统集成本地部署的 Whisper 语音转文字服务和 Claude Code CLI，提供简洁的 Web 界面供用户上传录音文件并获取总结结果。

## 术语表

- **Meeting_Summary_System**: 会议录音智能总结系统，本项目的核心应用
- **Whisper_Service**: 本地部署的 MLX Whisper 语音转文字服务，运行在可配置的地址上
- **Claude_CLI**: Claude Code 命令行工具，用于调用 AI 进行文本总结
- **Transcription**: 语音转文字的结果文本
- **Summary_Report**: AI 生成的 Markdown 格式会议总结报告
- **Audio_File**: 用户上传的会议录音文件（支持 mp3、wav、m4a 等格式）

## 需求

### 需求 1：音频文件上传

**用户故事：** 作为用户，我希望通过 Web 界面上传会议录音文件，以便系统能够处理我的会议录音。

#### 验收标准

1. WHEN 用户访问系统首页 THEN Meeting_Summary_System SHALL 显示一个简洁的文件上传界面
2. WHEN 用户选择音频文件上传 THEN Meeting_Summary_System SHALL 验证文件格式是否为支持的类型（mp3、wav、m4a）
3. WHEN 用户上传不支持的文件格式 THEN Meeting_Summary_System SHALL 显示明确的错误提示信息
4. WHEN 用户上传有效的音频文件 THEN Meeting_Summary_System SHALL 显示上传进度并在完成后确认
5. WHEN 音频文件上传成功 THEN Meeting_Summary_System SHALL 自动开始处理流程

### 需求 2：语音转文字

**用户故事：** 作为用户，我希望系统能够将我的会议录音转换为文字，以便后续进行智能分析。

#### 验收标准

1. WHEN 音频文件上传完成 THEN Meeting_Summary_System SHALL 调用 Whisper_Service 进行语音转文字
2. WHEN 调用 Whisper_Service THEN Meeting_Summary_System SHALL 使用 OpenAI 兼容的 /v1/audio/transcriptions 接口
3. WHEN 转写过程进行中 THEN Meeting_Summary_System SHALL 向用户显示处理状态
4. IF Whisper_Service 不可用 THEN Meeting_Summary_System SHALL 显示服务不可用的错误信息并建议用户检查服务状态
5. WHEN 转写完成 THEN Meeting_Summary_System SHALL 保存 Transcription 并进入总结阶段

### 需求 3：智能总结生成

**用户故事：** 作为用户，我希望系统能够对转写文本进行智能分析，生成精炼的会议总结报告。

#### 验收标准

1. WHEN Transcription 准备就绪 THEN Meeting_Summary_System SHALL 调用 Claude_CLI 进行智能总结
2. WHEN 生成总结 THEN Meeting_Summary_System SHALL 剔除会议中的废话和闲聊内容
3. WHEN 生成总结 THEN Meeting_Summary_System SHALL 提取会议的结论性内容
4. WHEN 生成总结 THEN Meeting_Summary_System SHALL 保留支撑结论的关键论据和沟通要点
5. WHEN 总结生成完成 THEN Meeting_Summary_System SHALL 输出业务导向的 Markdown 格式 Summary_Report
6. IF Claude_CLI 调用失败 THEN Meeting_Summary_System SHALL 显示错误信息并允许用户重试

### 需求 4：结果展示与导出

**用户故事：** 作为用户，我希望能够查看和导出会议总结报告，以便分享和存档。

#### 验收标准

1. WHEN Summary_Report 生成完成 THEN Meeting_Summary_System SHALL 在 Web 界面上以 Markdown 渲染格式展示总结内容
2. WHEN 用户查看总结 THEN Meeting_Summary_System SHALL 同时显示原始 Transcription 供参考
3. WHEN 用户点击导出按钮 THEN Meeting_Summary_System SHALL 提供 Markdown 文件下载功能
4. WHEN 用户点击复制按钮 THEN Meeting_Summary_System SHALL 将总结内容复制到剪贴板

### 需求 5：多轮对话与问答

**用户故事：** 作为用户，我希望能够针对会议内容进行追问和深入探讨，以便获取更详细的信息或澄清疑问。

#### 验收标准

1. WHEN Summary_Report 展示后 THEN Meeting_Summary_System SHALL 提供对话输入框供用户追问
2. WHEN 用户输入追问内容并提交 THEN Meeting_Summary_System SHALL 将问题连同 Transcription 和对话历史发送给 Claude_CLI
3. WHEN Claude_CLI 返回回答 THEN Meeting_Summary_System SHALL 在对话区域展示 AI 回复
4. THE Meeting_Summary_System SHALL 保持当前会话的对话历史直到用户开始新的录音处理
5. WHEN 用户开始处理新的录音文件 THEN Meeting_Summary_System SHALL 清空之前的对话历史
6. WHEN 对话进行中 THEN Meeting_Summary_System SHALL 显示 AI 正在思考的加载状态
7. IF 多轮对话中 Claude_CLI 调用失败 THEN Meeting_Summary_System SHALL 显示错误信息并允许用户重新发送问题

### 需求 6：协作编辑与确认生成

**用户故事：** 作为用户，我希望能够与 AI 协作修改完善会议总结，在确认满意后再生成最终的总结文件，以确保输出质量。

#### 验收标准

1. WHEN Summary_Report 首次生成 THEN Meeting_Summary_System SHALL 将其标记为草稿状态并显示"草稿"标识
2. WHEN 总结处于草稿状态 THEN Meeting_Summary_System SHALL 允许用户通过对话请求 AI 修改总结内容
3. WHEN 用户请求修改总结（如"请补充第二点的细节"、"删除闲聊部分"） THEN Meeting_Summary_System SHALL 调用 Claude_CLI 生成修改后的总结并更新草稿
4. WHEN 草稿更新后 THEN Meeting_Summary_System SHALL 在界面上实时显示最新版本的总结内容
5. WHEN 用户点击"确认生成"按钮 THEN Meeting_Summary_System SHALL 将当前草稿标记为最终版本
6. WHEN 总结确认为最终版本 THEN Meeting_Summary_System SHALL 启用导出和下载功能
7. THE Meeting_Summary_System SHALL 保留草稿的修改历史供用户回顾

### 需求 7：系统配置

**用户故事：** 作为用户，我希望能够配置系统的服务地址和命令参数，以适应不同的部署环境。

#### 验收标准

1. THE Meeting_Summary_System SHALL 支持通过 YAML 配置文件设置 Whisper_Service 地址（默认 http://localhost:8765）
2. THE Meeting_Summary_System SHALL 支持通过 YAML 配置文件设置 Claude_CLI 命令（支持自定义命令和参数）
3. WHEN 系统启动时 THEN Meeting_Summary_System SHALL 读取配置文件并验证配置有效性
4. IF 配置文件不存在 THEN Meeting_Summary_System SHALL 使用默认配置值并记录警告日志
5. WHEN Whisper_Service 地址配置变更 THEN Meeting_Summary_System SHALL 在下次请求时使用新地址

### 需求 8：健康检查与错误处理

**用户故事：** 作为用户，我希望系统能够检测依赖服务的状态，并在出现问题时给出明确的提示。

#### 验收标准

1. WHEN 系统启动时 THEN Meeting_Summary_System SHALL 检查 Whisper_Service 的健康状态（GET /health）
2. WHEN 用户开始处理任务前 THEN Meeting_Summary_System SHALL 验证 Whisper_Service 可用性
3. IF Whisper_Service 健康检查失败 THEN Meeting_Summary_System SHALL 在界面上显示服务状态警告
4. WHEN 处理过程中发生错误 THEN Meeting_Summary_System SHALL 记录详细错误日志并向用户显示友好的错误信息
5. IF 处理超时 THEN Meeting_Summary_System SHALL 允许用户取消当前任务并重新开始
