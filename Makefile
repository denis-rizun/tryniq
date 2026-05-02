.PHONY: ext-dev ext-build help bc fr

help:
	@echo "Targets:"
	@echo "  ext-dev    cd extension && pnpm dev"
	@echo "  ext-build  cd extension && pnpm build"
	@echo "  bc  		cd backend && docker compose up --build -d"
	@echo "  fr  		cd frontend && pnpm dev"

ext-dev:
	cd extension && pnpm install && pnpm dev

ext-build:
	cd extension && pnpm install && pnpm build

bc:
	cd backend && docker compose up --build -d

fr:
	cd frontend && pnpm dev
