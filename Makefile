.PHONY: setup setup-hooks

setup: setup-hooks  ## Initial project setup

setup-hooks:  ## Configure git to use project hooks (auto-tag on vX.Y.Z commits)
	@python3 -m dev_cycle.cli setup-hooks
