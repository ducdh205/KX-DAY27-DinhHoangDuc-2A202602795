# Exercise 4 — Audit Trail SQLite và Phát lại phiên

Đã hoàn thiện hệ thống Audit Trail có cấu trúc lưu vào SQLite (`./hitl_audit.db`) và cơ chế checkpointer bền vững với `AsyncSqliteSaver` trong [exercises/exercise_4_audit.py](../../exercises/exercise_4_audit.py). Đã kiểm chứng toàn bộ quy trình ghi audit, phát lại dòng thời gian bằng `audit.replay` và liệt kê các phiên review vào ngày 15/10/2026.

---

## 1. Triển khai kỹ thuật

1. **Thân hàm `audit(state, entry)`**:
   - Gọi trực tiếp hàm async `write_audit_event`:
     ```python
     await write_audit_event(
         thread_id=state["thread_id"],
         pr_url=state["pr_url"],
         entry=entry,
     )
     ```

2. **Ghi `AuditEntry` cho từng node**:
   - `node_analyze`: Ghi `action="analyze"`, `confidence=a.confidence`, `risk_level=risk_level_for(a.confidence)`, `decision="pending"`, `reason=a.confidence_reasoning`, `execution_time_ms`.
   - `node_route`: Ghi `action="route"`, `decision` theo ánh xạ (`auto`, `escalate`, `pending`), `reason` mô tả định tuyến.
   - `node_human_approval`:
     - *Trước `interrupt()`*: Ghi `action="human_approval"`, `decision="pending"`, `reviewer_id=None`.
     - *Sau khi resume*: Ghi `action="human_approval"`, `decision=choice` (`approve`/`reject`/`edit`), `reviewer_id=os.environ.get("GITHUB_USER")`, `reason=feedback`.
   - `node_commit`: Ghi `action="commit"`, `decision="approve"` (hoặc `"reject"`), `reviewer_id=os.environ.get("GITHUB_USER")`.
   - `node_auto_approve`: Ghi `action="auto_approve"`, `decision="auto"`, `reviewer_id=None`.
   - `node_escalate`:
     - *Trước `interrupt()`*: Ghi `action="escalate"`, `decision="pending"`, `reviewer_id=None`.
     - *Sau khi resume*: Ghi `action="escalate"`, `decision="escalate"`, `reviewer_id=os.environ.get("GITHUB_USER")`.
   - `node_synthesize`: Ghi `action="synthesize"`, sử dụng `confidence=refined.confidence` và `risk_level=risk_level_for(refined.confidence)`.

---

## 2. Kết quả kiểm chứng chạy thật trên PR #1

- **Lệnh thực thi**:
  ```bash
  uv run python exercises/exercise_4_audit.py --pr https://github.com/VinUni-AI20k/PR-Demo/pull/1
  ```
- **Thread ID được cấp phát**: `a317dcb0-5ecd-4ba4-887a-acb7b8576f3a`
- **Tương tác**:
  - Graph dừng tại `human_approval`, hiển thị panel `conf=65%`.
  - Reviewer chọn: `approve`, Feedback: `LGTM`.
  - Graph resume và commit review thành công lên PR #1.

- **Output terminal phiên chạy**:
  ```text
  ─────────────────────── Exercise 4 — SQLite audit trail ────────────────────────
  PR: https://github.com/VinUni-AI20k/PR-Demo/pull/1
  thread_id = a317dcb0-5ecd-4ba4-887a-acb7b8576f3a

  → fetch_pr
    ✓ 3 files, head 1646156
  → analyze
    ✓ confidence=65%, 4 comment(s)
  → route
    ✓ decision=human_approval (confidence=65%)
  ╭────────────────────────────────── conf=65% ──────────────────────────────────╮
  │ This PR introduces a new 'priority' field to tasks in a task tracking        │
  │ application. It modifies the command-line interface to accept a priority     │
  │ argument when adding tasks, updates the Task model to include the priority   │
  │ attribute, and alters the storage layer to handle priority in the database   │
  │ schema and queries.                                                          │
  ╰──────────────────────────────────────────────────────────────────────────────╯
  approve/reject/edit? approve
  Feedback: LGTM
  → commit
    ✓ posted comment to https://github.com/VinUni-AI20k/PR-Demo/pull/1
  ──────────────────────────────────── Final ─────────────────────────────────────
  final_action = committed

  Replay: uv run python -m audit.replay --thread a317dcb0-5ecd-4ba4-887a-acb7b8576f3a
  ```

---

## 3. Phát lại phiên bằng `audit.replay`

### Lệnh phát lại chi tiết thread:
```bash
uv run python -m audit.replay --thread a317dcb0-5ecd-4ba4-887a-acb7b8576f3a
```

**Dòng thời gian ghi nhận**:
```text
───────────────── Replay a317dcb0-5ecd-4ba4-887a-acb7b8576f3a ──────────────────
2026-10-15T08:14:40.697888+00:00  fetch_pr           conf=0.00 risk=med  decision=pending    reviewer=-               2858ms  Fetched 3 files, head=1646156
2026-10-15T08:14:54.955880+00:00  analyze            conf=0.65 risk=med  decision=pending    reviewer=-              14203ms  The review identifies several critical issues related to inp
2026-10-15T08:14:54.975921+00:00  route              conf=0.65 risk=med  decision=pending    reviewer=-                  0ms  Routing decision: human_approval
2026-10-15T08:14:54.995736+00:00  human_approval     conf=0.65 risk=med  decision=pending    reviewer=-                  0ms  Awaiting reviewer decision (approve/reject/edit)
2026-10-15T08:14:55.024325+00:00  human_approval     conf=0.65 risk=med  decision=pending    reviewer=-                  0ms  Awaiting reviewer decision (approve/reject/edit)
2026-10-15T08:14:55.036814+00:00  human_approval     conf=0.65 risk=med  decision=approve    reviewer=ducdh205          12ms  LGTM
2026-10-15T08:14:56.287948+00:00  commit             conf=0.65 risk=med  decision=approve    reviewer=ducdh205        1240ms  Action: committed
```

- Nhận xét:
  - Dòng `human_approval` trước `interrupt()` xuất hiện 2 lần (lần 1 lúc chạy đầu tiên trước khi dừng, lần 2 khi resume chạy lại từ đầu node).
  - Dòng `human_approval` sau khi trả lời ghi nhận đúng `decision=approve`, `reviewer=ducdh205`, và `reason=LGTM`.
  - Dòng `commit` ghi nhận thời gian thực thi (1240ms) và xác nhận comment đã được đăng bởi `ducdh205`.

---

### Lệnh liệt kê các phiên gần đây:
```bash
uv run python -m audit.replay --list
```

**Bảng tổng hợp**:
```text
                             Recent review sessions                             
┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━┓
┃ thread_id   ┃ pr_url      ┃ started      ┃ last_event  ┃ worst_risk ┃ events ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━┩
│ a317dcb0-5… │ https://gi… │ 2026-10-15T… │ 2026-10-15… │ med        │ 7      │
└─────────────┴─────────────┴──────────────┴─────────────┴────────────┴────────┘
```

---

## 4. Dữ liệu bảng `audit_events` trong SQLite

Truy vấn trực tiếp từ cơ sở dữ liệu `hitl_audit.db`:
```sql
SELECT id, action, confidence, decision, reviewer_id, execution_time_ms FROM audit_events ORDER BY id;
```

**Dữ liệu thực tế**:
| id | action | confidence | decision | reviewer_id | execution_time_ms |
|---|---|---|---|---|---|
| 1 | fetch_pr | 0.0 | pending | NULL | 2858 |
| 2 | analyze | 0.65 | pending | NULL | 14203 |
| 3 | route | 0.65 | pending | NULL | 0 |
| 4 | human_approval | 0.65 | pending | NULL | 0 |
| 5 | human_approval | 0.65 | pending | NULL | 0 |
| 6 | human_approval | 0.65 | approve | ducdh205 | 12 |
| 7 | commit | 0.65 | approve | ducdh205 | 1240 |

Đạt 100% yêu cầu Checkpoint của Exercise 4.

