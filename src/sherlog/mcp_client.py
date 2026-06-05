"""Load Sherlog's MCP tools as LangChain tools the agents can call.

This spawns `sherlog.mcp_server` as a stdio MCP subprocess (pointed at the project
under diagnosis via SHERLOG_TARGET_DIR) and returns its tools as LangChain tools.
Binding those to the model is what turns a log-only diagnosis into an investigation
that can actually read the code and run the tests.
"""

import os
import sys

from langchain_mcp_adapters.client import MultiServerMCPClient


def make_client(target_dir: str) -> MultiServerMCPClient:
    """Build an MCP client wired to our tool server, scoped to `target_dir`."""
    return MultiServerMCPClient(
        {
            "sherlog-tools": {
                # Use the current venv's interpreter so the subprocess can import sherlog.
                "command": sys.executable,
                "args": ["-m", "sherlog.mcp_server"],
                "transport": "stdio",
                # Confine the tools to the project being diagnosed.
                "env": {**os.environ, "SHERLOG_TARGET_DIR": target_dir},
            }
        }
    )


# Tools that cannot mutate the project — safe to hand to investigation agents.
READ_ONLY_TOOLS = {"read_file", "search_code"}


async def load_tools(target_dir: str):
    """Return all MCP tools (read_file, search_code, run_command) as LangChain tools."""
    return await make_client(target_dir).get_tools()


async def load_read_tools(target_dir: str):
    """Return only the read-only tools, so an agent can investigate but never mutate the repo.

    Running commands (which could change files) is reserved for the deterministic verify
    step, which operates on a throwaway copy — never on the project being diagnosed.
    """
    return [t for t in await load_tools(target_dir) if t.name in READ_ONLY_TOOLS]
