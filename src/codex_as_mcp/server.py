from mcp.server.fastmcp import FastMCP, Context
import subprocess
import re
import argparse
import sys
import os
from shutil import which
from typing import List, Dict, Optional, Sequence

# Global safe mode setting
SAFE_MODE = True

# Expose the server with the name expected by clients/config (e.g., "codex")
mcp = FastMCP("codex-as-mcp")

# Resolve how to invoke Codex CLI in a cross-platform way
def resolve_codex_invoker() -> List[str]:
    # First check if codex.cmd exists on Windows (typical npm install)
    if sys.platform == "win32":
        # Try the .cmd wrapper first (typical npm global install)
        codex_cmd = which("codex.cmd")
        if codex_cmd:
            print(f"DEBUG: Using codex.cmd at {codex_cmd}", file=sys.stderr)
            return [codex_cmd]
            
        # Try codex without extension
        codex_exe = which("codex")
        if codex_exe:
            print(f"DEBUG: Using codex at {codex_exe}", file=sys.stderr)
            return [codex_exe]
            
        # Try the direct npm path on Windows
        npm_path = os.path.expandvars(r"%APPDATA%\npm\codex.cmd")
        if os.path.exists(npm_path):
            print(f"DEBUG: Using npm codex.cmd at {npm_path}", file=sys.stderr)
            return [npm_path]
            
        # Fallback: try the global npm install path with node
        windows_path = os.path.expandvars(r"%APPDATA%\npm\node_modules\@openai\codex\bin\codex.js")
        if os.path.exists(windows_path):
            print(f"DEBUG: Using node + JS entry at {windows_path}", file=sys.stderr)
            return ["node", windows_path]
    else:
        # On Unix-like systems, check for codex in PATH
        found = which("codex")
        if found:
            print(f"DEBUG: Using codex executable at {found}", file=sys.stderr)
            return [found]

    # Last resort: hope shell can resolve 'codex'
    print("DEBUG: 'codex' not found on PATH; falling back to 'codex'", file=sys.stderr)
    return ["codex"]

CODEX_INVOKER = resolve_codex_invoker()

HEADER_RE = re.compile(
    r'^'
    r'\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\]'   # 1: timestamp
    r'\s+'
    r'([^\n]+)'                                    # 2: tag (full line, allows spaces/colons)
    r'\n',
    flags=re.M
)

BLOCK_RE = re.compile(
    r'^'
    r'\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\]\s+([^\n]+)\n'  # 1: ts, 2: tag
    r'(.*?)'                                                   # 3: body
    r'(?=^\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\]\s+[^\n]+\n|\Z)',
    flags=re.M | re.S
)

def run_and_extract_codex_blocks(
    cmd: Sequence[str],
    tags: Optional[Sequence[str]] = ("codex",),
    last_n: int = 1,
    safe_mode: bool = True
) -> List[Dict[str, str]]:
    """
    Run command and extract log blocks. Each block consists of:
    [YYYY-MM-DDTHH:MM:SS] <tag>
    <body text...until next timestamp header or end of file>
    
    :param cmd: Full command (as list)
    :param tags: Tags to filter (case insensitive). None means no filtering.
    :param last_n: Return last N matching blocks
    :return: [{timestamp, tag, body, raw}] in time order (old->new)
    """
    # Modify command based on safe mode
    final_cmd = list(cmd)
    
    if safe_mode == True:
        # Full safe mode: replace --full-auto with read-only sandbox
        if "--full-auto" in final_cmd:
            idx = final_cmd.index("--full-auto")
            final_cmd[idx:idx+1] = ["--sandbox", "read-only"]
    elif safe_mode == "skip-git":
        # Skip git mode: replace --full-auto with workspace-write sandbox
        if "--full-auto" in final_cmd:
            idx = final_cmd.index("--full-auto")
            final_cmd[idx:idx+1] = ["--sandbox", "workspace-write"]
    # If safe_mode is False (--yolo), keep --full-auto as is
    
    # Debug: Print what we're trying to run
    print(f"DEBUG: Safe mode = {safe_mode}", file=sys.stderr)
    print(f"DEBUG: Running command: {' '.join(final_cmd)}", file=sys.stderr)
    
    try:
        proc = subprocess.run(
            final_cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True,
            shell=False
        )
        
        if proc.stderr:
            print(f"DEBUG: stderr: {proc.stderr}", file=sys.stderr)
        if proc.returncode != 0:
            print(f"DEBUG: Return code: {proc.returncode}", file=sys.stderr)
            
        out = proc.stdout
        print(f"DEBUG: Raw stdout (first 500 chars): {out[:500] if out else 'EMPTY'}", file=sys.stderr)
        print(f"DEBUG: Raw stdout length: {len(out) if out else 0}", file=sys.stderr)
        
    except Exception as e:
        print(f"DEBUG: Exception running command: {e}", file=sys.stderr)
        print(f"DEBUG: Exception type: {type(e)}", file=sys.stderr)
        raise
    
    blocks = []
    for m in BLOCK_RE.finditer(out):
        ts, tag, body = m.group(1), m.group(2).strip(), m.group(3)
        if tags is None or tag.lower() in {t.lower() for t in tags}:
            raw = f'[{ts}] {tag}\n{body}'
            blocks.append({"timestamp": ts, "tag": tag, "body": body, "raw": raw})
    
    print(f"DEBUG: Found {len(blocks)} blocks matching pattern", file=sys.stderr)
    
    # If no blocks found but we have output, return the raw output
    if not blocks and out:
        print("DEBUG: No blocks found, returning raw output", file=sys.stderr)
        return [{"timestamp": "unknown", "tag": "codex", "body": out, "raw": out}]
    
    # Return only the last n blocks
    return blocks[-last_n:]


# Pre-defined review prompts for different scenarios
REVIEW_PROMPTS = {
    "files": """You are an expert code reviewer. Please conduct a thorough code review of the specified files.

Focus on:
- Code quality and best practices
- Potential bugs and security issues
- Performance considerations
- Maintainability and readability
- Design patterns and architecture

Files to review: {target}

{custom_prompt}

Please provide detailed feedback with specific suggestions for improvement.""",

    "staged": """You are an expert code reviewer. Please review the staged changes (git diff --cached) that are ready to be committed.

Focus on:
- Code quality and adherence to best practices
- Potential bugs introduced by the changes
- Security vulnerabilities
- Performance impact
- Breaking changes or compatibility issues
- Commit readiness

{custom_prompt}

Please provide feedback on whether these changes are ready for commit and any improvements needed.""",

    "unstaged": """You are an expert code reviewer. Please review the unstaged changes (git diff) in the working directory.

Focus on:
- Code quality and best practices
- Potential bugs and issues
- Incomplete implementations
- Code style and formatting
- Areas that need attention before staging

{custom_prompt}

Please provide feedback on the current changes and what should be addressed before committing.""",

    "changes": """You are an expert code reviewer. Please review the git changes in the specified commit range.

Focus on:
- Overall impact and coherence of the changes
- Code quality and best practices
- Potential regressions or bugs
- Security implications
- Performance impact
- Documentation needs

Commit range: {target}

{custom_prompt}

Please provide comprehensive feedback on these changes.""",

    "pr": """You are an expert code reviewer. Please conduct a comprehensive pull request review.

Focus on:
- Overall design and architecture decisions
- Code quality and best practices
- Test coverage and quality
- Documentation completeness
- Breaking changes and backward compatibility
- Security considerations
- Performance implications

Pull Request: {target}

{custom_prompt}

Please provide detailed review feedback suitable for a pull request review.""",

    "general": """You are an expert code reviewer. Please conduct a general code review of the codebase.

Focus on:
- Overall code architecture and design
- Code quality and maintainability
- Security best practices
- Performance optimization opportunities
- Technical debt identification
- Documentation quality

{custom_prompt}

Please provide a comprehensive review with prioritized recommendations."""
}


@mcp.tool()
async def codex_execute(prompt: str, work_dir: str, ctx: Context) -> str:
    """
    Execute prompt using codex for general purpose.

    Args:
        prompt (str): The prompt for codex
        work_dir (str): The working directory, e.g. /Users/kevin/Projects/demo_project
        ctx (Context): MCP context for logging
    """
    # Call Codex CLI non-interactively with the prompt as an argument
    cmd = [
        *CODEX_INVOKER, "exec",
        "--skip-git-repo-check",
        "--cd", work_dir,
    ]
    
    if SAFE_MODE == True:
        cmd.extend(["--sandbox", "read-only"])
    elif SAFE_MODE == "skip-git":
        cmd.extend(["--sandbox", "workspace-write"])
    else:
        cmd.append("--full-auto")

    # Positional prompt must be last
    cmd.append(prompt)
    
    print(f"DEBUG: Running: {' '.join(cmd)}", file=sys.stderr)
    print(f"DEBUG: With prompt: {prompt[:100]}...", file=sys.stderr)
    
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=False,
            timeout=300  # 5 minute timeout
        )

        if proc.stdout:
            print(f"DEBUG: Got output: {len(proc.stdout)} chars", file=sys.stderr)
            return proc.stdout
        elif proc.stderr:
            print(f"DEBUG: Got stderr: {len(proc.stderr)} chars", file=sys.stderr)
            return f"Error: {proc.stderr}"
        else:
            return "No output from codex"
            
    except subprocess.TimeoutExpired:
        return "Error: Codex command timed out after 5 minutes"
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
async def ping() -> str:
    """Lightweight health check to verify MCP handshake and tool calls."""
    return "pong"


@mcp.tool()
async def codex_review(review_type: str, work_dir: str, target: str = "", prompt: str = "", ctx: Context = None) -> str:
    """
    Execute code review using codex with pre-defined review prompts for different scenarios.
    
    This tool provides specialized code review capabilities for various development scenarios,
    combining pre-defined review templates with custom instructions.

    Args:
        review_type (str): Type of code review to perform. Must be one of:
            - "files": Review specific files for code quality, bugs, and best practices
                       Target: comma-separated file paths (e.g., "src/main.py,src/utils.py")
                       Example: review_type="files", target="src/auth.py,src/db.py"
            
            - "staged": Review staged changes (git diff --cached) ready for commit
                       Target: not needed (automatically detects staged changes)
                       Example: review_type="staged"
            
            - "unstaged": Review unstaged changes (git diff) in working directory
                         Target: not needed (automatically detects unstaged changes)
                         Example: review_type="unstaged"
            
            - "changes": Review specific commit range or git changes
                        Target: git commit range (e.g., "HEAD~3..HEAD", "main..feature-branch")
                        Example: review_type="changes", target="HEAD~2..HEAD"
            
            - "pr": Review pull request changes comprehensively
                   Target: pull request number or identifier
                   Example: review_type="pr", target="123"
            
            - "general": General codebase review for architecture and quality
                        Target: optional, can specify scope or leave empty for full codebase
                        Example: review_type="general", target="src/"

        work_dir (str): The working directory path (e.g., "/Users/kevin/Projects/demo_project")
        
        target (str, optional): Target specification based on review_type:
            - For "files": comma-separated file paths
            - For "staged"/"unstaged": not needed (leave empty)
            - For "changes": git commit range (commit1..commit2)
            - For "pr": pull request number/identifier
            - For "general": optional scope (directory path or leave empty)
        
        prompt (str, optional): Additional custom instructions to append to the review prompt.
                               Use this to specify particular aspects to focus on or additional context.
                               Example: "Focus on security vulnerabilities and performance"
        
        ctx (Context, optional): MCP context for logging

    Returns:
        str: Detailed code review results from codex

    Examples:
        # Review specific files with security focus
        codex_review("files", "/path/to/project", "src/auth.py,src/api.py", "Focus on security vulnerabilities")
        
        # Review staged changes before commit
        codex_review("staged", "/path/to/project")
        
        # Review unstaged work-in-progress changes
        codex_review("unstaged", "/path/to/project", "", "Check for incomplete implementations")
        
        # Review recent commits
        codex_review("changes", "/path/to/project", "HEAD~3..HEAD", "Look for performance regressions")
        
        # Review pull request
        codex_review("pr", "/path/to/project", "456", "Focus on test coverage")
        
        # General codebase review
        codex_review("general", "/path/to/project", "src/", "Identify technical debt")
    """
    if review_type not in REVIEW_PROMPTS:
        raise ValueError(f"Invalid review_type '{review_type}'. Must be one of: {list(REVIEW_PROMPTS.keys())}")
    
    # Get the appropriate review prompt template
    template = REVIEW_PROMPTS[review_type]
    
    # Format the template with target and custom prompt
    custom_prompt_section = f"\nAdditional instructions: {prompt}" if prompt else ""
    final_prompt = template.format(
        target=target if target else "current scope",
        custom_prompt=custom_prompt_section
    )
    
    cmd = [
        *CODEX_INVOKER, "exec",
        "--full-auto", "--skip-git-repo-check",
        "--cd", work_dir,
        final_prompt,
    ]
    blocks = run_and_extract_codex_blocks(cmd, safe_mode=SAFE_MODE)
    if not blocks:
        return "No output from codex"
    return blocks[-1]["raw"]


def main():
    """Entry point for the MCP server"""
    global SAFE_MODE
    
    parser = argparse.ArgumentParser(
        prog="codex-as-mcp",
        description="MCP server that provides codex agent tools"
    )
    parser.add_argument(
        "--yolo", 
        action="store_true",
        help="Enable full writable mode with --full-auto (allows file modifications, git operations, etc.)"
    )
    parser.add_argument(
        "--skip-git",
        action="store_true",
        help="Skip git repository check but stay in workspace-write sandbox mode"
    )
    parser.add_argument(
        "--help-modes",
        action="store_true", 
        help="Show detailed explanation of safe vs writable modes"
    )
    
    args = parser.parse_args()
    
    if args.help_modes:
        print("""
Codex-as-MCP Execution Modes:

Safe Mode (default):
  - Read-only operations only (--sandbox read-only)
  - No file modifications
  - No git operations  
  - Safe for exploration and analysis
  
Skip Git Mode (--skip-git):
  - Workspace write sandbox (--sandbox workspace-write)
  - Can modify files in workspace
  - Skips git repository check
  - Safer than full auto
  
Writable Mode (--yolo):
  - Full codex agent capabilities (--full-auto)
  - Can modify files, run git commands
  - Sequential execution prevents conflicts
  - Use with caution in production
  
Why Sequential Execution?
Codex is an agent that modifies files and system state. Running multiple
instances in parallel could cause file conflicts, git race conditions,
and conflicting system modifications. Sequential execution is safer.
""")
        sys.exit(0)
    
    # Set safe mode based on flags
    if args.yolo:
        SAFE_MODE = False
    elif args.skip_git:
        SAFE_MODE = "skip-git"  # Special mode
    else:
        SAFE_MODE = True
    
    if SAFE_MODE == True:
        print("Running in SAFE mode (read-only). Use --skip-git or --yolo for write modes.", file=sys.stderr)
    elif SAFE_MODE == "skip-git":
        print("Running in WORKSPACE-WRITE mode (skip git check). Use --yolo for full auto.", file=sys.stderr)
    else:
        print("Running in FULL AUTO mode. Codex can modify files and system state.", file=sys.stderr)
    
    mcp.run()


if __name__ == "__main__":
    main()
