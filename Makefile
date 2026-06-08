up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f api

ps:
	docker compose ps

rebuild:
	docker compose down && docker compose up -d --build

dbshell:
	docker compose exec db psql -U app -d app
