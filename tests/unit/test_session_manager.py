# 会话管理器单元测试
# Session Manager Unit Tests

"""
SessionManager 的单元测试。

测试覆盖：
- 会话创建 (create_session)
- 会话获取 (get_session)
- 会话更新 (update_session)
- 会话删除 (delete_session)
- 会话内存存储
- 对话历史管理

Requirements:
- 5.4: 保持当前会话的对话历史直到用户开始新的录音处理
- 5.5: 用户开始处理新的录音文件时清空之前的对话历史
"""

import pytest
import uuid

from src.session_manager import SessionManager, SessionNotFoundError
from src.models import (
    ChatMessage,
    MessageRole,
    MessageType,
    Session,
    Summary,
    SummaryStatus,
)


class TestSessionManagerCreate:
    """测试 SessionManager 创建会话功能"""
    
    def test_create_session_returns_session_id(self):
        """测试创建会话返回有效的 session_id"""
        manager = SessionManager()
        
        session_id = manager.create_session()
        
        assert session_id is not None
        assert isinstance(session_id, str)
        assert len(session_id) > 0
    
    def test_create_session_generates_uuid(self):
        """测试创建会话生成有效的 UUID"""
        manager = SessionManager()
        
        session_id = manager.create_session()
        
        # 验证是有效的 UUID 格式
        try:
            uuid.UUID(session_id)
        except ValueError:
            pytest.fail(f"session_id '{session_id}' is not a valid UUID")
    
    def test_create_session_with_audio_filename(self):
        """测试创建会话时指定音频文件名"""
        manager = SessionManager()
        
        session_id = manager.create_session(audio_filename="meeting.mp3")
        session = manager.get_session(session_id)
        
        assert session.audio_filename == "meeting.mp3"
    
    def test_create_session_without_audio_filename(self):
        """测试创建会话时不指定音频文件名"""
        manager = SessionManager()
        
        session_id = manager.create_session()
        session = manager.get_session(session_id)
        
        assert session.audio_filename == ""
    
    def test_create_multiple_sessions_unique_ids(self):
        """测试创建多个会话生成唯一 ID"""
        manager = SessionManager()
        
        session_ids = [manager.create_session() for _ in range(10)]
        
        # 所有 ID 应该唯一
        assert len(set(session_ids)) == 10
    
    def test_create_session_initializes_empty_transcription(self):
        """测试新会话的转写文本为空"""
        manager = SessionManager()
        
        session_id = manager.create_session()
        session = manager.get_session(session_id)
        
        assert session.transcription == ""
    
    def test_create_session_initializes_draft_summary(self):
        """测试新会话的总结为草稿状态 - Validates: Requirements 6.1"""
        manager = SessionManager()
        
        session_id = manager.create_session()
        session = manager.get_session(session_id)
        
        assert session.summary.status == SummaryStatus.DRAFT
        assert session.summary.version == 1
    
    def test_create_session_initializes_empty_chat_history(self):
        """测试新会话的对话历史为空"""
        manager = SessionManager()
        
        session_id = manager.create_session()
        session = manager.get_session(session_id)
        
        assert session.chat_history == []
        assert len(session.chat_history) == 0


class TestSessionManagerGet:
    """测试 SessionManager 获取会话功能"""
    
    def test_get_session_returns_correct_session(self):
        """测试获取会话返回正确的会话对象"""
        manager = SessionManager()
        session_id = manager.create_session(audio_filename="test.mp3")
        
        session = manager.get_session(session_id)
        
        assert session.id == session_id
        assert session.audio_filename == "test.mp3"
    
    def test_get_session_not_found_raises_error(self):
        """测试获取不存在的会话抛出错误"""
        manager = SessionManager()
        
        with pytest.raises(SessionNotFoundError) as exc_info:
            manager.get_session("non-existent-id")
        
        assert exc_info.value.session_id == "non-existent-id"
    
    def test_get_session_after_delete_raises_error(self):
        """测试删除后获取会话抛出错误"""
        manager = SessionManager()
        session_id = manager.create_session()
        manager.delete_session(session_id)
        
        with pytest.raises(SessionNotFoundError):
            manager.get_session(session_id)
    
    def test_get_session_returns_same_object(self):
        """测试多次获取返回同一个会话对象"""
        manager = SessionManager()
        session_id = manager.create_session()
        
        session1 = manager.get_session(session_id)
        session2 = manager.get_session(session_id)
        
        assert session1 is session2


class TestSessionManagerUpdate:
    """测试 SessionManager 更新会话功能"""
    
    def test_update_session_transcription(self):
        """测试更新会话转写文本"""
        manager = SessionManager()
        session_id = manager.create_session()
        
        manager.update_session(session_id, {"transcription": "会议内容..."})
        
        session = manager.get_session(session_id)
        assert session.transcription == "会议内容..."
    
    def test_update_session_audio_filename(self):
        """测试更新会话音频文件名"""
        manager = SessionManager()
        session_id = manager.create_session()
        
        manager.update_session(session_id, {"audio_filename": "new_meeting.mp3"})
        
        session = manager.get_session(session_id)
        assert session.audio_filename == "new_meeting.mp3"
    
    def test_update_session_summary_with_object(self):
        """测试使用 Summary 对象更新会话总结"""
        manager = SessionManager()
        session_id = manager.create_session()
        new_summary = Summary.create_draft("# 新总结内容")
        
        manager.update_session(session_id, {"summary": new_summary})
        
        session = manager.get_session(session_id)
        assert session.summary.content == "# 新总结内容"
    
    def test_update_session_summary_with_dict(self):
        """测试使用字典更新会话总结"""
        manager = SessionManager()
        session_id = manager.create_session()
        summary_dict = {
            "content": "# 字典总结",
            "status": "draft",
            "version": 1,
            "history": []
        }
        
        manager.update_session(session_id, {"summary": summary_dict})
        
        session = manager.get_session(session_id)
        assert session.summary.content == "# 字典总结"
    
    def test_update_session_chat_history_with_objects(self):
        """测试使用 ChatMessage 对象列表更新对话历史"""
        manager = SessionManager()
        session_id = manager.create_session()
        messages = [
            ChatMessage(MessageRole.USER, "问题1", MessageType.QUESTION),
            ChatMessage(MessageRole.ASSISTANT, "回答1", MessageType.RESPONSE),
        ]
        
        manager.update_session(session_id, {"chat_history": messages})
        
        session = manager.get_session(session_id)
        assert len(session.chat_history) == 2
        assert session.chat_history[0].content == "问题1"
        assert session.chat_history[1].content == "回答1"
    
    def test_update_session_chat_history_with_dicts(self):
        """测试使用字典列表更新对话历史"""
        manager = SessionManager()
        session_id = manager.create_session()
        messages = [
            {"role": "user", "content": "问题", "message_type": "question"},
            {"role": "assistant", "content": "回答", "message_type": "response"},
        ]
        
        manager.update_session(session_id, {"chat_history": messages})
        
        session = manager.get_session(session_id)
        assert len(session.chat_history) == 2
    
    def test_update_session_multiple_fields(self):
        """测试同时更新多个字段"""
        manager = SessionManager()
        session_id = manager.create_session()
        
        manager.update_session(session_id, {
            "audio_filename": "updated.mp3",
            "transcription": "更新的转写内容"
        })
        
        session = manager.get_session(session_id)
        assert session.audio_filename == "updated.mp3"
        assert session.transcription == "更新的转写内容"
    
    def test_update_session_not_found_raises_error(self):
        """测试更新不存在的会话抛出错误"""
        manager = SessionManager()
        
        with pytest.raises(SessionNotFoundError):
            manager.update_session("non-existent-id", {"transcription": "test"})
    
    def test_update_session_preserves_other_fields(self):
        """测试更新会话时保留其他字段 - Validates: Requirements 5.4"""
        manager = SessionManager()
        session_id = manager.create_session(audio_filename="original.mp3")
        
        # 先添加一些对话历史
        manager.add_message(
            session_id,
            ChatMessage(MessageRole.USER, "问题", MessageType.QUESTION)
        )
        
        # 只更新转写文本
        manager.update_session(session_id, {"transcription": "新转写"})
        
        session = manager.get_session(session_id)
        assert session.audio_filename == "original.mp3"  # 保留原值
        assert session.transcription == "新转写"  # 更新的值
        assert len(session.chat_history) == 1  # 对话历史保留


class TestSessionManagerDelete:
    """测试 SessionManager 删除会话功能"""
    
    def test_delete_session_removes_session(self):
        """测试删除会话从存储中移除"""
        manager = SessionManager()
        session_id = manager.create_session()
        
        manager.delete_session(session_id)
        
        assert not manager.session_exists(session_id)
    
    def test_delete_session_not_found_raises_error(self):
        """测试删除不存在的会话抛出错误"""
        manager = SessionManager()
        
        with pytest.raises(SessionNotFoundError):
            manager.delete_session("non-existent-id")
    
    def test_delete_session_twice_raises_error(self):
        """测试重复删除会话抛出错误"""
        manager = SessionManager()
        session_id = manager.create_session()
        manager.delete_session(session_id)
        
        with pytest.raises(SessionNotFoundError):
            manager.delete_session(session_id)
    
    def test_delete_session_does_not_affect_others(self):
        """测试删除会话不影响其他会话"""
        manager = SessionManager()
        session_id1 = manager.create_session(audio_filename="file1.mp3")
        session_id2 = manager.create_session(audio_filename="file2.mp3")
        
        manager.delete_session(session_id1)
        
        assert not manager.session_exists(session_id1)
        assert manager.session_exists(session_id2)
        session2 = manager.get_session(session_id2)
        assert session2.audio_filename == "file2.mp3"


class TestSessionManagerChatHistory:
    """测试 SessionManager 对话历史管理功能"""
    
    def test_add_message_to_session(self):
        """测试向会话添加消息 - Validates: Requirements 5.4"""
        manager = SessionManager()
        session_id = manager.create_session()
        msg = ChatMessage(MessageRole.USER, "问题", MessageType.QUESTION)
        
        manager.add_message(session_id, msg)
        
        session = manager.get_session(session_id)
        assert len(session.chat_history) == 1
        assert session.chat_history[0].content == "问题"
    
    def test_add_multiple_messages_preserves_order(self):
        """测试添加多条消息保持顺序 - Validates: Requirements 5.4"""
        manager = SessionManager()
        session_id = manager.create_session()
        
        manager.add_message(
            session_id,
            ChatMessage(MessageRole.USER, "问题1", MessageType.QUESTION)
        )
        manager.add_message(
            session_id,
            ChatMessage(MessageRole.ASSISTANT, "回答1", MessageType.RESPONSE)
        )
        manager.add_message(
            session_id,
            ChatMessage(MessageRole.USER, "问题2", MessageType.QUESTION)
        )
        
        session = manager.get_session(session_id)
        assert len(session.chat_history) == 3
        assert session.chat_history[0].content == "问题1"
        assert session.chat_history[1].content == "回答1"
        assert session.chat_history[2].content == "问题2"
    
    def test_add_message_not_found_raises_error(self):
        """测试向不存在的会话添加消息抛出错误"""
        manager = SessionManager()
        msg = ChatMessage(MessageRole.USER, "问题", MessageType.QUESTION)
        
        with pytest.raises(SessionNotFoundError):
            manager.add_message("non-existent-id", msg)
    
    def test_clear_chat_history(self):
        """测试清空对话历史 - Validates: Requirements 5.5"""
        manager = SessionManager()
        session_id = manager.create_session()
        
        # 添加一些消息
        manager.add_message(
            session_id,
            ChatMessage(MessageRole.USER, "问题", MessageType.QUESTION)
        )
        manager.add_message(
            session_id,
            ChatMessage(MessageRole.ASSISTANT, "回答", MessageType.RESPONSE)
        )
        
        # 清空历史
        manager.clear_chat_history(session_id)
        
        session = manager.get_session(session_id)
        assert len(session.chat_history) == 0
    
    def test_clear_chat_history_not_found_raises_error(self):
        """测试清空不存在会话的历史抛出错误"""
        manager = SessionManager()
        
        with pytest.raises(SessionNotFoundError):
            manager.clear_chat_history("non-existent-id")
    
    def test_clear_chat_history_preserves_other_data(self):
        """测试清空历史保留其他数据 - Validates: Requirements 5.5"""
        manager = SessionManager()
        session_id = manager.create_session(audio_filename="meeting.mp3")
        manager.update_session(session_id, {"transcription": "转写内容"})
        manager.add_message(
            session_id,
            ChatMessage(MessageRole.USER, "问题", MessageType.QUESTION)
        )
        
        manager.clear_chat_history(session_id)
        
        session = manager.get_session(session_id)
        assert len(session.chat_history) == 0
        assert session.audio_filename == "meeting.mp3"  # 保留
        assert session.transcription == "转写内容"  # 保留


class TestSessionManagerUtilities:
    """测试 SessionManager 辅助功能"""
    
    def test_session_exists_returns_true_for_existing(self):
        """测试 session_exists 对存在的会话返回 True"""
        manager = SessionManager()
        session_id = manager.create_session()
        
        assert manager.session_exists(session_id) is True
    
    def test_session_exists_returns_false_for_non_existing(self):
        """测试 session_exists 对不存在的会话返回 False"""
        manager = SessionManager()
        
        assert manager.session_exists("non-existent-id") is False
    
    def test_get_all_sessions_empty(self):
        """测试获取所有会话（空）"""
        manager = SessionManager()
        
        sessions = manager.get_all_sessions()
        
        assert sessions == []
    
    def test_get_all_sessions_returns_all(self):
        """测试获取所有会话"""
        manager = SessionManager()
        manager.create_session(audio_filename="file1.mp3")
        manager.create_session(audio_filename="file2.mp3")
        manager.create_session(audio_filename="file3.mp3")
        
        sessions = manager.get_all_sessions()
        
        assert len(sessions) == 3
        filenames = {s.audio_filename for s in sessions}
        assert filenames == {"file1.mp3", "file2.mp3", "file3.mp3"}
    
    def test_get_session_count_empty(self):
        """测试获取会话数量（空）"""
        manager = SessionManager()
        
        assert manager.get_session_count() == 0
    
    def test_get_session_count_after_create(self):
        """测试创建后获取会话数量"""
        manager = SessionManager()
        manager.create_session()
        manager.create_session()
        
        assert manager.get_session_count() == 2
    
    def test_get_session_count_after_delete(self):
        """测试删除后获取会话数量"""
        manager = SessionManager()
        session_id = manager.create_session()
        manager.create_session()
        manager.delete_session(session_id)
        
        assert manager.get_session_count() == 1
    
    def test_clear_all_sessions(self):
        """测试清空所有会话"""
        manager = SessionManager()
        manager.create_session()
        manager.create_session()
        manager.create_session()
        
        manager.clear_all_sessions()
        
        assert manager.get_session_count() == 0
        assert manager.get_all_sessions() == []


class TestSessionNotFoundError:
    """测试 SessionNotFoundError 异常"""
    
    def test_error_contains_session_id(self):
        """测试异常包含 session_id"""
        error = SessionNotFoundError("test-session-id")
        
        assert error.session_id == "test-session-id"
        assert "test-session-id" in str(error)
    
    def test_error_message_format(self):
        """测试异常消息格式"""
        error = SessionNotFoundError("abc-123")
        
        assert str(error) == "Session not found: abc-123"


class TestSessionManagerIsolation:
    """测试 SessionManager 实例隔离"""
    
    def test_different_managers_are_isolated(self):
        """测试不同管理器实例是隔离的"""
        manager1 = SessionManager()
        manager2 = SessionManager()
        
        session_id = manager1.create_session()
        
        assert manager1.session_exists(session_id)
        assert not manager2.session_exists(session_id)
    
    def test_manager_state_is_independent(self):
        """测试管理器状态是独立的"""
        manager1 = SessionManager()
        manager2 = SessionManager()
        
        manager1.create_session()
        manager1.create_session()
        manager2.create_session()
        
        assert manager1.get_session_count() == 2
        assert manager2.get_session_count() == 1
