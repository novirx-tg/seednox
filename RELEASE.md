# 📦 Релизы Seednox

Все официальные релизы и сборки публикуются на странице [GitHub Releases](https://github.com/novirx-tg/seednox/releases).

---

## 🔗 Официальные ресурсы

- 📢 **Telegram-канал**: [@seednox](https://t.me/seednox)
- 🌐 **Официальный сайт**: [novirx.cyou/seednox/](https://novirx.cyou/seednox/)
- 🐙 **Исходный код на GitHub**: [github.com/novirx-tg/seednox](https://github.com/novirx-tg/seednox)

---

## 🗂 История релизов

### v1.0.3 — 2026-09-06
- 🚨 **OpSec & Правдоподобное отрицание (Plausible Deniability)**: унифицирована запись в журнал аудита при входе под принуждением (`unlock` вместо раскрывающего `unlock_duress`).
- ⏳ **Устранение UI Freeze при импорте бэкапов**:
  - Внедрен формат бэкапа `SNX2` с сохраненными метаданными KDF в заголовке, исключающий тяжелый перебор параметров KDF наугад.
  - Дешифрование и импорт бэкапов перенесены в асинхронный фоновый поток (`threading.Thread` в GUI и `asyncio.to_thread` в Telegram-боте).
- 🔑 **Защита от RAM-атак (Zeroize RAM)**:
  - Пароли сессий и мастер-пароль хранятся в изменяемом `bytearray`.
  - Реализовано зануление байтов (`0x00`) при блокировке сейфа или закрытии сессии с принудительным `gc.collect()`.
- 🌱 **Полноценная валидация BIP-39**:
  - Встроен официальный английский словарь BIP-39 (2048 слов).
  - Реализована строгая проверка контрольной суммы мнемоник (SHA-256 checksum).
- ⚙️ **Исправление сборщика Windows**:
  - Устранена ошибка `ModuleNotFoundError: No module named 'pydantic'` путем внедрения `collect_all('pydantic')` и `collect_all('pydantic_settings')` в PyInstaller spec-файл.
- 🚀 **Официальный Установщик**: выпущен `Seednox-Setup-v1.0.3.exe`.

### v1.0.2 — 2026-08-01
- 🚀 **Официальный Установщик Windows (Setup Wizard)**: добавлен `Seednox-Setup-v1.0.2.exe` для автоматической установки с деинсталлятором.
- 🛡 **Комплексный фикс уязвимостей (PR #2 & Аудит)**:
  - Fail-safe защита `SQLCipher` при заданном `DB_ENCRYPTION_KEY`.
  - Усиленный контроль доступа Telegram-бота (`ALLOWED_USER_IDS`).
  - Запуск Docker от non-root пользователя `appuser`.
- 🧪 **CI Quality Gate**: 100% покрытие автотестами (`pytest` / `unittest`) в каталоге `tests/`.
- 📦 Закрепление точных версий зависимостей в `requirements.txt` и очистка Git от бинарников.

### v1.0.1 — 2026-07-24
- ✅ Универсальное хранилище: сид-фразы, пароли, приватные ключи, заметки, прочее.
- 🛠 Исправлено сохранение `.env` — корректно работает и в `.exe`, и из исходников.
- 🔄 Автоматическая миграция БД (новая колонка `entry_type`).

### v1.0.0 — 2026-07-22
- Первый официальный релиз. GUI Launcher для Windows x64.
- Обход блокировок Telegram API, портативные `.snx` бэкапы, Docker/VPS поддержка.

---

## 💻 Установка — Windows x64

### Вариант 1. Установочный мастер (Рекомендуется)
1. Перейдите на страницу [GitHub Releases v1.0.3](https://github.com/novirx-tg/seednox/releases/tag/v1.0.3).
2. Скачайте программу установки `Seednox-Setup-v1.0.3.exe`.
3. Запустите инсталлятор и следуйте подсказкам мастера.

### Вариант 2. Портативная версией (.zip)
1. Скачайте архив `Seednox-v1.0.3-Windows-x64.zip` и `SHA256SUMS.txt`.
2. Сверьте хеш в PowerShell:
   ```powershell
   Get-FileHash Seednox-v1.0.3-Windows-x64.zip -Algorithm SHA256
   ```
3. Распакуйте и запустите `Seednox-Windows-v1.0.3.exe`.

> **Самостоятельная сборка из исходников**:
> ```powershell
> pip install -r requirements.txt pyinstaller pillow
> pyinstaller Seednox-Windows-v1.0.3.spec
> iscc Seednox-Setup.iss
> ```

---

## ⚡ Docker (24/7 VPS)

```bash
git clone https://github.com/novirx-tg/seednox.git
cd seednox
git checkout v1.0.3
cp .env.example .env   # заполните BOT_TOKEN
docker compose up -d --build
```
