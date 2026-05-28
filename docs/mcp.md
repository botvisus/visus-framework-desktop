# Visus Desktop — MCP server

`visus-desktop` ships a [Model Context Protocol](https://modelcontextprotocol.io) server that exposes every automation primitive as an agent-callable tool. Once running, any MCP-aware client (Claude Desktop, Claude Code, Cursor, custom agents) can drive desktop apps through `visus-desktop` without you writing a single line of glue code.

## Install

```bash
pip install 'visus-desktop[mcp]'
```

The extra pulls in [`mcp[cli]`](https://github.com/modelcontextprotocol/python-sdk) (FastMCP). After installation the `visus-mcp` console script is on `PATH`.

## Run

```bash
visus-mcp                     # stdio transport (default; what Claude Desktop expects)
python -m visus.desktop.mcp_server
```

For a smoke check while developing the server itself:

```bash
mcp dev visus.desktop.mcp_server:mcp
```

## Wire into Claude Desktop / Claude Code

Append the server to your host config. On Claude Desktop (Windows):

```jsonc
// %APPDATA%\Claude\claude_desktop_config.json
{
  "mcpServers": {
    "visus-desktop": {
      "command": "visus-mcp"
    }
  }
}
```

On Claude Code:

```jsonc
// ~/.claude/settings.json
{
  "mcpServers": {
    "visus-desktop": { "command": "visus-mcp" }
  }
}
```

Restart the host. The 30 `visus-desktop` tools (see below) become discoverable by the agent.

## Tool surface

The server registers **30 tools**, grouped by capability. Every tool's docstring is its MCP description (the agent reads it before deciding when to call). Each tool's type hints become the JSON schema the agent populates.

### Find / click
* `find_text(text, region?, confidence_threshold?, occurrence?)` → `{x, y, width, height} | null`
* `click_text(text, region?, delay?, mouse_button?, occurrence?)` → `bool`
* `find_image(image_path, region?, confidence?)` → `{x, y, width, height} | null`
* `click_image(image_path, region?, confidence?, delay?, mouse_button?)` → `bool`
* `click_at(x, y, width?, height?, mouse_button?, delay?)` → `bool`
* `hybrid_find(name, region?)` → `{x, y, width, height} | null` *(native → OCR → image fallback chain)*

### Keyboard
* `type_text(text, interval?, delay?)` → `bool`
* `keyboard_command(command, delay?)` → `bool` *(named shortcut: `Ctrl+S`, `Alt+F4`, `Enter`, …)*

### Screen / monitors / waits
* `take_screenshot(region?, monitor?)` → `{mime_type, data_base64, width, height}` *(base64 PNG inline)*
* `get_monitors()` → `[{index, x, y, width, height, is_primary}]`
* `wait_for_stable_screen(region?, stable_for?, timeout?, poll_interval?)` → `bool`

### Files / clipboard
* `wait_for_file(path, timeout?, poll_interval?)` → `bool`
* `wait_for_file_stable(path, timeout?, stable_for?, poll_interval?)` → `bool`
* `get_clipboard()` → `str`
* `copy_to_clipboard(text)` → `bool`
* `extract_text_from_region(region, filter_type?, full_data?)` → `list | dict`

### Process / window
* `launch(command, args?)` → `int (pid)`
* `find_process(name)` → `list[int]`
* `kill_process(pid)` → `bool`
* `focus_window(title_substring)` → `bool`
* `maximize_window(title_substring)` → `bool`
* `minimize_window(title_substring)` → `bool`
* `close_window(title_substring)` → `bool`

### Task lists
* `execute_tasks(tasks, resume?)` → `list[{task_index, task_name, success, attempts, duration_ms, error, failure_screenshot}]`

### Sessions + reporting
* `start_recording(path)` → `str (absolute path of the zip)`
* `stop_recording()` → `bool`
* `replay_session(zip_path)` → `list[dict]`
* `render_report(zip_path, html_path)` → `str (absolute path of the html)`

### Diagnostics + configuration
* `doctor()` → `int (exit code; 0 = healthy)`
* `configure(config)` → `dict (active config after rebuild)`

## Skills

The repo also ships agent-ready [Skills](../skills/) that compose these tools into playbooks: login flows, table scraping, downloads, captchas, file dialogs, record/replay. Each Skill is a markdown file with `name` / `description` / `when_to_use` frontmatter — language-agnostic, importable by any skill framework. See [`skills/README.md`](../skills/README.md) for the catalogue and the host wiring snippet.

## Testing the server in-process

Each tool is a normal Python function decorated with `@mcp.tool()`. You can invoke them directly from a Python REPL:

```python
from visus.desktop import mcp_server as ms

# Lists the {name: callable} registry.
tools = ms._tools_for_tests()

# Call a tool with normal kwargs (no MCP transport spin-up).
tools["doctor"]()
tools["take_screenshot"](region=[0, 0, 200, 200])
```

The same shape is used by `tests/test_mcp_server.py`.

## Operational notes

* **Bot singleton**: the server holds one `VisusBot` per process lifetime. Use `configure(config={…})` to rebuild it with new settings (e.g. switch OCR backend, lower confidence, disable overlay).
* **Sync, not async**: all tools are synchronous (so are visus-desktop's primitives). FastMCP accepts sync `def` transparently.
* **Stdio is the default transport** — this is what desktop hosts expect. For network transports, look at the upstream [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) docs and replace `mcp.run()` in `main()`.
* **Recording state** persists across tool calls. Always call `stop_recording()` before starting a new session; the server does not auto-close recordings.
