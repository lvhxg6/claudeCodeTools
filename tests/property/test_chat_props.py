# 对话服务属性测试
# Chat Service Property Tests

"""
对话服务的属性测试。

测试属性：
- Property 3: 对话上下文完整性

**Validates: Requirements 5.2**
"""

import pytest
from hypothesis import given, strategies as st, settings

from src.chat_service import ChatService
from src.config_manager import ConfigManager
from src.models import ChatMessage, MessageRole, MessageType


# ============== 策略定义 ==============

# 文本内容策略
text_content_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=('L', 'N', 'P', 'S', 'Z'),
        whitelist_characters='\n\t '
    ),
    min_size=0,
    max_size=500
)

# 非空文本策略
non_empty_text_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=('L', 'N', 'P', 'S', 'Z'),
        whitelist_characters='\n\t '
    ),
    min_size=1,
    max_size=200
)

# 对话消息策略
chat_message_strategy = st.fixed_dictionaries({
    "role": st.sampled_from([MessageRole.USER, MessageRole.ASSISTANT]),
    "content": non_empty_text_strategy
})

# 对话历史策略
chat_history_strategy = st.lists(
    chat_message_strategy,
    min_size=0,
    max_size=10
)


# ============== Property 3: 对话上下文完整性 ==============

class TestChatContextProperty:
    """
    Property 3: 对话上下文完整性
    
    *对于任意* 用户追问请求，发送给 Claude CLI 的上下文应该包含：
    - 原始转写文本
    - 当前总结内容
    - 完整的对话历史
    
    **Validates: Requirements 5.2**
    """
    
    @given(
        transcription=text_content_strategy,
        summary=text_content_strategy,
        message=non_empty_text_strategy,
        history=chat_history_strategy
    )
    @settings(max_examples=100)
    def test_context_contains_transcription(
        self,
        transcription: str,
        summary: str,
        message: str,
        history: list
    ):
        """
        测试上下文包含转写文本
        
        Feature: meeting-summary, Property 3: 对话上下文完整性
        **Validates: Requirements 5.2**
        """
        config = ConfigManager("nonexistent.yaml")
        service = ChatService(config)
        
        context = service._build_context(
            transcription=transcription,
            summary=summary,
            message=message,
            history=history,
            message_type=MessageType.QUESTION
        )
        
        # 验证转写文本在上下文中
        assert transcription in context
    
    @given(
        transcription=text_content_strategy,
        summary=text_content_strategy,
        message=non_empty_text_strategy,
        history=chat_history_strategy
    )
    @settings(max_examples=100)
    def test_context_contains_summary(
        self,
        transcription: str,
        summary: str,
        message: str,
        history: list
    ):
        """
        测试上下文包含总结内容
        
        Feature: meeting-summary, Property 3: 对话上下文完整性
        **Validates: Requirements 5.2**
        """
        config = ConfigManager("nonexistent.yaml")
        service = ChatService(config)
        
        context = service._build_context(
            transcription=transcription,
            summary=summary,
            message=message,
            history=history,
            message_type=MessageType.QUESTION
        )
        
        # 验证总结内容在上下文中
        assert summary in context
    
    @given(
        transcription=text_content_strategy,
        summary=text_content_strategy,
        message=non_empty_text_strategy,
        history=chat_history_strategy
    )
    @settings(max_examples=100)
    def test_context_contains_message(
        self,
        transcription: str,
        summary: str,
        message: str,
        history: list
    ):
        """
        测试上下文包含用户消息
        
        Feature: meeting-summary, Property 3: 对话上下文完整性
        **Validates: Requirements 5.2**
        """
        config = ConfigManager("nonexistent.yaml")
        service = ChatService(config)
        
        context = service._build_context(
            transcription=transcription,
            summary=summary,
            message=message,
            history=history,
            message_type=MessageType.QUESTION
        )
        
        # 验证用户消息在上下文中
        assert message in context
    
    @given(
        transcription=text_content_strategy,
        summary=text_content_strategy,
        message=non_empty_text_strategy,
        history=st.lists(chat_message_strategy, min_size=1, max_size=5)
    )
    @settings(max_examples=100)
    def test_context_contains_history_content(
        self,
        transcription: str,
        summary: str,
        message: str,
        history: list
    ):
        """
        测试上下文包含对话历史内容
        
        Feature: meeting-summary, Property 3: 对话上下文完整性
        **Validates: Requirements 5.2**
        """
        config = ConfigManager("nonexistent.yaml")
        service = ChatService(config)
        
        context = service._build_context(
            transcription=transcription,
            summary=summary,
            message=message,
            history=history,
            message_type=MessageType.QUESTION
        )
        
        # 验证每条历史消息的内容都在上下文中
        for msg in history:
            assert msg["content"] in context
    
    @given(
        transcription=text_content_strategy,
        summary=text_content_strategy,
        history=chat_history_strategy
    )
    @settings(max_examples=100)
    def test_context_info_reflects_inputs(
        self,
        transcription: str,
        summary: str,
        history: list
    ):
        """
        测试上下文信息正确反映输入
        
        Feature: meeting-summary, Property 3: 对话上下文完整性
        **Validates: Requirements 5.2**
        """
        config = ConfigManager("nonexistent.yaml")
        service = ChatService(config)
        
        info = service.get_context_info(
            transcription=transcription,
            summary=summary,
            history=history
        )
        
        # 验证上下文信息
        assert info["has_transcription"] == bool(transcription)
        assert info["transcription_length"] == len(transcription)
        assert info["has_summary"] == bool(summary)
        assert info["summary_length"] == len(summary)
        assert info["history_count"] == len(history)
    
    @given(
        transcription=non_empty_text_strategy,
        summary=non_empty_text_strategy,
        message=non_empty_text_strategy
    )
    @settings(max_examples=100)
    def test_empty_history_handled(
        self,
        transcription: str,
        summary: str,
        message: str
    ):
        """
        测试空历史正确处理
        
        Feature: meeting-summary, Property 3: 对话上下文完整性
        **Validates: Requirements 5.2**
        """
        config = ConfigManager("nonexistent.yaml")
        service = ChatService(config)
        
        context = service._build_context(
            transcription=transcription,
            summary=summary,
            message=message,
            history=[],
            message_type=MessageType.QUESTION
        )
        
        # 验证空历史有适当的占位符
        assert "无历史对话" in context
        # 验证其他内容仍然存在
        assert transcription in context
        assert summary in context
        assert message in context
    
    @given(
        transcription=text_content_strategy,
        summary=text_content_strategy,
        message=non_empty_text_strategy,
        history=chat_history_strategy
    )
    @settings(max_examples=100)
    def test_edit_request_context_contains_all_parts(
        self,
        transcription: str,
        summary: str,
        message: str,
        history: list
    ):
        """
        测试编辑请求上下文包含所有部分
        
        Feature: meeting-summary, Property 3: 对话上下文完整性
        **Validates: Requirements 5.2**
        """
        config = ConfigManager("nonexistent.yaml")
        service = ChatService(config)
        
        context = service._build_context(
            transcription=transcription,
            summary=summary,
            message=message,
            history=history,
            message_type=MessageType.EDIT_REQUEST
        )
        
        # 验证所有部分都在上下文中
        assert transcription in context
        assert summary in context
        assert message in context
