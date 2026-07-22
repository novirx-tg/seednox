import os
import sys
import subprocess
import threading
import queue
import logging

logger = logging.getLogger(__name__)

class BotLauncher:
    """Класс для управления процессом Telegram-бота в отдельном подпроцессе."""

    def __init__(self, log_queue: queue.Queue) -> None:
        self.log_queue = log_queue
        self.process: subprocess.Popen | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def is_running(self) -> bool:
        """Проверить, запущен ли бот."""
        return self.process is not None and self.process.poll() is None

    def start(self) -> bool:
        """Запустить бота в подпроцессе."""
        if self.is_running():
            return False

        self._stop_event.clear()
        
        # Настройка переменных окружения для правильного кодирования вывода
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"

        try:
            # Запуск бота через тот же интерпретатор Python
            self.process = subprocess.Popen(
                [sys.executable, "-m", "src.main"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                env=env,
                bufsize=1, # Построчная буферизация
            )
        except Exception as e:
            logger.exception("Ошибка при запуске подпроцесса бота")
            self.log_queue.put(f"❌ Ошибка запуска: {e}\n")
            return False

        # Поток для чтения логов из stdout подпроцесса
        self._thread = threading.Thread(target=self._read_logs, daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        """Остановить процесс бота."""
        if not self.is_running():
            return

        self._stop_event.set()
        try:
            # Отправляем сигнал мягкого завершения (SIGTERM на Linux/macOS, CTRL_BREAK/SIGTERM на Windows)
            # На Windows terminate() работает как TerminateProcess, но aiogram также корректно завершает работу.
            self.process.terminate()
            try:
                # Ожидаем завершения процесса до 5 секунд
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Если не завершился сам, убиваем принудительно
                self.process.kill()
        except Exception as e:
            logger.exception("Ошибка при остановке процесса бота")
            self.log_queue.put(f"⚠️ Ошибка при остановке: {e}\n")
        finally:
            self.process = None

    def _read_logs(self) -> None:
        """Метод для чтения вывода процесса в фоновом режиме."""
        if not self.process or not self.process.stdout:
            return

        while not self._stop_event.is_set():
            line = self.process.stdout.readline()
            if not line:
                break
            # Передаем строчку лога в очередь GUI
            self.log_queue.put(line)

        # Ожидаем завершения процесса, если он еще жив
        if self.process:
            self.process.wait()
            self.log_queue.put(f"ℹ️ Процесс бота завершился с кодом {self.process.returncode}\n")
            self.process = None
