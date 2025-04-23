from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain.output_parsers import PydanticOutputParser
from tools.llm_generatory import get_llm_model
import logging
from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain_core.output_parsers import JsonOutputParser



class TaskItem(BaseModel):
    """Task item schema for parsing LLM output"""

    id: str = Field(description="Unique identifier for the task")
    description: str = Field(description="Description of the task to be completed")
    dependsOn: List[str] = Field(
        default_factory=list, description="Dependencies (task IDs)"
    )
    result: Optional[str] = Field(
        default="", description="Result of the task execution"
    )


class TaskSplitter:
    """Splits a high-level task into detailed subtasks using LLM"""

    def __init__(self, prompt_map: Dict[str, str]):
        self.prompt_map = prompt_map
        self.output_parser = JsonOutputParser()

    def split_task(self, task: str) -> List[TaskItem]:
        """
        Splits a high-level task into structured subtasks using LLM.

        Args:
            task: High-level task description.

        Returns:
            A list of structured task dictionaries.
        """
        llm = get_llm_model()
        system_prompt_str = self.prompt_map.get("task_split", "")

        chat_prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessagePromptTemplate.from_template(system_prompt_str),
                HumanMessagePromptTemplate.from_template("{task}"),
            ]
        )

        messages = chat_prompt.format_messages(task=task)

        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                response = llm(messages)
                parsed = self.output_parser.invoke(response)
                task_items = [TaskItem(**item) for item in parsed]
                return task_items
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
                    return []
