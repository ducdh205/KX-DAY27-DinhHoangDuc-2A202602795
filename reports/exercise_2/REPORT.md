# Exercise 2 — Dừng chờ người duyệt bằng `interrupt()`

Đã hoàn thiện cơ chế HITL (Human-in-the-loop) với `interrupt()`, `Command(resume=...)` và `MemorySaver` trên [exercises/exercise_2_hitl.py](../../exercises/exercise_2_hitl.py). Đã kiểm chứng đầy đủ cả hai kịch bản `reject` và `approve` trên PR #1 thật (<https://github.com/VinUni-AI20k/PR-Demo/pull/1>) vào ngày 15/10/2026.

---

## 1. Triển khai kỹ thuật

1. **`node_human_approval`**:
   - Gọi `interrupt(payload)` với các trường theo đúng contract mà `prompt_human()` yêu cầu:
     - `kind`: `"approval_request"`
     - `confidence`: `a.confidence`
     - `confidence_reasoning`: `a.confidence_reasoning`
     - `summary`: `a.summary`
     - `comments`: `[c.model_dump() for c in a.comments]`
     - `diff_preview`: `state["pr_diff"][:2000]`
   - Giá trị trả về từ `interrupt()` nhận từ `Command(resume=...)`, sau đó trích xuất:
     ```python
     return {"human_choice": response["choice"], "human_feedback": response.get("feedback")}
     ```
   - Tách biệt hoàn toàn side-effect (không gọi `post_review_comment` ở node này) để tránh việc node bị gọi lại từ đầu khi resume làm trùng lặp side-effect.

2. **`build_graph`**:
   - Compile StateGraph với checkpointer:
     ```python
     return g.compile(checkpointer=MemorySaver())
     ```

3. **`main`**:
   - Khởi tạo `thread_id = str(uuid.uuid4())` và `cfg = {"configurable": {"thread_id": thread_id}}`.
   - Vòng lặp resume xử lý mọi lần interrupt:
     ```python
     while "__interrupt__" in result:
         payload = result["__interrupt__"][0].value
         answer = prompt_human(payload)
         result = app.invoke(Command(resume=answer), cfg)
     ```

---

## 2. Kết quả kiểm chứng chạy thật trên PR #1

### Kịch bản 1: Người duyệt chọn `reject`

- **Lệnh thực thi**:
  ```bash
  uv run python exercises/exercise_2_hitl.py --pr https://github.com/VinUni-AI20k/PR-Demo/pull/1
  ```
- **Thread ID**: `84a3bbde-ee8a-417f-89ac-64a05dfee29f`
- **Tương tác**:
  - Graph dừng tại `node_human_approval`, hiển thị panel màu xanh `Approval request`.
  - Confidence: `65%`
  - Nhập `Choice (approve/reject/edit)?`: `reject`
  - Nhập `Feedback:`: `Need more unit tests`
- **Output ghi nhận**:
  ```text
  ────────────────────── Exercise 2 — HITL with interrupt() ──────────────────────
  PR: https://github.com/VinUni-AI20k/PR-Demo/pull/1

  thread_id = 84a3bbde-ee8a-417f-89ac-64a05dfee29f

  → fetch_pr
    ✓ 3 files, head 1646156
  → analyze
    ✓ confidence=65%, 4 comment(s)
  → route
    ✓ decision=human_approval (confidence=65%)
  ╭────────────────────────────── Approval request ──────────────────────────────╮
  │ Confidence: 65%                                                              │
  │ The review identifies several important aspects of the changes, including    │
  │ the need for validation of the priority input and the implications of        │
  │ changing the database schema. However, there is insufficient evidence        │
  │ regarding how existing data will be migrated and whether the priority        │
  │ handling is consistent throughout the application. This leads to moderate    │
  │ confidence in the review completeness.                                       │
  │                                                                              │
  │ Summary: This PR adds a priority field to tasks in a task tracking           │
  │ application, allowing users to specify the priority level (normal, high,     │
  │ urgent) when adding tasks. It modifies the command-line interface to accept  │
  │ a priority argument, updates the task model to include the priority          │
  │ attribute, and alters the storage layer to handle priority in the database   │
  │ schema and task management methods.                                          │
  ╰──────────────────────────────────────────────────────────────────────────────╯
     tasktrack/cli.py:8 — Consider adding validation for the priority argument...
     tasktrack/models.py:7 — Add a docstring to the Task class...
     tasktrack/storage.py:10 — Ensure that the priority column is properly indexed...
     tasktrack/storage.py:21 — The database schema change requires a migration strategy...

  Choice (approve/reject/edit)? reject
  Feedback: Need more unit tests
  → commit
    · skipping comment (choice=reject)
  ───────────────────────────────────── Done ─────────────────────────────────────
  rejected
  ```
- **Kết luận**: Khi reject, `node_commit` bỏ qua việc đăng comment lên GitHub và kết thúc với `final_action = rejected`. Không có comment nào được đăng lên PR.

---

### Kịch bản 2: Người duyệt chọn `approve`

- **Lệnh thực thi**:
  ```bash
  uv run python exercises/exercise_2_hitl.py --pr https://github.com/VinUni-AI20k/PR-Demo/pull/1
  ```
- **Thread ID**: `be39de57-9a0e-43ff-8e80-3de95cfcdbd6`
- **Tương tác**:
  - Graph dừng tại `node_human_approval`, hiển thị panel màu xanh `Approval request`.
  - Confidence: `65%`
  - Nhập `Choice (approve/reject/edit)?`: `approve`
- **Output ghi nhận**:
  ```text
  ────────────────────── Exercise 2 — HITL with interrupt() ──────────────────────
  PR: https://github.com/VinUni-AI20k/PR-Demo/pull/1

  thread_id = be39de57-9a0e-43ff-8e80-3de95cfcdbd6

  → fetch_pr
    ✓ 3 files, head 1646156
  → analyze
    ✓ confidence=65%, 5 comment(s)
  → route
    ✓ decision=human_approval (confidence=65%)
  ╭────────────────────────────── Approval request ──────────────────────────────╮
  │ Confidence: 65%                                                              │
  │ The review identifies several critical areas where validation and migration  │
  │ handling are necessary, but the overall changes are localized to the task    │
  │ management functionality. There is a moderate level of confidence due to the │
  │ lack of tests and potential data integrity issues that could arise from the  │
  │ schema change.                                                               │
  │                                                                              │
  │ Summary: This PR introduces a new priority field to tasks in a task tracking │
  │ application. It modifies the command-line interface to accept a priority     │
  │ argument when adding tasks, updates the Task model to include the priority   │
  │ attribute, and alters the storage layer to accommodate the new field in the  │
  │ database schema and related operations.                                      │
  ╰──────────────────────────────────────────────────────────────────────────────╯
  Choice (approve/reject/edit)? approve
  → commit
    ✓ posted comment to https://github.com/VinUni-AI20k/PR-Demo/pull/1
  ───────────────────────────────────── Done ─────────────────────────────────────
  committed
  ```
- **Xác minh trực tiếp trên GitHub API**:
  - **Author**: `ducdh205`
  - **Thời điểm**: `2026-10-15T08:01:12Z`
  - **Nội dung comment**:
    ```markdown
    ### Automated review (confidence 65%)

    This PR introduces a new 'priority' field to tasks in the task tracking application, allowing users to specify task urgency levels (normal, high, urgent) when adding tasks. It updates the command-line interface to accept a priority argument, modifies the Task model to include the priority attribute, and alters the storage layer to handle the new priority field in the database schema and operations.

    - **[issue]** `tasktrack/cli.py:8` — The priority argument is not validated. Consider adding validation to ensure it only accepts values 0, 1, or 2.
    - **[issue]** `tasktrack/storage.py:12` — The database schema is modified to include a priority field, but there is no migration strategy for existing databases. Ensure that existing users can upgrade without data loss.
    - **[suggestion]** `tasktrack/storage.py:21` — Consider using an Enum for priority values instead of raw integers to improve code readability and maintainability.
    ```
- **Kết luận**: Đạt toàn bộ tiêu chí Checkpoint của Exercise 2.
