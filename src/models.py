# 数据模型
# Data Models

"""
数据模型模块 - 定义系统核心数据结构。

包含：
- Session: 用户会话数据
- Summary: 会议总结数据
- ChatMessage: 对话消息

支持功能：
- 数据序列化 (to_dict)
- 数据反序列化 (from_dict)
- 版本管理
- 历史记录

Requirements:
- 5.4: 保持当前会话的对话历史直到用户开始新的录音处理
- 6.1: 首次生成的总结标记为草稿状态
- 6.7: 保留草稿的修改历史供用户回顾
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


class SummaryStatus:
    """总结状态常量"""
    DRAFT = "draft"
    FINAL = "final"


class MessageRole:
    """消息角色常量"""
    USER = "user"
    ASSISTANT = "assistant"


class MessageType:
    """消息类型常量"""
    QUESTION = "question"
    EDIT_REQUEST = "edit_request"
    RESPONSE = "response"


@dataclass
class ChatMessage:
    """
    对话消息数据类。
    
    用于存储用户与 AI 之间的对话消息。
    
    Attributes:
        role: 消息角色，可选值: "user" | "assistant"
        content: 消息内容
        message_type: 消息类型，可选值: "question" | "edit_request" | "response"
        timestamp: 消息时间戳
    
    Example:
        >>> msg = ChatMessage(
        ...     role="user",
        ...     content="请补充第二点的细节",
        ...     message_type="edit_request"
        ... )
        >>> msg_dict = msg.to_dict()
        >>> restored = ChatMessage.from_dict(msg_dict)
    """
    role: str
    content: str
    message_type: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """验证字段值"""
        valid_roles = {MessageRole.USER, MessageRole.ASSISTANT}
        if self.role not in valid_roles:
            raise ValueError(
                f"Invalid role '{self.role}'. Must be one of: {valid_roles}"
            )
        
        valid_types = {
            MessageType.QUESTION, 
            MessageType.EDIT_REQUEST, 
            MessageType.RESPONSE
        }
        if self.message_type not in valid_types:
            raise ValueError(
                f"Invalid message_type '{self.message_type}'. "
                f"Must be one of: {valid_types}"
            )
    
    def to_dict(self) -> dict[str, Any]:
        """
        将对象序列化为字典。
        
        Returns:
            包含所有字段的字典，timestamp 转换为 ISO 格式字符串
        
        Example:
            >>> msg = ChatMessage("user", "Hello", "question")
            >>> d = msg.to_dict()
            >>> d["role"]
            'user'
        """
        return {
            "role": self.role,
            "content": self.content,
            "message_type": self.message_type,
            "timestamp": self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChatMessage":
        """
        从字典反序列化创建对象。
        
        Args:
            data: 包含字段数据的字典
        
        Returns:
            ChatMessage 实例
        
        Raises:
            KeyError: 缺少必需字段
            ValueError: 字段值无效
        
        Example:
            >>> data = {"role": "user", "content": "Hi", "message_type": "question", 
            ...         "timestamp": "2024-01-15T10:30:00"}
            >>> msg = ChatMessage.from_dict(data)
        """
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            timestamp = datetime.now()
        
        return cls(
            role=data["role"],
            content=data["content"],
            message_type=data["message_type"],
            timestamp=timestamp
        )


@dataclass
class Summary:
    """
    会议总结数据类。
    
    用于存储会议总结内容及其版本历史。
    
    Attributes:
        content: Markdown 格式的总结内容
        status: 总结状态，可选值: "draft" | "final"
        version: 版本号，从 1 开始
        history: 历史版本内容列表
    
    Requirements:
        - 6.1: 首次生成的总结标记为草稿状态
        - 6.7: 保留草稿的修改历史供用户回顾
    
    Example:
        >>> summary = Summary.create_draft("# 会议总结\\n...")
        >>> summary.status
        'draft'
        >>> summary.version
        1
    """
    content: str
    status: str = SummaryStatus.DRAFT
    version: int = 1
    history: list[str] = field(default_factory=list)
    
    def __post_init__(self):
        """验证字段值"""
        valid_statuses = {SummaryStatus.DRAFT, SummaryStatus.FINAL}
        if self.status not in valid_statuses:
            raise ValueError(
                f"Invalid status '{self.status}'. Must be one of: {valid_statuses}"
            )
        
        if self.version < 1:
            raise ValueError(f"Version must be >= 1, got {self.version}")
    
    @classmethod
    def create_draft(cls, content: str) -> "Summary":
        """
        创建新的草稿总结。
        
        创建一个新的总结，状态为 draft，版本号为 1。
        
        Args:
            content: Markdown 格式的总结内容
        
        Returns:
            新的 Summary 实例
        
        Validates: Requirements 6.1
        
        Example:
            >>> summary = Summary.create_draft("# 会议总结")
            >>> summary.status
            'draft'
            >>> summary.version
            1
        """
        return cls(
            content=content,
            status=SummaryStatus.DRAFT,
            version=1,
            history=[]
        )
    
    def update_content(self, new_content: str) -> None:
        """
        更新总结内容。
        
        将当前内容保存到历史记录，然后更新为新内容，版本号加 1。
        只有草稿状态的总结可以更新。
        
        Args:
            new_content: 新的总结内容
        
        Raises:
            ValueError: 如果总结已经是最终版本
        
        Validates: Requirements 6.3, 6.7
        
        Example:
            >>> summary = Summary.create_draft("v1 content")
            >>> summary.update_content("v2 content")
            >>> summary.version
            2
            >>> summary.history
            ['v1 content']
        """
        if self.status == SummaryStatus.FINAL:
            raise ValueError("Cannot update a finalized summary")
        
        # 保存当前内容到历史
        self.history.append(self.content)
        # 更新内容
        self.content = new_content
        # 版本号加 1
        self.version += 1
    
    def finalize(self) -> None:
        """
        确认生成最终版本。
        
        将总结状态从 draft 变更为 final。
        
        Raises:
            ValueError: 如果总结已经是最终版本
        
        Validates: Requirements 6.5
        
        Example:
            >>> summary = Summary.create_draft("content")
            >>> summary.finalize()
            >>> summary.status
            'final'
        """
        if self.status == SummaryStatus.FINAL:
            raise ValueError("Summary is already finalized")
        
        self.status = SummaryStatus.FINAL
    
    def to_dict(self) -> dict[str, Any]:
        """
        将对象序列化为字典。
        
        Returns:
            包含所有字段的字典
        
        Example:
            >>> summary = Summary.create_draft("content")
            >>> d = summary.to_dict()
            >>> d["status"]
            'draft'
        """
        return {
            "content": self.content,
            "status": self.status,
            "version": self.version,
            "history": self.history.copy()
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Summary":
        """
        从字典反序列化创建对象。
        
        Args:
            data: 包含字段数据的字典
        
        Returns:
            Summary 实例
        
        Raises:
            KeyError: 缺少必需字段
            ValueError: 字段值无效
        
        Example:
            >>> data = {"content": "text", "status": "draft", "version": 1, "history": []}
            >>> summary = Summary.from_dict(data)
        """
        return cls(
            content=data["content"],
            status=data.get("status", SummaryStatus.DRAFT),
            version=data.get("version", 1),
            history=data.get("history", []).copy()
        )


@dataclass
class Session:
    """
    用户会话数据类。
    
    用于存储完整的用户会话信息，包括音频文件、转写文本、总结和对话历史。
    
    Attributes:
        id: 会话唯一标识
        audio_filename: 原始音频文件名
        transcription: 转写文本
        summary: 总结对象
        chat_history: 对话历史列表
        created_at: 创建时间
        updated_at: 更新时间
    
    Requirements:
        - 5.4: 保持当前会话的对话历史直到用户开始新的录音处理
    
    Example:
        >>> session = Session.create("meeting.mp3")
        >>> session.add_message(ChatMessage("user", "问题", "question"))
        >>> len(session.chat_history)
        1
    """
    id: str
    audio_filename: str
    transcription: str
    summary: Summary
    chat_history: list[ChatMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    @classmethod
    def create(
        cls, 
        audio_filename: str, 
        session_id: Optional[str] = None
    ) -> "Session":
        """
        创建新会话。
        
        创建一个新的会话，包含空的转写文本和草稿总结。
        
        Args:
            audio_filename: 音频文件名
            session_id: 可选的会话 ID，如果不提供则自动生成
        
        Returns:
            新的 Session 实例
        
        Example:
            >>> session = Session.create("meeting.mp3")
            >>> session.audio_filename
            'meeting.mp3'
        """
        import uuid
        
        now = datetime.now()
        return cls(
            id=session_id or str(uuid.uuid4()),
            audio_filename=audio_filename,
            transcription="",
            summary=Summary.create_draft(""),
            chat_history=[],
            created_at=now,
            updated_at=now
        )
    
    def add_message(self, message: ChatMessage) -> None:
        """
        添加对话消息。
        
        将消息添加到对话历史，并更新会话的更新时间。
        
        Args:
            message: 要添加的消息
        
        Validates: Requirements 5.4
        
        Example:
            >>> session = Session.create("meeting.mp3")
            >>> msg = ChatMessage("user", "问题", "question")
            >>> session.add_message(msg)
            >>> len(session.chat_history)
            1
        """
        self.chat_history.append(message)
        self.updated_at = datetime.now()
    
    def clear_chat_history(self) -> None:
        """
        清空对话历史。
        
        清空所有对话消息，用于开始新的录音处理时。
        
        Validates: Requirements 5.5
        
        Example:
            >>> session = Session.create("meeting.mp3")
            >>> session.add_message(ChatMessage("user", "问题", "question"))
            >>> session.clear_chat_history()
            >>> len(session.chat_history)
            0
        """
        self.chat_history.clear()
        self.updated_at = datetime.now()
    
    def set_transcription(self, transcription: str) -> None:
        """
        设置转写文本。
        
        Args:
            transcription: 转写文本内容
        
        Example:
            >>> session = Session.create("meeting.mp3")
            >>> session.set_transcription("会议内容...")
            >>> session.transcription
            '会议内容...'
        """
        self.transcription = transcription
        self.updated_at = datetime.now()
    
    def set_summary(self, summary: Summary) -> None:
        """
        设置总结对象。
        
        Args:
            summary: 总结对象
        
        Example:
            >>> session = Session.create("meeting.mp3")
            >>> summary = Summary.create_draft("# 总结")
            >>> session.set_summary(summary)
        """
        self.summary = summary
        self.updated_at = datetime.now()
    
    def update_summary_content(self, new_content: str) -> None:
        """
        更新总结内容。
        
        更新总结内容并保存历史版本。
        
        Args:
            new_content: 新的总结内容
        
        Validates: Requirements 6.3, 6.7
        
        Example:
            >>> session = Session.create("meeting.mp3")
            >>> session.summary = Summary.create_draft("v1")
            >>> session.update_summary_content("v2")
            >>> session.summary.version
            2
        """
        self.summary.update_content(new_content)
        self.updated_at = datetime.now()
    
    def finalize_summary(self) -> None:
        """
        确认生成最终版本总结。
        
        Validates: Requirements 6.5
        
        Example:
            >>> session = Session.create("meeting.mp3")
            >>> session.summary = Summary.create_draft("content")
            >>> session.finalize_summary()
            >>> session.summary.status
            'final'
        """
        self.summary.finalize()
        self.updated_at = datetime.now()
    
    def to_dict(self) -> dict[str, Any]:
        """
        将对象序列化为字典。
        
        Returns:
            包含所有字段的字典，datetime 转换为 ISO 格式字符串
        
        Example:
            >>> session = Session.create("meeting.mp3")
            >>> d = session.to_dict()
            >>> d["audio_filename"]
            'meeting.mp3'
        """
        return {
            "id": self.id,
            "audio_filename": self.audio_filename,
            "transcription": self.transcription,
            "summary": self.summary.to_dict(),
            "chat_history": [msg.to_dict() for msg in self.chat_history],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Session":
        """
        从字典反序列化创建对象。
        
        Args:
            data: 包含字段数据的字典
        
        Returns:
            Session 实例
        
        Raises:
            KeyError: 缺少必需字段
            ValueError: 字段值无效
        
        Example:
            >>> data = {
            ...     "id": "123",
            ...     "audio_filename": "meeting.mp3",
            ...     "transcription": "text",
            ...     "summary": {"content": "", "status": "draft", "version": 1, "history": []},
            ...     "chat_history": [],
            ...     "created_at": "2024-01-15T10:00:00",
            ...     "updated_at": "2024-01-15T10:00:00"
            ... }
            >>> session = Session.from_dict(data)
        """
        # 解析时间戳
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now()
        
        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        elif updated_at is None:
            updated_at = datetime.now()
        
        # 解析 summary
        summary_data = data.get("summary")
        if isinstance(summary_data, dict):
            summary = Summary.from_dict(summary_data)
        else:
            summary = Summary.create_draft("")
        
        # 解析 chat_history
        chat_history_data = data.get("chat_history", [])
        chat_history = [
            ChatMessage.from_dict(msg) for msg in chat_history_data
        ]
        
        return cls(
            id=data["id"],
            audio_filename=data["audio_filename"],
            transcription=data.get("transcription", ""),
            summary=summary,
            chat_history=chat_history,
            created_at=created_at,
            updated_at=updated_at
        )
