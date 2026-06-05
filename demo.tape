# Record a terminal demo GIF of Sherlog.
#
#   brew install vhs        # https://github.com/charmbracelet/vhs
#   make demo-gif           # or: vhs demo.tape  ->  docs/demo.gif
#
# Requires a configured .env (ANTHROPIC_API_KEY) and the pgvector DB running.

Output docs/demo.gif

Set Shell "bash"
Set FontSize 15
Set Width 1200
Set Height 760
Set Padding 18

Type "uv run sherlog diagnose examples/buggy_calculator/failure.log --target-dir examples/buggy_calculator --test-command 'python -m pytest -q'"
Sleep 1s
Enter
# The agent reads the code, proposes a fix, and verifies it against the tests.
Sleep 35s
Sleep 2s
