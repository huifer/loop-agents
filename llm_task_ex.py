from typing import Optional
from pydantic import BaseModel, Field
from langchain.output_parsers import PydanticOutputParser
from tools.llm_generatory import get_llm_model
import logging
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_community.callbacks import get_openai_callback
from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)

# 模板
PROMPT_TEMPLATE_1 = """**CONTEXT FROM PREVIOUS TASKS:**
{PREVIOUS_TASK_RESULTS}
---
**CURRENT TASK:**
{TASK}
---
**REQUIRED OUTPUT FORMAT & CONTENT:**
{FINAL_PRODUCT_DESCRIPTION}
---
**INSTRUCTION:**
Based *only* on the information provided above ('CONTEXT FROM PREVIOUS TASKS' and 'CURRENT TASK'), generate the final output. Your response must *strictly and exclusively* match the description under 'REQUIRED OUTPUT FORMAT & CONTENT'. Do not include *any* other text, headings, explanations, greetings, or apologies before or after the required output. Your entire response should be *only* the final product itself.
"""

PROMPT_TEMPLATE_2 = """**CURRENT TASK:**
{TASK}
---
**REQUIRED OUTPUT FORMAT & CONTENT:**
{FINAL_PRODUCT_DESCRIPTION}
---
**INSTRUCTION:**
Based *only* on the 'CURRENT TASK', generate the final output. Your response must *strictly and exclusively* match the description under 'REQUIRED OUTPUT FORMAT & CONTENT'. Do not include *any* other text, headings, explanations, greetings, or apologies before or after the required output. Your entire response should be *only* the final product itself."""


class LLMTaskProcessor:
    """Processes tasks and generates results using LLM"""

    def __init__(self, sys_prompt: str):
        self.sys_prompt = sys_prompt

    def process_task(
        self, PREVIOUS_TASK_RESULTS: str, TASK: str, FINAL_PRODUCT_DESCRIPTION: str
    ) -> str:
        """
        Processes the given task and generates a result using LLM.

        Args:
            PREVIOUS_TASK_RESULTS (str): Context from previous tasks.
            TASK (str): Current task to perform.
            FINAL_PRODUCT_DESCRIPTION (str): Description of desired output.

        Returns:
            str: Generated result or empty string if failed.
        """
        llm = get_llm_model()

        # Select the appropriate template based on if previous task results exist
        template = PROMPT_TEMPLATE_1 if PREVIOUS_TASK_RESULTS else PROMPT_TEMPLATE_2

        # If using template 2, no need for PREVIOUS_TASK_RESULTS parameter
        if template == PROMPT_TEMPLATE_2:
            final_prompt = template.format(
                TASK=TASK,
                FINAL_PRODUCT_DESCRIPTION=FINAL_PRODUCT_DESCRIPTION,
            )
        else:
            final_prompt = template.format(
                PREVIOUS_TASK_RESULTS=PREVIOUS_TASK_RESULTS,
                TASK=TASK,
                FINAL_PRODUCT_DESCRIPTION=FINAL_PRODUCT_DESCRIPTION,
            )

        chat_prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessagePromptTemplate.from_template(self.sys_prompt),
                HumanMessage(content = final_prompt),
            ]
        )

        messages = chat_prompt.format_messages()

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = llm(messages)
                return response.content
            except Exception as e:
                logging.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    logging.error("All retry attempts failed.")
                    logging.error(f"Last exception: {e}")
                    return ""


if __name__ == "__main__":
    # Example system prompt
    system_prompt = (
        "You are a helpful AI assistant that performs tasks based on instructions."
    )

    # Initialize the task processor
    task_processor = LLMTaskProcessor(system_prompt)

    # Example task parameters
    previous_results = """
    The analysis of the customer satisfaction survey shows that 75% of customers are satisfied with our service,
    but 25% reported issues with response time.
    """

    current_task = """
    Based on the customer satisfaction survey results, create a short action plan to improve response time.
    """

    output_description = """
    A bulleted list of 3-5 concrete actions to improve customer response time, with each action being specific and implementable within 30 days.
    """

    # Process the task
    print("Processing task...")
    with get_openai_callback() as cb:
        result = task_processor.process_task(
            previous_results, current_task, output_description
        )
        print(f"Total tokens: {cb.total_tokens}")
        print(f"Total cost: ${cb.total_cost:.6f}")

    # Print the result
    print("\nResult:")
    print(result)
