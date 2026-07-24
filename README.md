# 🛡 Seednox v1.0.1 — Personal Vault & Telegram Bot

> **Ваши секреты всегда под надёжной аметистовой защитой!**

Open-source графическое ПК-приложение (GUI Launcher) и Telegram-бот для **безопасного хранения любых секретных данных** — сид-фраз, паролей, приватных ключей, заметок и других чувствительных записей. Шифрование Argon2id + AES-256-GCM.

[![Version](https://img.shields.io/badge/version-1.0.1-purple.svg)](https://github.com/novirx-tg/seednox/releases/tag/v1.0.1)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-green.svg)](https://python.org)
[![GitHub](https://img.shields.io/badge/GitHub-novirx--tg%2Fseednox-181717?logo=github)](https://github.com/novirx-tg/seednox)

---

## 🔗 Официальные ресурсы

- 📢 **Telegram-канал**: [@seednox](https://t.me/seednox)
- 🌐 **Официальный сайт**: [novirx.cyou/seednox/](https://novirx.cyou/seednox/)
- 🐙 **Исходный код на GitHub**: [github.com/novirx-tg/seednox](https://github.com/novirx-tg/seednox)

---

## ✨ Ключевые возможности

- 🗄 **Универсальное хранилище** — храните не только сид-фразы, но и **пароли**, **приватные ключи**, **заметки** и **любые другие данные** — всё в зашифрованном виде.
- 🖥 **Графическое ПК-Приложение (GUI Launcher)** — управление сейфом, генерация бэкапов и запуск бота прямо с рабочего стола Windows.
- 🔐 **Шифрование AES-256-GCM & Argon2id KDF** — криптографическая защита всех записей, ключи хранятся исключительно в RAM во время активной сессии.
- 🌐 **Обход блокировок Telegram API** — встроенная поддержка HTTP / SOCKS5 прокси и кастомных зеркал Telegram API (для стабильной работы в РФ).
- ☁️ **Автономный 24/7 Хостинг (VPS / Docker)** — экспорт готового `.zip` пакета для развёртывания бота на сервере в 1 клик (рекомендуемый хостинг: **@ohoster** в Telegram).
- 📋 **Быстрый ввод** — правый клик на любом поле → контекстное меню, inline-кнопки вставки токенов/ID, переключатели видимости `👁`.
- 💾 **Портативный формат бэкапов `.snx`** — безопасная миграция и импорт/экспорт между устройствами.
- 🎭 **Duress-пароль & Stealth-режим** — ложный сейф при принуждении, автосброс запросов от неизвестных Telegram ID.

---

## 🗄 Типы записей (v1.0.1)

В версии 1.0.1 хранилище стало универсальным. При добавлении новой записи через Telegram-бота выберите тип:

| Тип | Описание |
|-----|----------|
| 🌱 **Сид-фраза** | BIP39 мнемоника (12/18/24 слова) |
| 🔑 **Пароль** | Пароль от аккаунта, кошелька, сервиса |
| 🗝 **Приватный ключ** | HEX или WIF приватный ключ |
| 📝 **Заметка** | Свободный текст любого размера |
| 📦 **Другое** | Любые другие чувствительные данные |

Все записи шифруются одинаково стойко — `AES-256-GCM` с ключом, производным через `Argon2id`.

---

## 🚀 Быстрый запуск

### Готовый билд для Windows x64

1. Скачайте архив `Seednox-v1.0.1-Windows-x64.zip` на странице [GitHub Releases](https://github.com/novirx-tg/seednox/releases/tag/v1.0.1).
2. Распакуйте и запустите `Seednox-Windows-v1.0.1.exe`.
3. В разделе **«⚙️ Настройки»** вставьте ваш `BOT_TOKEN` и нажмите **«💾 Сохранить»**.
4. Нажмите **«▶ Запустить бота»**.

> 💡 Файл `.env` создаётся автоматически рядом с `.exe` — все настройки сохраняются в нём.

### Запуск из исходного кода

```bash
git clone https://github.com/novirx-tg/seednox.git
cd seednox

python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS

pip install -r requirements.txt
python -m src.gui.app
```

### Docker (24/7 VPS)

```bash
cp .env.example .env            # заполните BOT_TOKEN
docker compose up -d --build
```

---

## 🔒 Безопасность и архитектура

| Компонент | Технология | Описание |
|-----------|------------|---------|
| **KDF** | `Argon2id` | `t=3, m=64MB, p=4`, соль `os.urandom(32)` |
| **Шифрование** | `AES-256-GCM` | 12-байтовый криптографический нонс на запись |
| **Сессии** | RAM-Only | Ключи дешифровки затираются при блокировке сейфа |
| **Бэкапы** | `SNX1` Portable | Бинарный magic-заголовок + embedded salt + GCM tag |
| **Доступ** | `ALLOWED_USER_IDS` | AccessControlMiddleware отбрасывает чужие запросы |

### ⚠️ Важно помнить

- **Потеря мастер-пароля = потеря доступа** ко всем записям навсегда.
- Telegram-боты не используют E2E шифрование. Для максимальной безопасности — **self-host** на своём сервере.
- Seednox — **хранилище**, а не кошелёк. Транзакции не подписываются.

---

## 📋 Changelog

### v1.0.1 (2026-07-24)
- ✅ **Универсальное хранилище** — добавлена поддержка 5 типов записей: сид-фразы, пароли, приватные ключи, заметки, прочее.
- 🛠 **Исправлено сохранение `.env`** — настройки теперь корректно сохраняются и при запуске из `.exe`, и из исходников.
- 🔄 Миграция базы данных: новая колонка `entry_type` добавляется автоматически к существующим записям.

### v1.0.0 (2026-07-22)
- 🖥 Первый официальный релиз с GUI Launcher для Windows x64.
- 🌐 Обход блокировок Telegram API (SOCKS5/HTTP прокси, зеркала API).
- 🔐 Дизайн с аметистовой темой, портативные `.snx` бэкапы, поддержка VPS/Docker.

---

## 📁 Структура проекта

```
seednox/
├── src/
│   ├── __init__.py          # Версия проекта
│   ├── main.py              # Точка входа (бот)
│   ├── config.py            # Pydantic-настройки из .env
│   ├── crypto/              # Шифрование (Argon2id + AES-GCM)
│   ├── security/            # Сессии, rate-limit, бэкапы
│   ├── database/            # SQLite репозиторий + модели
│   └── bot/
│       ├── handlers/        # Обработчики команд и FSM
│       ├── keyboards.py     # Клавиатуры
│       ├── middlewares.py   # AccessControlMiddleware
│       └── states.py        # FSM-состояния
├── src/gui/
│   └── app.py               # GUI Launcher (CustomTkinter)
├── Dockerfile
├── docker-compose.yml
├── SECURITY.md
├── CONTRIBUTING.md
└── LICENSE
```

---

## 📄 Лицензия

Проект распространяется под лицензией [MIT](LICENSE). Используйте свободно, но на свой страх и риск.

---

**Seednox v1.0.1** — [@seednox](https://t.me/seednox) · [Сайт](https://novirx.cyou/seednox/) · [GitHub](https://github.com/novirx-tg/seednox)
