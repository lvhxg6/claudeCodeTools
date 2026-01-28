# 总结服务属性测试
# Summary Service Property Tests

"""
总结服务的属性测试。

测试属性：
- Property 2: Markdown 格式输出与导出
- Property 7: 版本管理正确性
- Property 8: 确认后状态变更

**Validates: Requirements 3.5, 4.3, 6.3, 6.5, 6.7**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume

from src.models import Summary, SummaryStatus


# ============== 策略定义 ==============

# 有效的 Markdown 内容策略
markdown_content_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=('L', 'N', 'P', 'S', 'Z'),
        whitelist_characters='#*-_[]()>`\n\t '
    ),
    min_size=0,
    max_size=1000
)

# 非空 Markdown 内容策略
non_empty_markdown_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=('L', 'N', 'P', 'S', 'Z'),
        whitelist_characters='#*-_[]()>`\n\t '
    ),
    min_size=1,
    max_size=500
)

# 版本号策略
version_strategy = st.integers(min_value=1, max_value=100)


# ============== Property 2: Markdown 格式输出与导出 ==============

class TestMarkdownFormatProperty:
    """
    Property 2: Markdown 格式输出与导出
    
    *对于任意* 有效的总结内容，系统输出和导出的内容应该是有效的 Markdown 格式，
    且导出文件的内容应与界面显示的内容一致。
    
    **Validates: Requirements 3.5, 4.3**
    """
    
    @given(content=markdown_content_strategy)
    @settings(max_examples=100)
    def test_summary_content_preserved_in_serialization(self, content: str):
        """
        测试总结内容在序列化/反序列化过程中保持不变
        
        Feature: meeting-summary, Property 2: Markdown 格式输出与导出
        **Validates: Requirements 3.5, 4.3**
        """
        # 创建总结
        summary = Summary.create_draft(content)
        
        # 序列化
        data = summary.to_dict()
        
        # 反序列化
        restored = Summary.from_dict(data)
        
        # 验证内容一致
        assert restored.content == content
        assert restored.content == summary.content
    
    @given(content=markdown_content_strategy)
    @settings(max_examples=100)
    def test_summary_to_dict_contains_content(self, content: str):
        """
        测试序列化结果包含完整内容
        
        Feature: meeting-summary, Property 2: Markdown 格式输出与导出
        **Validates: Requirements 3.5, 4.3**
        """
        summary = Summary.create_draft(content)
        data = summary.to_dict()
        
        # 验证导出数据包含内容
        assert "content" in data
        assert data["content"] == content
    
    @given(
        initial_content=markdown_content_strategy,
        updated_content=markdown_content_strategy
    )
    @settings(max_examples=100)
    def test_updated_content_preserved(
        self, 
        initial_content: str, 
        updated_content: str
    ):
        """
        测试更新后的内容正确保存
        
        Feature: meeting-summary, Property 2: Markdown 格式输出与导出
        **Validates: Requirements 3.5, 4.3**
        """
        summary = Summary.create_draft(initial_content)
        summary.update_content(updated_content)
        
        # 序列化并反序列化
        data = summary.to_dict()
        restored = Summary.from_dict(data)
        
        # 验证当前内容是更新后的内容
        assert restored.content == updated_content


# ============== Property 7: 版本管理正确性 ==============

class TestVersionManagementProperty:
    """
    Property 7: 版本管理正确性
    
    *对于任意* 总结修改操作：
    - 修改后的版本号应该比修改前的版本号大 1
    - 修改前的内容应该被保存到历史记录中
    - 历史记录的长度应该等于当前版本号减 1
    
    **Validates: Requirements 6.3, 6.7**
    """
    
    @given(
        initial_content=non_empty_markdown_strategy,
        new_content=non_empty_markdown_strategy
    )
    @settings(max_examples=100)
    def test_version_increments_by_one(
        self, 
        initial_content: str, 
        new_content: str
    ):
        """
        测试版本号每次更新增加 1
        
        Feature: meeting-summary, Property 7: 版本管理正确性
        **Validates: Requirements 6.3**
        """
        summary = Summary.create_draft(initial_content)
        initial_version = summary.version
        
        summary.update_content(new_content)
        
        assert summary.version == initial_version + 1
    
    @given(
        initial_content=non_empty_markdown_strategy,
        new_content=non_empty_markdown_strategy
    )
    @settings(max_examples=100)
    def test_old_content_saved_to_history(
        self, 
        initial_content: str, 
        new_content: str
    ):
        """
        测试旧内容保存到历史记录
        
        Feature: meeting-summary, Property 7: 版本管理正确性
        **Validates: Requirements 6.7**
        """
        summary = Summary.create_draft(initial_content)
        
        summary.update_content(new_content)
        
        # 验证旧内容在历史记录中
        assert initial_content in summary.history
        assert summary.history[-1] == initial_content
    
    @given(
        initial_content=non_empty_markdown_strategy,
        updates=st.lists(non_empty_markdown_strategy, min_size=1, max_size=10)
    )
    @settings(max_examples=100)
    def test_history_length_equals_version_minus_one(
        self, 
        initial_content: str, 
        updates: list[str]
    ):
        """
        测试历史记录长度等于版本号减 1
        
        Feature: meeting-summary, Property 7: 版本管理正确性
        **Validates: Requirements 6.3, 6.7**
        """
        summary = Summary.create_draft(initial_content)
        
        for update in updates:
            summary.update_content(update)
        
        # 验证历史记录长度
        assert len(summary.history) == summary.version - 1
    
    @given(
        initial_content=non_empty_markdown_strategy,
        updates=st.lists(non_empty_markdown_strategy, min_size=2, max_size=5)
    )
    @settings(max_examples=100)
    def test_history_preserves_order(
        self, 
        initial_content: str, 
        updates: list[str]
    ):
        """
        测试历史记录保持正确顺序
        
        Feature: meeting-summary, Property 7: 版本管理正确性
        **Validates: Requirements 6.7**
        """
        summary = Summary.create_draft(initial_content)
        
        all_contents = [initial_content] + updates[:-1]  # 除了最后一个更新
        
        for update in updates:
            summary.update_content(update)
        
        # 验证历史记录顺序
        assert summary.history == all_contents
    
    @given(
        initial_content=non_empty_markdown_strategy,
        new_content=non_empty_markdown_strategy
    )
    @settings(max_examples=100)
    def test_version_management_after_serialization(
        self, 
        initial_content: str, 
        new_content: str
    ):
        """
        测试序列化后版本管理信息保持正确
        
        Feature: meeting-summary, Property 7: 版本管理正确性
        **Validates: Requirements 6.3, 6.7**
        """
        summary = Summary.create_draft(initial_content)
        summary.update_content(new_content)
        
        # 序列化并反序列化
        data = summary.to_dict()
        restored = Summary.from_dict(data)
        
        # 验证版本信息
        assert restored.version == summary.version
        assert restored.history == summary.history
        assert len(restored.history) == restored.version - 1


# ============== Property 8: 确认后状态变更 ==============

class TestFinalizeStatusProperty:
    """
    Property 8: 确认后状态变更
    
    *对于任意* 处于草稿状态的总结，当用户确认生成后，
    其状态应该变为 "final"，且状态变更后内容不应发生改变。
    
    **Validates: Requirements 6.5**
    """
    
    @given(content=markdown_content_strategy)
    @settings(max_examples=100)
    def test_finalize_changes_status_to_final(self, content: str):
        """
        测试确认后状态变为 final
        
        Feature: meeting-summary, Property 8: 确认后状态变更
        **Validates: Requirements 6.5**
        """
        summary = Summary.create_draft(content)
        assert summary.status == SummaryStatus.DRAFT
        
        summary.finalize()
        
        assert summary.status == SummaryStatus.FINAL
    
    @given(content=markdown_content_strategy)
    @settings(max_examples=100)
    def test_content_unchanged_after_finalize(self, content: str):
        """
        测试确认后内容不变
        
        Feature: meeting-summary, Property 8: 确认后状态变更
        **Validates: Requirements 6.5**
        """
        summary = Summary.create_draft(content)
        original_content = summary.content
        
        summary.finalize()
        
        assert summary.content == original_content
    
    @given(
        initial_content=non_empty_markdown_strategy,
        updates=st.lists(non_empty_markdown_strategy, min_size=0, max_size=5)
    )
    @settings(max_examples=100)
    def test_version_unchanged_after_finalize(
        self, 
        initial_content: str, 
        updates: list[str]
    ):
        """
        测试确认后版本号不变
        
        Feature: meeting-summary, Property 8: 确认后状态变更
        **Validates: Requirements 6.5**
        """
        summary = Summary.create_draft(initial_content)
        
        for update in updates:
            summary.update_content(update)
        
        version_before = summary.version
        summary.finalize()
        
        assert summary.version == version_before
    
    @given(content=markdown_content_strategy)
    @settings(max_examples=100)
    def test_cannot_update_after_finalize(self, content: str):
        """
        测试确认后不能再更新
        
        Feature: meeting-summary, Property 8: 确认后状态变更
        **Validates: Requirements 6.5**
        """
        summary = Summary.create_draft(content)
        summary.finalize()
        
        with pytest.raises(ValueError):
            summary.update_content("new content")
    
    @given(content=markdown_content_strategy)
    @settings(max_examples=100)
    def test_cannot_finalize_twice(self, content: str):
        """
        测试不能重复确认
        
        Feature: meeting-summary, Property 8: 确认后状态变更
        **Validates: Requirements 6.5**
        """
        summary = Summary.create_draft(content)
        summary.finalize()
        
        with pytest.raises(ValueError):
            summary.finalize()
    
    @given(content=markdown_content_strategy)
    @settings(max_examples=100)
    def test_finalize_preserves_history(self, content: str):
        """
        测试确认后历史记录保持不变
        
        Feature: meeting-summary, Property 8: 确认后状态变更
        **Validates: Requirements 6.5**
        """
        summary = Summary.create_draft(content)
        summary.update_content("updated content")
        
        history_before = summary.history.copy()
        summary.finalize()
        
        assert summary.history == history_before
