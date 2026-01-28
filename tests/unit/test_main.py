# 主应用单元测试
# Main Application Unit Tests

"""
测试 FastAPI 主应用的 API 端点。

测试内容：
- POST /api/upload 文件上传端点
- GET /api/health 健康检查端点

Requirements:
- 1.2: 验证文件格式是否为支持的类型（mp3、wav、m4a）
- 1.3: 上传不支持的文件格式时显示明确的错误提示信息
- 1.4: 上传有效的音频文件时显示上传进度并在完成后确认
- 1.5: 音频文件上传成功后自动开始处理流程
"""

import io
import pytest
from fastapi.testclient import TestClient

from src.main import app, session_manager


# 创建测试客户端
client = TestClient(app)


class TestHealthCheck:
    """健康检查端点测试"""
    
    def test_health_check_returns_healthy(self):
        """测试健康检查返回正常状态"""
        response = client.get("/api/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert data["version"] == "1.0.0"
    
    def test_health_check_includes_whisper_status(self):
        """测试健康检查包含 Whisper 服务状态"""
        response = client.get("/api/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "whisper_service" in data


class TestUploadEndpoint:
    """文件上传端点测试"""
    
    def setup_method(self):
        """每个测试前清理会话"""
        session_manager.clear_all_sessions()
    
    # ============== 成功场景测试 ==============
    
    def test_upload_mp3_file_success(self):
        """
        测试上传 MP3 文件成功
        
        Validates: Requirements 1.2, 1.4, 1.5
        """
        # 创建模拟的 MP3 文件
        file_content = b"fake mp3 content for testing"
        files = {"file": ("meeting.mp3", io.BytesIO(file_content), "audio/mpeg")}
        
        response = client.post("/api/upload", files=files)
        
        assert response.status_code == 200
        data = response.json()
        
        # 验证响应结构
        assert "session_id" in data
        assert "transcription" in data
        assert "summary" in data
        
        # 验证 session_id 是有效的 UUID
        assert len(data["session_id"]) == 36  # UUID 格式
        
        # 验证 summary 结构
        assert data["summary"]["status"] == "draft"
        assert data["summary"]["version"] == 1
    
    def test_upload_wav_file_success(self):
        """
        测试上传 WAV 文件成功
        
        Validates: Requirements 1.2
        """
        file_content = b"fake wav content"
        files = {"file": ("recording.wav", io.BytesIO(file_content), "audio/wav")}
        
        response = client.post("/api/upload", files=files)
        
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
    
    def test_upload_m4a_file_success(self):
        """
        测试上传 M4A 文件成功
        
        Validates: Requirements 1.2
        """
        file_content = b"fake m4a content"
        files = {"file": ("audio.m4a", io.BytesIO(file_content), "audio/mp4")}
        
        response = client.post("/api/upload", files=files)
        
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
    
    def test_upload_with_uppercase_extension(self):
        """
        测试上传大写扩展名的文件成功
        
        Validates: Requirements 1.2
        """
        file_content = b"fake content"
        files = {"file": ("meeting.MP3", io.BytesIO(file_content), "audio/mpeg")}
        
        response = client.post("/api/upload", files=files)
        
        assert response.status_code == 200
    
    def test_upload_with_mixed_case_extension(self):
        """
        测试上传混合大小写扩展名的文件成功
        
        Validates: Requirements 1.2
        """
        file_content = b"fake content"
        files = {"file": ("meeting.Mp3", io.BytesIO(file_content), "audio/mpeg")}
        
        response = client.post("/api/upload", files=files)
        
        assert response.status_code == 200
    
    def test_upload_with_language_parameter(self):
        """测试上传时指定语言参数"""
        file_content = b"fake content"
        files = {"file": ("meeting.mp3", io.BytesIO(file_content), "audio/mpeg")}
        data = {"language": "en"}
        
        response = client.post("/api/upload", files=files, data=data)
        
        assert response.status_code == 200
    
    def test_upload_creates_session(self):
        """
        测试上传文件后创建会话
        
        Validates: Requirements 1.5
        """
        initial_count = session_manager.get_session_count()
        
        file_content = b"fake content"
        files = {"file": ("meeting.mp3", io.BytesIO(file_content), "audio/mpeg")}
        
        response = client.post("/api/upload", files=files)
        
        assert response.status_code == 200
        assert session_manager.get_session_count() == initial_count + 1
        
        # 验证会话存在
        session_id = response.json()["session_id"]
        assert session_manager.session_exists(session_id)
    
    # ============== 错误场景测试 ==============
    
    def test_upload_unsupported_format_txt(self):
        """
        测试上传不支持的 TXT 格式返回错误
        
        Validates: Requirements 1.3
        """
        file_content = b"text content"
        files = {"file": ("document.txt", io.BytesIO(file_content), "text/plain")}
        
        response = client.post("/api/upload", files=files)
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert data["detail"]["error"]["code"] == "FILE_FORMAT_ERROR"
        assert "mp3" in data["detail"]["error"]["message"].lower() or \
               "wav" in data["detail"]["error"]["message"].lower() or \
               "m4a" in data["detail"]["error"]["message"].lower()
    
    def test_upload_unsupported_format_pdf(self):
        """
        测试上传不支持的 PDF 格式返回错误
        
        Validates: Requirements 1.3
        """
        file_content = b"pdf content"
        files = {"file": ("document.pdf", io.BytesIO(file_content), "application/pdf")}
        
        response = client.post("/api/upload", files=files)
        
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error"]["code"] == "FILE_FORMAT_ERROR"
    
    def test_upload_unsupported_format_ogg(self):
        """
        测试上传不支持的 OGG 格式返回错误
        
        Validates: Requirements 1.3
        """
        file_content = b"ogg content"
        files = {"file": ("audio.ogg", io.BytesIO(file_content), "audio/ogg")}
        
        response = client.post("/api/upload", files=files)
        
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error"]["code"] == "FILE_FORMAT_ERROR"
    
    def test_upload_file_without_extension(self):
        """
        测试上传没有扩展名的文件返回错误
        
        Validates: Requirements 1.3
        """
        file_content = b"content"
        files = {"file": ("audiofile", io.BytesIO(file_content), "application/octet-stream")}
        
        response = client.post("/api/upload", files=files)
        
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error"]["code"] == "FILE_FORMAT_ERROR"
    
    def test_upload_empty_file(self):
        """测试上传空文件返回错误"""
        file_content = b""
        files = {"file": ("meeting.mp3", io.BytesIO(file_content), "audio/mpeg")}
        
        response = client.post("/api/upload", files=files)
        
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error"]["code"] == "FILE_FORMAT_ERROR"
        assert "空" in data["detail"]["error"]["message"]
    
    def test_upload_error_response_has_retry_allowed(self):
        """测试错误响应包含 retry_allowed 字段"""
        file_content = b"content"
        files = {"file": ("document.txt", io.BytesIO(file_content), "text/plain")}
        
        response = client.post("/api/upload", files=files)
        
        assert response.status_code == 400
        data = response.json()
        assert "retry_allowed" in data["detail"]["error"]
        assert data["detail"]["error"]["retry_allowed"] is True
    
    # ============== 边界条件测试 ==============
    
    def test_upload_file_with_special_characters_in_name(self):
        """测试上传文件名包含特殊字符"""
        file_content = b"content"
        files = {"file": ("会议录音 (2024).mp3", io.BytesIO(file_content), "audio/mpeg")}
        
        response = client.post("/api/upload", files=files)
        
        assert response.status_code == 200
    
    def test_upload_file_with_path_in_name(self):
        """测试上传文件名包含路径（应该被清理）"""
        file_content = b"content"
        files = {"file": ("../../../etc/passwd.mp3", io.BytesIO(file_content), "audio/mpeg")}
        
        response = client.post("/api/upload", files=files)
        
        # 应该成功，因为路径会被清理
        assert response.status_code == 200
    
    def test_multiple_uploads_create_different_sessions(self):
        """测试多次上传创建不同的会话"""
        file_content = b"content"
        
        # 第一次上传
        files1 = {"file": ("meeting1.mp3", io.BytesIO(file_content), "audio/mpeg")}
        response1 = client.post("/api/upload", files=files1)
        
        # 第二次上传
        files2 = {"file": ("meeting2.mp3", io.BytesIO(file_content), "audio/mpeg")}
        response2 = client.post("/api/upload", files=files2)
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # 验证是不同的会话
        session_id1 = response1.json()["session_id"]
        session_id2 = response2.json()["session_id"]
        assert session_id1 != session_id2


class TestUploadResponseFormat:
    """上传响应格式测试"""
    
    def setup_method(self):
        """每个测试前清理会话"""
        session_manager.clear_all_sessions()
    
    def test_response_contains_required_fields(self):
        """测试响应包含所有必需字段"""
        file_content = b"content"
        files = {"file": ("meeting.mp3", io.BytesIO(file_content), "audio/mpeg")}
        
        response = client.post("/api/upload", files=files)
        
        assert response.status_code == 200
        data = response.json()
        
        # 验证顶层字段
        assert "session_id" in data
        assert "transcription" in data
        assert "summary" in data
        
        # 验证 summary 字段
        summary = data["summary"]
        assert "content" in summary
        assert "status" in summary
        assert "version" in summary
    
    def test_response_summary_is_draft(self):
        """测试响应中的总结状态为草稿"""
        file_content = b"content"
        files = {"file": ("meeting.mp3", io.BytesIO(file_content), "audio/mpeg")}
        
        response = client.post("/api/upload", files=files)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["summary"]["status"] == "draft"
        assert data["summary"]["version"] == 1
