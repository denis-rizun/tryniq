.PHONY: help streamer streamer-build ext-dev ext-build fr bc eval-smoke eval-nightly eval-release

help:
	@echo "Targets:"
	@echo "  streamer        run the Swift streamer locally (requires Apple Silicon + .env)"
	@echo "  streamer-build  build the Swift streamer in release mode"
	@echo "  ext-dev         run the Chrome extension dev build"
	@echo "  ext-build       produce a production extension bundle"
	@echo "  fr              run the frontend dev server (outside docker)"
	@echo "  bc              docker compose up --build (backend stack only, legacy alias)"
	@echo "  eval-smoke      run the Langfuse foundation smoke experiment"
	@echo "  eval-nightly    run scheduled application evaluation suites"
	@echo "  eval-release    run release qualification against approved baselines"

streamer:
	$(MAKE) -C streamer run

streamer-build:
	$(MAKE) -C streamer build

ext-dev:
	cd extension && pnpm install && pnpm dev

ext-build:
	cd extension && pnpm install && pnpm build

fr:
	cd frontend && pnpm dev

bc:
	$(COMPOSE) up --build -d

eval-smoke:
	$(MAKE) -C evals eval-smoke

eval-nightly:
	$(MAKE) -C evals eval-nightly

eval-release:
	$(MAKE) -C evals eval-release
