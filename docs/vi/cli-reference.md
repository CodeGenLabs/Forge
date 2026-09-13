[ [English](../en/cli-reference.md) | 🌐 **Tiếng Việt** | [日本語](../ja/cli-reference.md) ]
---

# Tra cứu câu lệnh CLI

Danh mục hướng dẫn đầy đủ cho toàn bộ 11 câu lệnh của Forge CLI.

---

## Bảng tổng hợp câu lệnh

| Lệnh | Ý nghĩa | Tham số chính |
| :--- | :--- | :--- |
| `forge init` | Khởi tạo cấu trúc Forge trong dự án | `--repo <path>`, `--dry-run` |
| `forge doctor` | Chẩn đoán môi trường Python, Git, Tree-sitter | `--json` |
| `forge check` | Kiểm tra toàn diện claim, neo AST và gate | `--repo <path>`, `--scope <all\|claims\|trace>` |
| `forge sync` | Đồng bộ tầng dữ liệu máy (derived tier) | `derived`, `--repo <path>` |
| `forge anchor` | Phân tích và kiểm tra các điểm neo AST | `classify <anchor>`, `find <file>` |
| `forge claim` | Liệt kê và kiểm tra trạng thái claim | `list`, `show <id>`, `stale` |
| `forge change` | Quản lý vòng đời tính năng | `new`, `list`, `show`, `archive` |
| `forge gate` | Đánh giá các cổng kiểm soát | `<point>`, `--change <id>` |
| `forge verify` | Chạy bộ test và kiểm tra chạm claim | `--change <id>`, `--fast` |
| `forge reconcile`| Định vị tác giả gây trôi lệch và gợi ý sửa | `--repo <path>`, `--auto-retire` |
| `forge host` | Khởi chạy máy chủ giao tiếp MCP hoặc Agent | `--port <port>` |
