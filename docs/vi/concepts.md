[ [English](../en/concepts.md) | 🌐 **Tiếng Việt** | [日本語](../ja/concepts.md) ]
---

# Khái niệm cốt lõi

Forge vận hành và bảo vệ tính toàn vẹn của mã nguồn dựa trên 5 khái niệm nền tảng.

---

## 1. Mô hình 3 Tầng (3-Tier Model)

1. **Tầng 1 - Ý định con người (Human Intent)**: Lưu trữ tại `docs/system/`. Bao gồm quy tắc kiến trúc, ràng buộc bảo mật, mô hình thực thể và ADR. Máy không bao giờ tự ý sửa đổi tầng này nếu không có sự phê duyệt của con người.
2. **Tầng 2 - Không gian thay đổi (Agent Work)**: Nằm tại `changes/XXXX-name/`. Nơi các kỹ sư và AI Agent phác thảo đề xuất (proposal), thiết kế chi tiết (design), phân tích ảnh hưởng (impact) và chia nhỏ tác vụ (tasks).
3. **Tầng 3 - Sự thật máy móc (Machine Truth)**: Tự động tổng hợp từ Git commit vào `docs/system/derived/`. Không bao giờ chỉnh sửa thủ công; được cập nhật bằng lệnh `forge sync derived`.

---

## 2. Phát biểu & Kho lưu trữ (Claims & Claim Store)

Một **Claim** là một khẳng định kỹ thuật rõ ràng, đi kèm các điểm neo mã nguồn:

```markdown
### PIT-token-never-logged
Mã thông báo xác thực (token) không bao giờ được xuất ra log dưới dạng thô.
<!-- forge:claim
status: ratified
anchors:
  - src/auth/token.py#create_session_token
  - src/logging/formatter.py#RedactingFormatter
-->
```

* `candidate`: Đề xuất đang xem xét.
* `ratified`: Quy tắc đã được phê chuẩn chính thức. Bất kỳ commit nào vi phạm sẽ làm gãy CI.
* `retired`: Quy tắc đã hết hiệu lực do hệ thống thay đổi.

---

## 3. Điểm neo cú pháp AST (AST Anchors)

Thay vì neo theo số dòng code (rất dễ vỡ khi thêm một dòng trống), Forge neo theo cấu trúc cú pháp Tree-sitter:
* `src/core/router.py#Router.dispatch`
* `packages/ui/src/button.tsx#PrimaryButton`
* `internal/storage/sqlite.go#OpenDatabase`

### Cơ chế chống báo động giả
* Đổi thụt lề hoặc thêm khoảng trắng? **Neo vẫn tươi mới (Fresh).**
* Sửa chú thích (comments) hoặc docstring? **Neo vẫn tươi mới (Fresh).**
* Sửa đổi thân hàm hoặc đổi tên symbol? **Neo bị đánh dấu cũ (Stale - Drifted).**
* Xóa symbol? **Neo bị đánh dấu mất tích (Missing).**

---

## 4. Cổng kiểm soát vòng đời (Change Gates)

Mỗi thay đổi đều đi qua 4 giai đoạn kiểm soát:
1. **Proposal**: Đặt vấn đề và lý do thực hiện.
2. **Design**: Thiết kế giải pháp kỹ thuật.
3. **Impact**: Báo cáo các Claim bị chạm đến.
4. **Verification**: Chạy test và đối chiếu diff thực tế.
