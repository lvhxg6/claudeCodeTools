// 会议录音智能总结系统 - 前端应用

// 全局状态
let currentSessionId = null;
let currentSummary = null;
let isProcessing = false;

// DOM 元素
const elements = {
    statusDot: document.getElementById('statusDot'),
    statusText: document.getElementById('statusText'),
    uploadArea: document.getElementById('uploadArea'),
    uploadSection: document.getElementById('uploadSection'),
    fileInput: document.getElementById('fileInput'),
    progressSection: document.getElementById('progressSection'),
    progressText: document.getElementById('progressText'),
    progressPercent: document.getElementById('progressPercent'),
    progressFill: document.getElementById('progressFill'),
    resultsSection: document.getElementById('resultsSection'),
    transcriptionContent: document.getElementById('transcriptionContent'),
    transcriptionText: document.getElementById('transcriptionText'),
    transcriptionIcon: document.getElementById('transcriptionIcon'),
    summaryContent: document.getElementById('summaryContent'),
    summaryBadge: document.getElementById('summaryBadge'),
    chatSection: document.getElementById('chatSection'),
    chatMessages: document.getElementById('chatMessages'),
    chatInput: document.getElementById('chatInput'),
    chatSendBtn: document.getElementById('chatSendBtn'),
    actionButtons: document.getElementById('actionButtons'),
    finalizeBtn: document.getElementById('finalizeBtn'),
    exportBtn: document.getElementById('exportBtn'),
    copyBtn: document.getElementById('copyBtn'),
    toast: document.getElementById('toast')
};

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    initUploadArea();
    checkServiceHealth();
    // 定期检查服务状态
    setInterval(checkServiceHealth, 30000);
});

// 初始化上传区域
function initUploadArea() {
    const { uploadArea, fileInput } = elements;
    
    // 点击上传
    uploadArea.addEventListener('click', () => {
        if (!isProcessing) {
            fileInput.click();
        }
    });
    
    // 文件选择
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileUpload(e.target.files[0]);
        }
    });
    
    // 拖拽事件
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });
    
    uploadArea.addEventListener('dragleave', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
    });
    
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0 && !isProcessing) {
            handleFileUpload(e.dataTransfer.files[0]);
        }
    });
}

// 检查服务健康状态
async function checkServiceHealth() {
    const { statusDot, statusText } = elements;
    
    try {
        const response = await fetch('/api/health');
        
        if (!response.ok) {
            statusDot.className = 'status-dot offline';
            statusText.textContent = '服务连接失败';
            return;
        }
        
        const data = await response.json();
        
        if (data.whisper_service === 'available') {
            statusDot.className = 'status-dot';
            statusText.textContent = 'Whisper 服务可用';
        } else {
            statusDot.className = 'status-dot offline';
            statusText.textContent = 'Whisper 服务不可用';
        }
    } catch (error) {
        console.error('健康检查失败:', error);
        statusDot.className = 'status-dot offline';
        statusText.textContent = '服务连接失败';
    }
}


// 处理文件上传
async function handleFileUpload(file) {
    // 验证文件格式
    const validExtensions = ['mp3', 'wav', 'm4a'];
    const extension = file.name.split('.').pop().toLowerCase();
    
    if (!validExtensions.includes(extension)) {
        showToast('不支持的文件格式，请上传 mp3、wav 或 m4a 文件', 'error');
        return;
    }
    
    // 验证文件大小 (100MB)
    const maxSize = 100 * 1024 * 1024;
    if (file.size > maxSize) {
        showToast('文件过大，请上传小于 100MB 的文件', 'error');
        return;
    }
    
    isProcessing = true;
    elements.uploadArea.classList.add('uploading');
    showProgress('正在上传文件...', 10);
    
    try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('language', 'zh');
        
        showProgress('正在转写音频...', 30);
        
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error?.message || '上传失败');
        }
        
        showProgress('正在生成总结...', 70);
        
        const data = await response.json();
        currentSessionId = data.session_id;
        currentSummary = data.summary;
        
        showProgress('处理完成', 100);
        
        // 显示结果
        setTimeout(() => {
            displayResults(data.transcription, data.summary);
            hideProgress();
            showToast('处理完成！', 'success');
        }, 500);
        
    } catch (error) {
        hideProgress();
        showToast(error.message || '处理失败，请重试', 'error');
    } finally {
        isProcessing = false;
        elements.uploadArea.classList.remove('uploading');
        elements.fileInput.value = '';
    }
}

// 显示进度
function showProgress(text, percent) {
    const { progressSection, progressText, progressPercent, progressFill } = elements;
    progressSection.classList.add('visible');
    progressText.textContent = text;
    progressPercent.textContent = `${percent}%`;
    progressFill.style.width = `${percent}%`;
}

// 隐藏进度
function hideProgress() {
    elements.progressSection.classList.remove('visible');
}

// 显示结果
function displayResults(transcription, summary) {
    const { uploadSection, resultsSection, transcriptionText, summaryContent, summaryBadge, chatSection, actionButtons } = elements;
    
    // 隐藏上传区域，显示结果
    uploadSection.style.display = 'none';
    resultsSection.classList.add('visible');
    chatSection.classList.add('visible');
    actionButtons.classList.add('visible');
    
    // 显示转写文本
    transcriptionText.textContent = transcription;
    
    // 渲染 Markdown 总结
    summaryContent.innerHTML = marked.parse(summary.content);
    
    // 更新状态标签
    updateSummaryBadge(summary.status);
    
    // 更新按钮状态
    updateButtonStates(summary.status);
}

// 更新总结状态标签
function updateSummaryBadge(status) {
    const { summaryBadge } = elements;
    if (status === 'final') {
        summaryBadge.textContent = '最终版';
        summaryBadge.classList.add('final');
    } else {
        summaryBadge.textContent = '草稿';
        summaryBadge.classList.remove('final');
    }
}

// 更新按钮状态
function updateButtonStates(status) {
    const { finalizeBtn, exportBtn } = elements;
    if (status === 'final') {
        finalizeBtn.disabled = true;
        finalizeBtn.textContent = '✅ 已确认';
        exportBtn.disabled = false;
    } else {
        finalizeBtn.disabled = false;
        finalizeBtn.textContent = '✅ 确认生成';
        exportBtn.disabled = true;
    }
}

// 切换转写文本显示
function toggleTranscription() {
    const { transcriptionContent, transcriptionIcon } = elements;
    transcriptionContent.classList.toggle('collapsed');
    transcriptionIcon.classList.toggle('collapsed');
}


// 发送聊天消息
async function sendMessage() {
    const { chatInput, chatSendBtn, chatMessages, summaryContent } = elements;
    const message = chatInput.value.trim();
    
    if (!message || !currentSessionId) return;
    
    // 禁用输入
    chatInput.disabled = true;
    chatSendBtn.disabled = true;
    
    // 添加用户消息
    addChatMessage('user', message);
    chatInput.value = '';
    
    // 判断消息类型
    const isEditRequest = message.includes('修改') || message.includes('更新') || 
                          message.includes('添加') || message.includes('删除') ||
                          message.includes('补充') || message.includes('调整');
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                session_id: currentSessionId,
                message: message,
                type: isEditRequest ? 'edit_request' : 'question'
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error?.message || '发送失败');
        }
        
        const data = await response.json();
        
        // 添加 AI 回复
        addChatMessage('assistant', data.response);
        
        // 如果有更新的总结，刷新显示
        if (data.updated_summary) {
            currentSummary = data.updated_summary;
            summaryContent.innerHTML = marked.parse(data.updated_summary.content);
            updateSummaryBadge(data.updated_summary.status);
            showToast('总结已更新', 'info');
        }
        
    } catch (error) {
        addChatMessage('assistant', `抱歉，发生错误：${error.message}`);
        showToast(error.message, 'error');
    } finally {
        chatInput.disabled = false;
        chatSendBtn.disabled = false;
        chatInput.focus();
    }
}

// 添加聊天消息
function addChatMessage(role, content) {
    const { chatMessages } = elements;
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${role}`;
    
    const avatar = role === 'assistant' ? '🤖' : '👤';
    
    messageDiv.innerHTML = `
        <div class="chat-avatar">${avatar}</div>
        <div class="chat-bubble">${escapeHtml(content)}</div>
    `;
    
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// 处理聊天输入回车
function handleChatKeypress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

// 确认生成最终版本
async function finalizeSummary() {
    if (!currentSessionId) return;
    
    const { finalizeBtn } = elements;
    finalizeBtn.disabled = true;
    finalizeBtn.innerHTML = '<span class="loading-spinner"></span>处理中...';
    
    try {
        const response = await fetch('/api/finalize', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                session_id: currentSessionId
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error?.message || '确认失败');
        }
        
        const data = await response.json();
        currentSummary = data.summary;
        
        // 更新显示
        updateSummaryBadge('final');
        updateButtonStates('final');
        
        showToast('已确认生成最终版本！', 'success');
        addChatMessage('assistant', '总结已确认为最终版本，您现在可以导出 Markdown 文件。');
        
    } catch (error) {
        showToast(error.message, 'error');
        finalizeBtn.disabled = false;
        finalizeBtn.textContent = '✅ 确认生成';
    }
}

// 导出 Markdown
async function exportMarkdown() {
    if (!currentSessionId) return;
    
    try {
        const response = await fetch(`/api/download/${currentSessionId}`);
        
        if (!response.ok) {
            throw new Error('导出失败');
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `meeting-summary-${currentSessionId}.md`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        showToast('导出成功！', 'success');
        
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// 复制总结内容
async function copySummary() {
    if (!currentSummary) return;
    
    try {
        await navigator.clipboard.writeText(currentSummary.content);
        showToast('已复制到剪贴板！', 'success');
    } catch (error) {
        // 降级方案
        const textarea = document.createElement('textarea');
        textarea.value = currentSummary.content;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        showToast('已复制到剪贴板！', 'success');
    }
}

// 开始新会话
function startNewSession() {
    if (confirm('确定要开始新会话吗？当前会话数据将被清除。')) {
        currentSessionId = null;
        currentSummary = null;
        
        // 重置界面
        elements.uploadSection.style.display = 'block';
        elements.resultsSection.classList.remove('visible');
        elements.chatSection.classList.remove('visible');
        elements.actionButtons.classList.remove('visible');
        
        // 清空聊天记录
        elements.chatMessages.innerHTML = `
            <div class="chat-message assistant">
                <div class="chat-avatar">🤖</div>
                <div class="chat-bubble">总结已生成，您可以提问或请求修改。</div>
            </div>
        `;
        
        // 重置按钮状态
        updateButtonStates('draft');
        
        showToast('已开始新会话', 'info');
    }
}

// 显示 Toast 通知
function showToast(message, type = 'info') {
    const { toast } = elements;
    toast.textContent = message;
    toast.className = `toast ${type} visible`;
    
    setTimeout(() => {
        toast.classList.remove('visible');
    }, 3000);
}

// HTML 转义
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
