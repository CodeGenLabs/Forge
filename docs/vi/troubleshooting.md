[ [English](../en/troubleshooting.md) | 🌐 **Tiếng Việt** | [日本語](../ja/troubleshooting.md) ]
---

# Xử lý sự cố & Câu hỏi thường gặp

---

## 1. Lỗi `forge: command not found`
**Nguyên nhân**: Thư mục cài đặt shim (`~/.local/bin`) chưa được thêm vào biến môi trường `PATH`.
**Cách xử lý**:
* Trên Windows: Chạy `scripts/install.ps1`.
* Trên Linux/macOS: Thêm `export PATH="$HOME/.local/bin:$PATH"` vào `~/.bashrc` hoặc `~/.zshrc`.

## 2. Cảnh báo "Derived tier stale" trong `forge check`
**Cách xử lý**:
```powershell
forge sync derived
git add docs/system/derived
git commit -m "chore: sync derived tier"
```
