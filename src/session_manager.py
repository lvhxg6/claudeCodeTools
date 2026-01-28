# 会话管理器
# Session Manager

"""
会话管理器模块 - 管理用户会话状态。

支持功能：
- 会话创建、获取、更新、删除
- 会话内存存储
- 会话生命周期管理

Requirements:
- 5.4: 保持当前会话的对话历史直到用户开始新的录音处理
- 5.5: 用户开始处理新的录音文件时清空之前的对话历史
"""

import logging
import uuid
from datetime import datetime
from threading import Lock
from typing import Any, Optional

from src.models import Session, Summary, ChatMessage

# 配置日志
logger = logging.getLogger(__name__)


class SessionNotFoundError(Exception):
    """会话不存在异常"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        super().__init__(f"Session not found: {session_id}")


class SessionManager:
    """
    会话管理器，管理用户会话状态。
    
    使用内存存储管理会话数据，支持会话的创建、获取、更新和删除操作。
    线程安全，支持并发访问。
    
    Attributes:
        _sessions: 会话存储字典，key 为 session_id
        _lock: 线程锁，保证并发安全
    
    Requirements:
        - 5.4: 保持当前会话的对话历史直到用户开始新的录音处理
        - 5.5: 用户开始处理新的录音文件时清空之前的对话历史
    
    Example:
        >>> manager = SessionManager()
        >>> session_id = manager.create_session()
        >>> session = manager.get_session(session_id)
        >>> manager.update_session(session_id, {"transcription": "会议内容..."})
        >>> manager.delete_session(session_id)
    """
    
    def __init__(self):
        """
        初始化会话管理器。
        
        创建空的会话存储和线程锁。
        """
        self._sessions: dict[str, Session] = {}
        self._lock = Lock()
        logger.info("SessionManager 初始化完成")
    
    def create_session(self, audio_filename: str = "") -> str:
        """
        创建新会话，返回 session_id。
        
        创建一个新的会话，包含空的转写文本和草稿状态的总结。
        会话 ID 使用 UUID4 生成，保证唯一性。
        
        Args:
            audio_filename: 音频文件名，可选
        
        Returns:
            新创建的会话 ID
        
        Example:
            >>> manager = SessionManager()
            >>> session_id = manager.create_session("meeting.mp3")
            >>> print(session_id)  # "550e8400-e29b-41d4-a716-446655440000"
        """
        session_id = str(uuid.uuid4())
        
        with self._lock:
            session = Session.create(
                audio_filename=audio_filename,
                session_id=session_id
            )
            self._sessions[session_id] = session
        
        logger.info(f"创建新会话: {session_id}, 文件名: {audio_filename}")
        return session_id
    
    def get_session(self, session_id: str) -> Session:
        """
        获取会话数据。
        
        根据 session_id 获取对应的会话对象。
        
        Args:
            session_id: 会话 ID
        
        Returns:
            Session 对象
        
        Raises:
            SessionNotFoundError: 会话不存在时抛出
        
        Example:
            >>> manager = SessionManager()
            >>> session_id = manager.create_session()
            >>> session = manager.get_session(session_id)
            >>> print(session.id)
        """
        with self._lock:
            if session_id not in self._sessions:
                logger.warning(f"会话不存在: {session_id}")
                raise SessionNotFoundError(session_id)
            
            return self._sessions[session_id]
    
    def update_session(self, session_id: str, data: dict[str, Any]) -> None:
        """
        更新会话数据。
        
        根据提供的数据字典更新会话的相应字段。
        支持更新的字段包括：
        - audio_filename: 音频文件名
        - transcription: 转写文本
        - summary: 总结对象或字典
        - chat_history: 对话历史列表
        
        Args:
            session_id: 会话 ID
            data: 要更新的数据字典
        
        Raises:
            SessionNotFoundError: 会话不存在时抛出
        
        Validates: Requirements 5.4
        
        Example:
            >>> manager = SessionManager()
            >>> session_id = manager.create_session()
            >>> manager.update_session(session_id, {
            ...     "transcription": "会议内容...",
            ...     "audio_filename": "meeting.mp3"
            ... })
        """
        with self._lock:
            if session_id not in self._sessions:
                logger.warning(f"更新失败，会话不存在: {session_id}")
                raise SessionNotFoundError(session_id)
            
            session = self._sessions[session_id]
            
            # 更新音频文件名
            if "audio_filename" in data:
                session.audio_filename = data["audio_filename"]
            
            # 更新转写文本
            if "transcription" in data:
                session.set_transcription(data["transcription"])
            
            # 更新总结
            if "summary" in data:
                summary_data = data["summary"]
                if isinstance(summary_data, Summary):
                    session.set_summary(summary_data)
                elif isinstance(summary_data, dict):
                    session.set_summary(Summary.from_dict(summary_data))
            
            # 更新对话历史
            if "chat_history" in data:
                chat_history = data["chat_history"]
                session.chat_history.clear()
                for msg in chat_history:
                    if isinstance(msg, ChatMessage):
                        session.chat_history.append(msg)
                    elif isinstance(msg, dict):
                        session.chat_history.append(ChatMessage.from_dict(msg))
                session.updated_at = datetime.now()
            
            # 更新时间戳
            session.updated_at = datetime.now()
        
        logger.debug(f"更新会话: {session_id}, 字段: {list(data.keys())}")
    
    def delete_session(self, session_id: str) -> None:
        """
        删除会话。
        
        从存储中删除指定的会话。
        
        Args:
            session_id: 会话 ID
        
        Raises:
            SessionNotFoundError: 会话不存在时抛出
        
        Example:
            >>> manager = SessionManager()
            >>> session_id = manager.create_session()
            >>> manager.delete_session(session_id)
        """
        with self._lock:
            if session_id not in self._sessions:
                logger.warning(f"删除失败，会话不存在: {session_id}")
                raise SessionNotFoundError(session_id)
            
            del self._sessions[session_id]
        
        logger.info(f"删除会话: {session_id}")
    
    def session_exists(self, session_id: str) -> bool:
        """
        检查会话是否存在。
        
        Args:
            session_id: 会话 ID
        
        Returns:
            会话是否存在
        
        Example:
            >>> manager = SessionManager()
            >>> session_id = manager.create_session()
            >>> manager.session_exists(session_id)
            True
            >>> manager.session_exists("invalid-id")
            False
        """
        with self._lock:
            return session_id in self._sessions
    
    def add_message(self, session_id: str, message: ChatMessage) -> None:
        """
        向会话添加对话消息。
        
        Args:
            session_id: 会话 ID
            message: 要添加的消息
        
        Raises:
            SessionNotFoundError: 会话不存在时抛出
        
        Validates: Requirements 5.4
        
        Example:
            >>> manager = SessionManager()
            >>> session_id = manager.create_session()
            >>> msg = ChatMessage("user", "问题", "question")
            >>> manager.add_message(session_id, msg)
        """
        with self._lock:
            if session_id not in self._sessions:
                logger.warning(f"添加消息失败，会话不存在: {session_id}")
                raise SessionNotFoundError(session_id)
            
            self._sessions[session_id].add_message(message)
        
        logger.debug(f"添加消息到会话: {session_id}")
    
    def clear_chat_history(self, session_id: str) -> None:
        """
        清空会话的对话历史。
        
        用于用户开始处理新的录音文件时清空之前的对话历史。
        
        Args:
            session_id: 会话 ID
        
        Raises:
            SessionNotFoundError: 会话不存在时抛出
        
        Validates: Requirements 5.5
        
        Example:
            >>> manager = SessionManager()
            >>> session_id = manager.create_session()
            >>> manager.add_message(session_id, ChatMessage("user", "问题", "question"))
            >>> manager.clear_chat_history(session_id)
            >>> session = manager.get_session(session_id)
            >>> len(session.chat_history)
            0
        """
        with self._lock:
            if session_id not in self._sessions:
                logger.warning(f"清空历史失败，会话不存在: {session_id}")
                raise SessionNotFoundError(session_id)
            
            self._sessions[session_id].clear_chat_history()
        
        logger.info(f"清空会话对话历史: {session_id}")
    
    def get_all_sessions(self) -> list[Session]:
        """
        获取所有会话列表。
        
        Returns:
            所有会话的列表
        
        Example:
            >>> manager = SessionManager()
            >>> manager.create_session()
            >>> manager.create_session()
            >>> sessions = manager.get_all_sessions()
            >>> len(sessions)
            2
        """
        with self._lock:
            return list(self._sessions.values())
    
    def get_session_count(self) -> int:
        """
        获取会话数量。
        
        Returns:
            当前存储的会话数量
        
        Example:
            >>> manager = SessionManager()
            >>> manager.create_session()
            >>> manager.get_session_count()
            1
        """
        with self._lock:
            return len(self._sessions)
    
    def clear_all_sessions(self) -> None:
        """
        清空所有会话。
        
        删除所有存储的会话数据。
        
        Example:
            >>> manager = SessionManager()
            >>> manager.create_session()
            >>> manager.clear_all_sessions()
            >>> manager.get_session_count()
            0
        """
        with self._lock:
            self._sessions.clear()
        
        logger.info("清空所有会话")
