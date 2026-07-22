# Участие в проекте Seednox

Спасибо за интерес к Seednox! Это open-source проект, и мы ценим любой вклад.

## Как помочь

### 🔍 Аудит безопасности
Самый ценный вклад — проверка криптографии и логики безопасности:
- `src/crypto/` — шифрование и KDF
- `src/security/` — валидация, сессии, rate limiting
- `src/bot/handlers/` — обработка чувствительных данных

### 🐛 Баг-репорты
Создавайте issue с описанием:
- Шаги воспроизведения
- Ожидаемое vs фактическое поведение
- Версия бота

### 💡 Предложения
Обсуждайте в Issues перед крупными изменениями.

### 🔧 Код
1. Fork репозитория: [github.com/novirx-tg/seednox](https://github.com/novirx-tg/seednox)
2. Создайте ветку: `git checkout -b feature/my-feature`
3. Следуйте стилю проекта (Python 3.11+, type hints)
4. Pull Request с описанием изменений

## Правила

- **Никогда** не коммитьте `.env`, токены, базы данных
- Не добавляйте телеметрию или внешние запросы без обсуждения
- Любой код, касающийся криптографии, требует подробного описания в PR
- Чувствительные данные не должны попадать в логи

## Локальная разработка v1.0.0

```bash
git clone https://github.com/novirx-tg/seednox.git
cd seednox
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
python -m src.gui.app
```

---

## 🔗 Официальные ресурсы

- 📢 **Telegram-канал**: [@seednox](https://t.me/seednox)
- 🌐 **Официальный сайт**: [novirx.cyou/seednox/](https://novirx.cyou/seednox/)
- 🐙 **Исходный код**: [github.com/novirx-tg/seednox](https://github.com/novirx-tg/seednox)
