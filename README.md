<p align="center">
  <a href="https://normahub.cc">
    <img src="./docs/images/logo.png" alt="NormaHub" width="120" />
  </a>
</p>

# normahub-cli

[![Release](https://img.shields.io/badge/release-v1.0.0-blue?style=flat-square)](https://github.com/normahubcc/normahub-cli/releases)
[![Python](https://img.shields.io/badge/python-3.9+-blue?style=flat-square)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)

Локальный AI Gateway демон с SQLite-кэшированием, авто-маршрутизатором моделей и патчером IDE для API [NormaHub](https://normahub.cc).

Шлюз поднимает локальный прокси (`127.0.0.1:8000`), эмулирующий протоколы **OpenAI** и **Ollama**, перенаправляя запросы к моделям (DeepSeek, Claude, GPT, Qwen, SeeDance) через единый API без необходимости VPN.

---

## Архитектура

```mermaid
flowchart LR
    IDE["IDE / Агент (Cursor, Cline, Python SDK, Ollama)"] -->|OpenAI / Ollama Wire| Gateway["normahub-cli (127.0.0.1:8000)"]
    Gateway --> Cache["SQLite Cache"]
    Cache -->|Cache Miss| Router["Model Router (normahub/auto)"]
    Router --> NormaHub["NormaHub Cloud API"]
    Cache -.->|Cache Hit (0 ms, 0 ₽)| Gateway
```

---

## Возможности

- **Zero dependencies:** написан строго на стандартной библиотеке Python 3.9+ (`http.server`, `urllib`, `sqlite3`, `asyncio`). Работает без установки сторонних пакетов.
- **Два протокола:**
  - OpenAI-совместимый (`/v1/chat/completions`, `/v1/models`, `/v1/responses`) для Cursor, Cline, Continue, Aider и `openai-python`.
  - Ollama-совместимый (`/api/chat`, `/api/generate`, `/api/tags`) для Open WebUI и локальных тулов.
- **Локальный SQLite кэш:** детерминированное SHA-256 хеширование запросов. Повторные идентичные промпты отдаются мгновенно без обращения к сети и без списания средств.
- **Маршрутизация `normahub/auto`:** эвристический анализ сложности промпта (код, длинный контекст, простые реплики) для выбора оптимальной модели по соотношению цена/качество.
- **1-Click IDE Patcher:** автоматическая настройка конфигураций Cursor, Cline, OpenCode и Claude Desktop.
- **Локальный Web UI:** веб-интерфейс на `http://127.0.0.1:8000/ui` для ручного тестирования моделей и мониторинга метрик кэша.

---

## Установка

```bash
pip install normahub-cli
```

Или запуск из исходников:

```bash
git clone https://github.com/normahubcc/normahub-cli.git
cd normahub-cli
pip install .
```

---

## Быстрый старт

### 1. Настройка ключа

Задайте ключ из личного кабинета [normahub.cc](https://normahub.cc):

```bash
export NORMAHUB_API_KEY="nr_hub_..."
```

### 2. Запуск демона

```bash
normahub start
```

Демон запустится на порту 8000:
- OpenAI эндпоинт: `http://127.0.0.1:8000/v1`
- Ollama эндпоинт: `http://127.0.0.1:8000/api`
- Web UI: `http://127.0.0.1:8000/ui`

---

## Подключение клиентов

### Cursor IDE

Автоматическая настройка:

```bash
normahub setup cursor
```

Либо вручную в настройках Cursor (**Settings > Models > OpenAI API**):
- **Base URL:** `http://127.0.0.1:8000/v1`
- **API Key:** `normahub` (любая строка)
- **Model:** `normahub/auto` или конкретная модель из каталога

### Cline / Roo-Code

```bash
normahub setup cline
```

Или выберите провайдер **OpenAI Compatible**:
- **Base URL:** `http://127.0.0.1:8000/v1`
- **API Key:** `normahub`
- **Model ID:** `normahub/auto`

### Python OpenAI SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:8000/v1",
    api_key="normahub"
)

response = client.chat.completions.create(
    model="normahub/auto",
    messages=[{"role": "user", "content": "Напиши функцию quicksort на Python"}],
)

print(response.choices[0].message.content)
```

---

## Команды CLI

| Команда | Описание |
|---|---|
| `normahub start [-p 8000]` | Запуск локального gateway-сервера |
| `normahub setup [cursor \| cline \| opencode \| claude \| all]` | Автоматическая настройка конфигов IDE |
| `normahub models` | Вывод списка поддерживаемых моделей и тарифов |
| `normahub stats` | Статистика кэша и сэкономленных токенов |

---

## Docker

```bash
docker run -d \
  -p 8000:8000 \
  -e NORMAHUB_API_KEY="nr_hub_..." \
  -v ~/.normahub:/root/.normahub \
  --name normahub-gateway \
  normahubcc/normahub-cli:latest
```

---

## Лицензия

MIT License. См. [LICENSE](LICENSE).
