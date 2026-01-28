SHELL := /bin/bash
PROJECT_DIR := $(shell pwd)
PLIST_NAME := com.htlin.telegram-tunnel
PLIST_PATH := ~/Library/LaunchAgents/$(PLIST_NAME).plist
LOG_FILE := $(PROJECT_DIR)/bot.log
PID_FILE := $(PROJECT_DIR)/bot.pid

.PHONY: help dev run stop restart log log-tail status register install uninstall clean

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Development:"
	@echo "  dev        Start bot in foreground (Ctrl+C to stop)"
	@echo "  run        Start bot in background"
	@echo "  stop       Stop background bot"
	@echo "  restart    Restart background bot"
	@echo "  status     Check if bot is running"
	@echo ""
	@echo "Logs:"
	@echo "  log        View log file"
	@echo "  log-tail   Follow log in real-time"
	@echo ""
	@echo "LaunchAgent (auto-start on login):"
	@echo "  register   Register LaunchAgent (alias: install)"
	@echo "  uninstall  Remove LaunchAgent"
	@echo ""
	@echo "Maintenance:"
	@echo "  clean      Remove log and pid files"

dev:
	@echo "Starting bot in dev mode (Ctrl+C to stop)..."
	cd $(PROJECT_DIR) && uv run python bot.py

run:
	@# Check for existing bot processes in THIS project (check uv parent process)
	@EXISTING=$$(lsof +D $(PROJECT_DIR) 2>/dev/null | grep "uv.*python" | awk '{print $$2}' | head -1); \
	if [ -n "$$EXISTING" ]; then \
		echo "Bot already running (PID: $$EXISTING). Use 'make stop' first."; \
		exit 1; \
	fi
	@cd $(PROJECT_DIR) && \
		nohup uv run python bot.py >> $(LOG_FILE) 2>&1 & \
		UV_PID=$$!; \
		sleep 2; \
		if kill -0 $$UV_PID 2>/dev/null; then \
			echo "$$UV_PID" > $(PID_FILE); \
			echo "Bot started (PID: $$UV_PID)"; \
		else \
			echo "Failed to start bot"; \
			exit 1; \
		fi

stop:
	@# Kill bot processes for THIS project using PID file
	@if [ -f $(PID_FILE) ]; then \
		PID=$$(cat $(PID_FILE)); \
		if kill -0 $$PID 2>/dev/null; then \
			kill $$PID 2>/dev/null && echo "Killed PID $$PID"; \
		fi; \
	fi
	@# Also kill any uv/python bot.py processes in this directory
	@lsof +D $(PROJECT_DIR) 2>/dev/null | grep -E "(uv|python|Python).*bot" | awk '{print $$2}' | sort -u | while read pid; do \
		kill $$pid 2>/dev/null && echo "Killed PID $$pid"; \
	done || true
	@rm -f $(PID_FILE)
	@echo "Bot stopped"

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
	@PIDS=$$(lsof +D $(PROJECT_DIR) 2>/dev/null | grep -E "(uv|python|Python).*bot" | awk '{print $$2}' | sort -u | tr '\n' ',' | sed 's/,$$//'); \
	if [ -n "$$PIDS" ]; then \
		echo "Bot running:"; \
		ps -p $$PIDS -o pid,etime,command 2>/dev/null | tail -n +2; \
	else \
		echo "Bot not running"; \
	fi

register: install

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
