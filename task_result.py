from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain.output_parsers import PydanticOutputParser
from tools.llm_generatory import get_llm_model
import logging
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain_core.output_parsers import JsonOutputParser


class TaskResultCalculator:
    """Calculates the execution result of a task using LLM"""

    def __init__(self, prompt_map: Dict[str, str]):
        self.prompt_map = prompt_map

    def calculate_result(self, task: str,role:str) -> str:
        """
        Calculates the execution result for a given task using LLM.

        Args:
            task: Task to calculate result for.

        Returns:
            A string representing the task execution result.
        """
        llm = get_llm_model()
        system_prompt_str = self.prompt_map.get("task_result", "")

        chat_prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessagePromptTemplate.from_template(system_prompt_str),
                HumanMessagePromptTemplate.from_template("task: {task} \nrole={role}"),
            ]
        )

        messages = chat_prompt.format_messages(task=task,role=role)

        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                response = llm(messages)
                return response.content
            except Exception as e:
                retry_count += 1
                if retry_count < max_retries:
                    logging.warning(f"Attempt {retry_count} failed: {e}. Retrying...")
                else:
                    logging.error(
                        f"Failed to parse LLM response after {max_retries} attempts: {e}"
                    )
                    if "response" in locals():
                        logging.error(
                            f"Raw Response: {getattr(response, 'content', str(response))}"
                        )
                    return ""
