# Релизы Seednox

Релизы публикуются на [GitHub Releases](https://github.com/novirx-tg/seednox/releases).

## Проверка целостности

1. Скачайте `SHA256SUMS.txt` из релиза
2. Проверьте хеши:

```bash
sha256sum -c SHA256SUMS.txt
```

## Docker (рекомендуется)

```bash
git clone https://github.com/novirx-tg/seednox.git
cd seednox
git checkout v0.2.0   # нужная версия
cp .env.example .env
docker compose up -d --build
```

## SQLCipher (опционально)

В `.env` добавьте длинный случайный ключ:

```env
DB_ENCRYPTION_KEY=ваш_случайный_ключ_32_символа_минимум
```

Требует `sqlcipher3` (автоматически в Docker).
