# 1C Syntax Checker

MCP-сервер для проверки синтаксиса кода 1С (BSL) через [BSL Language Server](https://github.com/1c-syntax/bsl-language-server) **v0.29.0** (JDK 21).

Инструмент для Cursor и других MCP-клиентов: **`syntaxcheck(code)`** — передаёте фрагмент BSL, получаете JSON с ошибками и предупреждениями.

## Требования

- **Python 3.10+**
- **Docker Desktop** (Windows/macOS) или **Docker Engine** (Linux) — [скачать](https://www.docker.com/products/docker-desktop/)
- **~2 ГБ** свободного места (образ Docker + BSL jar ~110 МБ)

Java на компьютере **не нужна** — Temurin 21 и BSL LS работают внутри Docker.

---

## Быстрый старт

### 1. Клонировать репозиторий

```bash
git clone https://github.com/yavityai/1C_SyntaxChecker.git
cd 1C_SyntaxChecker
```

### 2. Запустить Docker

```bash
docker info
```

### 3. Установка (один раз)

**Windows (PowerShell):**

```powershell
.\scripts\install.ps1
```

**Linux / macOS:**

```bash
chmod +x scripts/*.sh
./scripts/install.sh
```

Скрипт скачивает BSL jar (версия из [`bsl.version`](bsl.version)) и собирает Docker-образ.

### 4. Запуск

| Windows | Linux / macOS |
|---------|---------------|
| `.\scripts\start.ps1` | `./scripts/start.sh` |

MCP по умолчанию: **http://localhost:8010/mcp**

Проверка:

| Windows | Linux / macOS |
|---------|---------------|
| `.\scripts\test-syntaxcheck.ps1` | `./scripts/test-syntaxcheck.sh` |

### 5. Подключить в проект 1С (Cursor)

```bash
# любая ОС
python -m syntaxcheck_mcp.cli mcp-snippet
```

Скопируйте вывод в **`.cursor/mcp.json`** проекта 1С. В Cursor: **Settings → MCP → Reload**.

---

## Python CLI (все платформы)

```bash
pip install -e .

python -m syntaxcheck_mcp.cli install      # jar + docker build
python -m syntaxcheck_mcp.cli start        # запуск контейнера
python -m syntaxcheck_mcp.cli stop
python -m syntaxcheck_mcp.cli set-port 9000
python -m syntaxcheck_mcp.cli mcp-snippet
python -m syntaxcheck_mcp.cli test
python -m syntaxcheck_mcp.cli update-bsl   # проверить / обновить BSL LS
python -m syntaxcheck_mcp.cli update-bsl --check   # exit 1 если есть новая версия
python -m syntaxcheck_mcp.cli update-bsl --yes     # обновить без вопросов
```

Entry point: `syntaxcheck` (после `pip install -e .`).

---

## Обновление BSL Language Server

Версия по умолчанию задаётся в [`bsl.version`](bsl.version) (SSoT) и синхронизируется с `.env`.

```powershell
# Windows
.\scripts\update-bsl.ps1
```

```bash
# Linux / macOS
./scripts/update-bsl.sh
```

После обновления пересоберите образ:

```bash
python -m syntaxcheck_mcp.cli install
```

GitHub Actions (еженедельно) создаёт **Issue** с меткой `bsl-update`, если вышла новая версия BSL LS.

---

## Смена порта

```bash
python -m syntaxcheck_mcp.cli set-port 9000
docker compose down
python -m syntaxcheck_mcp.cli start
python -m syntaxcheck_mcp.cli mcp-snippet
```

Обновите `url` в `.cursor/mcp.json`.

---

## Настройки (`.env`)

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `SYNTAXCHECK_PORT` | `8010` | Порт на хосте |
| `BSL_VERSION` | `0.29.0` | Версия BSL LS (дублирует `bsl.version`) |
| `BSL_MEMORY_MB` | `2048` | Память JVM |
| `BSL_ANALYZE_TIMEOUT_SEC` | `120` | Таймаут анализа |

Правила диагностики — [`bsl-language-server.json`](bsl-language-server.json).

---

## Устранение неполадок

**Docker не запущен** → `docker info` должен работать без ошибок.

**Образ не собран** → `python -m syntaxcheck_mcp.cli install`.

**MCP красный в Cursor** → контейнер running, URL совпадает с портом, Reload MCP.

**Скачивание jar** → проверьте сеть; версия в `bsl.version` / `.env`.

---

## Архитектура

```
Cursor → HTTP /mcp → Python FastMCP → temp Module.bsl → BSL LS analyze → JSON
         ↑
    scripts/*.ps1 | scripts/*.sh → syntaxcheck_mcp.cli → docker compose
```

---

## Лицензия

MIT — см. [LICENSE](LICENSE).
