# Loop Agent - AI-Driven Task Decomposition and Execution Framework

## Overview

Loop Agent is an AI-powered framework that decomposes complex tasks into smaller, actionable steps and executes them in
a coordinated, parallel manner. It leverages large language models (LLMs) for task decomposition and execution using a
role-based approach with ReAct (Reasoning, Action, Observation) patterns.

## Key Features

1. **Task Decomposition**: Automatically breaks down complex tasks into smaller, sequential steps with clear
   dependencies.
2. **Role-Based Execution**: Assigns specialized AI roles to each task (e.g., Designer, Developer, Tester).
3. **Parallel Task Execution**: Executes tasks concurrently while respecting dependencies.
4. **Visualization**: Provides a web interface to monitor task execution and dependencies.
5. **ReAct Pattern Implementation**: Each AI role follows the Reasoning, Action, Observation pattern for structured
   problem-solving.

## System Architecture

The system consists of several key components:

### 1. Task Decomposition

- **Basic Task Split**: Decomposes a user request into sequential steps with dependencies
- **Role-Based Decomposition**: Enhanced decomposition that also assigns appropriate roles to each task
- Prompt files: `prompt/task_split.md`, `prompt/task_jx.md`

### 2. Role Generation

- Automatically identifies required roles and generates specialized system prompts for each
- Ensures each role follows the ReAct pattern
- Prompt file: `prompt/gen_role_sys.md`

### 3. LLM Integration

- Supports multiple LLM providers (Google Gemini, OpenAI)
- Handles conversation management and context
- Files: `tools/llm_generatory.py`, `tools/common_llm.py`

### 4. Task Execution Engine

- Parallel execution with dependency tracking
- Thread-safe execution of the task dependency graph
- File: `sample.task.py`

### 5. Results Visualization

- Interactive web interface showing task dependencies and execution status
- Detailed task information and dependency graph
- File: `index.html`

## Usage

The framework can be used by:

1. Decomposing a task using the task decomposition prompts
2. Generating appropriate roles for the task
3. Creating a structured task list with dependencies and role assignments
4. Executing the tasks using the parallel execution framework
5. Reviewing results through the visualization interface


