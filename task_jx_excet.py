import logging
import concurrent.futures
from typing import List, Dict, Any, Optional, Set
import time
import json
from datetime import datetime
from pydantic import BaseModel, Field

from GenRoleSys import RoleDefinition
from llm_task_ex import LLMTaskProcessor
from task_jx import TaskDefinition
from task_result import TaskResultCalculator


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - [%(pathname)s:%(lineno)d] - %(message)s",
)
logger = logging.getLogger(__name__)


class TaskJxExecutor:
    """
    Executes tasks in parallel while respecting their dependencies.
    """

    def __init__(
        self,
        tasks: List[TaskDefinition],
        roles,
        prompt_map,
        max_workers: int = 5,
    ):
        """
        Initialize the task executor.

        Args:
            tasks: List of TaskDefinition objects to execute
            max_workers: Maximum number of worker threads
        """
        self.tasks = {task.id: task for task in tasks}
        self.max_workers = max_workers
        self.results = {}
        self.completed_tasks: Set[str] = set()
        self.failed_tasks: Set[str] = set()
        self.in_progress: Set[str] = set()
        self.roles: List[RoleDefinition] = roles
        self.prompt_map = prompt_map

    def _find_role_by_name(self, role_name: str) -> Optional[RoleDefinition]:
        """
        Find a role in self.roles that matches the specified role name.

        Args:
            role_name: Name of the role to find

        Returns:
            Matching RoleDefinition object if found, None otherwise
        """
        for role in self.roles:
            if role_name in role.role_name or role.role_name in role_name:
                return role
        logger.warning(f"Role '{role_name}' not found")
        return None

    def _are_dependencies_met(self, task_id: str) -> bool:
        """
        Check if all dependencies for a task have been completed.

        Args:
            task_id: ID of the task to check

        Returns:
            True if all dependencies are met, False otherwise
        """
        task = self.tasks.get(task_id)
        if not task:
            logger.warning(f"Task {task_id} not found")
            return False

        for dep_id in task.dependsOn:
            if dep_id not in self.completed_tasks:
                return False

        return True

    def _execute_task(self, task_id: str) -> Dict[str, Any]:
        """
        Execute a single task.

        Args:
            task_id: ID of the task to execute

        Returns:
            Result of the task execution
        """
        task = self.tasks.get(task_id)

        if not task:
            logger.error(f"Task {task_id} not found")
            return {"status": "failed", "error": "Task not found", "task_id": task_id}

        # Find the role responsible for this task
        role = self._find_role_by_name(task.role_name)
        if not role:
            return {
                "task_id": task_id,
                "status": "failed",
                "error": f"Role '{task.role_name}' not found",
                "description": task.description,
                "dependsOn": task.dependsOn,
            }

        try:
            logger.info(
                f"Executing task {task_id}: {task.description} with role {task.role_name}"
            )
            self.in_progress.add(task_id)

            # Gather results from dependent tasks
            dependency_results = {}
            for dep_id in task.dependsOn:
                if dep_id in self.results:
                    dependency_results[dep_id] = {
                        "description": self.results[dep_id]["description"],
                        "result": self.results[dep_id]["result"],
                    }

            # Process the task with its dependencies
            result = self.process_task(task, role, dependency_results)

            self.in_progress.remove(task_id)
            self.completed_tasks.add(task_id)
            logger.info(f"Task {task_id} completed")
            return result

        except Exception as e:
            logger.error(f"Error executing task {task_id}: {str(e)}", exc_info=True)
            self.in_progress.remove(task_id)
            self.failed_tasks.add(task_id)
            return {
                "task_id": task_id,
                "status": "failed",
                "error": str(e),
                "description": task.description,
                "dependsOn": task.dependsOn,
            }

    def handler_dep_result(self, dependency_results: Dict[str, Any]):
        """
        Format dependency results into a markdown string.

        Args:
            dependency_results: Dictionary of dependency results where keys are task IDs
                               and values contain description and result

        Returns:
            Formatted markdown string of dependency results
        """
        if not dependency_results:
            return ""

        md_output = "## Previous Task Results\n\n"

        for task_id, task_data in dependency_results.items():
            description = task_data.get("description", "No description")
            result = task_data.get("result", "No result")

            md_output += f"### Task {task_id}: {description}\n\n"
            md_output += f"{result}\n\n"
            md_output += "---\n\n"

        return md_output

    def process_task(
        self,
        task: TaskDefinition,
        role: RoleDefinition,
        dependency_results: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Process a task with its dependencies.

        Args:
            task: The task to process
            role: The role responsible for the task
            dependency_results: Results from dependent tasks

        Returns:
            Result of the task execution
        """
        time.sleep(1)

        # step1:
        # 需要确认任务的产物的提示词
        task_result_calc = TaskResultCalculator(self.prompt_map)
        task_result_format = task_result_calc.calculate_result(
            task.description, role.role_name
        )
        # step2:
        # 任务执行的系统提示词
        # role.prompt_text
        # user message =
        # task :
        # 最终产物:

        llm_task_proc = LLMTaskProcessor(role.prompt_text)

        result = llm_task_proc.process_task(
            self.handler_dep_result(dependency_results),
            task.description,
            task_result_format,
        )

        # Create result with dependency information
        return {
            "task_id": task.id,
            "status": "completed",
            "description": task.description,
            "role_name": task.role_name,
            "role_sys_prompt": role.prompt_text,
            "dependsOn": task.dependsOn,
            "task_result_format": task_result_format,
            "result": result,
        }

    def execute_all(self) -> List[Dict[str, Any]]:
        """
        Execute all tasks in parallel while respecting their dependencies.

        Returns:
            List of task results
        """
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers
        ) as executor:
            futures = {}

            while len(self.completed_tasks) + len(self.failed_tasks) < len(self.tasks):
                # Find tasks that can be executed (dependencies met and not in progress)
                for task_id, task in self.tasks.items():
                    if (
                        task_id not in self.completed_tasks
                        and task_id not in self.failed_tasks
                        and task_id not in self.in_progress
                        and self._are_dependencies_met(task_id)
                    ):
                        # Submit task for execution
                        futures[executor.submit(self._execute_task, task_id)] = task_id

                # Wait for at least one task to complete if there are futures
                if futures:
                    done, _ = concurrent.futures.wait(
                        futures.keys(), return_when=concurrent.futures.FIRST_COMPLETED
                    )

                    # Process completed tasks
                    for future in done:
                        task_id = futures.pop(future)
                        try:
                            result = future.result()
                            self.results[task_id] = result
                            # Update the result field of the TaskDefinition object
                            if result["status"] == "completed" and "result" in result:
                                self.tasks[task_id].result = result["result"]
                        except Exception as e:
                            logger.error(
                                f"Task {task_id} failed with exception: {str(e)}"
                            )
                            self.failed_tasks.add(task_id)
                else:
                    # No tasks can be executed right now, wait a bit before checking again
                    time.sleep(0.1)

                    # Check if we're in a deadlock (all remaining tasks have dependencies that can't be met)
                    if not self.in_progress:
                        remaining = (
                            set(self.tasks.keys())
                            - self.completed_tasks
                            - self.failed_tasks
                        )
                        if remaining:
                            logger.warning(
                                f"Possible deadlock detected. Remaining tasks: {remaining}"
                            )
                            break

        # Return results as a list
        return list(self.results.values())

    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of task execution.

        Returns:
            Dictionary containing task execution status
        """
        return {
            "total": len(self.tasks),
            "completed": len(self.completed_tasks),
            "failed": len(self.failed_tasks),
            "in_progress": len(self.in_progress),
            "pending": len(self.tasks)
            - len(self.completed_tasks)
            - len(self.failed_tasks)
            - len(self.in_progress),
        }


def execute_tasks_jx(
    tasks: List[TaskDefinition],
    roles,
    prompt_map,
    max_workers: int = 5,
) -> List[Dict[str, Any]]:
    """
    Convenience function to execute a list of tasks.

    Args:
        tasks: List of TaskDefinition objects
        max_workers: Maximum number of concurrent workers

    Returns:
        List of task results
    """
    executor = TaskJxExecutor(
        tasks=tasks, roles=roles, max_workers=max_workers, prompt_map=prompt_map
    )
    return executor.execute_all()
