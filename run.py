#!/usr/bin/env python3
"""Запуск Seednox бота из корневой папки проекта."""

import asyncio

from src.main import main

if __name__ == "__main__":
    asyncio.run(main())
