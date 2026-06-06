# Common Sherlog tasks. Run `make help` for the list.
.DEFAULT_GOAL := help

.PHONY: help install db-up db-down seed test lint eval demo demo-gif

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies (incl. eval extra)
	uv sync --extra eval

db-up: ## Start the pgvector database
	docker compose up -d

db-down: ## Stop the pgvector database
	docker compose down

seed: ## Load the RAG knowledge base
	uv run python scripts/seed_incidents.py

test: ## Run the test suite
	uv run pytest -q

lint: ## Lint with ruff
	uv run ruff check .

eval: ## Run the grounded-gain and gate benchmarks
	uv run python -m sherlog.eval.run_grounded
	uv run python -m sherlog.eval.run_gates

demo: ## Diagnose the bundled buggy project, with verification
	uv run sherlog diagnose examples/buggy_calculator/failure.log \
		--target-dir examples/buggy_calculator \
		--test-command "python -m pytest -q"

demo-gif: ## Record + 2x-speed docs/demo.gif (needs: brew install vhs ttyd ffmpeg)
	vhs demo.tape
	ffmpeg -y -i docs/demo.gif -filter_complex \
		"[0:v]setpts=0.5*PTS,fps=12,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" \
		docs/.demo.tmp.gif
	mv docs/.demo.tmp.gif docs/demo.gif
