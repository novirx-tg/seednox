# 🛡 Seednox v1.0.0 — Personal Vault & Telegram Bot

> **Ваши сид-фразы всегда под надежной аметистовой защитой!**

Open-source графическое ПК-приложение (GUI Launcher) и Telegram-бот для безопасного хранения и управления сид-фразами криптокошельков с Argon2id + AES-256-GCM шифрованием.

[![Version](https://img.shields.io/badge/version-1.0.0-purple.svg)](https://github.com/novirx-tg/seednox/releases/tag/v1.0.0)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-green.svg)](https://python.org)
[![GitHub](https://img.shields.io/badge/GitHub-novirx--tg%2Fseednox-181717?logo=github)](https://github.com/novirx-tg/seednox)

---

## 🔗 Официальные ресурсы

- 📢 **Telegram-канал**: [@seednox](https://t.me/seednox)
- 🌐 **Официальный сайт**: [novirx.cyou/seednox/](https://novirx.cyou/seednox/)
- 🐙 **Исходный код на GitHub**: [github.com/novirx-tg/seednox](https://github.com/novirx-tg/seednox)

---

## ✨ Ключевые возможности v1.0.0

- 🖥 **Графическое ПК-Приложение (GUI Launcher)** — управление сейфом, генерация бэкапов и запуск бота с рабочего стола.
- 🔐 **Шифрование AES-256-GCM & Argon2id KDF** — криптографическая защита сид-фраз, ключи хранятся исключительно в RAM во время активной сессии.
- 🌐 **Обход блокировок Telegram API** — встроенная поддержка HTTP / SOCKS5 прокси и кастомных зеркал Telegram API (для стабильной работы в РФ).
- ☁️ **Автономный 24/7 Хостинг (VPS / Docker)** — возможность экспорта готового `.zip` пакета для развертывания бота на сервере в 1 клик (рекомендуемый хостинг: **@ohoster** в Telegram).
- 📋 **Интерактивные контекстные меню и быстрый ввод** — выпадающее меню по правому клику мыши на любых полях ввода, мгновенная вставка токенов/ID и кнопки переключения видимости `👁`.
- 💾 **Портативный формат бэкапов `.snx`** — безопасная миграция и импорт/экспорт кошельков между устройствами.
- 🎭 **Duress-пароль & Stealth-режим** — ложный сейф при принуждении и автоматический отброс запросов от неизвестных Telegram ID.

---

## 🚀 Быстрый запуск

### Запуск через ПК-Приложение (Windows x64)

1. Скачайте готовый архив `Seednox-v1.0.0-Windows-x64.zip` на странице [GitHub Releases](https://github.com/novirx-tg/seednox/releases/tag/v1.0.0).
2. Распакуйте и запустите `Seednox-Windows-v1.0.0.exe`.
3. Укажите свой **BOT_TOKEN** в разделе **«⚙️ Настройки»** и нажмите **«▶ Запустить бота»**.

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

---

## 🔒 Безопасность и Архитектура

| Компонент | Технология | Описание |
|---|---|---|
| **KDF** | `Argon2id` | `t=3, m=64MB, p=4` с 32-байтовой случайной солью |
| **Шифрование** | `AES-256-GCM` | 12-байтовый криптографический нонс на запись |
| **Сессии** | RAM-Only | Ключи дешифрования затираются при закрытии сейфа |
| **Бэкапы** | `SNX1` Portable | Бинарный маджик-заголовок + проверка целостности |

---

## 📄 Лицензия

Проект распространяется под лицензией [MIT](LICENSE). 

**Seednox v1.0.0** — [@seednox](https://t.me/seednox) · [Сайт](https://novirx.cyou/seednox/) · [GitHub](https://github.com/novirx-tg/seednox)нология |
|-----------|------------|
| KDF | Argon2id |
| Шифрование | AES-256-GCM |
| Key derivation | HKDF-SHA256 |
| Хеш пароля | Argon2id |
| БД | SQLite (WAL mode) |

### ⚠️ Важно

- **Потеря пароля = потеря доступа** к сид-фразам навсегда
- Для максимальной безопасности — **self-host** на своём сервере
- Telegram-боты не используют E2E шифрование
- Seednox — **хранилище**, не кошелёк

## 🤝 Open Source

Проект открыт для аудита и вклада сообщества:

- [GitHub — novirx-tg/seednox](https://github.com/novirx-tg/seednox) — исходный код
- [CONTRIBUTING.md](CONTRIBUTING.md) — как помочь проекту
- [SECURITY.md](SECURITY.md) — политика безопасности
- Проверяйте `src/crypto/` — ядро шифрования

## 📁 Структура проекта

```
seednox/
├── src/
│   ├── main.py              # Точка входа
│   ├── config.py            # Настройки
│   ├── crypto/              # Шифрование (Argon2 + AES-GCM)
│   ├── security/            # Сессии, rate limit, валидация
│   ├── database/            # SQLite репозиторий
│   └── bot/
│       ├── handlers/        # Обработчики команд
│       ├── keyboards.py     # Клавиатуры
│       ├── middlewares.py   # Безопасность
│       └── states.py        # FSM состояния
├── Dockerfile
├── docker-compose.yml
├── SECURITY.md
├── CONTRIBUTING.md
└── LICENSE
```

## 📄 Лицензия

[MIT](LICENSE) — используйте свободно, но на свой страх и риск.

---

**Seednox v1.0.0** — [@seednox](https://t.me/seednox) · [Сайт](https://novirx.cyou/seednox/) · [GitHub](https://github.com/novirx-tg/seednox)
