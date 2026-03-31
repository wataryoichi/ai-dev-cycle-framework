# Request — bootstrap self-hosting flow

**Version:** v0.1.0

## Goal

Set up the initial framework: CLI, config, docs, and self-application support so
that the project can use its own dev cycle tooling from day one.

## Context

This is the very first cycle. The project directory was empty — everything needs
to be created from scratch: Python package, CLI commands, configuration, Claude
Code slash commands, and documentation.

## Scope

In scope:
- `dev_cycle/` Python package with CLI
- `devcycle.config.json` for self-application
- `.claude/commands/` for Claude Code integration
- `docs/` with self-hosting guide and operational playbook
- `ops/dev-cycles/` directory structure
- README with full documentation

Out of scope:
- CI/CD integration
- External project templates
- Automated Codex review triggering

## Notes

- This is a bootstrap cycle, so some manual steps are expected.
- The framework should be usable for both this project and external projects.
