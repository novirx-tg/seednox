# 🛡 Seednox

> **Ваши сид-фразы всегда под нашей защитой!**

Open-source Telegram-бот для безопасного хранения сид-фраз криптокошельков.

[![Version](https://img.shields.io/badge/version-0.2.0-blue.svg)](https://github.com/novirx-tg/seednox/releases/tag/v0.2.0)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-green.svg)](https://python.org)
[![GitHub](https://img.shields.io/badge/GitHub-novirx--tg%2Fseednox-181717?logo=github)](https://github.com/novirx-tg/seednox)

## ✨ Возможности

- 🔐 **Шифрование AES-256-GCM** — сид-фразы никогда не хранятся в открытом виде
- 🔑 **Мастер-пароль** — один пароль для всех кошельков
- 👛 **Неограниченные кошельки** — добавляйте сколько угодно (до 100)
- 🔒 **Привязка к Telegram ID** — доступ только с вашего аккаунта
- ⏱ **Автоблокировка** — сессия закрывается при неактивности (по умолчанию 15 мин)
- 🚫 **Защита от брутфорса** — блокировка после 5 неверных попыток
- 🗑 **Автоудаление** — сообщения с паролем и сид-фразой удаляются
- 📖 **Open Source** — проверьте код сами!
- 🔢 **PIN** — второй фактор при разблокировке
- 🎭 **Duress-пароль** — ложные кошельки под принуждением
- 💾 **Бэкап / восстановление** — зашифрованные `.snx` файлы
- 📜 **Журнал активности** — аудит без чувствительных данных
- ✏️ **Заметки, поиск, переименование** кошельков
- 📤 **Экспорт** одного кошелька
- 🛡 **zxcvbn** — оценка силы пароля

## 🏗 Архитектура

```
Пользователь → Telegram → Seednox Bot
                              │
                    ┌─────────┴─────────┐
                    │   Session (RAM)   │  ← пароль только в памяти
                    └─────────┬─────────┘
                              │
                    ┌─────────┴─────────┐
                    │  SQLite (encrypted)│  ← только шифротекст
                    └───────────────────┘
```

## 🚀 Быстрый старт

### 1. Создайте бота

1. Напишите [@BotFather](https://t.me/BotFather) в Telegram
2. `/newbot` → имя: **Seednox**, username: `@seednoxbot`
3. Скопируйте токен

### 2. Установка

```bash
git clone https://github.com/novirx-tg/seednox.git
cd seednox

python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS

pip install -r requirements.txt
cp .env.example .env            # вставьте BOT_TOKEN
```

### 3. Запуск

```bash
python -m src.main
```

### Docker

```bash
cp .env.example .env
docker compose up -d
```

> **Важно:** данные хранятся в `./data/seednox.db` на диске.  
> Не используйте `docker compose down -v` — это не удалит `./data`, но старые Docker-volumes могли хранить БД отдельно.  
> При переключении local ↔ Docker всегда один файл: `data/seednox.db`.

## 📱 Использование

| Команда | Описание |
|---------|----------|
| `/start` | Главное меню |
| `/register` | Регистрация (новый пользователь) |
| `/unlock` | Разблокировать сейф |
| `/lock` | Заблокировать сейф |
| `/help` | Справка |

### Типичный сценарий

1. `/register` → создайте мастер-пароль
2. `➕ Добавить кошелёк` → название + сид-фраза
3. `📋 Мои кошельки` → просмотр / удаление
4. `🔒 Заблокировать` → когда закончили

## 🔒 Безопасность

Подробности в [SECURITY.md](SECURITY.md).

| Компонент | Технология |
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

**Seednox v0.2.0** — @seednoxbot · [GitHub](https://github.com/novirx-tg/seednox)
