[ [English](../en/concepts.md) | [Tiếng Việt](../vi/concepts.md) | 🌐 **日本語** ]
---

# コアコンセプト

Forge を構成する中核的な概念について解説します。

---

## 1. 3層モデル (3-Tier Model)
1. **第1層: 人間の意図 (Human Intent)**: `docs/system/` に保存されるアーキテクチャルールやドメイン定義。
2. **第2層: エージェントの作業 (Agent Work)**: `changes/XXXX-name/` に保存される個別の機能変更やタスク。
3. **第3層: マシンの真実 (Machine Truth)**: `docs/system/derived/` にGitコミットから自動導出される依存関係やテスト情報。

---

## 2. クレームとクレームストア (Claims & Claim Store)
コードベースに関する明確な不変条件や落とし穴を形式化して定義します：

```markdown
### PIT-token-never-logged
トークンは生の状態でログに出力されてはならない。
<!-- forge:claim
status: ratified
anchors:
  - src/auth/token.py#create_session_token
-->
```

---

## 3. ASTアンカー (AST Anchors)
行番号ではなく、Tree-sitter による構文木のシンボル名にアンカーします：
* `src/core/router.py#Router.dispatch`
* `packages/ui/src/button.tsx#PrimaryButton`
