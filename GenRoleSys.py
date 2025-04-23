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


class RoleDefinition(BaseModel):
    role_name: str = Field(description="Name of the role to be generated")
    prompt_text: str = Field(description="Prompt text for instructing the role")


class RoleGenerator:
    """Generates specific roles based on a high-level task description"""

    def __init__(self, prompt_map: Dict[str, str]):
        self.prompt_map = prompt_map
        self.parser = PydanticOutputParser(pydantic_object=List[RoleDefinition])
        self.output_parser = JsonOutputParser()

    def generate_roles(self, task: str) -> List[RoleDefinition]:
        """
        Generates specific roles based on a high-level task description.

        Args:
            task: High-level task description.

        Returns:
            A list of structured role definitions.
        """
        llm = get_llm_model()
        system_prompt_str = self.prompt_map.get("role_system", "")

        chat_prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=system_prompt_str),
                HumanMessagePromptTemplate.from_template("{task}"),
            ]
        )

        messages = chat_prompt.format_messages(task=task)

        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                response = llm(messages)
                parsed_json = self.output_parser.invoke(response)
                role_definitions = [RoleDefinition(**role_dict) for role_dict in parsed_json]
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
