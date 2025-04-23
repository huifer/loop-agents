from typing import List, Dict, Any, Optional

from langchain_core.messages import SystemMessage
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


class TaskDefinition(BaseModel):
    """
    定义分解后的细分任务结构

    这个类用于表示从高级任务分解出来的子任务，每个子任务会分配给特定角色执行。
    任务之间可以存在依赖关系，通过dependsOn字段表示。
    """

    id: str = Field(description="子任务的唯一标识符")
    description: str = Field(description="子任务的详细描述")
    role_name: str = Field(description="负责执行该子任务的角色名称")
    dependsOn: List[str] = Field(
        description="该子任务依赖的其他任务ID列表，表示执行顺序和依赖关系",
        default_factory=list,
    )
    result:Optional[str] = Field( default="",  description="")


class TaskJxGenerator:
    """Generates specific roles based on a high-level task description"""

    def __init__(self, prompt_map: Dict[str, str]):
        self.prompt_map = prompt_map
        self.parser = PydanticOutputParser(pydantic_object=List[TaskDefinition])
        self.output_parser = JsonOutputParser()

    def generator_task(self, task: str, roles: List[str]) -> List[TaskDefinition]:
        """
        Generates specific roles based on a high-level task description.

        Args:
            task: High-level task description.

        Returns:
            A list of structured role definitions.
        """
        llm = get_llm_model()
        system_prompt_str = self.prompt_map.get("task_jx", "")

        chat_prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=system_prompt_str),
                HumanMessagePromptTemplate.from_template("taks: {task}\nrole: {role}"),
            ]
        )

        messages = chat_prompt.format_messages(task=task, role=",".join(roles))

        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                response = llm(messages)
                parsed_json = self.output_parser.invoke(response)
                role_definitions = [
                    TaskDefinition(**role_dict) for role_dict in parsed_json
                ]
                return role_definitions

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
