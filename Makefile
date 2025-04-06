.PHONY: up-api up-arq up down down-api down-arq logs logs-api logs-arq

API_COMPOSE = api/docker-compose.yml
ARQ_COMPOSE = arq_worker/docker-compose.yml

up-api:
	docker compose -f $(API_COMPOSE) up -d --build


up-arq:
	docker compose -f $(ARQ_COMPOSE) up -d --build

up:
	$(MAKE) -j 2 up-api up-arq

down-api:
	docker compose -f $(API_COMPOSE) down --remove-orphans -t 1

down-arq:
	docker compose -f $(ARQ_COMPOSE) down --remove-orphans -t 1

down:
	$(MAKE) -j 2 down-api down-arq

logs-api:
	docker compose -f $(API_COMPOSE) logs -f

logs-arq:
	docker compose -f $(ARQ_COMPOSE) logs -f

logs:
	$(MAKE) -j 2 logs-api logs-arq








