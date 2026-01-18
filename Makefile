SHELL := /bin/bash
PROJECT_DIR := $(shell pwd)
PLIST_NAME := com.htlin.telegram-tunnel
PLIST_PATH := ~/Library/LaunchAgents/$(PLIST_NAME).plist
LOG_FILE := $(PROJECT_DIR)/bot.log
PID_FILE := $(PROJECT_DIR)/bot.pid

.PHONY: dev run stop restart log install uninstall status

dev:
	@echo "Starting bot in dev mode (Ctrl+C to stop)..."
	cd $(PROJECT_DIR) && uv run python bot.py

run:
	@if [ -f $(PID_FILE) ] && kill -0 $$(cat $(PID_FILE)) 2>/dev/null; then \
		echo "Bot already running (PID: $$(cat $(PID_FILE)))"; \
	else \
		cd $(PROJECT_DIR) && \
		nohup uv run python bot.py >> $(LOG_FILE) 2>&1 & \
		echo $$! > $(PID_FILE); \
		echo "Bot started (PID: $$(cat $(PID_FILE)))"; \
	fi

stop:
	@if [ -f $(PID_FILE) ]; then \
		PID=$$(cat $(PID_FILE)); \
		if kill -0 $$PID 2>/dev/null; then \
			kill $$PID; \
			echo "Bot stopped (PID: $$PID)"; \
		else \
			echo "Process not running"; \
		fi; \
		rm -f $(PID_FILE); \
	else \
		echo "No PID file found"; \
		pkill -f "python bot.py" 2>/dev/null && echo "Killed bot process" || echo "No process found"; \
	fi

restart: stop
	@sleep 1
	@$(MAKE) run

log:
	@if [ -f $(LOG_FILE) ]; then \
		cat $(LOG_FILE); \
	else \
		echo "No log file found"; \
	fi

log-tail:
	@if [ -f $(LOG_FILE) ]; then \
		tail -f $(LOG_FILE); \
	else \
		echo "No log file found"; \
	fi

status:
	@if [ -f $(PID_FILE) ] && kill -0 $$(cat $(PID_FILE)) 2>/dev/null; then \
		echo "Bot running (PID: $$(cat $(PID_FILE)))"; \
	else \
		echo "Bot not running"; \
	fi

install:
	@echo "Creating LaunchAgent plist..."
	@mkdir -p ~/Library/LaunchAgents
	@sed "s|{{PROJECT_DIR}}|$(PROJECT_DIR)|g" $(PROJECT_DIR)/launchd.plist.template > $(PLIST_PATH)
	@launchctl load $(PLIST_PATH)
	@echo "Installed and loaded $(PLIST_NAME)"
	@echo "Bot will auto-start on login"

uninstall:
	@if [ -f $(PLIST_PATH) ]; then \
		launchctl unload $(PLIST_PATH) 2>/dev/null || true; \
		rm -f $(PLIST_PATH); \
		echo "Uninstalled $(PLIST_NAME)"; \
	else \
		echo "Plist not found"; \
	fi

clean:
	@rm -f $(LOG_FILE) $(PID_FILE)
	@echo "Cleaned log and pid files"
