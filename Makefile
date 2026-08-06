.PHONY: help streamer streamer-build ext-dev ext-build fr bc

help:
	@echo "Targets:"
	@echo "  streamer        run the Swift streamer locally (requires Apple Silicon + .env)"
	@echo "  streamer-build  build the Swift streamer in release mode"
	@echo "  ext-dev         run the Chrome extension dev build"
	@echo "  ext-build       produce a production extension bundle"
	@echo "  fr              run the frontend dev server (outside docker)"
	@echo "  bc              docker compose up --build (backend stack only, legacy alias)"

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
