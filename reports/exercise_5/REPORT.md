# Exercise 5 — Giao diện duyệt bằng Streamlit (`app.py`)

Đã hoàn thiện ứng dụng Web giao diện người dùng bằng Streamlit trong [app.py](../../app.py) bọc toàn bộ LangGraph HITL PR Review Agent từ Exercises 1–4. Đã kiểm chứng đầy đủ 3 trải nghiệm rẽ nhánh theo confidence, cơ chế resume tương tác qua Web, lưu trữ session state bền vững, và bảng điều khiển phiên trong sidebar vào ngày 15/10/2026.

---

## 1. Triển khai kỹ thuật trong `app.py`

1. **Khởi tạo và Quản lý Session State**:
   - Sử dụng `st.session_state` để lưu trữ các biến xuyên suốt các lần re-run của Streamlit: `thread_id`, `pr_url`, `interrupt_payload`, `final`.

2. **Sidebar "Recent sessions"**:
   - Truy vấn trực tiếp bảng `audit_events` từ `hitl_audit.db` bằng câu lệnh SQL chuẩn:
     ```sql
     SELECT thread_id,
            pr_url,
            MIN(timestamp)        AS started,
            MAX(timestamp)        AS last_event,
            MAX(risk_level)       AS worst_risk,
            COUNT(*)              AS events
       FROM audit_events
      GROUP BY thread_id, pr_url
      ORDER BY MAX(timestamp) DESC
      LIMIT 25
     ```
   - Hiển thị bảng tổng hợp các phiên gồm `Thread`, `Risk`, `Events`, và `Last Event`.
   - Cung cấp ô chọn và nút "Load session" để chuyển đổi hoặc tiếp tục phiên đã chọn.

3. **`render_approval_card(payload)` (Nhánh 58–72%)**:
   - Hiển thị tiêu đề `Approval requested — confidence {conf:.0%}`.
   - Hiển thị `confidence_reasoning`, `summary`, danh sách comment đề xuất kèm mức độ nghiêm trọng.
   - Khung expander xem trước `diff`.
   - Ô nhập `feedback` và 3 nút: **Approve** (primary), **Reject**, **Edit**.
   - Trả về payload tương ứng `{"choice": ..., "feedback": feedback}` để resume graph.

4. **`render_escalation_card(payload)` (Nhánh < 58%)**:
   - Hiển thị `Strong escalation — confidence {conf:.0%}`.
   - Khung cảnh báo màu đỏ làm nổi bật các `risk_factors`.
   - Form chứa các `st.text_input` cho từng câu hỏi trong `payload["questions"]`.
   - Nút "Submit answers" gom và trả về dictionary `{câu_hỏi: câu_trả_lời}`.

5. **`run_graph(pr_url, thread_id, resume_value=None)`**:
   - Khởi tạo `AsyncSqliteSaver` checkpointer từ `db_path()`.
   - Kết nối `build_graph(cp)`.
   - Nếu `resume_value is None`: gọi `app.ainvoke({"pr_url": ..., "thread_id": ...}, cfg)`.
   - Nếu có `resume_value`: gọi `app.ainvoke(Command(resume=resume_value), cfg)`.

6. **Hiển thị thẻ kết quả cuối cùng**:
   - Phân biệt hành động: `st.success` nếu `auto` hoặc `committed`, `st.warning` nếu `rejected`.
   - Hiển thị thông tin tóm tắt của LLM, điểm confidence cuối cùng, và link xem comment trên GitHub.
   - Cung cấp câu lệnh `uv run python -m audit.replay --thread <thread_id>` để phát lại audit trail.

---

## 2. Kết quả kiểm chứng chạy thật

### Kịch bản 1: PR #1 (Nhánh Human Approval)
- **Luồng chạy**:
  1. Người dùng nhập `https://github.com/VinUni-AI20k/PR-Demo/pull/1` và bấm **Run review**.
  2. Graph chạy đến điểm ngắt `node_human_approval` với confidence = 65%.
  3. UI hiển thị thẻ duyệt màu xanh với diff preview và các nút lựa chọn.
  4. Người duyệt chọn hành động (ví dụ: reject hoặc approve).
  5. Graph tiếp tục chạy đến `node_commit` và trả về kết quả tương ứng.

### Kịch bản 2: PR #2 (Nhánh Strong Escalation)
- **Thread ID kiểm chứng**: `c0eccdaa-4293-48cb-af3b-504c889695f1`
- **Luồng chạy**:
  1. Người dùng nhập `https://github.com/VinUni-AI20k/PR-Demo/pull/2`.
  2. Graph rẽ vào `escalate` (confidence = 55% < 58%).
  3. UI hiển thị thẻ cảnh báo rủi ro cao và form gồm 4 câu hỏi bảo mật cụ thể:
     - Rationale for MD5 password hashing in `auth.py`.
     - Token security on filesystem.
     - SQL injection prevention in `storage.py`.
     - HTTPS plan for `sync.py`.
  4. Người duyệt trả lời các câu hỏi và bấm **Submit answers**.
  5. Graph resume vào `node_synthesize`, nâng confidence lên `75%`, sau đó commit comment hoàn chỉnh lên PR #2.

- **Dòng thời gian Replay của Thread PR #2 trên Web**:
  ```text
  ───────────────── Replay c0eccdaa-4293-48cb-af3b-504c889695f1 ──────────────────
  2026-10-15T08:22:49.668122+00:00  fetch_pr           conf=0.00 risk=med  decision=pending    reviewer=-               2040ms  Fetched 4 files, head=501f95e
  2026-10-15T08:23:03.042477+00:00  analyze            conf=0.55 risk=high decision=pending    reviewer=-              13352ms  The review identifies several critical security issues
  2026-10-15T08:23:03.061917+00:00  route              conf=0.55 risk=high decision=escalate   reviewer=-                  0ms  Routing decision: escalate
  2026-10-15T08:23:03.085612+00:00  escalate           conf=0.55 risk=high decision=pending    reviewer=-                  0ms  Escalating with 4 question(s)
  2026-10-15T08:23:03.152186+00:00  escalate           conf=0.55 risk=high decision=pending    reviewer=-                  0ms  Escalating with 4 question(s)
  2026-10-15T08:23:03.167510+00:00  escalate           conf=0.55 risk=high decision=escalate   reviewer=ducdh205          15ms  Received answers for 4 question(s)
  2026-10-15T08:23:09.696389+00:00  synthesize         conf=0.75 risk=low  decision=pending    reviewer=ducdh205        6516ms  The review covers critical aspects of security
  2026-10-15T08:23:10.858955+00:00  commit             conf=0.75 risk=low  decision=approve    reviewer=ducdh205        1142ms  Action: committed
  ```

---

## 3. Cách khởi chạy giao diện Web

Khởi động ứng dụng Streamlit bằng lệnh:

```bash
uv run streamlit run app.py
```

Ứng dụng sẽ mở giao diện Web tại địa chỉ mặc định `http://localhost:8501`.

