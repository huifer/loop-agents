import os
import subprocess
import json
from datetime import datetime
import threading
import queue
import time

# 示例任务清单，任务依赖关系更复杂
task_list = [
    {"id": "1", "description": "安装所需依赖库，如 requests 和 beautifulsoup4", "dependsOn": []},
    {"id": "2", "description": "模拟浏览器请求，获取用户主页HTML", "dependsOn": ["1"]},
    {"id": "3", "description": "从HTML中提取笔记标题、发布时间和点赞数", "dependsOn": ["2"]},
    {"id": "4", "description": "清洗数据，去掉无效数据行", "dependsOn": ["3", "2"]},
    {"id": "5", "description": "存储清洗后的数据到数据库", "dependsOn": ["4"]},
    {"id": "6", "description": "生成任务执行报告，包含成功与失败的详细信息", "dependsOn": ["5", "4"]}
]

# 任务执行结果存储路径
result_storage_path = "task_results.json"

# 检查所有依赖任务是否完成
def all_dependencies_finished(dependencies, completed_tasks):
    return all(dep in completed_tasks for dep in dependencies)

# 执行任务并记录结果
def execute_task(task, all_results):
    task_result = {
        "id": task["id"],
        "description": task["description"],
        "status": "failed",  # 默认任务失败
        "output": None,
        "timestamp": datetime.now().isoformat(),
        "dependencyResults": {}  # 添加依赖任务结果字段
    }
    
    # 获取依赖任务的执行结果
    for dep_id in task["dependsOn"]:
        for result in all_results:
            if result["id"] == dep_id:
                task_result["dependencyResults"][dep_id] = {
                    "status": result["status"],
                    "output": result["output"]
                }
                break

    try:
        # 模拟执行任务，这里可以执行实际命令，例如 subprocess.run()
        print(f"执行任务: {task['id']} - {task['description']}")
        
        # 假设任务执行成功并返回结果
        task_result["status"] = "success"
        task_result["output"] = f"任务 {task['id']} 执行成功"
        
    except Exception as e:
        task_result["status"] = "failed"
        task_result["output"] = str(e)

    return task_result

# 一次性保存所有任务结果
def save_all_task_results(all_results):
    with open(result_storage_path, "w", encoding="utf-8") as file:
        json.dump(all_results, file, indent=4, ensure_ascii=False)

# 线程安全的数据结构
completed_tasks_lock = threading.Lock()
all_results_lock = threading.Lock()

# 工作线程函数
def worker(task_queue, completed_tasks, all_task_results):
    while True:
        try:
            task = task_queue.get(block=False)
            
            print(f"线程 {threading.current_thread().name} 正在执行任务: {task['id']}")
            result = execute_task(task, all_task_results)
            
            # 安全地更新共享数据
            with all_results_lock:
                all_task_results.append(result)
            
            with completed_tasks_lock:
                completed_tasks.append(task["id"])
            
            print(f"任务 {task['id']} 完成")
            
            # 检查是否有新任务可以执行
            check_new_tasks(task_list, task_queue, completed_tasks)
            
            task_queue.task_done()
        except queue.Empty:
            time.sleep(0.1)  # 避免CPU过度使用
            if task_queue.empty() and all(task["id"] in completed_tasks for task in task_list):
                break

# 检查并添加可执行的新任务到队列
def check_new_tasks(tasks, task_queue, completed_tasks):
    with completed_tasks_lock:
        curr_completed = completed_tasks.copy()
    
    for task in tasks:
        if task["id"] not in curr_completed and all_dependencies_finished(task["dependsOn"], curr_completed):
            try:
                task_queue.put(task, block=False)
            except queue.Full:
                pass

# 多线程任务执行
def execute_tasks_parallel(tasks, num_threads=4):
    task_queue = queue.Queue()
    completed_tasks = []
    all_task_results = []
    
    # 首先添加没有依赖的任务
    for task in tasks:
        if not task["dependsOn"]:
            task_queue.put(task)
    
    # 创建并启动工作线程
    threads = []
    for i in range(num_threads):
        t = threading.Thread(
            target=worker, 
            args=(task_queue, completed_tasks, all_task_results),
            name=f"Worker-{i+1}"
        )
        t.daemon = True
        threads.append(t)
        t.start()
    
    # 等待所有线程完成
    for t in threads:
        t.join()
    
    return all_task_results

def main(task_list_file=None, num_threads=4, output_file=None):
    """
    主函数：控制整个任务执行流程
    
    参数:
        task_list_file: 任务列表JSON文件路径（可选）
        num_threads: 并行执行的线程数
        output_file: 结果输出文件路径（可选）
    """
    global task_list, result_storage_path
    
    # 加载自定义任务列表（如有）
    if task_list_file and os.path.exists(task_list_file):
        try:
            with open(task_list_file, "r", encoding="utf-8") as f:
                task_list = json.load(f)
            print(f"从 {task_list_file} 加载了 {len(task_list)} 个任务")
        except Exception as e:
            print(f"加载任务列表失败: {str(e)}")
            return 1
    
    # 设置输出文件路径（如有）
    if output_file:
        result_storage_path = output_file
    
    print(f"开始执行任务，使用 {num_threads} 个线程...")
    start_time = time.time()
    
    try:
        # 启动多线程执行
        all_task_results = execute_tasks_parallel(task_list, num_threads=num_threads)
        
        # 保存结果
        save_all_task_results(all_task_results)
        
        # 计算统计信息
        succeeded = sum(1 for r in all_task_results if r["status"] == "success")
        failed = len(all_task_results) - succeeded
        
        # 输出执行摘要
        elapsed_time = time.time() - start_time
        print(f"\n执行摘要:")
        print(f"总任务数: {len(all_task_results)}")
        print(f"成功: {succeeded}, 失败: {failed}")
        print(f"总执行时间: {elapsed_time:.2f}秒")
        print(f"结果已保存到: {result_storage_path}")
        
        return 0 if failed == 0 else 1
        
    except Exception as e:
        print(f"执行过程中发生错误: {str(e)}")
        return 1

if __name__ == "__main__":
    import argparse
    
    # 命令行参数解析
    parser = argparse.ArgumentParser(description='并行执行任务工具')
    parser.add_argument('-t', '--threads', type=int, default=4,
                        help='并行线程数 (默认: 4)')
    parser.add_argument('-i', '--input', type=str,
                        help='任务列表JSON文件路径')
    parser.add_argument('-o', '--output', type=str,
                        help='结果输出文件路径')
    
    args = parser.parse_args()
    
    # 执行主函数
    exit_code = main(
        task_list_file=args.input,
        num_threads=args.threads,
        output_file=args.output
    )
    
    # 设置退出码
    exit(exit_code)
