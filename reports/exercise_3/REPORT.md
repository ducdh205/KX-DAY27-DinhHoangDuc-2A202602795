# Exercise 3 — Escalation: Hỏi reviewer câu hỏi cụ thể

Đã hoàn thiện nhánh Escalation và quy trình hỏi–đáp ngữ cảnh trên [exercises/exercise_3_escalation.py](../../exercises/exercise_3_escalation.py). Đã kiểm chứng chạy thật thành công trên PR #2 (<https://github.com/VinUni-AI20k/PR-Demo/pull/2>) vào ngày 15/10/2026.

---

## 1. Triển khai kỹ thuật

1. **`node_analyze`**:
   - Tinh chỉnh system prompt để khi mô hình đánh giá độ đầy đủ trong band low-confidence (`confidence < ESCALATE_THRESHOLD` = 0.58), mô hình bắt buộc phải điền trường `escalation_questions` với 2–4 câu hỏi cụ thể, chỉ rõ file/đoạn mã liên quan (như MD5 trong `auth.py`, SQL injection trong `storage.py`, `SYNC_URL` trong `sync.py`).

2. **`node_escalate`**:
   - Gọi `interrupt(payload)` với `kind="escalation"`.
   - Payload chứa: `pr_url`, `confidence`, `confidence_reasoning`, `summary`, `risk_factors`, và danh sách `questions`.
   - Trả về `{"escalation_answers": answers}` (dict ánh xạ từng câu hỏi sang câu trả lời của reviewer).

3. **`node_synthesize`**:
   - Đọc `state["escalation_answers"]`.
   - Tổng hợp prompt chứa PR title, diff gốc, summary ban đầu và các cặp Q&A.
   - Gọi LLM với structured output `PRAnalysis` để tinh chỉnh và cập nhật lại review:
     ```python
     refined = llm.invoke(...)
     return {"analysis": refined}
     ```

4. **`build_graph`**:
   - Nối luồng hoàn chỉnh:
     ```python
     g.add_edge("escalate", "synthesize")
     g.add_edge("synthesize", "commit")
     g.add_edge("commit", END)
     ```
   - Graph được biên dịch với `MemorySaver` checkpointer.

---

## 2. Kết quả kiểm chứng chạy thật trên PR #2

- **Lệnh thực thi**:
  ```bash
  uv run python exercises/exercise_3_escalation.py --pr https://github.com/VinUni-AI20k/PR-Demo/pull/2
  ```
- **Thread ID**: `fbe70cb6-b0d2-46d7-bf94-8c19db459feb`
- **Tương tác**:
  - LLM ban đầu chấm confidence = 55% (< 58%), rẽ vào nhánh `escalate`.
  - Hiển thị panel viền vàng `Escalation conf=55%`.
  - LLM sinh ra 4 câu hỏi bám sát diff (không dùng 2 câu hỏi fallback):
    1. *What is the rationale for using MD5 for password hashing in `auth.py`?*
       $\rightarrow$ `MD5 was used as a quick prototype, we will migrate to bcrypt before release.`
    2. *Can you provide details on how the token will be secured when saved to the filesystem?*
       $\rightarrow$ `Hard-coded user_id=1 is a temporary stub; production will resolve user_id from session tokens.`
    3. *What measures are in place to prevent SQL injection in the `add` method in `storage.py`?*
       $\rightarrow$ `Input validation and parameterized SQL in Storage.add are planned in the next commit.`
    4. *Is there a plan to implement HTTPS for the sync URL in `sync.py`?*
       $\rightarrow$ `Comprehensive unit tests covering auth, sync and CLI will be added in a follow-up PR.`
  - Graph resume vào `node_synthesize`, nâng confidence từ `55%` lên `75%`.
  - `node_commit` đăng comment tinh chỉnh lên PR #2 kèm phần câu hỏi - câu trả lời.

- **Output terminal ghi nhận**:
  ```text
  ────────────────── Exercise 3 — escalation with reviewer Q&A ───────────────────
  PR: https://github.com/VinUni-AI20k/PR-Demo/pull/2

  thread_id = fbe70cb6-b0d2-46d7-bf94-8c19db459feb

  → fetch_pr
    ✓ 4 files, head 501f95e
  → analyze
    ✓ confidence=55%, 4 question(s)
  → route
    ✓ decision=escalate (confidence=55%)
  ╭──────────────────────────── Escalation conf=55% ─────────────────────────────╮
  │ This PR introduces user login functionality and cloud synchronization for a  │
  │ task tracking application. It includes password hashing, token issuance, and │
  │ the ability to push tasks to a cloud endpoint.                               │
  ╰──────────────────────────────────────────────────────────────────────────────╯
  Q: What is the rationale for using MD5 for password hashing in `auth.py`?
  A: MD5 was used as a quick prototype, we will migrate to bcrypt before release.
  Q: Can you provide details on how the token will be secured when saved to the filesystem?
  A: Hard-coded user_id=1 is a temporary stub; production will resolve user_id from session tokens.
  Q: What measures are in place to prevent SQL injection in the `add` method in `storage.py`?
  A: Input validation and parameterized SQL in Storage.add are planned in the next commit.
  Q: Is there a plan to implement HTTPS for the sync URL in `sync.py`?
  A: Comprehensive unit tests covering auth, sync and CLI will be added in a follow-up PR.
  → synthesize
    ✓ refined confidence=75%, 4 comment(s)
  → commit
    ✓ posted comment to https://github.com/VinUni-AI20k/PR-Demo/pull/2
  ──────────────────────────────────── Final ─────────────────────────────────────
  final_action = committed_after_escalation
  final confidence = 75%
  ```

---

## 3. Xác minh trực tiếp trên GitHub API

- **Tác giả comment**: `ducdh205`
- **Thời điểm**: `2026-10-15T08:06:47Z`
- **Nội dung comment trên PR #2**:
  ```markdown
  ### Automated review (confidence 75%)

  This PR introduces user login functionality and cloud synchronization for a task tracking application. It includes password hashing, token issuance, and the ability to push tasks to a cloud endpoint. The implementation uses MD5 for password hashing as a prototype, with plans to migrate to bcrypt before release. The token is saved to the filesystem, and user_id handling is currently hard-coded but will be improved in future updates. SQL injection prevention measures are planned for the next commit, and HTTPS for the sync URL is also on the roadmap.

  - **[issue]** `tasktrack/auth.py:5` — Consider replacing MD5 with bcrypt for password hashing in the final release to enhance security.
  - **[issue]** `tasktrack/storage.py:12` — Implement parameterized queries to prevent SQL injection in the add method.
  - **[issue]** `tasktrack/sync.py:7` — Plan to implement HTTPS for the sync URL to secure data in transit.
  - **[issue]** `tasktrack/sync.py:25` — The hard-coded user_id=1 should be replaced with a dynamic retrieval from session tokens in a future update.

  _Reviewer answered escalation questions:_
  > **What is the rationale for using MD5 for password hashing in `auth.py`?** MD5 was used as a quick prototype, we will migrate to bcrypt before release.
  > **Can you provide details on how the token will be secured when saved to the filesystem?** Hard-coded user_id=1 is a temporary stub; production will resolve user_id from session tokens.
  > **What measures are in place to prevent SQL injection in the `add` method in `storage.py`?** Input validation and parameterized SQL in Storage.add are planned in the next commit.
  > **Is there a plan to implement HTTPS for the sync URL in `sync.py`?** Comprehensive unit tests covering auth, sync and CLI will be added in a follow-up PR.
  ```

---

## 4. Kết luận Checkpoint
- Mô hình nhận diện chính xác PR nguy cơ cao và hạ confidence xuống dưới 58%.
- Tự động sinh ra 4 câu hỏi đào sâu về rủi ro bảo mật thay vì chỉ hỏi duyệt/từ chối chung chung.
- Graph tạm dừng qua `interrupt()`, thu thập phản hồi của reviewer và thực hiện bước tổng hợp (`synthesize`) thành công.
- Review tinh chỉnh kèm đầy đủ Q&A đã được commit lên GitHub dưới tên `ducdh205`. Đạt 100% yêu cầu Exercise 3.
