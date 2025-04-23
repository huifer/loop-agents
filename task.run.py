import os
import json
import logging
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from langchain.prompts import PromptTemplate
from pydantic import BaseModel, Field

from GenRoleSys import RoleGenerator
from task_exect import execute_tasks
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


def run(task: str) -> tuple[List[Dict[str, Any]], float]:
    """
    运行函数，执行任务。

    Args:
        task: 要执行的任务

    Returns:
        Tuple containing:
        - List of task items
        - Execution time in minutes
    """
    start_time = time.time()

    # 获取 prompt_map
    prompt_map = load_prompt()
    # 使用 TaskSplitter 类处理任务，传入 prompt_map
    task_splitter = TaskSplitter(prompt_map)
    tasks = task_splitter.split_task(task)

    logger.info(f"Task split into {len(tasks)} items.")
    logger.info(f"Tasks: {tasks}")
    result = execute_tasks(tasks=tasks, prompt_map=prompt_map)

    end_time = time.time()
    execution_time_minutes = (end_time - start_time) / 60

    return result, execution_time_minutes


if __name__ == "__main__":
    task_list, execution_time = run("做一个数据分析报告")

    # Create output directory if it doesn't exist
    output_dir = "output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Create timestamped filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"task_result_{timestamp}.json")

    # Write results to JSON file
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(task_list, f, ensure_ascii=False, indent=2)

    logger.info(f"Results saved to: {output_file}")
    logger.info(f"Task execution completed in {execution_time:.2f} minutes")
