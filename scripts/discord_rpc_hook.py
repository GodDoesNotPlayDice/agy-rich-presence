#!/usr/bin/env python3
"""
Discord Rich Presence Lifecycle Hook for Antigravity CLI
Triggers on SessionStart, PreInvocation, PreToolUse, PostInvocation, and Stop events.
"""
import os
import sys
import json
import time
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DAEMON_SCRIPT = os.path.join(SCRIPT_DIR, "discord_rpc_daemon.py")

CONFIG_DIR = os.path.expanduser("~/.gemini/antigravity-cli")
STATE_FILE = os.path.join(CONFIG_DIR, "discord_rpc_state.json")
PID_FILE = os.path.join(CONFIG_DIR, "discord_rpc_daemon.pid")

def is_pid_alive(pid):
    try:
        pid = int(pid)
        if sys.platform == "win32":
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(0x1000, False, pid)
            if handle:
                kernel32.CloseHandle(handle)
                return True
            return False
        else:
            if os.path.exists(f"/proc/{pid}"):
                return True
            os.kill(pid, 0)
            return True
    except Exception:
        return False

def get_agy_ancestor():
    if sys.platform == "win32":
        return os.getppid()
    curr = os.getppid()
    while curr > 1:
        try:
            with open(f"/proc/{curr}/cmdline", "rb") as f:
                cmd = f.read().replace(b"\x00", b" ").decode(errors="ignore")
                parts = cmd.strip().split()
                if parts and "agy" in os.path.basename(parts[0]):
                    return curr
            with open(f"/proc/{curr}/stat") as sf:
                curr = int(sf.read().split()[3])
        except Exception:
            break
    return os.getppid()

def is_daemon_running():
    if not os.path.exists(PID_FILE):
        return False
    try:
        with open(PID_FILE, "r") as f:
            pid = int(f.read().strip())
        return is_pid_alive(pid)
    except (ValueError, OSError):
        return False

def ensure_daemon():
    if not is_daemon_running() and os.path.exists(DAEMON_SCRIPT):
        try:
            kwargs = {
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.DEVNULL,
                "stdin": subprocess.DEVNULL
            }
            if sys.platform == "win32":
                kwargs["creationflags"] = 0x00000008 | 0x08000000
            else:
                kwargs["start_new_session"] = True
                display = os.environ.get("DISPLAY", ":0")
                env = dict(os.environ, DISPLAY=display)
                if "XAUTHORITY" not in env:
                    env["XAUTHORITY"] = os.path.expanduser("~/.Xauthority")
                kwargs["env"] = env
            subprocess.Popen([sys.executable, DAEMON_SCRIPT], **kwargs)
        except Exception:
            pass

def parse_tool_activity(tool_call):
    """
    Parses toolCall object from Antigravity hook payload.
    Returns: (status, status_text, state)
    status: reading | editing | executing | searching | tool | working | idle
    """
    if not isinstance(tool_call, dict):
        return ("tool", "Running tool", "Running tool...")

    name = tool_call.get("name", "tool")
    args = tool_call.get("args", {})
    if not isinstance(args, dict):
        args = {}

    tool_action = args.get("toolAction") or args.get("toolSummary")

    # If call_mcp_tool wrapper, unwrap
    if name == "call_mcp_tool":
        server = args.get("ServerName", "mcp")
        inner_tool = args.get("ToolName", "tool")
        inner_args = args.get("Arguments", {})
        if isinstance(inner_args, dict):
            args = inner_args
        name = inner_tool

    # Helper to extract clean filename
    def get_filename():
        for k in ("AbsolutePath", "TargetFile", "file_path", "path", "Uri", "uri"):
            v = args.get(k)
            if v and isinstance(v, str):
                return os.path.basename(v.strip().rstrip("/\\"))
        return None

    # Helper to extract query or pattern
    def get_query():
        for k in ("query", "query_string", "name_pattern", "pattern", "search_term", "q"):
            v = args.get(k)
            if v and isinstance(v, str) and v.strip():
                return v.strip()
        return None

    filename = get_filename()
    query = get_query()

    # 1. Reading / Inspecting
    read_tools = {
        "view_file", "read_file", "read_resource", "list_resources",
        "get_code_snippet", "get_function_source", "get_class_source",
        "get_file_dependencies", "get_file_dependents", "list_files",
        "mem_context", "mem_get_observation", "mem_review"
    }
    if name in read_tools or name.startswith("view_") or name.startswith("read_file"):
        status = "reading"
        if filename:
            state = f"Reading {filename}"
            status_text = tool_action or f"Reading {filename}"
        else:
            state = "Reading files..."
            status_text = tool_action or "Inspecting code"
        return (status, status_text, state)

    # 2. Editing / Writing
    edit_tools = {
        "replace_file_content", "write_to_file", "edit_file",
        "replace_symbol_source", "edit_lines_in_symbol", "insert_near_symbol",
        "move_symbol", "add_field_to_model"
    }
    if name in edit_tools or name.startswith("edit_") or name.startswith("write_") or name.startswith("modify_"):
        status = "editing"
        action_verb = "Writing" if "write" in name else "Editing"
        if filename:
            state = f"{action_verb} {filename}"
            status_text = tool_action or f"{action_verb} {filename}"
        else:
            state = f"{action_verb} code..."
            status_text = tool_action or f"{action_verb} code"
        return (status, status_text, state)

    # 3. Executing Commands
    exec_tools = {"run_command", "bash", "execute_command", "manage_task", "run_project_action"}
    if name in exec_tools or "command" in name or "exec" in name:
        status = "executing"
        cmd = args.get("CommandLine", "")
        if isinstance(cmd, str) and cmd.strip():
            first_line = cmd.strip().splitlines()[0]
            if len(first_line) > 35:
                clean_cmd = first_line[:32] + "..."
            else:
                clean_cmd = first_line
            state = f"Running: {clean_cmd}"
            status_text = tool_action or f"Running: {clean_cmd}"
        else:
            state = "Executing command..."
            status_text = tool_action or "Executing command"
        return (status, status_text, state)

    # 4. Searching / Researching
    search_tools = {
        "search_web", "read_url_content", "read_browser_page",
        "search_code", "search_graph", "query_graph", "trace_path",
        "search_codebase", "search_in_symbols", "corpus_query", "mem_search"
    }
    if name in search_tools or "search" in name or "query" in name:
        status = "searching"
        if query:
            clean_q = query.splitlines()[0]
            if len(clean_q) > 35:
                clean_q = clean_q[:32] + "..."
            state = f"Searching: {clean_q}"
            status_text = tool_action or f"Searching: {clean_q}"
        elif name == "read_url_content":
            url = args.get("Url", "")
            domain = ""
            if url and isinstance(url, str):
                try:
                    from urllib.parse import urlparse
                    domain = urlparse(url).netloc
                except Exception:
                    pass
            state = f"Reading {domain or 'web page'}"
            status_text = tool_action or f"Browsing {domain or 'web'}"
        else:
            state = "Searching codebase..."
            status_text = tool_action or "Searching codebase / web"
        return (status, status_text, state)

    # 5. Question / User Input
    if name == "ask_question":
        return ("idle", "Waiting for user input", "Awaiting input...")

    # 6. Fallback Tool
    status = "tool"
    if tool_action and isinstance(tool_action, str):
        state = tool_action[:60]
        status_text = tool_action[:60]
    else:
        state = f"Running {name}"
        status_text = f"Tool: {name}"
    return (status, status_text, state)

def main():
    event = sys.argv[1] if len(sys.argv) > 1 else "PreInvocation"
    
    payload = {}
    if not sys.stdin.isatty():
        try:
            stdin_data = sys.stdin.read().strip()
            if stdin_data:
                payload = json.loads(stdin_data)
        except Exception:
            pass

    workspace_paths = payload.get("workspacePaths", [])
    workspace_name = "Antigravity CLI"
    if workspace_paths and isinstance(workspace_paths, list):
        workspace_name = os.path.basename(os.path.normpath(workspace_paths[0])) or "Workspace"

    agy_pid = str(get_agy_ancestor())

    # Load state
    state_data = {"sessions": {}}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict) and "sessions" in loaded:
                    state_data = loaded
        except Exception:
            pass

    sessions = state_data.get("sessions", {})
    curr_sess = sessions.get(agy_pid, {})
    start_ts = curr_sess.get("start_timestamp", int(time.time()))

    if event == "SessionStart":
        sessions[agy_pid] = {
            "status": "idle",
            "status_text": "Ready to code",
            "state": "Idle - Ready",
            "project": workspace_name,
            "start_timestamp": int(time.time()),
            "updated_at": time.time()
        }
    elif event == "PreInvocation":
        sessions[agy_pid] = {
            "status": "working",
            "status_text": "Thinking / Generating response",
            "state": "Thinking...",
            "project": workspace_name,
            "start_timestamp": start_ts,
            "updated_at": time.time()
        }
    elif event == "PreToolUse":
        tool_call = payload.get("toolCall", {})
        status, status_text, state = parse_tool_activity(tool_call)
        sessions[agy_pid] = {
            "status": status,
            "status_text": status_text,
            "state": state,
            "project": workspace_name,
            "start_timestamp": start_ts,
            "updated_at": time.time()
        }
    elif event == "PostToolUse":
        sessions[agy_pid] = {
            "status": "working",
            "status_text": "Thinking / Analyzing results",
            "state": "Thinking...",
            "project": workspace_name,
            "start_timestamp": start_ts,
            "updated_at": time.time()
        }
    elif event in ("PostInvocation", "Stop"):
        sessions[agy_pid] = {
            "status": "idle",
            "status_text": "Ready - Waiting for prompt",
            "state": "Idle - Ready",
            "project": workspace_name,
            "start_timestamp": start_ts,
            "updated_at": time.time()
        }

    # Clean up stale sessions
    clean_sessions = {}
    for spid, sval in sessions.items():
        try:
            pid_int = int(spid)
            if is_pid_alive(pid_int):
                clean_sessions[spid] = sval
        except Exception:
            pass
    state_data["sessions"] = clean_sessions

    os.makedirs(CONFIG_DIR, exist_ok=True)
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state_data, f)
    except Exception:
        pass

    ensure_daemon()

    if event == "PreToolUse":
        print(json.dumps({"decision": "allow"}))
    else:
        print(json.dumps({}))

if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("{}")
