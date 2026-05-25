# Syntax-Checker

MCP-сервер для проверки синтаксиса кода 1С (BSL) через [BSL Language Server](https://github.com/1c-syntax/bsl-language-server).

Инструмент для Cursor и других MCP-клиентов: **`syntaxcheck(code)`** — передаёте фрагмент BSL, получаете JSON с ошибками и предупреждениями.

## Требования

- **Windows 10/11** (инструкция ниже для PowerShell)
- **Docker Desktop** — [скачать](https://www.docker.com/products/docker-desktop/)
  - В Settings → General включите **Use the WSL 2 based engine**
  - Перед запуском Docker должен быть в статусе **Running** (иконка кита в трее)
- **~2 ГБ** свободного места (образ Docker + BSL jar ~100 МБ)

Java на компьютере **не нужна** — всё работает внутри Docker.

---

## Быстрый старт (5 шагов)

### 1. Клонировать репозиторий

```powershell
git clone https://github.com/yavityai/Syntax-Checker.git
cd Syntax-Checker
```

### 2. Запустить Docker Desktop

Убедитесь, что команда работает без ошибок:

```powershell
docker info
```

Если видите `open //./pipe/dockerDesktopLinuxEngine` — Docker не запущен. Откройте Docker Desktop и подождите 1–2 минуты.

### 3. Установка (один раз)

Скачивает BSL Language Server и собирает Docker-образ (~5–15 минут при первом запуске):

```powershell
.\scripts\install.ps1
```

### 4. Запуск сервера

```powershell
.\scripts\start.ps1
```

По умолчанию MCP доступен по адресу:

**http://localhost:8010/mcp**

Проверка (опционально):

```powershell
.\scripts\test-syntaxcheck.ps1
```

### 5. Подключить в проект 1С (Cursor)

Сгенерируйте готовый фрагмент конфигурации:

```powershell
.\scripts\show-mcp-snippet.ps1
```

Скопируйте вывод в файл **`.cursor/mcp.json`** вашего проекта 1С (создайте папку `.cursor`, если её нет).

Пример для порта по умолчанию:

```json
{
  "mcpServers": {
    "1c-syntax-checker-mcp": {
      "url": "http://localhost:8010/mcp",
      "connection_id": "1c_lsp_service_001",
      "description": "BSL syntax validation via BSL Language Server"
    }
  }
}
```

В Cursor: **Settings → MCP → Reload**. Сервер `1c-syntax-checker-mcp` должен стать зелёным.

---

## Смена порта

Если порт **8010** занят:

```powershell
.\scripts\set-port.ps1 -Port 9000
docker compose down
.\scripts\start.ps1
.\scripts\show-mcp-snippet.ps1
```

Обновите `url` в `.cursor/mcp.json` — он должен совпадать с портом из `.env` (`SYNTAXCHECK_PORT`).

---

## Ежедневное использование

| Действие | Команда |
|----------|---------|
| Запустить сервер | `.\scripts\start.ps1` |
| Остановить | `docker compose down` |
| Логи | `docker compose logs -f` |
| Пересобрать после обновления кода | `.\scripts\install.ps1` |

После перезагрузки Windows сначала запустите **Docker Desktop**, затем `.\scripts\start.ps1`.

---

## Настройки (`.env`)

Скопируйте `.env.example` в `.env` (создаётся автоматически при `install.ps1`):

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `SYNTAXCHECK_PORT` | `8010` | Порт на хосте (`http://localhost:PORT/mcp`) |
| `BSL_VERSION` | `0.24.2` | Версия BSL Language Server |
| `BSL_MEMORY_MB` | `2048` | Память JVM для анализа |
| `BSL_ANALYZE_TIMEOUT_SEC` | `120` | Таймаут анализа (сек) |

Правила диагностики — в [`bsl-language-server.json`](bsl-language-server.json).

---

## Устранение неполадок

**Docker Desktop не запущен**
```
open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified
```
→ Запустите Docker Desktop, дождитесь **Running**, повторите команду.

**Образ не собран**
```
Docker image not built. Run .\scripts\install.ps1 first.
```
→ Выполните `.\scripts\install.ps1`.

**Порт занят**
→ `.\scripts\set-port.ps1 -Port <другой>` и обновите `.cursor/mcp.json`.

**MCP в Cursor красный**
→ Проверьте: `docker compose ps` (контейнер running), URL в `mcp.json` совпадает с портом, нажмите Reload в Settings → MCP.

**Скачивание BSL jar не удалось**
→ Проверьте интернет и `BSL_VERSION` в `.env`. Повторите `.\scripts\install.ps1`.

---

## Архитектура

```
Cursor → HTTP /mcp → Python FastMCP → temp Module.bsl → java -jar analyze → JSON
```

---

## Лицензия

MIT — см. [LICENSE](LICENSE).
