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

SYS_PROMPT = """# Role
You are an AI assistant specialized in information analysis, integration, and synthesis.

# Context
You will receive the following information:
1.  **Main Task:** The primary objective to be achieved.
2.  **Prerequisite Task Result:** Information or results from tasks completed *before* the main task, providing necessary background or context.
3.  **Sub-task Execution Results:** A collection of results from individual steps taken to fulfill the main task.

# Core Objective
Your goal is to:
1.  **Thoroughly Understand** the requirements of the **Main Task**.
2.  **Analyze** all provided information – the **Prerequisite Task Result** and all **Sub-task Execution Results** – evaluating their relevance, accuracy, and contribution to the Main Task.
3.  **Integrate** key findings and essential data points from *all* these sources.
4.  **Synthesize** this integrated information into a **single, coherent, and comprehensive** final output that **directly addresses and fulfills** the original **Main Task**.

# Processing Guidelines (Internal Thought Process)
*   **Clarify Goal:** What is the core requirement of the Main Task? What is the expected final deliverable?
*   **Analyze Inputs:** What crucial background does the Prerequisite Task Result provide? What specific information does each Sub-task Result contribute? How do these pieces relate (e.g., sequence, cause-effect, supporting details)? Are there overlaps, gaps, or inconsistencies?
*   **Plan Synthesis:** How should the final output be structured for clarity and logical flow? What are the key points to highlight? How can overlapping information be merged effectively?
*   **Generate Output:** Draft the final synthesized text. Focus on clear articulation, summarization, and refinement. **Do not simply copy and paste** raw results; restructure and rephrase as needed for a unified narrative.

# Input Format
You will receive information structured as follows:

```text
# Main Task
[Insert the clear and specific main task description here]

## Prerequisite Task Result
[Insert the result or information from the prerequisite task here]

## Sub-task Execution Results
[Insert the collected results from the executed sub-tasks here. This might be a list, paragraphs, or structured data.]"""

# 模板
PROMPT_TEMPLATE = """
# Main Task
[maintask]
## Prerequisite Task Result
[subtask]
## Sub-task Execution Results
[result]
"""


class TaskReducer:
    """Processes tasks and generates results using LLM"""

    def __init__(
        self,
        task_description: str,
        dependency_results: str = "",
        subtask_results: str = "",
    ):
        # 当前任务描述
        self.task_description = task_description
        # 当前任务依赖任务的任务执行结果
        self.dependency_results = dependency_results
        # 当前任务的子任务执行结果
        self.subtask_results = subtask_results

    def process_task(
        self,
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
        template = (PROMPT_TEMPLATE
                    .replace("[maintask]",self.task_description)
                    .replace("[result]",self.dependency_results)
                    .replace("[subtask]",self.subtask_results))

        # If using template 2, no need for PREVIOUS_TASK_RESULTS parameter
        chat_prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=SYS_PROMPT),
                HumanMessage(content=template),
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
    # Initialize the task processor with task description
    task_processor = TaskReducer(
        task_description="Create an action plan to improve customer response time",
        dependency_results="The analysis of the customer satisfaction survey shows that 75% of customers are satisfied with our service, but 25% reported issues with response time.",
    )

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
