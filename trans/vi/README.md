# forge

Một bộ harness kỹ nghệ phần mềm (software-engineering harness) cá nhân giúp AI coding agent hành xử như một kỹ sư senior đầy kỷ luật: tìm hiểu kỹ trước khi sửa đổi, đặc tả rõ trước khi triển khai, và — phần mà chưa ai giải quyết được — duy trì tri thức chính xác, có thể kiểm chứng được về một hệ thống hiện có.

**Trạng thái: thiết kế hoàn tất; quá trình triển khai đang ở milestone M2 trên tổng số 6 milestone.** Những gì hiện có là anchor engine — bộ phát hiện lỗi thời mang tính xác định (deterministic staleness detector) làm nền tảng cho toàn bộ thiết kế — cùng phép đo lường đóng vai trò cổng kiểm soát (gate) phần còn lại của bản build, tầng phái sinh (derived tier) và chỉ mục truy vết (traceability index). Chưa có vòng đời thay đổi (change lifecycle), chưa có gates, và chưa có skills.

```bash
pip install -e ".[grammars,dev]"
forge doctor
forge sync derived
forge status
forge drift "src/forge/anchor.py#classify" --baseline <sha>
forge trace INV-7
forge check
```

`forge drift` và `forge check` trả về mã thoát (exit code) 0 khi sạch sẽ (clean), 1 khi có điểm cần xem xét, 2 khi gặp lỗi sử dụng — do đó cả hai đều có thể phối hợp làm các cổng kiểm soát (gates).

## Đọc theo thứ tự này

| Tài liệu | Giải đáp điều gì |
|---|---|
| [RESEARCH.md](RESEARCH.md) | Sáu dự án tham chiếu thực sự làm gì, được đọc trực tiếp từ mã nguồn tại các pinned commit; y văn / tài liệu nghiên cứu nói gì; những gì chưa ai giải quyết được. Dữ kiện thực tế, cách diễn giải và khuyến nghị được phân tách riêng biệt |
| [COMPETITIVE_ANALYSIS.md](COMPETITIVE_ANALYSIS.md) | Ma trận năng lực và các quyết định tiếp thu / từ chối / chỉnh sửa theo từng dự án |
| [SYSTEM_KNOWLEDGE.md](SYSTEM_KNOWLEDGE.md) | **Tài liệu trụ cột (load-bearing document).** Mô hình anchored-claim: lược đồ (schema), nguồn chân lý (truth sources), phát hiện lỗi thời (staleness detection), các phán quyết về độ lệch (drift verdicts), khả năng truy vết (traceability), chính sách chống nhiễu (anti-noise policy) |
| [WORKFLOW.md](WORKFLOW.md) | Vòng đời theo từng giai đoạn: đầu vào, đầu ra, các cổng do con người duyệt (human gates), kiểm tra xác định (deterministic checks), kiểm tra bằng LLM, tiêu chí hoàn thành (exit criteria). Đi kèm các track và bootstrap |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Kiến trúc nội tại của harness: kernel / skills / artifacts, bố cục thư mục repository, bề mặt lệnh (command surface), mô hình trạng thái và kiểm định (state & validation models), ngân sách tăng trưởng (growth budgets) |
| [CONSTITUTION.md](CONSTITUTION.md) | 16 nguyên tắc kỹ nghệ, mỗi nguyên tắc đều có cơ chế phát hiện vi phạm |
| [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) | 15 câu hỏi chưa giải quyết kèm các phương án, khuyến nghị, và những bằng chứng còn thiếu |
| [MVP.md](MVP.md) | Sáu milestone, 39 kiểm tra xác định (deterministic checks), những gì KHÔNG nên xây dựng, và câu trả lời cho câu hỏi "bạn sẽ xây dựng gì từ con số 0 hôm nay" |

## Tóm tắt ngắn gọn

Ba phát hiện chính đã định hình thiết kế này:

1. **Trong sáu dự án tham chiếu, chỉ có đúng một dự án cung cấp cơ chế kiểm tra xác định so sánh mã nguồn với mô tả hệ thống được lưu trữ** — và cơ chế đó hoạt động bằng cách so khớp chuỗi con (substring-matching) tên thư mục với các tệp markdown tự do. Mọi thứ khác được gọi là "phân tích tính nhất quán", "kiểm chứng" hay "phát hiện độ lệch" thực chất chỉ là một prompt. Văn xuôi tự do thì không thể kiểm tra tự động được.
2. **LLM không thể làm bộ phát hiện độ lệch (drift detector).** Số liệu đo lường thực tế: LLM phát hiện lỗi tài liệu ở mức 67–94% nhưng độ chính xác giảm 21–43 điểm phần trăm khi chỉ có phần triển khai thay đổi — trường hợp then chốt nhất — và độ tự tin của chúng không phân biệt được phán đoán đúng hay sai ([arXiv:2604.03447](https://arxiv.org/abs/2604.03447)).
3. **Các dự án có bộ máy cồng kềnh nhất lại có ít bằng chứng nhất về tính hiệu quả.** Dự án hoàn toàn không có phương pháp luận nào (mini-SWE-agent, ~200 dòng code) lại công bố những con số benchmark thực tế duy nhất.

Vì vậy, đề xuất này được tinh giản có chủ đích, và đóng góp mới mẻ duy nhất của nó là **anchored claim** (khẳng định có neo):

```markdown
### INV-7 — A refund never exceeds the captured amount

```claim
kind: invariant
status: enforced
truth-source: tests
anchors:  [src/payments/refund.ts#computeRefundable@a1b2c3d]
evidence: [test: tests/payments/refund.spec.ts::refund cannot exceed capture]
governs:  [CMP-payments]
since:    ADR-0014
reviewed: 2026-09-10
```

Khoản hoàn tiền một phần có tính tích lũy: tổng các khoản hoàn tiền đã xử lý mới là giá trị bị giới hạn, không phải từng khoản hoàn riêng lẻ. Một yêu cầu vượt quá số dư còn lại sẽ bị từ chối tại ranh giới domain (domain boundary), chứ không bị kẹp gọt (clamped) — việc âm thầm kẹp gọt sẽ khiến khách hàng bị hoàn thiếu tiền.
```

Từ cấu trúc duy nhất đó, ba cơ chế ra đời mà chưa từng xuất hiện ở bất kỳ đâu trong toàn bộ tài liệu tham chiếu:

- **Phát hiện lỗi thời mang tính xác định (Deterministic staleness)** — dấu vân tay AST (tree-sitter AST fingerprints) đối chiếu với commit SHA được ghi nhận của neo. Không phải là "điều này có đúng không" (câu hỏi không thể trả lời tuyệt đối) mà là "đoạn code mà nó mô tả có bị thay đổi kể từ khi con người xác nhận hay không".
- **Quy tắc chạm-claim (The claim-touch rule)** — mọi thay đổi đều phải giải trình mọi claim có neo giao cắt với git diff của nó, dưới dạng `unaffected` / `updated` / `superseded-by-ADR`. Điều này biến câu hỏi *"tài liệu nào cần phải thay đổi?"* thành một phép toán tập hợp (set operation) thay vì một phán đoán cảm tính.
- **Sổ cái độ lệch với 4 phán quyết, không có đường dẫn tự động đối soát (auto-reconciliation).** Kernel không chứa lệnh nào tự động viết lại claim cho khớp với code. Độ lệch được phân loại rõ — code sai / claim chưa từng đúng / quyết định đã thay đổi (cần có ADR) / claim chưa đủ cụ thể — và con người sẽ là bên ghi nhận phán quyết.

Mọi thứ khác đều được chủ ý kế thừa từ các dự án khác: đồ thị phụ thuộc artifact (artifact DAG) và archive fold của OpenSpec, các cổng khai báo (declarative gates) của GSD, bộ định tuyến quy mô (scale router) và định dạng kế hoạch của Superpowers, từ vựng yêu cầu của Spec Kit, ngân sách (budgets) của mini-SWE-agent, tiêu chí kết nạp và căn cứ xóa bỏ của BMAD.

## Trạng thái triển khai

| Milestone | Trạng thái | Nội dung chi tiết |
|---|---|---|
| **M1 — anchors & drift** | **hoàn thành** | `gitio`, `fingerprint`, `anchor`; phép đo lường trong [docs/measurements/M1-anchor-stability.md](docs/measurements/M1-anchor-stability.md) — 0% dương tính giả (false positive), 0% âm tính giả (false negative) |
| **M2 — derived tier & trace index** | **hoàn thành** | `derive`, `store`, `trace`; `forge sync derived`, `forge trace`, `forge status`, `forge check` |
| M0 — claim store & validation | một phần | `store.py` phân tích các claim (chỉ mục cần đến nó). 18 kiểm tra store checks vẫn đang được phát triển |
| M3 — change DAG, gates, một workflow | chưa bắt đầu | Phần đầu tiên cần đến `deps.json`, được hoãn lại từ M2 |
| M4 — skills | chưa bắt đầu | |
| M5 — bootstrap | chưa bắt đầu | |

M1 được thực hiện đầu tiên vì nó nắm giữ điều kiện dừng (stop condition): nếu các neo tạo ra quá nhiều báo động giả (noise) trên lịch sử commit thực tế, lược đồ claim ở M0 sẽ phải thay đổi (neo thô hơn, hoặc chỉ dừng ở cấp độ component). Đo lường trước khi chốt định dạng là giải pháp ít tốn kém hơn, và nó đã phát huy hiệu quả — xem Q2 trong [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) để biết rủi ro này đã được loại bỏ như thế nào.

Quá trình xây dựng M1 và M2 đã đính chính 4 điểm trong tài liệu thiết kế ban đầu, mỗi điểm đều được ghi lại tại nơi có sai sót: các trạng thái drift (bổ sung `shifted`, hạ cấp `coarse` thành một flag), vỏ bọc tầng phái sinh / envelope (dấu thời gian từng khiến việc kiểm tra dirty không thể thực hiện được), ngữ pháp ID (cho phép dạng slug, không chỉ là số), và quy tắc lỗi thời (một commit chỉ chạm vào derived tier sẽ không khiến nó bị coi là lỗi thời). Mọi đính chính đều nêu rõ lý do tại sao phương án ban đầu chưa chuẩn xác trong tài liệu.
