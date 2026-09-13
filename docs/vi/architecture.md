[ [English](../en/architecture.md) | 🌐 **Tiếng Việt** | [日本語](../ja/architecture.md) ]
---

# Kiến trúc kỹ thuật

Chi tiết kỹ thuật về nhân Kernel của Forge, cơ chế phân tích cú pháp AST và mô hình băm mã hóa.

---

## Nguyên tắc thiết kế
1. **Kiểm tra tất định**: Không dựa vào đoán mò xác suất của LLM tại các cổng gate. Node AST tồn tại và khớp thì là hợp lệ, ngược lại thì báo lỗi.
2. **Phụ thuộc tối thiểu**: Chỉ phụ thuộc vào Tree-sitter và PyYAML.
3. **Tổng hợp tự động**: Toàn bộ dữ liệu tầng `docs/system/derived/` được sinh trực tiếp từ commit Git.
