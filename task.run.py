import os
import json
import logging
from typing import List, Dict, Any, Optional
from langchain.prompts import PromptTemplate
from pydantic import BaseModel, Field

from GenRoleSys import RoleGenerator
from task_jx import TaskJxGenerator
from tools.llm_generatory import get_llm_model
from tools.task_splitter import TaskSplitter, TaskItem

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def read_files_to_map(file_mapping):
    """
    Read the content of multiple files into a dictionary
    with custom keys and content as values

    Args:
        file_mapping: Dictionary where keys are custom names and values are file paths
    """
    prompt_map = {}

    for key_name, file_path in file_mapping.items():
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()
                prompt_map[key_name] = content
                logger.info(f"Successfully read: {file_path} as '{key_name}'")
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")

    return prompt_map


def log_prompt_map(prompt_map):
    """
    记录提示词映射内容以供验证。

    Args:
        prompt_map: 包含提示词键值对的字典
    """
    logger.info("Prompt Map Contents:")
    for key in prompt_map:
        logger.info(f"{key}: {len(prompt_map[key])} characters")
        # 记录内容预览
        logger.info(f"{prompt_map[key][:50]}...")


def load_prompt():
    """
    执行脚本的主函数。
    """
    # 带自定义键名的要读取的文件
    files_mapping = {
        "role_system": "prompt/gen_role_sys.md",
        "task_jx": "prompt/task_jx.md",
        "task_result": "prompt/task_result.md",
        "task_split": "prompt/task_split.md",
    }

    # 读取文件内容并使用自定义键存储在映射中
    prompt_map = read_files_to_map(files_mapping)

    # 记录映射以进行验证
    log_prompt_map(prompt_map)

    return prompt_map


def run(task: str) -> List[Dict[str, Any]]:
    """
    运行函数，执行任务。

    Args:
        task: 要执行的任务

    Returns:
        List of task items
    """
    # 获取 prompt_map
    prompt_map = load_prompt()
    # 使用 TaskSplitter 类处理任务，传入 prompt_map
    task_splitter = TaskSplitter(prompt_map)
    tasks = task_splitter.split_task(task)

    result_tasks = []
    # 循环 tasks
    for task_item in tasks:
        try:
            # 确保我们有一个有效的描述
            description = task_item.description
            if description:
                # 任务描述
                role_gen = RoleGenerator(prompt_map)
                # 传递规范化的描述
                roles = role_gen.generate_roles(description)

                role_names = [role.role_name for role in roles if role.role_name]
                taskJxGenerator = TaskJxGenerator(prompt_map)
                task_items = taskJxGenerator.generator_task(description, role_names)
            else:
                logger.warning(f"Task item missing description: {task_item}")
        except Exception as e:
            logger.error(f"Error processing task item: {e}", exc_info=True)

    return result_tasks if result_tasks else tasks


if __name__ == "__main__":
    task_list = run("做一个数据分析报告")
    logger.info(task_list)
