# SYSTEM_KNOWLEDGE.md — アンカー付きシステム知識

コードとドキュメントの乖離（Drift）を機械的に防止する知識管理アーキテクチャ。

---

## 1. アンカー付きクレーム (Anchored Claims)

すべてのシステム知識は構造化されたクレームとして表現されます:

```claim
kind: invariant | concept | architecture | domain | api
status: candidate | ratified | superseded | retired
truth-source: tests | code | adr | config
anchors:
  - path/to/file.py#symbol_name@commit_sha
evidence:
  - test: tests/test_file.py::test_case
governs: [CMP-component-id]
since: ADR-0001
reviewed: YYYY-MM-DD
```

---

## 2. ASTフィンガープリント

行番号ではなく、Tree-Sitterによる抽象構文木（AST）ノードをハッシュ化:
- 空白やコメントの整形差分は吸収。
- 構造的変更が発生した瞬間に `STALE`（陳腐化）として即座に警告。

---

## 3. クレーム接触計算 (Claim-Touch Rule)

$$\text{変更差分} \cap \text{全クレームのアンカー} = \text{接触クレーム集合}$$

変更差分がアンカーに触れている場合、影響説明書 `impact.md` による正当な説明がない限りコミットを阻止します。
