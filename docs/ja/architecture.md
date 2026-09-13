[ [English](../en/architecture.md) | [Tiếng Việt](../vi/architecture.md) | 🌐 **日本語** ]
---

# アーキテクチャ

Forge カーネルの内部設計と決定論的検証メカニズムについて解説します。

* **決定論的評価**: 確率的な推論を行わず、ASTノードの一致・不一致を厳密に評価。
* **最小限の依存関係**: Tree-sitter と PyYAML のみに依存。
* **自動導出層の不可逆性**: マシン導出層 (`docs/system/derived/`) はGitのコミットハッシュから常に一意に再生成可能。
