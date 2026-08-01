# 🤝 Участие в проекте Seednox

Спасибо за интерес к Seednox! Это open-source проект, и мы ценим любой вклад.

---

## Как помочь

### 🔍 Аудит безопасности
Самый ценный вклад — проверка криптографии и логики безопасности:
- `src/crypto/` — шифрование (Argon2id + AES-256-GCM)
- `src/security/` — сессии, rate-limiting, валидация
- `src/bot/handlers/` — обработка чувствительных данных
- `src/database/repository.py` — хранение зашифрованных записей

### 🐛 Баг-репорты
Создавайте issue с описанием:
- Шаги воспроизведения
- Ожидаемое vs фактическое поведение
- Версия приложения (v1.0.2)
- ОС и версия Python

### 💡 Предложения
Обсуждайте в Issues перед реализацией крупных изменений.

### 🔧 Код
1. Fork репозитория: [github.com/novirx-tg/seednox](https://github.com/novirx-tg/seednox)
2. Создайте ветку: `git checkout -b feature/my-feature`
3. Следуйте стилю проекта (Python 3.11+, type hints, async/await)
4. Pull Request с описанием изменений

---

## Правила гигиены Git и приватности

- **Настройка git config**: Убедитесь, что ваше имя разработчика и публичный email заданы корректно перед созданием коммитов:
  ```bash
  git config user.name "Developer Name"
  git config user.email "username@users.noreply.github.com"
  ```
- **Приватность**: Для защиты личной электронной почты используйте анонимный `ID+username@users.noreply.github.com` адрес от GitHub (Settings -> Emails -> Keep my email addresses private).
- **Никогда** не коммитьте `.env`, токены, секреты, скомпилированные бинарники (`*.exe`, `*.zip`) или базы данных (`*.db`).
- Не добавляйте телеметрию или внешние запросы без обсуждения.
- Любой код, касающийся криптографии, требует подробного описания в PR и прохождения автотестов (`python -m unittest discover -s tests`).
- Чувствительные данные не должны попадать в логи.

---

## Локальная разработка v1.0.2

```bash
git clone https://github.com/novirx-tg/seednox.git
cd seednox

python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

pip install -r requirements.txt

# Запуск GUI Launcher
python -m src.gui.app

# Запуск только бота (без GUI)
cp .env.example .env          # заполните BOT_TOKEN
python -m src.main
```

---

## 🔗 Официальные ресурсы

- 📢 **Telegram-канал**: [@seednox](https://t.me/seednox)
- 🌐 **Официальный сайт**: [novirx.cyou/seednox/](https://novirx.cyou/seednox/)
- 🐙 **Исходный код**: [github.com/novirx-tg/seednox](https://github.com/novirx-tg/seednox)

---

Будьте уважительны. Мы строим инструмент для защиты ценных данных людей.
