# AGENTS.md — Syntax-Checker

MCP-сервер проверки BSL для Cursor. **Инфраструктурный** репозиторий (Python + Docker).

## Быстрый контекст

- Tool: **`syntaxcheck(code: string)`**
- HTTP: `http://localhost:8010/mcp` (`SYNTAXCHECK_PORT`)
- BSL LS version SSoT: [`bsl.version`](bsl.version) (currently **0.29.0**)
- Memory Bank: `memory-bank/`

## Правила

1. Читай `memory-bank/activeContext.md` и `memory-bank/tasks.md` в начале сессии.
2. Не ломай контракт `syntaxcheck(code)`.
3. Логика установки/портов/обновлений — в `syntaxcheck_mcp/cli.py`, не дублировать в PS1/sh.
4. PS1 и `.sh` — thin wrappers над `python -m syntaxcheck_mcp.cli`.
5. После изменений Python: `python -m pytest tests/ -q`.
6. README — на русском.

## CLI

```bash
pip install -e .
python -m syntaxcheck_mcp.cli install
python -m syntaxcheck_mcp.cli update-bsl --check
```

## Верификация

- Unit: `pytest tests/`
- E2E: `cli test` (Docker + running container)
