# 数据模型单元测试
# Data Models Unit Tests

"""
数据模型的单元测试。

测试覆盖：
- ChatMessage: 创建、序列化、反序列化
- Summary: 创建、版本管理、状态变更
- Session: 创建、对话历史管理、序列化

Requirements:
- 5.4: 保持当前会话的对话历史直到用户开始新的录音处理
- 6.1: 首次生成的总结标记为草稿状态
- 6.7: 保留草稿的修改历史供用户回顾
"""

from datetime import datetime

import pytest

from src.models import (
    ChatMessage,
    MessageRole,
    MessageType,
    Session,
    Summary,
    SummaryStatus,
)


class TestChatMessage:
    """测试 ChatMessage 数据类"""
    
    def test_create_user_question(self):
        """测试创建用户问题消息"""
        msg = ChatMessage(
            role=MessageRole.USER,
            content="这个会议的主要结论是什么？",
            message_type=MessageType.QUESTION
        )
        
        assert msg.role == "user"
        assert msg.content == "这个会议的主要结论是什么？"
        assert msg.message_type == "question"
        assert isinstance(msg.timestamp, datetime)
    
    def test_create_assistant_response(self):
        """测试创建助手回复消息"""
        msg = ChatMessage(
            role=MessageRole.ASSISTANT,
            content="会议的主要结论是...",
            message_type=MessageType.RESPONSE
        )
        
        assert msg.role == "assistant"
        assert msg.message_type == "response"
    
    def test_create_edit_request(self):
        """测试创建编辑请求消息"""
        msg = ChatMessage(
            role=MessageRole.USER,
            content="请补充第二点的细节",
            message_type=MessageType.EDIT_REQUEST
        )
        
        assert msg.message_type == "edit_request"
    
    def test_invalid_role_raises_error(self):
        """测试无效角色抛出错误"""
        with pytest.raises(ValueError, match="Invalid role"):
            ChatMessage(
                role="invalid_role",
                content="test",
                message_type=MessageType.QUESTION
            )
    
    def test_invalid_message_type_raises_error(self):
        """测试无效消息类型抛出错误"""
        with pytest.raises(ValueError, match="Invalid message_type"):
            ChatMessage(
                role=MessageRole.USER,
                content="test",
                message_type="invalid_type"
            )
    
    def test_to_dict(self):
        """测试序列化为字典"""
        timestamp = datetime(2024, 1, 15, 10, 30, 0)
        msg = ChatMessage(
            role=MessageRole.USER,
            content="问题内容",
            message_type=MessageType.QUESTION,
            timestamp=timestamp
        )
        
        result = msg.to_dict()
        
        assert result["role"] == "user"
        assert result["content"] == "问题内容"
        assert result["message_type"] == "question"
        assert result["timestamp"] == "2024-01-15T10:30:00"
    
    def test_from_dict(self):
        """测试从字典反序列化"""
        data = {
            "role": "assistant",
            "content": "回复内容",
            "message_type": "response",
            "timestamp": "2024-01-15T10:30:00"
        }
        
        msg = ChatMessage.from_dict(data)
        
        assert msg.role == "assistant"
        assert msg.content == "回复内容"
        assert msg.message_type == "response"
        assert msg.timestamp == datetime(2024, 1, 15, 10, 30, 0)
    
    def test_from_dict_without_timestamp(self):
        """测试从字典反序列化（无时间戳）"""
        data = {
            "role": "user",
            "content": "问题",
            "message_type": "question"
        }
        
        msg = ChatMessage.from_dict(data)
        
        assert msg.role == "user"
        assert isinstance(msg.timestamp, datetime)
    
    def test_roundtrip_serialization(self):
        """测试序列化和反序列化往返"""
        original = ChatMessage(
            role=MessageRole.USER,
            content="测试内容",
            message_type=MessageType.QUESTION,
            timestamp=datetime(2024, 1, 15, 10, 30, 0)
        )
        
        data = original.to_dict()
        restored = ChatMessage.from_dict(data)
        
        assert restored.role == original.role
        assert restored.content == original.content
        assert restored.message_type == original.message_type
        assert restored.timestamp == original.timestamp


class TestSummary:
    """测试 Summary 数据类"""
    
    def test_create_draft(self):
        """测试创建草稿总结 - Validates: Requirements 6.1"""
        summary = Summary.create_draft("# 会议总结\n\n这是内容...")
        
        assert summary.content == "# 会议总结\n\n这是内容..."
        assert summary.status == SummaryStatus.DRAFT
        assert summary.version == 1
        assert summary.history == []
    
    def test_default_status_is_draft(self):
        """测试默认状态为草稿"""
        summary = Summary(content="内容")
        
        assert summary.status == SummaryStatus.DRAFT
    
    def test_invalid_status_raises_error(self):
        """测试无效状态抛出错误"""
        with pytest.raises(ValueError, match="Invalid status"):
            Summary(content="内容", status="invalid_status")
    
    def test_invalid_version_raises_error(self):
        """测试无效版本号抛出错误"""
        with pytest.raises(ValueError, match="Version must be >= 1"):
            Summary(content="内容", version=0)
    
    def test_update_content(self):
        """测试更新内容 - Validates: Requirements 6.3, 6.7"""
        summary = Summary.create_draft("版本1内容")
        
        summary.update_content("版本2内容")
        
        assert summary.content == "版本2内容"
        assert summary.version == 2
        assert summary.history == ["版本1内容"]
    
    def test_update_content_multiple_times(self):
        """测试多次更新内容 - Validates: Requirements 6.7"""
        summary = Summary.create_draft("v1")
        
        summary.update_content("v2")
        summary.update_content("v3")
        summary.update_content("v4")
        
        assert summary.content == "v4"
        assert summary.version == 4
        assert summary.history == ["v1", "v2", "v3"]
        assert len(summary.history) == summary.version - 1
    
    def test_update_finalized_summary_raises_error(self):
        """测试更新已确认的总结抛出错误"""
        summary = Summary.create_draft("内容")
        summary.finalize()
        
        with pytest.raises(ValueError, match="Cannot update a finalized summary"):
            summary.update_content("新内容")
    
    def test_finalize(self):
        """测试确认生成 - Validates: Requirements 6.5"""
        summary = Summary.create_draft("最终内容")
        original_content = summary.content
        
        summary.finalize()
        
        assert summary.status == SummaryStatus.FINAL
        assert summary.content == original_content  # 内容不变
    
    def test_finalize_already_final_raises_error(self):
        """测试重复确认抛出错误"""
        summary = Summary.create_draft("内容")
        summary.finalize()
        
        with pytest.raises(ValueError, match="Summary is already finalized"):
            summary.finalize()
    
    def test_to_dict(self):
        """测试序列化为字典"""
        summary = Summary(
            content="内容",
            status=SummaryStatus.DRAFT,
            version=2,
            history=["历史内容"]
        )
        
        result = summary.to_dict()
        
        assert result["content"] == "内容"
        assert result["status"] == "draft"
        assert result["version"] == 2
        assert result["history"] == ["历史内容"]
    
    def test_from_dict(self):
        """测试从字典反序列化"""
        data = {
            "content": "总结内容",
            "status": "final",
            "version": 3,
            "history": ["v1", "v2"]
        }
        
        summary = Summary.from_dict(data)
        
        assert summary.content == "总结内容"
        assert summary.status == "final"
        assert summary.version == 3
        assert summary.history == ["v1", "v2"]
    
    def test_from_dict_with_defaults(self):
        """测试从字典反序列化（使用默认值）"""
        data = {"content": "内容"}
        
        summary = Summary.from_dict(data)
        
        assert summary.content == "内容"
        assert summary.status == SummaryStatus.DRAFT
        assert summary.version == 1
        assert summary.history == []
    
    def test_roundtrip_serialization(self):
        """测试序列化和反序列化往返"""
        original = Summary(
            content="测试内容",
            status=SummaryStatus.DRAFT,
            version=2,
            history=["历史1"]
        )
        
        data = original.to_dict()
        restored = Summary.from_dict(data)
        
        assert restored.content == original.content
        assert restored.status == original.status
        assert restored.version == original.version
        assert restored.history == original.history
    
    def test_history_is_independent_copy(self):
        """测试历史记录是独立副本"""
        data = {
            "content": "内容",
            "history": ["v1", "v2"]
        }
        
        summary = Summary.from_dict(data)
        
        # 修改原始数据不应影响 summary
        data["history"].append("v3")
        assert summary.history == ["v1", "v2"]
        
        # to_dict 返回的也是副本
        result = summary.to_dict()
        result["history"].append("v4")
        assert summary.history == ["v1", "v2"]


class TestSession:
    """测试 Session 数据类"""
    
    def test_create_session(self):
        """测试创建会话"""
        session = Session.create("meeting.mp3")
        
        assert session.audio_filename == "meeting.mp3"
        assert session.transcription == ""
        assert session.summary.status == SummaryStatus.DRAFT
        assert session.summary.version == 1
        assert session.chat_history == []
        assert isinstance(session.id, str)
        assert len(session.id) > 0
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.updated_at, datetime)
    
    def test_create_session_with_custom_id(self):
        """测试使用自定义 ID 创建会话"""
        session = Session.create("meeting.mp3", session_id="custom-id-123")
        
        assert session.id == "custom-id-123"
    
    def test_add_message(self):
        """测试添加消息 - Validates: Requirements 5.4"""
        session = Session.create("meeting.mp3")
        msg = ChatMessage(
            role=MessageRole.USER,
            content="问题",
            message_type=MessageType.QUESTION
        )
        
        session.add_message(msg)
        
        assert len(session.chat_history) == 1
        assert session.chat_history[0] == msg
    
    def test_add_multiple_messages(self):
        """测试添加多条消息 - Validates: Requirements 5.4"""
        session = Session.create("meeting.mp3")
        
        msg1 = ChatMessage(MessageRole.USER, "问题1", MessageType.QUESTION)
        msg2 = ChatMessage(MessageRole.ASSISTANT, "回答1", MessageType.RESPONSE)
        msg3 = ChatMessage(MessageRole.USER, "问题2", MessageType.QUESTION)
        
        session.add_message(msg1)
        session.add_message(msg2)
        session.add_message(msg3)
        
        assert len(session.chat_history) == 3
        # 验证消息顺序
        assert session.chat_history[0].content == "问题1"
        assert session.chat_history[1].content == "回答1"
        assert session.chat_history[2].content == "问题2"
    
    def test_clear_chat_history(self):
        """测试清空对话历史 - Validates: Requirements 5.5"""
        session = Session.create("meeting.mp3")
        session.add_message(
            ChatMessage(MessageRole.USER, "问题", MessageType.QUESTION)
        )
        session.add_message(
            ChatMessage(MessageRole.ASSISTANT, "回答", MessageType.RESPONSE)
        )
        
        session.clear_chat_history()
        
        assert len(session.chat_history) == 0
    
    def test_set_transcription(self):
        """测试设置转写文本"""
        session = Session.create("meeting.mp3")
        
        session.set_transcription("这是会议的转写内容...")
        
        assert session.transcription == "这是会议的转写内容..."
    
    def test_set_summary(self):
        """测试设置总结"""
        session = Session.create("meeting.mp3")
        new_summary = Summary.create_draft("# 新总结")
        
        session.set_summary(new_summary)
        
        assert session.summary.content == "# 新总结"
    
    def test_update_summary_content(self):
        """测试更新总结内容 - Validates: Requirements 6.3, 6.7"""
        session = Session.create("meeting.mp3")
        session.summary = Summary.create_draft("v1")
        
        session.update_summary_content("v2")
        
        assert session.summary.content == "v2"
        assert session.summary.version == 2
        assert session.summary.history == ["v1"]
    
    def test_finalize_summary(self):
        """测试确认生成总结 - Validates: Requirements 6.5"""
        session = Session.create("meeting.mp3")
        session.summary = Summary.create_draft("最终内容")
        
        session.finalize_summary()
        
        assert session.summary.status == SummaryStatus.FINAL
    
    def test_updated_at_changes_on_modification(self):
        """测试修改时更新时间戳"""
        session = Session.create("meeting.mp3")
        original_updated_at = session.updated_at
        
        # 等待一小段时间确保时间戳不同
        import time
        time.sleep(0.01)
        
        session.add_message(
            ChatMessage(MessageRole.USER, "问题", MessageType.QUESTION)
        )
        
        assert session.updated_at >= original_updated_at
    
    def test_to_dict(self):
        """测试序列化为字典"""
        session = Session.create("meeting.mp3", session_id="test-id")
        session.transcription = "转写内容"
        session.summary = Summary.create_draft("总结内容")
        session.add_message(
            ChatMessage(
                role=MessageRole.USER,
                content="问题",
                message_type=MessageType.QUESTION,
                timestamp=datetime(2024, 1, 15, 10, 30, 0)
            )
        )
        
        result = session.to_dict()
        
        assert result["id"] == "test-id"
        assert result["audio_filename"] == "meeting.mp3"
        assert result["transcription"] == "转写内容"
        assert result["summary"]["content"] == "总结内容"
        assert result["summary"]["status"] == "draft"
        assert len(result["chat_history"]) == 1
        assert result["chat_history"][0]["content"] == "问题"
        assert "created_at" in result
        assert "updated_at" in result
    
    def test_from_dict(self):
        """测试从字典反序列化"""
        data = {
            "id": "session-123",
            "audio_filename": "test.mp3",
            "transcription": "转写文本",
            "summary": {
                "content": "总结",
                "status": "draft",
                "version": 1,
                "history": []
            },
            "chat_history": [
                {
                    "role": "user",
                    "content": "问题",
                    "message_type": "question",
                    "timestamp": "2024-01-15T10:30:00"
                }
            ],
            "created_at": "2024-01-15T10:00:00",
            "updated_at": "2024-01-15T10:30:00"
        }
        
        session = Session.from_dict(data)
        
        assert session.id == "session-123"
        assert session.audio_filename == "test.mp3"
        assert session.transcription == "转写文本"
        assert session.summary.content == "总结"
        assert len(session.chat_history) == 1
        assert session.chat_history[0].content == "问题"
        assert session.created_at == datetime(2024, 1, 15, 10, 0, 0)
        assert session.updated_at == datetime(2024, 1, 15, 10, 30, 0)
    
    def test_from_dict_with_minimal_data(self):
        """测试从最小数据反序列化"""
        data = {
            "id": "min-session",
            "audio_filename": "audio.mp3"
        }
        
        session = Session.from_dict(data)
        
        assert session.id == "min-session"
        assert session.audio_filename == "audio.mp3"
        assert session.transcription == ""
        assert session.summary.status == SummaryStatus.DRAFT
        assert session.chat_history == []
    
    def test_roundtrip_serialization(self):
        """测试序列化和反序列化往返"""
        original = Session.create("meeting.mp3", session_id="test-session")
        original.transcription = "转写内容"
        original.summary = Summary.create_draft("v1")
        original.summary.update_content("v2")
        original.add_message(
            ChatMessage(MessageRole.USER, "问题", MessageType.QUESTION)
        )
        original.add_message(
            ChatMessage(MessageRole.ASSISTANT, "回答", MessageType.RESPONSE)
        )
        
        data = original.to_dict()
        restored = Session.from_dict(data)
        
        assert restored.id == original.id
        assert restored.audio_filename == original.audio_filename
        assert restored.transcription == original.transcription
        assert restored.summary.content == original.summary.content
        assert restored.summary.version == original.summary.version
        assert restored.summary.history == original.summary.history
        assert len(restored.chat_history) == len(original.chat_history)
        for i, msg in enumerate(restored.chat_history):
            assert msg.content == original.chat_history[i].content
            assert msg.role == original.chat_history[i].role


class TestSummaryStatusConstants:
    """测试状态常量"""
    
    def test_summary_status_values(self):
        """测试 SummaryStatus 常量值"""
        assert SummaryStatus.DRAFT == "draft"
        assert SummaryStatus.FINAL == "final"


class TestMessageConstants:
    """测试消息常量"""
    
    def test_message_role_values(self):
        """测试 MessageRole 常量值"""
        assert MessageRole.USER == "user"
        assert MessageRole.ASSISTANT == "assistant"
    
    def test_message_type_values(self):
        """测试 MessageType 常量值"""
        assert MessageType.QUESTION == "question"
        assert MessageType.EDIT_REQUEST == "edit_request"
        assert MessageType.RESPONSE == "response"
