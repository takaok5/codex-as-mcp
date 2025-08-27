# codex-as-mcp (Windows 分支)

[kky42/codex-as-mcp](https://github.com/kky42/codex-as-mcp) 的 Windows 兼容分支。修复了子进程挂起和 PowerShell 兼容性问题。

## 安装与配置

### 1. 安装 Python（如需要）

**检查 Python 是否已安装：**
```bash
python --version
# 或
py --version
```

**如未安装：**
1. 从 [python.org](https://www.python.org/downloads/) 下载 Python
2. 安装时，**务必勾选 "Add Python to PATH"** ✅
3. 安装后重启终端

**验证 Python 在 PATH 中：**
```bash
where python
# 应显示：C:\Users\[用户名]\AppData\Local\Programs\Python\Python3X\python.exe
```

### 2. 安装 Codex CLI
```bash
npm install -g @openai/codex
codex login
```

### 3. 安装此分支
```bash
git clone https://github.com/takaok5/codex-as-mcp-windows.git
cd codex-as-mcp-windows
pip install -e .
```

### 4. 配置 MCP

**Windows 用户 - 添加到 `.claude.json`：**

【安全模式（只读）】
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

【跳过 Git 模式（工作区写入，推荐）】
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

【可写模式（完全自动，危险）】
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

**注意：** 如果 `python` 命令不起作用，请在 command 字段中尝试使用 `py`。

## 工具

MCP 服务器暴露两个工具：
- `codex_execute(prompt, work_dir)` - 通用的 Codex 执行
- `codex_review(review_type, work_dir, target?, prompt?)` - 专项代码审查

## 已修复的问题

- ✅ Windows PowerShell/CMD 兼容性
- ✅ 非交互式执行（无挂起）
- ✅ UTF-8 编码问题已解决
- ✅ 新增 `--skip-git` 模式用于非 git 目录

## 安全性

- **安全模式**：默认只读操作，保护你的环境
- **跳过 Git 模式**：新增 - 写入工作区但不检查 git
- **可写模式**：需要完整能力时使用 `--yolo` 标志
- **顺序执行**：避免多代理并行操作产生冲突

## 与原版的差异

- 使用直接 Python 执行而非 uvx
- 通过 stdin 传递提示并使用 `--json` 标志实现非交互模式
- 清理编码以实现 Windows 兼容性
- 新增中间级别的 `--skip-git` 模式

## 系统要求

- Windows 10/11
- Python 3.11+（必须在 PATH 中）
- Node.js 18+
- Codex CLI 已安装并认证

## 故障排除

**找不到 Python：**
- 确保 Python 在 PATH 中：`where python`
- 在配置中尝试使用 `py` 代替 `python`
- 重新安装 Python 并勾选 "Add to PATH"

**Codex 无响应：**
- 验证 codex 是否工作：`codex --version`
- 检查认证状态：`codex login`
