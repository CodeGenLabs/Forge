[ [English](../en/troubleshooting.md) | [Tiếng Việt](../vi/troubleshooting.md) | 🌐 **日本語** ]
---

# トラブルシューティング

---

## 1. `forge: command not found`
`~/.local/bin` が環境変数 `PATH` に含まれていない可能性があります。
* Windows: `scripts/install.ps1` を再実行するか、User PATH に追加してください。
* Linux/macOS: `export PATH="$HOME/.local/bin:$PATH"` を設定してください。

## 2. `Derived tier stale` エラー
```bash
forge sync derived
git add docs/system/derived
git commit -m "chore: sync derived tier"
```
