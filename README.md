# 1C Syntax Checker

MCP-сервер для проверки синтаксиса кода 1С (BSL) через [BSL Language Server](https://github.com/1c-syntax/bsl-language-server) **v0.29.0** (JDK 21).

Инструменты для Cursor и других MCP-клиентов — передаёте BSL, получаете JSON с ошибками и предупреждениями:

| Инструмент | Когда использовать |
|------------|--------------------|
| **`syntaxcheck(code, min_severity="HINT")`** | Отдельный фрагмент кода. |
| **`syntaxcheck_file(path, content=None, min_severity="HINT")`** | Один файл: `path` даёт BSL LS тип модуля, поэтому правила именования (CommonModule / ObjectModule / ManagerModule) применяются корректно. Если `content` не передан, сервер читает файл сам (локальная установка; внутри Docker передавайте `content`). |
| **`syntaxcheck_project(files, min_severity="HINT")`** | Пакетная проверка модулей. `files` — словарь `путь → код`. Пути сохраняются в диагностике; пустые файлы пропускаются. |
| **`bsl_list_rules(language="ru", filter=None)`** | Каталог правил из установленного JAR; список не означает, что все правила включены. |
| **`bsl_format_code(code)`** | Форматирование копии кода; исходный файл не изменяется. |

**`min_severity`** — минимальный уровень для вывода: `ERROR`, `WARNING`, `INFORMATION`, `HINT` (по умолчанию `HINT` показывает всё; `WARNING`/`ERROR` убирают стилистический шум для кода от ИИ). Ответ содержит `status`, счётчики `summary` по уровням, отфильтрованный список `diagnostics` (каждый с полем `file`) и человекочитаемый `summary_text`.

## Требования

- **Python 3.10+**
- **Docker Desktop** (Windows/macOS) или **Docker Engine** (Linux) — [скачать](https://www.docker.com/products/docker-desktop/)
- **~2 ГБ** свободного места (образ Docker + BSL jar ~110 МБ)

Java на компьютере **не нужна** — Temurin 21 и BSL LS работают внутри Docker.

### Запуск без Docker (Windows)

Нужна Java 21 в `PATH` (подойдёт переносимый JRE). Команды выполняются из корня репозитория:

```powershell
pip install -e ".[dev]"
python -m syntaxcheck_mcp.cli download-jar
$env:BSL_JAR = (Resolve-Path .\vendor\bsl-language-server.jar).Path
$env:BSL_CONFIG = (Resolve-Path .\bsl-language-server.json).Path
$env:MCP_HOST = "127.0.0.1"
$env:MCP_PORT = "8010"
python -m syntaxcheck_mcp
```

В другом терминале: `python -m syntaxcheck_mcp.cli test`.
Команда проверяет, что намеренно испорченный BSL возвращает `ParseError`, а не только HTTP 200.
Команды `install`, `start` и `stop` управляют Docker; для прямого запуска используется команда выше.

### Что проверяется и какие есть ограничения

- BSL LS проверяет синтаксис и правила статического анализа. Уровень `ERROR` включает также правила качества; это не синоним ошибки компиляции 1С.
- Проверка не заменяет проверку конфигурации платформой 1С: существование методов, реквизитов, справочников и корректность выполнения не гарантируются.
- Временное дерево содержит переданные исходники, но не полную конфигурацию и XML-метаданные. Сохранение путей помогает анализатору, однако полноценный контекст конфигурации и расширений не восстанавливается.
- Динамически собранные запросы могут давать `QueryParseError`, даже если сформированный при выполнении запрос корректен.
- `min_severity="ERROR"` скрывает предупреждения, включая `QueryParseError`; это фильтр уровня, а не режим «только синтаксис».
- Один вызов запускает новую JVM. Пакетная проверка обычно выгоднее отдельных вызовов на каждый модуль.
- Отсутствующий, повреждённый или нераспознанный JSON-отчёт возвращается как сбой анализа, а не как отсутствие ошибок.

### Проверка изменений

```powershell
python -m pytest tests/ -q
```

Без Java/`BSL_JAR` интеграционные тесты пропускаются. Чтобы запустить их, задайте `BSL_JAR`, `BSL_CONFIG` и добавьте Java в `PATH`, как при запуске без Docker, затем повторите команду.
Интеграционные тесты проверяют настоящий анализатор: корректный/некорректный BSL, сохранение путей двух модулей, форматирование и каталог правил.

Проверка от 10.11.2026 на BSL LS 0.29.0 / Java 21, без Docker: 41 модуль (35 непустых), 30 432 строки. Получено 2 986 диагностик: 305 ERROR, 810 WARNING, 708 INFORMATION, 1 163 HINT. `ParseError` не обнаружено; два `QueryParseError` относятся к динамически составляемым запросам. Контрольные примеры подтвердили обнаружение пропущенного выражения и незакрытой процедуры; несуществующий метод и справочник анализатор в режиме фрагмента не обнаружил. Эти цифры характеризуют конкретную выборку, а не полноту проверки произвольного кода 1С.

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
python -m syntaxcheck_mcp.cli update-bsl --offline --yes  # без GitHub API, jar по bsl.version
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
