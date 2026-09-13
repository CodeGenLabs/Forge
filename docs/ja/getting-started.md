[ [English](../en/getting-started.md) | [Tiếng Việt](../vi/getting-started.md) | 🌐 **日本語** ]
---

# クイックスタート

Forge Harness のインストールから初期設定、プロジェクトでの最初の実行までの手順を解説します。

---

## 動作要件
* **Python**: 3.11 以上
* **Git**: インストール済みで `PATH` に登録されていること
* **OS**: Windows 10/11, macOS, Linux

---

## インストール手順

### 推奨: `uv tool` または `pipx` を使用したグローバルインストール

```bash
# uv を使用する場合 (超高速):
uv tool install git+https://github.com/CodeGenLabs/forge-harness.git

# または pipx を使用する場合:
pipx install git+https://github.com/CodeGenLabs/forge-harness.git
pipx ensurepath
```

### 1クリック自動インストーラー

リポジトリをクローンしてセットアップする場合：

=== "Windows (PowerShell)"
    ```powershell
    git clone https://github.com/CodeGenLabs/forge-harness.git
    cd forge-harness
    powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1
    ```

=== "Linux / macOS (Bash)"
    ```bash
    git clone https://github.com/CodeGenLabs/forge-harness.git
    cd forge-harness
    bash ./scripts/install.sh
    ```

---

## インストールの確認

環境診断コマンドを実行します：
```bash
forge doctor
```

---

## 既存プロジェクトでの初期化

対象のリポジトリに移動し、初期化を実行します：
```bash
cd /path/to/my-project
forge init
```

整合性のチェック：
```bash
forge check
```
エラーがなければ終了コード `0` で完了します。
