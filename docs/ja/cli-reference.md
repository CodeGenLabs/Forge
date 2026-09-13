[ [English](../en/cli-reference.md) | [Tiếng Việt](../vi/cli-reference.md) | 🌐 **日本語** ]
---

# CLI リファレンス

Forge が提供する全11のサブコマンドのリファレンスです。

| コマンド | 用途 |
| :--- | :--- |
| `forge init` | リポジトリにForgeハーネスを初期化 |
| `forge doctor` | 実行環境（Python、Git、Tree-sitter）の診断 |
| `forge check` | クレームの鮮度と整合性の検証 |
| `forge sync` | マシン導出層（derived tier）の同期 |
| `forge anchor` | ASTアンカーの解析と分類 |
| `forge claim` | クレームの一覧表示と検証 |
| `forge change` | 変更ワークスペースのライフサイクル管理 |
| `forge gate` | フェーズごとのチェックポイントゲート評価 |
| `forge verify` | テスト実行とクレーム影響範囲の照合 |
| `forge reconcile`| ドリフトの発生原因を特定して修正支援 |
| `forge host` | MCPサーバーまたはエージェントアダプターの起動 |
| `forge report` | 不具合報告や機能提案（個人情報匿名化済み） |

---

## 🔒 プライバシーとテレメトリ方針

Forgeは**バックグラウンドテレメトリ（隠しデータ送信）ゼロ**を徹底しています:
* すべての処理はローカル環境で100%完結します。
* `forge report` や予期しないクラッシュ時の報告では、ローカルのユーザー名や絶対パス（`/home/<user>` や `C:\Users\<user>`）はすべて `~` に自動匿名化されます。
* 詳細は [PRIVACY.md](https://github.com/CodeGenLabs/forge-harness/blob/main/PRIVACY.md) をご確認ください。

