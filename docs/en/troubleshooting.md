[ 🌐 **English** | [Tiếng Việt](../vi/troubleshooting.md) | [日本語](../ja/troubleshooting.md) ]
---

# Troubleshooting & FAQ

Common questions and resolution steps for Forge Harness.

---

## Frequently Encountered Issues

### 1. `forge: command not found`
**Cause**: The executable shim directory (`~/.local/bin` or `%USERPROFILE%\.local\bin`) is not in your system `PATH`.

**Solution**:
=== "Windows"
    Run in PowerShell:
    ```powershell
    [Environment]::SetEnvironmentVariable("PATH", $env:PATH + ";$HOME\.local\bin", "User")
    ```
    Or use the 1-click installer:
    ```powershell
    powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1
    ```

=== "Linux / macOS"
    Add to your `~/.bashrc` or `~/.zshrc`:
    ```bash
    export PATH="$HOME/.local/bin:$PATH"
    ```

---

### 2. Unicode / Console Encoding Warnings on Windows (`cp1252`)
**Symptoms**: Character rendering warnings or `UnicodeEncodeError`.

**Solution**:
Forge includes native protection (`_survive_the_console()`) for Windows code pages. To ensure optimal Unicode display in PowerShell:
```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = "1"
```

---

### 3. "Derived tier stale" during `forge check`
**Symptoms**:
```text
ERROR derived_freshness: docs/system/derived/inventory.json was generated from commit abc1234, but HEAD is def5678
```

**Solution**:
Run synchronization and commit:
```bash
forge sync derived
git add docs/system/derived
git commit -m "chore: sync derived tier"
```

---

### 4. How to bypass a gate during emergency hotfixes?
Use the explicit bypass flag with a mandatory reason:
```bash
forge gate verify:post --change 0001 --bypass "Emergency CVE hotfix approved by SecOps"
```
