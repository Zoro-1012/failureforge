COMPOSE = docker compose -f docker/docker-compose.yml

.PHONY: up down logs ps redis-outage incidents test clean

up:            ## Build and start the stack
	$(COMPOSE) up --build -d

down:          ## Stop the stack
	$(COMPOSE) down

logs:          ## Tail all service logs
	$(COMPOSE) logs -f

web:           ## Run the frontend in dev mode (outside Docker)
	cd frontend && npm install && npm run dev

ps:            ## Show service status
	$(COMPOSE) ps

define run_scenario
	curl -s -X POST localhost:8000/scenario/start \
		-H 'content-type: application/json' \
		-d '{"scenario":"$(1)"}' | python3 -m json.tool
endef

redis-outage:      ## Run the Redis Outage scenario
	$(call run_scenario,redis_outage)

deadlock:          ## Run the Database Deadlock scenario
	$(call run_scenario,database_deadlock)

memory-leak:       ## Run the Memory Leak scenario
	$(call run_scenario,memory_leak)

slow-database:     ## Run the Slow Database scenario
	$(call run_scenario,slow_database)

all-scenarios: redis-outage deadlock memory-leak slow-database  ## Run all four

diagnose:      ## Run AI diagnosis on an incident: make diagnose ID=incident_001
	curl -s -X POST localhost:8000/diagnose/$(ID) | python3 -m json.tool

evaluation:    ## Show benchmark metrics (accuracy / precision / recall)
	curl -s localhost:8000/evaluation | python3 -m json.tool

demo:          ## Seed all scenarios + diagnose + show evaluation (ROUNDS=n)
	./scripts/demo.sh

e2e:           ## Backend pipeline E2E (boots stack w/ stub provider, KEEP=1 to keep)
	./scripts/e2e.sh

e2e-ui:        ## Frontend Playwright E2E (boots full stack w/ stub provider)
	./scripts/e2e-ui.sh

incidents:     ## List captured incidents
	curl -s localhost:8000/incidents | python3 -m json.tool

test:          ## Run pytest (against a running stack)
	cd backend && python3 -m pytest ../tests -v

clean:         ## Stop stack and remove captured datasets
	$(COMPOSE) down -v
	rm -rf datasets/incident_*
