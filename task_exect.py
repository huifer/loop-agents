import logging
import concurrent.futures
from typing import List, Dict, Any, Optional, Set
import time
import json
from datetime import datetime
from pydantic import BaseModel, Field

from GenRoleSys import RoleGenerator
from task_jx import TaskJxGenerator
from task_jx_excet import execute_tasks_jx
from task_reduce import TaskReducer
from tools.task_splitter import TaskItem

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - [%(pathname)s:%(lineno)d] - %(message)s",
)
logger = logging.getLogger(__name__)


class TaskExecutor:
    """
    Executes tasks in parallel while respecting their dependencies.
    """

    def __init__(self, tasks: List[TaskItem], max_workers: int = 5, prompt_map=None):
        """
        Initialize the task executor.

        Args:
            tasks: List of TaskItem objects to execute
            max_workers: Maximum number of worker threads
        """
        self.tasks = {task.id: task for task in tasks}
        self.max_workers = max_workers
        self.results = {}
        self.completed_tasks: Set[str] = set()
        self.failed_tasks: Set[str] = set()
        self.in_progress: Set[str] = set()
        self.prompt_map = prompt_map

    def _process_task(
            self,
            task_description: str,
            prompt_map=None,
            dependent_results: Dict[str, str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Process a task by generating roles and executing the task.

        Args:
            task_description: Description of the task to execute
            prompt_map: Map of prompts for role generation
            dependent_results: Results of dependent tasks that this task relies on

        Returns:
            Result of the task execution
        """
        # 任务描述
        role_gen = RoleGenerator(prompt_map)
        # 传递规范化的描述
        roles = role_gen.generate_roles(task_description)

        role_names = [role.role_name for role in roles if role.role_name]
        taskJxGenerator = TaskJxGenerator(prompt_map)
        task_items = taskJxGenerator.generator_task(task_description, role_names)

        return execute_tasks_jx(
            tasks=task_items, roles=roles, max_workers=3, prompt_map=prompt_map
        )

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

        try:
            logger.info(f"Executing task {task_id}: {task.description}")
            self.in_progress.add(task_id)

            # Collect results from dependencies
            dependent_results = {}
            for dep_id in task.dependsOn:
                if dep_id in self.results:
                    dependent_results[dep_id] = {
                        "description": self.results[dep_id]["description"],
                        "result": self.results[dep_id]["result"],
                    }

            # Call the class method with dependent results
            task_result = self._process_task(
                task.description, self.prompt_map, dependent_results
            )

            # todo:
            # 当前任务描述
            # 当前任务依赖任务的任务执行结果
            # 当前任务的子任务执行结果

            leaf_task = find_leaf_tasks(task_result)
            leaf_task_format = ""
            for e in leaf_task:
                task_desc = e.get("description", "")
                task_result_item = e.get("result", "")
                leaf_task_format += f"### task: {task_desc} \nresult:\n{task_result_item} \n\n"
            fc = self.handler_dep_result(dependent_results)
            task_reduce = TaskReducer(
                task_description=task.description,
                dependency_results=fc,
                subtask_results=leaf_task_format,
            )

            # Example result - replace with actual execution result
            result = {
                "task_id": task_id,
                "status": "completed",
                "description": task.description,
                "dependsOn": task.dependsOn,  # Include dependency information
                "children": task_result,
                "result": task_reduce.process_task(),
            }

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
                            # Update the result field of the TaskItem object
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


def execute_tasks(
        tasks: List[TaskItem], prompt_map, max_workers: int = 5
) -> List[Dict[str, Any]]:
    """
    Convenience function to execute a list of tasks.

    Args:
        tasks: List of TaskItem objects
        max_workers: Maximum number of concurrent workers

    Returns:
        List of task results
    """
    executor = TaskExecutor(tasks, max_workers, prompt_map)
    return executor.execute_all()


def find_leaf_tasks(task_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Find tasks that don't have any downstream dependencies (leaf nodes in the task graph).

    Args:
        task_results: List of task results from execute_tasks_jx

    Returns:
        List of task results that are leaf nodes (tasks that no other task depends on)
    """
    # Collect all task IDs that are depended upon by other tasks
    depended_upon = set()
    for task in task_results:
        if "dependsOn" in task and task["dependsOn"]:
            for dep_id in task["dependsOn"]:
                depended_upon.add(dep_id)

    # Find tasks that no other task depends on
    leaf_tasks = []
    for task in task_results:
        if task["task_id"] not in depended_upon:
            leaf_tasks.append(task)

    return leaf_tasks


if __name__ == "__main__":
    # Create sample tasks
    sample_tasks = [
        TaskItem(id="task1", description="First task"),
        TaskItem(id="task2", description="Second task", dependsOn=["task1"]),
        TaskItem(id="task3", description="Third task", dependsOn=["task1"]),
        TaskItem(id="task4", description="Fourth task", dependsOn=["task2", "task3"]),
        TaskItem(id="task5", description="Fifth task"),
    ]

    # Execute tasks
    logger.info("Starting task execution...")
    results = execute_tasks(sample_tasks, prompt_map=None)

    # Display results
    logger.info(f"Execution completed with {len(results)} results")
    for result in results:
        status = result.get("status", "unknown")
        task_id = result.get("task_id", "unknown")
        description = result.get("description", "")

        if status == "completed":
            logger.info(f"Task {task_id}: {description} - Completed")
        else:
            error = result.get("error", "Unknown error")
            logger.error(f"Task {task_id}: {description} - Failed: {error}")

    # Write results to JSON file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"task_results_{timestamp}.json"
    logger.info(f"Writing results to {output_filename}")

    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    logger.info(f"Results successfully written to {output_filename}")
