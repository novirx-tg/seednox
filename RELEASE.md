# 📦 Релизы Seednox

Все официальные релизы и сборки публикуются на странице [GitHub Releases](https://github.com/novirx-tg/seednox/releases).

---

## 🔗 Официальные ресурсы

- 📢 **Telegram-канал**: [@seednox](https://t.me/seednox)
- 🌐 **Официальный сайт**: [novirx.cyou/seednox/](https://novirx.cyou/seednox/)
- 🐙 **Исходный код на GitHub**: [github.com/novirx-tg/seednox](https://github.com/novirx-tg/seednox)

---

## 🗂 История релизов

### v1.0.1 — 2026-07-24
- ✅ Универсальное хранилище: сид-фразы, пароли, приватные ключи, заметки, прочее.
- 🛠 Исправлено сохранение `.env` — корректно работает и в `.exe`, и из исходников.
- 🔄 Автоматическая миграция БД (новая колонка `entry_type`).

### v1.0.0 — 2026-07-22
- Первый официальный релиз. GUI Launcher для Windows x64.
- Обход блокировок Telegram API, портативные `.snx` бэкапы, Docker/VPS поддержка.

---

## 💻 Установка — Windows x64 (готовый билд)

1. Перейдите на страницу [GitHub Releases](https://github.com/novirx-tg/seednox/releases/latest).
2. Скачайте архив `Seednox-v1.0.1-Windows-x64.zip`.
3. Распакуйте и запустите `Seednox-Windows-v1.0.1.exe`.
4. В разделе **«⚙️ Настройки»** вставьте `BOT_TOKEN` и нажмите **«💾 Сохранить»**.

> **Файл `.env` создаётся автоматически рядом с `.exe`** — все настройки сохраняются туда.

---

## 🐧🍎 Мультиплатформенность

Готовые бинарные сборки для **Windows x64** доступны уже сейчас.  
Сборки для **Linux** и **macOS** запланированы для следующих версий.

---

## ⚡ Docker (24/7 VPS)

```bash
git clone https://github.com/novirx-tg/seednox.git
cd seednox
git checkout v1.0.1
cp .env.example .env   # заполните BOT_TOKEN
docker compose up -d --build
```
