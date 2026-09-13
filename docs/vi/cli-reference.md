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
| `forge report` | Báo cáo lỗi hoặc đề xuất tính năng lên GitHub (ẩn danh dữ liệu) | `--feature`, `--no-browser` |

---

## 🔒 Quyền riêng tư & Báo cáo Lỗi

Forge cam kết **hoàn toàn không thu thập dữ liệu ngầm (Zero Telemetry)**:
* Toàn bộ thao tác chạy 100% offline trên máy của bạn.
* Khi gặp lỗi không lường trước hoặc khi chạy `forge report`, Forge tự động ẩn danh hóa toàn bộ đường dẫn cá nhân (thay thế `C:\Users\<tên>` hoặc `/home/<tên>` thành `~`).
* Người dùng luôn có toàn quyền kiểm tra nội dung trước khi gửi lên GitHub. Chi tiết xem tại [Chính sách Quyền riêng tư (PRIVACY.md)](https://github.com/CodeGenLabs/forge-harness/blob/main/PRIVACY.md).

