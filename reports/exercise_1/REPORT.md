# Exercise 1 — Định tuyến theo confidence

Đã hoàn thiện graph và đạt checkpoint trên hai PR thật: PR #1 đi `human_approval`, PR #2 đi `escalate`. Các kết quả dưới đây lấy trực tiếp từ lần chạy GitHub API và LLM ngày 15/10/2026, không dùng kết quả giả lập làm bằng chứng chạy thật.

## Phần đã triển khai

- `node_analyze`: dùng `get_llm().with_structured_output(PRAnalysis)`, gửi system message của senior reviewer và user message chứa title + diff; gọi `invoke` trong `console.status`, trả `{"analysis": analysis}`.
- Prompt yêu cầu đánh giá độ đầy đủ của review, phân biệt một thay đổi cục bộ còn thiếu ngữ cảnh với nhiều phần bảo mật chưa thể xác minh. Các khoảng confidence trong prompt lấy từ hằng số import, không có điều kiện theo URL hoặc số PR.
- `node_route`: chỉ đọc confidence và trả `decision`. `confidence >= AUTO_APPROVE_THRESHOLD` đi `auto_approve`; `confidence < ESCALATE_THRESHOLD` đi `escalate`; phần còn lại đi `human_approval`.
- `build_graph`: đăng ký đủ 6 node; nối `START → fetch_pr → analyze → route`; conditional edges đọc `state["decision"]`; cả ba node cuối nối tới `END`.
- Ba node cuối vẫn là placeholder của Exercise 1, chưa có HITL hoặc đăng comment lên GitHub. `PRAnalysis` và toàn bộ `common/` giữ nguyên.

## Môi trường và cách thu thập bằng chứng

Python 3.12.3 trong WSL, `langgraph=1.2.0`, `langchain-openai=1.2.1`, `pydantic=2.13.4`. Model cấu hình trong `.env`: `openai/gpt-4o-mini`, qua OpenRouter; temperature mặc định của `get_llm` là `0.2`.

Ngưỡng thực tế ở cả hai lần chạy cuối: `AUTO_APPROVE_THRESHOLD=0.73`, `ESCALATE_THRESHOLD=0.58`. Không nâng ngưỡng để ép nhánh.

PowerShell chưa có `uv`; môi trường `.venv` có sẵn được tạo bằng Linux nên các lệnh chạy trong WSL. Lệnh trực tiếp của đề với PR #1 đã được thử nhưng dừng ở `fetch_pr`, báo `RuntimeError: GITHUB_TOKEN is not set`.

Để tiếp tục lấy dữ liệu thật khi `.env` chưa có token, script [run_live.py](run_live.py) bỏ header Authorization **trong tiến trình thu thập bằng chứng**. Script vẫn gọi `common.github.fetch_pr` để đọc metadata, diff, danh sách file từ GitHub public API, rồi chạy graph và LLM thật. Không thay nội dung PR, không giả lập phản hồi LLM, không sửa mã `common/`. JSON lưu input thực tế, toàn bộ `PRAnalysis`, decision, action, thời gian, phiên bản và SHA-256 của mã nguồn. Log `.txt` lưu output terminal.

Các lệnh đã chạy từ thư mục gốc repository trong WSL:

```bash
uv run --frozen python -m reports.exercise_1.run_live --pr https://github.com/VinUni-AI20k/PR-Demo/pull/1 --anonymous-public-read --output reports/exercise_1/pr_1.json
uv run --frozen python -m reports.exercise_1.run_live --pr https://github.com/VinUni-AI20k/PR-Demo/pull/2 --anonymous-public-read --output reports/exercise_1/pr_2.json
```

## Kết quả chạy thật với prompt cuối

| PR | Head SHA | Số file | Bắt đầu (UTC) | Thời gian toàn lần chạy | Confidence | Decision | Final action |
|---|---|---:|---|---:|---:|---|---|
| [#1](https://github.com/VinUni-AI20k/PR-Demo/pull/1) | `1646156` | 3 | 2026-10-15 07:25:29 | 13.497 giây | 0.65 | `human_approval` | `pending_human_approval` |
| [#2](https://github.com/VinUni-AI20k/PR-Demo/pull/2) | `501f95e` | 4 | 2026-10-15 07:25:20 | 14.726 giây | 0.55 | `escalate` | `pending_escalation` |

PR #1: `0.58 <= 0.65 < 0.73`, nên cần human approval. Model trả 4 comments và 3 câu hỏi, nêu thiếu validation cho priority và chưa rõ migration của database hiện có. Output thực tế:

```text
✓ HUMAN APPROVAL — placeholder, exercise 2 will pause here
confidence = 65%
action     = pending_human_approval
```

Bằng chứng: [JSON PR #1](pr_1.json), [log PR #1](pr_1.txt).

PR #2: `0.55 < 0.58`, nên escalate. Model trả 5 comments và 3 câu hỏi, phát hiện MD5, token plaintext, SQL được tạo bằng string interpolation, thiếu xử lý lỗi HTTP và user ID hard-code. Câu hỏi tập trung vào lý do dùng MD5, kế hoạch quản lý session và bảo vệ token. Đây là nhận xét của model từ diff, không phải kết quả chạy hoặc khai thác mã của PR. Output thực tế:

```text
✓ ESCALATE — placeholder, exercise 3 will ask the reviewer questions
confidence = 55%
action     = pending_escalation
```

Bằng chứng: [JSON PR #2](pr_2.json), [log PR #2](pr_2.txt). Hai JSON cuối ghi cùng SHA-256 của file exercise: `ebf735315635a0121278d4023c5b70a85ded36fcd4b9068f7b264269410ef459`.

## Những lần chạy chưa đạt và điều chỉnh prompt

| Phiên bản prompt | Confidence PR #1 | Confidence PR #2 | Kết quả |
|---|---:|---:|---|
| 1 — nhắc đánh giá thận trọng, thiếu ngữ cảnh | 70% | 70% | Cả hai `human_approval`, chưa đạt |
| 2 — thêm tiêu chí độ đầy đủ theo phạm vi câu hỏi còn mở | 60% | 60% | Cả hai `human_approval`, chưa đạt |
| 3 — nêu rõ các khoảng confidence từ schema | 65% | 60% | Cả hai `human_approval`, chưa đạt |
| 4 — thêm checklist và quy tắc thiếu bằng chứng trên nhiều ranh giới bảo mật | 65% | 55% | Hai nhánh mong đợi, đạt checkpoint |

Giữ lại dữ liệu từng lần: [lần 1 PR #1](attempt_1_pr_1.json), [lần 1 PR #2](attempt_1_pr_2.json), [lần 2 PR #1](attempt_2_pr_1.json), [lần 2 PR #2](attempt_2_pr_2.json), [lần 3 PR #1](attempt_3_pr_1.json), [lần 3 PR #2](attempt_3_pr_2.json). Mỗi JSON có log `.txt` cùng tên.

Confidence là tự báo cáo và nhạy với prompt; các lần trên dùng prompt khác nhau nên không phải phép đo độ ổn định của cùng một prompt. Hai lần chạy cuối chứng minh checkpoint đã đạt trong lần kiểm chứng này, chưa chứng minh confidence đã được hiệu chỉnh hoặc mọi lần chạy sau đều chọn cùng nhánh. Phần reasoning cuối của PR #2 vẫn dùng từ “moderate” dù confidence số là `0.55`; graph dùng trường số đúng theo contract, không suy diễn nhánh từ văn bản reasoning.

## Kiểm thử offline và kiểm tra mã

```bash
uv run --frozen python -m unittest discover -s tests -v
```

Kết quả sau lần sửa prompt cuối: **3 tests passed**, thời gian `0.081s`:

- Kiểm tra routing ở `0`, ngay dưới `0.58`, đúng `0.58`, ngay dưới `0.73`, đúng `0.73`, và `1`.
- Kiểm tra contract structured output: truyền `PRAnalysis`, đủ system/user message, user message có title và diff, giữ object analysis trả về.
- Kiểm tra graph chạy tới đúng cả ba node cuối và không có interrupt.

Các test này chủ động dùng dữ liệu tổng hợp để kiểm tra logic; không dùng chúng để khẳng định đã phân tích hai PR thật. Test nằm ở [test_exercise_1_confidence.py](../../tests/test_exercise_1_confidence.py). Kiểm tra cú pháp AST cho ba file Python liên quan và `git diff --check` cho file exercise đều qua.

## Chạy lại bằng lệnh gốc của đề

Sau khi cấu hình `GITHUB_TOKEN` trong `.env`, cả hai lệnh gốc của đề bài đã được chạy trực tiếp và kiểm chứng thành công:

```bash
uv run python exercises/exercise_1_confidence.py --pr https://github.com/VinUni-AI20k/PR-Demo/pull/1
uv run python exercises/exercise_1_confidence.py --pr https://github.com/VinUni-AI20k/PR-Demo/pull/2
```

Kết quả thực tế ghi nhận:
- **PR #1**: Lấy được 3 files, head `1646156`, in `✓ HUMAN APPROVAL — placeholder, exercise 2 will pause here`, `confidence = 65%`, `action = pending_human_approval`.
- **PR #2**: Lấy được 4 files, head `501f95e`, in `✓ ESCALATE — placeholder, exercise 3 will ask the reviewer questions`, `confidence = 55%`, `action = pending_escalation`.

