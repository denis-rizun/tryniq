.PHONY: ci typecheck

ci:
	uv run ruff format . && uv run ruff check . --fix

typecheck:
	uv run ty check
