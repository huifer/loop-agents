import sys
from pathlib import Path
from typing import Optional, Any, List, Dict
import asyncio

from langchain.prompts.chat import (
    ChatPromptTemplate,
)
from langchain.chains import ConversationChain
from langchain.schema.messages import AIMessage, HumanMessage, SystemMessage
from langchain.memory import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

sys.path.append(str(Path(__file__).parent.parent))

from tools.llm_generatory import get_llm_model


class ConversationManager:
    """
    对话管理器，提供系统提示设定、消息写入和对话历史功能
    """

    def __init__(
            self,
            system_prompt: str = "你是一个有用的AI助手。",
            history_window_size: int = 10,
            conversation_id: Optional[str] = None,
    ):
        """
        初始化对话管理器

        Args:
            system_prompt: 系统提示词
            history_window_size: 保留的历史消息数量
            conversation_id: 会话ID，用于标识不同会话
        """
        self.system_prompt = system_prompt
        self.history_window_size = history_window_size
        self.conversation_id = conversation_id or "default"
        self.llm = get_llm_model()
        self.message_history = ChatMessageHistory()

        # 初始化系统消息
        if system_prompt:
            self.message_history.add_message(SystemMessage(content=system_prompt))

        # 创建对话链
        self.setup_conversation_chain()

    def setup_conversation_chain(self):
        """设置对话链，使用RunnableWithMessageHistory"""
        # 创建基本的提示模板
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self.system_prompt),
                ("human", "{input}"),
            ]
        )

        # 创建对话链
        chain = prompt | self.llm

        # 使用RunnableWithMessageHistory包装对话链
        self.conversation_chain = RunnableWithMessageHistory(
            chain,
            lambda session_id: self.message_history,
            input_messages_key="input",
            history_messages_key="history",
        )

    def update_system_prompt(self, new_system_prompt: str):
        """
        更新系统提示词

        Args:
            new_system_prompt: 新的系统提示词
        """
        self.system_prompt = new_system_prompt

        # 重置消息历史并添加新的系统消息
        self.message_history = ChatMessageHistory()
        self.message_history.add_message(SystemMessage(content=new_system_prompt))

        # 重新设置对话链
        self.setup_conversation_chain()

    def add_message(self, role: str, content: str):
        """
        添加消息到对话历史

        Args:
            role: 消息角色，'human'或'ai'
            content: 消息内容
        """
        if role.lower() == "human":
            self.message_history.add_message(HumanMessage(content=content))
        elif role.lower() == "ai":
            self.message_history.add_message(AIMessage(content=content))
        elif role.lower() == "system":
            self.message_history.add_message(SystemMessage(content=content))

    async def send_message(self, message: str) -> str:
        """
        发送消息并获取AI响应

        Args:
            message: 用户消息

        Returns:
            str: AI的响应
        """
        try:
            response = await self.conversation_chain.ainvoke(
                {"input": message},
                {"configurable": {"session_id": self.conversation_id}},
            )
            return response.content
        except Exception as e:
            print(f"Error in conversation: {e}")
            return f"抱歉，处理您的请求时出现错误: {str(e)}"

    def get_history(self) -> List[Dict[str, Any]]:
        """
        获取当前的对话历史

        Returns:
            List[Dict[str, Any]]: 对话历史列表
        """
        history = []
        for message in self.message_history.messages:
            if isinstance(message, HumanMessage):
                history.append({"role": "human", "content": message.content})
            elif isinstance(message, AIMessage):
                history.append({"role": "ai", "content": message.content})
            elif isinstance(message, SystemMessage):
                history.append({"role": "system", "content": message.content})
        return history

    def clear_history(self):
        """清空对话历史，只保留系统提示"""
        self.message_history = ChatMessageHistory()
        self.message_history.add_message(SystemMessage(content=self.system_prompt))
