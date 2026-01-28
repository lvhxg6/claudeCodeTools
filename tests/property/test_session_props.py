# SessionManager 属性测试
# SessionManager Property-Based Tests

"""
SessionManager 会话管理器的属性测试。

使用 Hypothesis 进行属性测试，验证会话管理器的核心属性：
- Property 4: 会话历史保持
- Property 5: 新会话清空历史
- Property 6: 新总结为草稿状态

**Feature: meeting-summary**
**Validates: Requirements 5.4, 5.5, 6.1**
"""

from datetime import datetime
from typing import List

import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st

from src.models import (
    Session, 
    Summary, 
    ChatMessage, 
    SummaryStatus, 
    MessageRole, 
    MessageType
)
from src.session_manager import SessionManager, SessionNotFoundError


# =============================================================================
# 自定义策略 (Custom Strategies)
# =============================================================================

@st.composite
def valid_message_roles(draw):
    """生成有效的消息角色"""
    return draw(st.sampled_from([MessageRole.USER, MessageRole.ASSISTANT]))


@st.composite
def valid_message_types(draw):
    """生成有效的消息类型"""
    return draw(st.sampled_from([
        MessageType.QUESTION, 
        MessageType.EDIT_REQUEST, 
        MessageType.RESPONSE
    ]))


@st.composite
def valid_chat_messages(draw):
    """生成有效的对话消息"""
    role = draw(valid_message_roles())
    content = draw(st.text(min_size=1, max_size=500))
    
    # 根据角色选择合适的消息类型
    if role == MessageRole.USER:
        message_type = draw(st.sampled_from([
            MessageType.QUESTION, 
            MessageType.EDIT_REQUEST
        ]))
    else:
        message_type = MessageType.RESPONSE
    
    return ChatMessage(
        role=role,
        content=content,
        message_type=message_type,
        timestamp=datetime.now()
    )


@st.composite
def valid_chat_message_lists(draw, min_size=0, max_size=20):
    """生成有效的对话消息列表"""
    messages = draw(st.lists(
        valid_chat_messages(),
        min_size=min_size,
        max_size=max_size
    ))
    return messages


@st.composite
def valid_audio_filenames(draw):
    """生成有效的音频文件名"""
    name = draw(st.text(
        alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='_-'),
        min_size=1,
        max_size=50
    ))
    extension = draw(st.sampled_from([".mp3", ".wav", ".m4a"]))
    return f"{name}{extension}"


@st.composite
def valid_summary_contents(draw):
    """生成有效的总结内容（Markdown 格式）"""
    title = draw(st.text(min_size=1, max_size=100))
    body = draw(st.text(min_size=0, max_size=1000))
    return f"# {title}\n\n{body}"


@st.composite
def valid_transcriptions(draw):
    """生成有效的转写文本"""
    return draw(st.text(min_size=0, max_size=5000))


# =============================================================================
# Property 4: 会话历史保持
# =============================================================================

class TestProperty4SessionHistoryPreservation:
    """
    **Feature: meeting-summary, Property 4: 会话历史保持**
    
    *对于任意* 会话，在用户未开始新录音处理之前，所有对话消息应该被保留在
    会话历史中，且消息顺序与添加顺序一致。
    
    **Validates: Requirements 5.4**
    """
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @given(messages=valid_chat_message_lists(min_size=1, max_size=20))
    def test_all_messages_preserved_in_order(self, messages: List[ChatMessage]):
        """
        **Feature: meeting-summary, Property 4: 会话历史保持**
        
        验证：对于任意数量的消息，添加到会话后应全部保留且顺序一致。
        
        **Validates: Requirements 5.4**
        """
        # Arrange: 创建会话管理器和新会话
        manager = SessionManager()
        session_id = manager.create_session("test.mp3")
        
        # Act: 按顺序添加所有消息
        for msg in messages:
            manager.add_message(session_id, msg)
        
        # Assert: 获取会话并验证消息
        session = manager.get_session(session_id)
        
        # 验证消息数量
        assert len(session.chat_history) == len(messages), \
            f"Expected {len(messages)} messages, but got {len(session.chat_history)}"
        
        # 验证消息顺序和内容
        for i, (expected, actual) in enumerate(zip(messages, session.chat_history)):
            assert actual.role == expected.role, \
                f"Message {i}: role mismatch, expected '{expected.role}', got '{actual.role}'"
            assert actual.content == expected.content, \
                f"Message {i}: content mismatch"
            assert actual.message_type == expected.message_type, \
                f"Message {i}: message_type mismatch"
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @given(
        messages1=valid_chat_message_lists(min_size=1, max_size=10),
        messages2=valid_chat_message_lists(min_size=1, max_size=10)
    )
    def test_messages_accumulated_across_multiple_additions(
        self, 
        messages1: List[ChatMessage], 
        messages2: List[ChatMessage]
    ):
        """
        **Feature: meeting-summary, Property 4: 会话历史保持**
        
        验证：多次添加消息后，所有消息应累积保留。
        
        **Validates: Requirements 5.4**
        """
        # Arrange: 创建会话管理器和新会话
        manager = SessionManager()
        session_id = manager.create_session("test.mp3")
        
        # Act: 分两批添加消息
        for msg in messages1:
            manager.add_message(session_id, msg)
        
        for msg in messages2:
            manager.add_message(session_id, msg)
        
        # Assert: 验证所有消息都被保留
        session = manager.get_session(session_id)
        expected_total = len(messages1) + len(messages2)
        
        assert len(session.chat_history) == expected_total, \
            f"Expected {expected_total} messages, but got {len(session.chat_history)}"
        
        # 验证顺序：先是 messages1，然后是 messages2
        all_messages = messages1 + messages2
        for i, (expected, actual) in enumerate(zip(all_messages, session.chat_history)):
            assert actual.content == expected.content, \
                f"Message {i}: content mismatch after accumulation"
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @given(messages=valid_chat_message_lists(min_size=1, max_size=15))
    def test_session_update_preserves_existing_messages(
        self, 
        messages: List[ChatMessage]
    ):
        """
        **Feature: meeting-summary, Property 4: 会话历史保持**
        
        验证：更新会话其他字段（如转写文本）不影响对话历史。
        
        **Validates: Requirements 5.4**
        """
        # Arrange: 创建会话并添加消息
        manager = SessionManager()
        session_id = manager.create_session("test.mp3")
        
        for msg in messages:
            manager.add_message(session_id, msg)
        
        # Act: 更新会话的转写文本
        manager.update_session(session_id, {
            "transcription": "新的转写文本内容..."
        })
        
        # Assert: 对话历史应保持不变
        session = manager.get_session(session_id)
        
        assert len(session.chat_history) == len(messages), \
            "Updating transcription should not affect chat history"
        
        for i, (expected, actual) in enumerate(zip(messages, session.chat_history)):
            assert actual.content == expected.content, \
                f"Message {i}: content changed after session update"
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @given(
        messages=valid_chat_message_lists(min_size=1, max_size=10),
        summary_content=valid_summary_contents()
    )
    def test_summary_update_preserves_chat_history(
        self, 
        messages: List[ChatMessage],
        summary_content: str
    ):
        """
        **Feature: meeting-summary, Property 4: 会话历史保持**
        
        验证：更新总结内容不影响对话历史。
        
        **Validates: Requirements 5.4**
        """
        # Arrange: 创建会话并添加消息
        manager = SessionManager()
        session_id = manager.create_session("test.mp3")
        
        for msg in messages:
            manager.add_message(session_id, msg)
        
        # Act: 更新总结内容
        new_summary = Summary.create_draft(summary_content)
        manager.update_session(session_id, {"summary": new_summary})
        
        # Assert: 对话历史应保持不变
        session = manager.get_session(session_id)
        
        assert len(session.chat_history) == len(messages), \
            "Updating summary should not affect chat history"


# =============================================================================
# Property 5: 新会话清空历史
# =============================================================================

class TestProperty5NewSessionClearsHistory:
    """
    **Feature: meeting-summary, Property 5: 新会话清空历史**
    
    *对于任意* 会话，当用户开始处理新的录音文件时，之前的对话历史应该被
    完全清空，新会话的对话历史长度应为 0。
    
    **Validates: Requirements 5.5**
    """
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @given(messages=valid_chat_message_lists(min_size=1, max_size=20))
    def test_clear_history_removes_all_messages(self, messages: List[ChatMessage]):
        """
        **Feature: meeting-summary, Property 5: 新会话清空历史**
        
        验证：清空对话历史后，消息数量应为 0。
        
        **Validates: Requirements 5.5**
        """
        # Arrange: 创建会话并添加消息
        manager = SessionManager()
        session_id = manager.create_session("test.mp3")
        
        for msg in messages:
            manager.add_message(session_id, msg)
        
        # 验证消息已添加
        session = manager.get_session(session_id)
        assert len(session.chat_history) == len(messages)
        
        # Act: 清空对话历史
        manager.clear_chat_history(session_id)
        
        # Assert: 对话历史应为空
        session = manager.get_session(session_id)
        assert len(session.chat_history) == 0, \
            f"Expected empty chat history, but got {len(session.chat_history)} messages"
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @given(audio_filename=valid_audio_filenames())
    def test_new_session_has_empty_history(self, audio_filename: str):
        """
        **Feature: meeting-summary, Property 5: 新会话清空历史**
        
        验证：新创建的会话对话历史长度应为 0。
        
        **Validates: Requirements 5.5**
        """
        # Arrange & Act: 创建新会话
        manager = SessionManager()
        session_id = manager.create_session(audio_filename)
        
        # Assert: 新会话的对话历史应为空
        session = manager.get_session(session_id)
        assert len(session.chat_history) == 0, \
            f"New session should have empty chat history, but got {len(session.chat_history)} messages"
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @given(
        messages=valid_chat_message_lists(min_size=1, max_size=15),
        new_filename=valid_audio_filenames()
    )
    def test_clear_history_preserves_other_session_data(
        self, 
        messages: List[ChatMessage],
        new_filename: str
    ):
        """
        **Feature: meeting-summary, Property 5: 新会话清空历史**
        
        验证：清空对话历史不影响会话的其他数据（如转写文本、总结）。
        
        **Validates: Requirements 5.5**
        """
        # Arrange: 创建会话并设置数据
        manager = SessionManager()
        session_id = manager.create_session("original.mp3")
        
        # 设置转写文本和总结
        transcription = "这是转写文本内容"
        summary = Summary.create_draft("# 会议总结")
        manager.update_session(session_id, {
            "transcription": transcription,
            "summary": summary
        })
        
        # 添加消息
        for msg in messages:
            manager.add_message(session_id, msg)
        
        # Act: 清空对话历史
        manager.clear_chat_history(session_id)
        
        # Assert: 其他数据应保持不变
        session = manager.get_session(session_id)
        
        assert len(session.chat_history) == 0, \
            "Chat history should be empty"
        assert session.transcription == transcription, \
            "Transcription should be preserved"
        assert session.summary.content == summary.content, \
            "Summary should be preserved"
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @given(
        messages1=valid_chat_message_lists(min_size=1, max_size=10),
        messages2=valid_chat_message_lists(min_size=1, max_size=10)
    )
    def test_clear_then_add_new_messages(
        self, 
        messages1: List[ChatMessage],
        messages2: List[ChatMessage]
    ):
        """
        **Feature: meeting-summary, Property 5: 新会话清空历史**
        
        验证：清空历史后可以正常添加新消息。
        
        **Validates: Requirements 5.5**
        """
        # Arrange: 创建会话并添加第一批消息
        manager = SessionManager()
        session_id = manager.create_session("test.mp3")
        
        for msg in messages1:
            manager.add_message(session_id, msg)
        
        # Act: 清空历史并添加新消息
        manager.clear_chat_history(session_id)
        
        for msg in messages2:
            manager.add_message(session_id, msg)
        
        # Assert: 只应包含新消息
        session = manager.get_session(session_id)
        
        assert len(session.chat_history) == len(messages2), \
            f"Expected {len(messages2)} messages, but got {len(session.chat_history)}"
        
        # 验证是新消息而不是旧消息
        for i, (expected, actual) in enumerate(zip(messages2, session.chat_history)):
            assert actual.content == expected.content, \
                f"Message {i}: should be from messages2"


# =============================================================================
# Property 6: 新总结为草稿状态
# =============================================================================

class TestProperty6NewSummaryIsDraft:
    """
    **Feature: meeting-summary, Property 6: 新总结为草稿状态**
    
    *对于任意* 新生成的总结，其初始状态应该为 "draft"，版本号应该为 1。
    
    **Validates: Requirements 6.1**
    """
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @given(content=valid_summary_contents())
    def test_create_draft_has_draft_status(self, content: str):
        """
        **Feature: meeting-summary, Property 6: 新总结为草稿状态**
        
        验证：使用 create_draft 创建的总结状态应为 "draft"。
        
        **Validates: Requirements 6.1**
        """
        # Act: 创建草稿总结
        summary = Summary.create_draft(content)
        
        # Assert: 状态应为 draft
        assert summary.status == SummaryStatus.DRAFT, \
            f"Expected status 'draft', but got '{summary.status}'"
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @given(content=valid_summary_contents())
    def test_create_draft_has_version_one(self, content: str):
        """
        **Feature: meeting-summary, Property 6: 新总结为草稿状态**
        
        验证：使用 create_draft 创建的总结版本号应为 1。
        
        **Validates: Requirements 6.1**
        """
        # Act: 创建草稿总结
        summary = Summary.create_draft(content)
        
        # Assert: 版本号应为 1
        assert summary.version == 1, \
            f"Expected version 1, but got {summary.version}"
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @given(content=valid_summary_contents())
    def test_create_draft_has_empty_history(self, content: str):
        """
        **Feature: meeting-summary, Property 6: 新总结为草稿状态**
        
        验证：使用 create_draft 创建的总结历史记录应为空。
        
        **Validates: Requirements 6.1**
        """
        # Act: 创建草稿总结
        summary = Summary.create_draft(content)
        
        # Assert: 历史记录应为空
        assert len(summary.history) == 0, \
            f"Expected empty history, but got {len(summary.history)} items"
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @given(audio_filename=valid_audio_filenames())
    def test_new_session_summary_is_draft(self, audio_filename: str):
        """
        **Feature: meeting-summary, Property 6: 新总结为草稿状态**
        
        验证：新创建的会话中的总结状态应为 "draft"。
        
        **Validates: Requirements 6.1**
        """
        # Act: 创建新会话
        manager = SessionManager()
        session_id = manager.create_session(audio_filename)
        session = manager.get_session(session_id)
        
        # Assert: 会话中的总结应为草稿状态
        assert session.summary.status == SummaryStatus.DRAFT, \
            f"Expected summary status 'draft', but got '{session.summary.status}'"
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @given(audio_filename=valid_audio_filenames())
    def test_new_session_summary_has_version_one(self, audio_filename: str):
        """
        **Feature: meeting-summary, Property 6: 新总结为草稿状态**
        
        验证：新创建的会话中的总结版本号应为 1。
        
        **Validates: Requirements 6.1**
        """
        # Act: 创建新会话
        manager = SessionManager()
        session_id = manager.create_session(audio_filename)
        session = manager.get_session(session_id)
        
        # Assert: 会话中的总结版本号应为 1
        assert session.summary.version == 1, \
            f"Expected summary version 1, but got {session.summary.version}"
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @given(
        audio_filename=valid_audio_filenames(),
        new_content=valid_summary_contents()
    )
    def test_set_new_draft_summary_preserves_draft_status(
        self, 
        audio_filename: str,
        new_content: str
    ):
        """
        **Feature: meeting-summary, Property 6: 新总结为草稿状态**
        
        验证：设置新的草稿总结后，状态仍为 "draft"，版本号为 1。
        
        **Validates: Requirements 6.1**
        """
        # Arrange: 创建会话
        manager = SessionManager()
        session_id = manager.create_session(audio_filename)
        
        # Act: 设置新的草稿总结
        new_summary = Summary.create_draft(new_content)
        manager.update_session(session_id, {"summary": new_summary})
        
        # Assert: 总结应为草稿状态，版本号为 1
        session = manager.get_session(session_id)
        assert session.summary.status == SummaryStatus.DRAFT, \
            f"Expected status 'draft', but got '{session.summary.status}'"
        assert session.summary.version == 1, \
            f"Expected version 1, but got {session.summary.version}"
        assert session.summary.content == new_content, \
            "Summary content should match"


# =============================================================================
# 综合属性测试
# =============================================================================

class TestSessionPropertiesCombined:
    """
    综合属性测试，验证 Property 4、5、6 的交互行为。
    
    **Feature: meeting-summary**
    **Validates: Requirements 5.4, 5.5, 6.1**
    """
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @given(
        messages=valid_chat_message_lists(min_size=1, max_size=10),
        summary_content=valid_summary_contents()
    )
    def test_full_session_workflow(
        self, 
        messages: List[ChatMessage],
        summary_content: str
    ):
        """
        **Feature: meeting-summary, Properties 4, 5, 6: 完整会话工作流**
        
        验证：完整的会话工作流程中，所有属性都得到满足。
        
        **Validates: Requirements 5.4, 5.5, 6.1**
        """
        # Arrange: 创建会话管理器
        manager = SessionManager()
        
        # Act & Assert 1: 创建新会话 (Property 5, 6)
        session_id = manager.create_session("meeting.mp3")
        session = manager.get_session(session_id)
        
        assert len(session.chat_history) == 0, \
            "New session should have empty chat history (Property 5)"
        assert session.summary.status == SummaryStatus.DRAFT, \
            "New session summary should be draft (Property 6)"
        assert session.summary.version == 1, \
            "New session summary version should be 1 (Property 6)"
        
        # Act & Assert 2: 添加消息 (Property 4)
        for msg in messages:
            manager.add_message(session_id, msg)
        
        session = manager.get_session(session_id)
        assert len(session.chat_history) == len(messages), \
            "All messages should be preserved (Property 4)"
        
        # Act & Assert 3: 设置新总结 (Property 6)
        new_summary = Summary.create_draft(summary_content)
        manager.update_session(session_id, {"summary": new_summary})
        
        session = manager.get_session(session_id)
        assert session.summary.status == SummaryStatus.DRAFT, \
            "Summary should remain draft (Property 6)"
        assert len(session.chat_history) == len(messages), \
            "Chat history should be preserved after summary update (Property 4)"
        
        # Act & Assert 4: 清空历史模拟新录音处理 (Property 5)
        manager.clear_chat_history(session_id)
        
        session = manager.get_session(session_id)
        assert len(session.chat_history) == 0, \
            "Chat history should be cleared (Property 5)"
        assert session.summary.content == summary_content, \
            "Summary should be preserved after clearing history"
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @given(
        filenames=st.lists(valid_audio_filenames(), min_size=2, max_size=5),
        messages=valid_chat_message_lists(min_size=1, max_size=5)
    )
    def test_multiple_sessions_independent(
        self, 
        filenames: List[str],
        messages: List[ChatMessage]
    ):
        """
        **Feature: meeting-summary, Properties 4, 5, 6: 多会话独立性**
        
        验证：多个会话之间相互独立，一个会话的操作不影响其他会话。
        
        **Validates: Requirements 5.4, 5.5, 6.1**
        """
        # Arrange: 创建会话管理器
        manager = SessionManager()
        session_ids = []
        
        # Act: 创建多个会话
        for filename in filenames:
            session_id = manager.create_session(filename)
            session_ids.append(session_id)
        
        # Act: 只向第一个会话添加消息
        for msg in messages:
            manager.add_message(session_ids[0], msg)
        
        # Assert: 第一个会话有消息，其他会话没有
        first_session = manager.get_session(session_ids[0])
        assert len(first_session.chat_history) == len(messages), \
            "First session should have all messages"
        
        for session_id in session_ids[1:]:
            session = manager.get_session(session_id)
            assert len(session.chat_history) == 0, \
                "Other sessions should have empty chat history"
            assert session.summary.status == SummaryStatus.DRAFT, \
                "Other sessions should have draft summary"
            assert session.summary.version == 1, \
                "Other sessions should have version 1 summary"
        
        # Act: 清空第一个会话的历史
        manager.clear_chat_history(session_ids[0])
        
        # Assert: 只有第一个会话被清空
        first_session = manager.get_session(session_ids[0])
        assert len(first_session.chat_history) == 0, \
            "First session history should be cleared"
