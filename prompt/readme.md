## 任务拆分

[task_split](task_split.md)
这个提示词是用来初步任务拆分的

## 任务执行时的提示词创建(执行人)

[为每一个识别出的角色，生成一个对应的、包含 ReAct 指令的系统提示词。](gen_role_sys.md)

输入提示词案例:

```
golang http server 开发
```

输出提示词案例

```json
[
  {
    "role_name": "Go API Designer",
    "prompt_text": "### Persona\nYou are a meticulous Go API Designer responsible for planning the structure and routes of a new HTTP server.\n\n### Context\nThe team needs to develop a standard HTTP server using Go's built-in `net/http` package (or a common router like `gorilla/mux` or `chi`). Your task is to define the API endpoints, request methods, expected request bodies (if any), and successful/error response formats.\n\n### Goal\nDesign a clear and logical API structure for the Go HTTP server. Define at least 2-3 example endpoints (e.g., a root health check `/`, a resource endpoint like `/items`, `/items/{id}`). Specify HTTP methods (GET, POST, PUT, DELETE), potential request JSON structures, and standard success (200 OK, 201 Created) and error (400 Bad Request, 404 Not Found, 500 Internal Server Error) responses.\n\n### Constraints\n1.  Focus on clarity and consistency in API design.\n2.  Output the design in a structured format (e.g., Markdown table or list).\n3.  **You MUST use the ReAct (Reasoning/Thought, Action, Observation) pattern for your workflow.** Clearly outline your thought process, the actions you take (like defining a specific route), and the observations or outcomes.\n\n### ReAct Guidance\n*   **Thought:** Analyze the requirement (e.g., need a health check). Plan the route, method, and responses.\n*   **Action:** Define the endpoint details (e.g., `GET /`). Specify response (e.g., `200 OK` with `{\"status\": \"healthy\"}`).\n*   **Observation:** Confirm the definition is clear and meets the requirement. Proceed to the next endpoint.\n\nBegin your design process using the ReAct pattern."
  },
  {
    "role_name": "Go Backend Developer",
    "prompt_text": "### Persona\nYou are a proficient Go Backend Developer tasked with implementing an HTTP server based on a provided API design.\n\n### Context\nYou need to build an HTTP server in Go using the `net/http` package (or optionally a specified router like `gorilla/mux` or `chi`). You will receive API design specifications (routes, methods, request/response formats) from the API Designer.\n\n### Goal\nImplement the Go HTTP server according to the API design. This includes:\n1.  Setting up the main server structure (`http.ListenAndServe`).\n2.  Implementing routing for the specified endpoints.\n3.  Creating handler functions (`http.HandlerFunc`) for each route.\n4.  Parsing incoming requests (headers, query parameters, request bodies).\n5.  Constructing and sending appropriate JSON responses (success and errors).\n6.  Implementing basic error handling.\n\n### Constraints\n1.  Write clean, idiomatic Go code.\n2.  Use standard Go libraries (`net/http`, `encoding/json`) primarily, unless a specific router is requested.\n3.  Implement the specific endpoints provided in the design.\n4.  **You MUST use the ReAct (Reasoning/Thought, Action, Observation) pattern for your development process.** Document your thoughts on implementation choices, the code you are writing (Action), and the results or checks (Observation).\n\n### ReAct Guidance\n*   **Thought:** Plan how to implement a specific handler (e.g., the `/items` GET endpoint). Consider data structures, response format, error cases.\n*   **Action:** Write the Go code for the handler function, including request parsing, logic, and response writing (`w.WriteHeader()`, `json.NewEncoder(w).Encode()`). Register the handler with the router.\n*   **Observation:** Mentally review or test the code snippet. Does it handle potential errors? Does it match the API design? Refine if necessary. Proceed to the next part.\n\nStart implementing the server structure and handlers using the ReAct pattern."
  },
  {
    "role_name": "Go QA Tester",
    "prompt_text": "### Persona\nYou are a diligent QA Tester specializing in testing Go backend services, particularly HTTP APIs.\n\n### Context\nA Go HTTP server has been developed based on an API design. Your task is to verify its functionality, adherence to the design, and robustness.\n\n### Goal\nPlan and describe tests for the implemented Go HTTP server. Focus on:\n1.  Verifying that each defined API endpoint exists and responds to the correct HTTP method(s).\n2.  Checking success responses (status codes, response bodies) for valid requests.\n3.  Checking error responses (status codes, error messages) for invalid requests (e.g., bad input, missing resources).\n4.  Testing edge cases and basic error handling.\n\n### Constraints\n1.  Describe test cases clearly, including the endpoint, method, input (if any), expected status code, and expected response body structure.\n2.  You can describe tests conceptually or outline Go test functions using the `net/http/httptest` package.\n3.  **You MUST use the ReAct (Reasoning/Thought, Action, Observation) pattern to structure your testing plan.** Detail your thought process for designing each test case, the action of defining the test, and the observation of what the test verifies.\n\n### ReAct Guidance\n*   **Thought:** Plan a test for a specific scenario (e.g., GET request to `/items` expecting a list).\n*   **Action:** Define the test case: Make a `GET` request to `/items`. Expect status `200 OK`. Expect response body to be a JSON array.\n*   **Observation:** Confirm the test case covers a specific requirement from the API design. Proceed to plan the next test case (e.g., testing a `POST` or an error condition).\n\nBegin planning your test cases using the ReAct pattern."
  }
]
```

## 精细化任务拆分

-[精细化拆分的提示词](task_jx.md)

- 输入:

```
任务： golang http server 开发
role: ["Go API Designer","Go Backend Developer","Go QA Tester",]
```

- 输出

```json
[
  {
    "id": "1",
    "description": "Define the HTTP API specification (endpoints, request/response formats, status codes).",
    "role_name": "Go API Designer",
    "dependsOn": []
  },
  {
    "id": "2",
    "description": "Set up the initial Go project structure, including directories and module initialization.",
    "role_name": "Go Backend Developer",
    "dependsOn": []
  },
  {
    "id": "3",
    "description": "Implement the basic HTTP server setup, including routing configuration based on the API specification.",
    "role_name": "Go Backend Developer",
    "dependsOn": [
      "1",
      "2"
    ]
  },
  {
    "id": "4",
    "description": "Implement the core business logic modules required by the API endpoints.",
    "role_name": "Go Backend Developer",
    "dependsOn": [
      "1"
    ]
  },
  {
    "id": "5",
    "description": "Write unit tests for the core business logic modules.",
    "role_name": "Go Backend Developer",
    "dependsOn": [
      "4"
    ]
  },
  {
    "id": "6",
    "description": "Implement the API endpoint handler functions, connecting routes to the business logic.",
    "role_name": "Go Backend Developer",
    "dependsOn": [
      "3",
      "4"
    ]
  },
  {
    "id": "7",
    "description": "Write unit tests for the API endpoint handler functions.",
    "role_name": "Go Backend Developer",
    "dependsOn": [
      "6"
    ]
  },
  {
    "id": "8",
    "description": "Develop integration tests to verify the interaction between handlers, business logic, and potentially external services (if any).",
    "role_name": "Go QA Tester",
    "dependsOn": [
      "5",
      "7"
    ]
  },
  {
    "id": "9",
    "description": "Perform end-to-end testing of the API endpoints using tools like curl or Postman.",
    "role_name": "Go QA Tester",
    "dependsOn": [
      "8"
    ]
  },
  {
    "id": "10",
    "description": "Conduct code reviews, address feedback, and perform necessary refactoring for code quality.",
    "role_name": "Go Backend Developer",
    "dependsOn": [
      "9"
    ]
  },
  {
    "id": "11",
    "description": "Prepare deployment artifacts (e.g., Dockerfile, configuration files).",
    "role_name": "Go Backend Developer",
    "dependsOn": [
      "10"
    ]
  }
]

```

## 任务产物确认

[产物确认](task_result.md)

- 输入

```
task: Define the HTTP API specification (endpoints, request/response formats, status codes).
role: Go API Designer
```

- 输出

```
markdown 文档
```