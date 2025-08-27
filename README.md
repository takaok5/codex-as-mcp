##markdown
# codex-as-mcp (Windows Fork)

Windows-compatible fork of [kky42/codex-as-mcp](https://github.com/kky42/codex-as-mcp). Fixes subprocess hanging and PowerShell compatibility issues.

## Setup

### 1. Install Python (if needed)

**Check if Python is installed:**
```bash
python --version
# or
py --version
```

**If not installed:**
1. Download Python from [python.org](https://www.python.org/downloads/)
2. During installation, **CHECK "Add Python to PATH"** ✅
3. Restart your terminal after installation

**Verify Python is in PATH:**
```bash
where python
# Should show: C:\Users\[YourName]\AppData\Local\Programs\Python\Python3X\python.exe
```

### 2. Install Codex CLI
```bash
npm install -g @openai/codex
codex login
```

### 3. Install this fork
```bash
git clone https://github.com/takaok5/codex-as-mcp-windows.git
cd codex-as-mcp-windows
pip install -e .
```

### 4. Configure MCP

**For Windows users - add to `.claude.json`:**

**Safe Mode (Read-only):**
```json
{
  "mcpServers": {
    "codex": {
      "type": "stdio",
      "command": "python",
      "args": [
        "C:\\path\\to\\codex-as-mcp-windows\\src\\codex_as_mcp\\server.py"
      ]
    }
  }
}
```

**Skip-Git Mode (Workspace writes, recommended):**
```json
{
  "mcpServers": {
    "codex": {
      "type": "stdio",
      "command": "python",
      "args": [
        "C:\\path\\to\\codex-as-mcp-windows\\src\\codex_as_mcp\\server.py",
        "--skip-git"
      ]
    }
  }
}
```

**Writable Mode (Full auto, dangerous):**
```json
{
  "mcpServers": {
    "codex": {
      "type": "stdio",
      "command": "python",
      "args": [
        "C:\\path\\to\\codex-as-mcp-windows\\src\\codex_as_mcp\\server.py",
        "--yolo"
      ]
    }
  }
}
```

**Note:** If `python` command doesn't work, try using `py` instead in the command field.

## Tools

The MCP server exposes two tools:
- `codex_execute(prompt, work_dir)` - General purpose codex execution
- `codex_review(review_type, work_dir, target?, prompt?)` - Specialized code review

## What's Fixed

- ✅ Windows PowerShell/CMD compatibility
- ✅ Non-interactive execution (no hanging)
- ✅ UTF-8 encoding issues resolved
- ✅ New `--skip-git` mode for non-git directories

## Safety

- **Safe Mode**: Default read-only operations protect your environment
- **Skip-Git Mode**: NEW - Write to workspace without git checks
- **Writable Mode**: Use `--yolo` flag when you need full codex capabilities
- **Sequential Execution**: Prevents conflicts from parallel agent operations

## Differences from Original

- Uses direct Python execution instead of uvx
- Passes prompts via stdin with `--json` flag for non-interactive mode
- Cleaned encoding for Windows compatibility
- Added intermediate `--skip-git` mode

## Requirements

- Windows 10/11
- Python 3.11+ (must be in PATH)
- Node.js 18+
- Codex CLI installed and authenticated

## Troubleshooting

**Python not found:**
- Make sure Python is in PATH: `where python`
- Try using `py` instead of `python` in the config
- Reinstall Python with "Add to PATH" checked

**Codex not responding:**
- Verify codex works: `codex --version`
- Check authentication: `codex login`
```
