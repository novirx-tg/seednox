import os
import sys
import asyncio
import queue
import logging
import shutil
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

# Подключаем модули проекта
from src.config import get_settings, PROJECT_ROOT
from src.database.repository import Repository
from src.crypto import (
    generate_salt,
    hash_password,
    verify_password,
    encrypt_seed,
    decrypt_seed,
)
from src.security.backup import (
    create_encrypted_backup,
    decrypt_backup_file,
    wallet_to_backup_item,
    backup_item_to_bytes,
)
from src.gui.launcher_worker import BotLauncher

# Настройка системного логгера
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Цветовая палитра на основе оригинального аметистово-сливового логотипа Seednox
COLOR_BG_DARK = "#120B16"       # Глубокий тёмно-сливовый фон
COLOR_SIDEBAR = "#1A0F21"       # Бархатно-фиолетовая боковая панель
COLOR_CARD = "#25152C"          # Аметистовые карточки
COLOR_CARD_HOVER = "#331C3C"    # Ховер карточек
COLOR_INPUT = "#201226"         # Поля ввода
COLOR_ACCENT = "#9B4B92"        # Пурпурный акцент (в тон логотипа)
COLOR_ACCENT_HOVER = "#B45AA9"  # Акцент при наведении
COLOR_TEXT = "#F7EFF6"          # Светло-перламутровый текст
COLOR_TEXT_MUTED = "#A890A6"    # Приглушенный сиреневый текст
COLOR_SUCCESS = "#10B981"       # Изумрудно-зеленый
COLOR_ERROR = "#F43F5E"         # Кораллово-розовый
COLOR_WARNING = "#F59E0B"       # Янтарно-золотой
COLOR_BORDER = "#44264A"        # Тонкий аметистовый контур

def load_logo_image(size: tuple[int, int]) -> ctk.CTkImage | None:
    """Загружает очищенный логотип приложения из папки assets."""
    try:
        from PIL import Image
        candidates = [
            PROJECT_ROOT / "assets" / "logo_clean.png",
            PROJECT_ROOT / "assets" / "photo_2026-06-08_09-07-36.jpg",
        ]
        logo_path = next((p for p in candidates if p.exists()), None)
        if not logo_path:
            for root_dir, _, files in os.walk(str(PROJECT_ROOT)):
                for f in files:
                    if f == 'logo_clean.png':
                        logo_path = Path(root_dir) / f
                        break
                if logo_path:
                    break

        if logo_path and logo_path.exists():
            img = Image.open(logo_path).convert("RGBA")
            if logo_path.suffix.lower() in ['.jpg', '.jpeg']:
                data = img.load()
                w, h = img.size
                for y in range(h):
                    for x in range(w):
                        r, g, b, a = data[x, y]
                        if r > 230 and g > 230 and b > 230:
                            data[x, y] = (0, 0, 0, 0)
                clean_path = logo_path.parent / "logo_clean.png"
                try:
                    img.save(clean_path, "PNG")
                except Exception:
                    pass

            return ctk.CTkImage(light_image=img, dark_image=img, size=size)
    except Exception as e:
        logger.warning("Не удалось загрузить логотип: %s", e)
    return None

def make_entry_context_menu(widget) -> None:
    """Добавляет контекстное меню по правому клику мыши и поддержку вставки для любых раскладок."""
    def show_menu(event):
        menu = tk.Menu(widget, tearoff=0, bg="#25152C", fg="#F7EFF6", activebackground="#9B4B92", activeforeground="#FFFFFF")
        
        def paste():
            try:
                clip = widget.clipboard_get()
                if isinstance(widget, ctk.CTkEntry):
                    try:
                        if widget.selection_get():
                            widget.delete("sel.first", "sel.last")
                    except Exception:
                        pass
                    widget.insert(tk.INSERT, clip)
                elif isinstance(widget, ctk.CTkTextbox):
                    widget.insert(tk.INSERT, clip)
            except Exception:
                pass

        def copy():
            try:
                text = ""
                if isinstance(widget, ctk.CTkEntry):
                    text = widget.get()
                    try:
                        sel = widget.selection_get()
                        if sel: text = sel
                    except Exception:
                        pass
                elif isinstance(widget, ctk.CTkTextbox):
                    try: sel = widget.get(tk.SEL_FIRST, tk.SEL_LAST)
                    except Exception: sel = ""
                    text = sel
                if text:
                    widget.clipboard_clear()
                    widget.clipboard_append(text)
            except Exception:
                pass

        def cut():
            copy()
            try:
                if isinstance(widget, ctk.CTkEntry):
                    try:
                        if widget.selection_get():
                            widget.delete("sel.first", "sel.last")
                        else:
                            widget.delete(0, tk.END)
                    except Exception:
                        widget.delete(0, tk.END)
                elif isinstance(widget, ctk.CTkTextbox):
                    try:
                        widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
                    except Exception:
                        widget.delete("1.0", tk.END)
            except Exception:
                pass

        def clear():
            try:
                if isinstance(widget, ctk.CTkEntry):
                    widget.delete(0, tk.END)
                elif isinstance(widget, ctk.CTkTextbox):
                    widget.delete("1.0", tk.END)
            except Exception:
                pass

        def select_all():
            try:
                if isinstance(widget, ctk.CTkEntry):
                    widget.select_range(0, tk.END)
                elif isinstance(widget, ctk.CTkTextbox):
                    widget.tag_add(tk.SEL, "1.0", tk.END)
            except Exception:
                pass

        menu.add_command(label="📋  Вставить (Paste)", command=paste)
        menu.add_command(label="📄  Копировать (Copy)", command=copy)
        menu.add_command(label="✂️  Вырезать (Cut)", command=cut)
        menu.add_separator()
        menu.add_command(label="🔘  Выделить всё (Select All)", command=select_all)
        menu.add_command(label="🧹  Очистить (Clear)", command=clear)

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    # Правый клик мыши
    try:
        widget.bind("<Button-3>", show_menu)
    except Exception:
        pass

    # Горячие клавиши для вставки
    def handle_paste(event):
        try:
            clip = widget.clipboard_get()
            if isinstance(widget, ctk.CTkEntry):
                try:
                    if widget.selection_get():
                        widget.delete("sel.first", "sel.last")
                except Exception:
                    pass
                widget.insert(tk.INSERT, clip)
            return "break"
        except Exception:
            pass

    for seq in ["<Control-v>", "<Control-V>", "<Control-Key-v>", "<Control-Key-V>"]:
        try:
            widget.bind(seq, handle_paste)
        except Exception:
            pass

def run_async(coro):
    """Синхронный хелпер для запуска асинхронных корутин из Tkinter."""
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        loop.close()

class SeednoxApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        # Конфигурация окна
        self.title("Seednox — PC Launcher & Local Vault v1.0.2")
        self.geometry("1000x650")
        self.minsize(760, 520)

        # Установка темы
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Переменные состояния
        self.settings = get_settings()
        self.log_queue = queue.Queue()
        self.launcher = BotLauncher(self.log_queue)

        # Состояние локального сейфа
        self.vault_unlocked = False
        self.vault_password = None
        self.vault_user_id = None
        self.vault_salt = None
        self.active_wallet = None

        # Инициализация репозитория базы данных
        db_key = (
            self.settings.db_encryption_key.get_secret_value()
            if self.settings.db_encryption_key
            else None
        )
        self.repo = Repository(self.settings.database_path, encryption_key=db_key)
        try:
            run_async(self.repo.connect())
        except Exception as e:
            logger.exception("Ошибка подключения к базе данных")
            # Освобождаем дескрипторы перед попыткой перемещения
            try:
                run_async(self.repo.close())
            except Exception:
                pass

            err_msg = str(e).lower()
            if "file is not a database" in err_msg or "databaseerror" in err_msg:
                import time
                timestamp = int(time.time())
                corrupted_path = self.settings.database_path.with_name(f"seednox_invalid_{timestamp}.bak")
                moved = False
                try:
                    if self.settings.database_path.exists():
                        shutil.move(str(self.settings.database_path), str(corrupted_path))
                        moved = True
                except Exception:
                    pass

                if not moved:
                    # Если файл заблокирован другими процессами, переключаемся на новый путь
                    self.settings.database_path = self.settings.database_path.with_name(f"seednox_vault_{timestamp}.db")

                # Переподключаемся к чистой базе данных
                self.repo = Repository(self.settings.database_path, encryption_key=db_key)
                run_async(self.repo.connect())

                messagebox.showwarning(
                    "База данных не распознана",
                    f"Файл не является валидной базой данных SQLite.\n\n"
                    f"Инициализирована новая рабочая база данных по пути:\n'{self.settings.database_path.name}'\n\n"
                    f"Вы можете восстановить свои кошельки из файла .snx в разделе 'Бэкапы'."
                )
            else:
                raise

        # Сетка главного окна: 2 колонки (боковое меню и основной контент)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Создание интерфейса
        self._create_sidebar()
        if hasattr(self, "logo_small") and self.logo_small:
            try:
                self.wm_iconphoto(True, self.logo_small._light_image)
            except Exception:
                pass
        self._create_pages()

        # По умолчанию открываем лаунчер
        self._select_page("launcher")

        # Начать опрос очереди логов подпроцесса бота
        self.after(100, self._process_logs)

    def _create_sidebar(self) -> None:
        """Создает левую боковую панель навигации."""
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=COLOR_SIDEBAR)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(6, weight=1)

        # Загрузка логотипов разных размеров
        self.logo_small = load_logo_image((36, 36))
        self.logo_medium = load_logo_image((64, 64))
        self.logo_large = load_logo_image((96, 96))

        # Фрейм шапки бокового меню
        header_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=15, pady=(20, 15), sticky="ew")

        if self.logo_small:
            lbl_logo_icon = ctk.CTkLabel(header_frame, image=self.logo_small, text="")
            lbl_logo_icon.pack(side="left", padx=(0, 10))
        else:
            lbl_logo_icon = ctk.CTkLabel(header_frame, text="🛡", font=ctk.CTkFont(size=24))
            lbl_logo_icon.pack(side="left", padx=(0, 10))

        title_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_box.pack(side="left", fill="both", expand=True)

        logo_label = ctk.CTkLabel(
            title_box,
            text="SEEDNOX",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=COLOR_TEXT,
            anchor="w"
        )
        logo_label.pack(anchor="w")

        sub_label = ctk.CTkLabel(
            title_box,
            text="Personal Vault & Bot",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=COLOR_TEXT_MUTED,
            anchor="w"
        )
        sub_label.pack(anchor="w")

        # Разделитель
        sep = ctk.CTkFrame(self.sidebar, fg_color=COLOR_BORDER, height=1)
        sep.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="ew")

        # Кнопки меню
        self.nav_buttons = {}
        menu_items = [
            ("launcher", "🚀  Лаунчер бота"),
            ("vault", "🔐  Локальный Сейф"),
            ("server", "🌐  Сервер / Хостинг"),
            ("settings", "⚙️  Настройки"),
            ("backup", "💾  Бэкапы"),
        ]

        for i, (page_name, label) in enumerate(menu_items):
            btn = ctk.CTkButton(
                self.sidebar,
                text=label,
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                height=42,
                corner_radius=8,
                fg_color="transparent",
                text_color=COLOR_TEXT_MUTED,
                hover_color=COLOR_CARD_HOVER,
                anchor="w",
                command=lambda p=page_name: self._select_page(p)
            )
            btn.grid(row=i+2, column=0, padx=12, pady=4, sticky="ew")
            self.nav_buttons[page_name] = btn

        # Официальные ссылки проекта внизу бокового меню
        links_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        links_frame.grid(row=7, column=0, padx=10, pady=(10, 10), sticky="ew")
        links_frame.grid_columnconfigure((0, 1, 2), weight=1)

        import webbrowser

        btn_tg = ctk.CTkButton(
            links_frame,
            text="📢 @seednox",
            font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
            height=26,
            fg_color="transparent",
            border_width=1,
            border_color=COLOR_BORDER,
            text_color=COLOR_TEXT_MUTED,
            hover_color=COLOR_CARD_HOVER,
            command=lambda: webbrowser.open("https://t.me/seednox")
        )
        btn_tg.grid(row=0, column=0, padx=2, sticky="ew")

        btn_site = ctk.CTkButton(
            links_frame,
            text="🌐 Сайт",
            font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
            height=26,
            fg_color="transparent",
            border_width=1,
            border_color=COLOR_BORDER,
            text_color=COLOR_TEXT_MUTED,
            hover_color=COLOR_CARD_HOVER,
            command=lambda: webbrowser.open("https://novirx.cyou/seednox/")
        )
        btn_site.grid(row=0, column=1, padx=2, sticky="ew")

        btn_gh = ctk.CTkButton(
            links_frame,
            text="🐙 GitHub",
            font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
            height=26,
            fg_color="transparent",
            border_width=1,
            border_color=COLOR_BORDER,
            text_color=COLOR_TEXT_MUTED,
            hover_color=COLOR_CARD_HOVER,
            command=lambda: webbrowser.open("https://github.com/novirx-tg/seednox")
        )
        btn_gh.grid(row=0, column=2, padx=2, sticky="ew")

        # Информация о версии внизу
        license_label = ctk.CTkLabel(
            self.sidebar,
            text="Seednox v1.0.2 • Open Source",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=COLOR_TEXT_MUTED
        )
        license_label.grid(row=8, column=0, padx=20, pady=(0, 15), sticky="s")

    def _create_pages(self) -> None:
        """Создает фреймы страниц на правой панели."""
        self.container = ctk.CTkFrame(self, fg_color=COLOR_BG_DARK, corner_radius=0)
        self.container.grid(row=0, column=1, sticky="nsew")
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(0, weight=1)

        self.pages = {}

        # 1. Страница Лаунчера
        self.pages["launcher"] = ctk.CTkFrame(self.container, fg_color="transparent")
        self._init_launcher_page(self.pages["launcher"])

        # 2. Страница Сейфа
        self.pages["vault"] = ctk.CTkFrame(self.container, fg_color="transparent")
        self._init_vault_page(self.pages["vault"])

        # 3. Страница Хостинга / Сервера
        self.pages["server"] = ctk.CTkFrame(self.container, fg_color="transparent")
        self._init_server_page(self.pages["server"])

        # 4. Страница Настроек
        self.pages["settings"] = ctk.CTkFrame(self.container, fg_color="transparent")
        self._init_settings_page(self.pages["settings"])

        # 5. Страница Бэкапов
        self.pages["backup"] = ctk.CTkFrame(self.container, fg_color="transparent")
        self._init_backup_page(self.pages["backup"])

    def _select_page(self, page_name: str) -> None:
        """Переключает активный фрейм страницы."""
        # Сброс подсветки кнопок
        for name, btn in self.nav_buttons.items():
            if name == page_name:
                btn.configure(fg_color=COLOR_ACCENT, text_color=COLOR_TEXT)
            else:
                btn.configure(fg_color="transparent", text_color=COLOR_TEXT_MUTED)

        # Скрытие всех страниц и отображение выбранной
        for name, frame in self.pages.items():
            if name == page_name:
                frame.grid(row=0, column=0, sticky="nsew", padx=25, pady=20)
                # Если перешли на сейф, обновляем отображение
                if name == "vault":
                    self._update_vault_ui()
                elif name == "launcher":
                    self._refresh_launcher_stats()
            else:
                frame.grid_forget()

    # --- СТРАНИЦА ЛАУНЧЕРА ---
    def _init_launcher_page(self, frame: ctk.CTkFrame) -> None:
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)

        # Верхняя панель управления и статуса
        top_bar = ctk.CTkFrame(
            frame,
            fg_color=COLOR_CARD,
            border_color=COLOR_BORDER,
            border_width=1,
            height=90,
            corner_radius=12
        )
        top_bar.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        top_bar.grid_columnconfigure(2, weight=1)

        # Логотип в шапке лаунчера
        if hasattr(self, "logo_medium") and self.logo_medium:
            lbl_hero_logo = ctk.CTkLabel(top_bar, image=self.logo_medium, text="")
            lbl_hero_logo.grid(row=0, column=0, padx=(20, 10), pady=15)
            col_offset = 1
        else:
            col_offset = 0

        # Индикатор статуса
        status_box = ctk.CTkFrame(top_bar, fg_color="transparent")
        status_box.grid(row=0, column=col_offset, padx=(10, 20), pady=15, sticky="w")

        self.status_indicator = ctk.CTkLabel(
            status_box,
            text="⬤",
            font=ctk.CTkFont(size=14),
            text_color=COLOR_ERROR
        )
        self.status_indicator.pack(side="left", padx=(0, 6))

        self.status_text = ctk.CTkLabel(
            status_box,
            text="Бот: Остановлен",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=COLOR_TEXT
        )
        self.status_text.pack(side="left")

        # Кнопки Старт / Стоп
        self.btn_start_bot = ctk.CTkButton(
            top_bar,
            text="▶  Запустить бота",
            fg_color=COLOR_SUCCESS,
            hover_color="#059669",
            height=40,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            command=self._start_bot
        )
        self.btn_start_bot.grid(row=0, column=3, padx=10, pady=15)

        self.btn_stop_bot = ctk.CTkButton(
            top_bar,
            text="⏹  Остановить",
            fg_color=COLOR_ERROR,
            hover_color="#dc2626",
            height=40,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            state="disabled",
            command=self._stop_bot
        )
        self.btn_stop_bot.grid(row=0, column=4, padx=(0, 20), pady=15)

        # Панель вывода логов
        log_frame = ctk.CTkFrame(
            frame,
            fg_color=COLOR_CARD,
            border_color=COLOR_BORDER,
            border_width=1,
            corner_radius=12
        )
        log_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 15))
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(1, weight=1)

        log_header = ctk.CTkFrame(log_frame, fg_color="transparent")
        log_header.grid(row=0, column=0, padx=20, pady=(15, 5), sticky="ew")
        log_header.grid_columnconfigure(0, weight=1)

        log_title = ctk.CTkLabel(
            log_header,
            text="🖥  Консоль логов Telegram-бота",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=COLOR_TEXT
        )
        log_title.grid(row=0, column=0, sticky="w")

        self.log_text = ctk.CTkTextbox(
            log_frame,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color="#0D0610",
            text_color="#A7F3D0",
            border_color=COLOR_BORDER,
            border_width=1,
            wrap="word",
        )
        self.log_text.grid(row=1, column=0, padx=15, pady=10, sticky="nsew")
        self.log_text.configure(state="disabled")

        # Нижняя панель статистики базы данных
        self.stats_panel = ctk.CTkFrame(
            frame,
            fg_color=COLOR_CARD,
            border_color=COLOR_BORDER,
            border_width=1,
            height=60,
            corner_radius=12
        )
        self.stats_panel.grid(row=2, column=0, sticky="ew")

        # Левая часть - счетчики БД
        stats_left = ctk.CTkFrame(self.stats_panel, fg_color="transparent")
        stats_left.pack(side="left", padx=15, pady=10)

        self.lbl_stats_users = ctk.CTkLabel(
            stats_left,
            text="👥  Пользователей в БД: 0",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=COLOR_TEXT_MUTED
        )
        self.lbl_stats_users.pack(side="left", padx=(0, 15))

        self.lbl_stats_wallets = ctk.CTkLabel(
            stats_left,
            text="👛  Кошельков в БД: 0",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=COLOR_TEXT_MUTED
        )
        self.lbl_stats_wallets.pack(side="left")

        # Правая часть - кнопки действия и ссылок
        stats_right = ctk.CTkFrame(self.stats_panel, fg_color="transparent")
        stats_right.pack(side="right", padx=15, pady=10)

        btn_refresh_stats = ctk.CTkButton(
            stats_right,
            text="🔄  Обновить",
            fg_color="transparent",
            border_width=1,
            border_color=COLOR_BORDER,
            text_color=COLOR_TEXT,
            hover_color=COLOR_CARD_HOVER,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            command=self._refresh_launcher_stats
        )
        btn_refresh_stats.pack(side="left", padx=(0, 6))

        btn_links_tg = ctk.CTkButton(
            stats_right,
            text="📢 @seednox",
            fg_color="transparent",
            border_width=1,
            border_color=COLOR_BORDER,
            text_color=COLOR_TEXT,
            hover_color=COLOR_CARD_HOVER,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=lambda: webbrowser.open("https://t.me/seednox")
        )
        btn_links_tg.pack(side="left", padx=2)

        btn_links_site = ctk.CTkButton(
            stats_right,
            text="🌐 Сайт",
            fg_color="transparent",
            border_width=1,
            border_color=COLOR_BORDER,
            text_color=COLOR_TEXT,
            hover_color=COLOR_CARD_HOVER,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=lambda: webbrowser.open("https://novirx.cyou/seednox/")
        )
        btn_links_site.pack(side="left", padx=2)

        btn_links_gh = ctk.CTkButton(
            stats_right,
            text="🐙 GitHub",
            fg_color="transparent",
            border_width=1,
            border_color=COLOR_BORDER,
            text_color=COLOR_TEXT,
            hover_color=COLOR_CARD_HOVER,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=lambda: webbrowser.open("https://github.com/novirx-tg/seednox")
        )
        btn_links_gh.pack(side="left", padx=2)

    def _start_bot(self) -> None:
        """Обработчик кнопки Запустить."""
        # Проверяем наличие токена перед запуском
        if not self.settings.bot_token.get_secret_value():
            # Попробуем считать из .env напрямую
            token = os.getenv("BOT_TOKEN", "").strip()
            if not token:
                messagebox.showerror(
                    "Ошибка конфигурации",
                    "Токен бота не задан. Перейдите во вкладку 'Настройки' и укажите BOT_TOKEN."
                )
                return

        self.log_text.configure(state="normal")
        self.log_text.insert("end", "⏳ Запуск процесса бота...\n")
        self.log_text.configure(state="disabled")

        if self.launcher.start():
            self.status_indicator.configure(text_color=COLOR_SUCCESS)
            self.status_text.configure(text="Бот: Работает")
            self.btn_start_bot.configure(state="disabled")
            self.btn_stop_bot.configure(state="normal")

    def _stop_bot(self) -> None:
        """Обработчик кнопки Остановить."""
        self.log_text.configure(state="normal")
        self.log_text.insert("end", "⏳ Остановка процесса бота...\n")
        self.log_text.configure(state="disabled")

        self.launcher.stop()
        self.status_indicator.configure(text_color=COLOR_ERROR)
        self.status_text.configure(text="Бот: Остановлен")
        self.btn_start_bot.configure(state="normal")
        self.btn_stop_bot.configure(state="disabled")

    def _process_logs(self) -> None:
        """Опрашивает очередь логов подпроцесса и вставляет в консоль."""
        try:
            while True:
                line = self.log_queue.get_nowait()
                self.log_text.configure(state="normal")
                self.log_text.insert("end", line)
                # Ограничение размера лога в консоли
                if float(self.log_text.index("end-1c")) > 2000:
                    self.log_text.delete("1.0", "50.0")
                self.log_text.see("end")
                self.log_text.configure(state="disabled")
                self.log_queue.task_done()
        except queue.Empty:
            pass

        # Если бот упал сам, переключаем кнопки
        if not self.launcher.is_running() and self.btn_stop_bot.cget("state") == "normal":
            self.status_indicator.configure(text_color=COLOR_ERROR)
            self.status_text.configure(text="Бот: Остановлен")
            self.btn_start_bot.configure(state="normal")
            self.btn_stop_bot.configure(state="disabled")

        self.after(100, self._process_logs)

    def _refresh_launcher_stats(self) -> None:
        """Обновляет статистику БД."""
        try:
            stats = run_async(self.repo.get_stats())
            self.lbl_stats_users.configure(text=f"Пользователей в БД: {stats['users']}")
            self.lbl_stats_wallets.configure(text=f"Кошельков в БД: {stats['wallets']}")
        except Exception as e:
            logger.exception("Ошибка обновления статистики")

    # --- СТРАНИЦА ЛОКАЛЬНОГО СЕЙФА ---
    def _init_vault_page(self, frame: ctk.CTkFrame) -> None:
        self.vault_frame = frame
        # Дизайн будет динамически перерисовываться в зависимости от авторизации (метод _update_vault_ui)

    def _update_vault_ui(self) -> None:
        """Перерисовывает страницу сейфа в зависимости от авторизации."""
        for widget in self.vault_frame.winfo_children():
            widget.destroy()

        if not self.vault_unlocked:
            self._draw_vault_login()
        else:
            self._draw_vault_dashboard()

    def _draw_vault_login(self) -> None:
        """Отрисовывает интерфейс входа в сейф."""
        self.vault_frame.grid_columnconfigure(0, weight=1)
        self.vault_frame.grid_rowconfigure((0, 1, 2), weight=1)

        card = ctk.CTkFrame(
            self.vault_frame,
            fg_color=COLOR_CARD,
            border_color=COLOR_BORDER,
            border_width=1,
            width=480,
            corner_radius=16
        )
        card.grid(row=1, column=0, sticky="n", pady=30)
        card.grid_columnconfigure(0, weight=1)

        # Отображение фирменного логотипа
        if hasattr(self, "logo_large") and self.logo_large:
            logo_img_lbl = ctk.CTkLabel(card, image=self.logo_large, text="")
            logo_img_lbl.grid(row=0, column=0, padx=30, pady=(30, 10))
            row_start = 1
        else:
            row_start = 0

        title = ctk.CTkLabel(
            card,
            text="🔐  Вход в локальный сейф",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=COLOR_TEXT
        )
        title.grid(row=row_start, column=0, padx=30, pady=(5, 5))

        desc = ctk.CTkLabel(
            card,
            text="Введите ваш мастер-пароль для безопасного дешифрования данных.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=COLOR_TEXT_MUTED,
            wraplength=380
        )
        desc.grid(row=row_start+1, column=0, padx=30, pady=(0, 20))

        # Выбор Telegram ID
        ctk.CTkLabel(
            card,
            text="Telegram ID пользователя:",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=COLOR_TEXT
        ).grid(row=row_start+2, column=0, padx=30, sticky="w", pady=(0, 2))

        # Загружаем список пользователей
        try:
            # Делаем простой запрос в БД для получения зарегистрированных telegram_id
            cursor = run_async(self.repo._connection.execute("SELECT telegram_id FROM users"))
            rows = run_async(cursor.fetchall())
            user_ids = [str(r["telegram_id"]) for r in rows]
        except Exception:
            user_ids = []

        if not user_ids:
            # Если пользователей нет, пишем предупреждение и показываем кнопку "Регистрация"
            desc.configure(text="База данных пуста. Зарегистрируйте новый локальный профиль.")
            self.entry_user_id = ctk.CTkEntry(
                card,
                placeholder_text="Ваш Telegram ID (например, 123456)",
                fg_color=COLOR_INPUT,
                border_color=COLOR_BORDER,
                font=ctk.CTkFont(size=12)
            )
            self.entry_user_id.grid(row=row_start+3, column=0, padx=30, pady=(0, 15), sticky="ew")
            make_entry_context_menu(self.entry_user_id)
        else:
            self.combo_user_id = ctk.CTkComboBox(
                card,
                values=user_ids,
                fg_color=COLOR_INPUT,
                border_color=COLOR_BORDER,
                button_color=COLOR_ACCENT,
                button_hover_color=COLOR_ACCENT_HOVER,
                font=ctk.CTkFont(size=12)
            )
            self.combo_user_id.grid(row=row_start+3, column=0, padx=30, pady=(0, 15), sticky="ew")
            # Если есть в настройках allowed_user_ids, выберем первый
            if self.settings.allowed_user_ids and str(self.settings.allowed_user_ids[0]) in user_ids:
                self.combo_user_id.set(str(self.settings.allowed_user_ids[0]))

        # Пароль
        ctk.CTkLabel(
            card,
            text="Мастер-пароль:",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=COLOR_TEXT
        ).grid(row=row_start+4, column=0, padx=30, sticky="w", pady=(0, 2))

        self.entry_password = ctk.CTkEntry(
            card,
            placeholder_text="Мастер-пароль",
            show="•",
            fg_color=COLOR_INPUT,
            border_color=COLOR_BORDER,
            font=ctk.CTkFont(size=12)
        )
        self.entry_password.grid(row=row_start+5, column=0, padx=30, pady=(0, 25), sticky="ew")
        make_entry_context_menu(self.entry_password)

        # Кнопки действий
        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.grid(row=row_start+6, column=0, padx=30, pady=(0, 30), sticky="ew")
        btn_frame.grid_columnconfigure((0, 1), weight=1)

        if not user_ids:
            btn_action = ctk.CTkButton(
                btn_frame,
                text="Регистрация сейфа",
                fg_color=COLOR_SUCCESS,
                hover_color="#059669",
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                command=self._vault_register
            )
            btn_action.grid(row=0, column=0, columnspan=2, sticky="ew")
        else:
            btn_login = ctk.CTkButton(
                btn_frame,
                text="Разблокировать",
                fg_color=COLOR_ACCENT,
                hover_color=COLOR_ACCENT_HOVER,
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                command=self._vault_login
            )
            btn_login.grid(row=0, column=0, padx=(0, 10), sticky="ew")

            btn_register = ctk.CTkButton(
                btn_frame,
                text="Создать профиль",
                fg_color="transparent",
                border_width=1,
                border_color=COLOR_TEXT_MUTED,
                text_color=COLOR_TEXT,
                hover_color=COLOR_SIDEBAR,
                font=ctk.CTkFont(family="Segoe UI", size=12),
                command=self._switch_to_registration
            )
            btn_register.grid(row=0, column=1, padx=(10, 0), sticky="ew")

    def _switch_to_registration(self) -> None:
        """Переключает окно в режим создания нового профиля (если база не пуста)."""
        # Просто перерисовываем, имитируя пустую БД для принудительного ввода нового user_id
        for widget in self.vault_frame.winfo_children():
            widget.destroy()

        self.vault_frame.grid_columnconfigure(0, weight=1)
        self.vault_frame.grid_rowconfigure((0, 1, 2), weight=1)

        card = ctk.CTkFrame(self.vault_frame, fg_color=COLOR_CARD, width=450, height=380, corner_radius=12)
        card.grid(row=1, column=0, sticky="n", pady=50)
        card.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            card,
            text="➕ Создать новый сейф",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=COLOR_TEXT
        )
        title.grid(row=0, column=0, padx=30, pady=(30, 10))

        desc = ctk.CTkLabel(
            card,
            text="Создайте локальный шифрованный профиль для нового Telegram ID.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=COLOR_TEXT_MUTED,
            wraplength=380
        )
        desc.grid(row=1, column=0, padx=30, pady=(0, 20))

        ctk.CTkLabel(
            card,
            text="Telegram ID:",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=COLOR_TEXT
        ).grid(row=2, column=0, padx=30, sticky="w", pady=(0, 2))

        self.entry_user_id = ctk.CTkEntry(
            card,
            placeholder_text="Telegram ID (например, 987654321)",
            font=ctk.CTkFont(size=12)
        )
        self.entry_user_id.grid(row=3, column=0, padx=30, pady=(0, 15), sticky="ew")

        ctk.CTkLabel(
            card,
            text="Новый мастер-пароль:",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=COLOR_TEXT
        ).grid(row=4, column=0, padx=30, sticky="w", pady=(0, 2))

        self.entry_password = ctk.CTkEntry(
            card,
            placeholder_text="Мастер-пароль (минимум 12 символов)",
            show="•",
            font=ctk.CTkFont(size=12)
        )
        self.entry_password.grid(row=5, column=0, padx=30, pady=(0, 20), sticky="ew")

        # Кнопки
        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.grid(row=6, column=0, padx=30, pady=(0, 30), sticky="ew")
        btn_frame.grid_columnconfigure((0, 1), weight=1)

        btn_action = ctk.CTkButton(
            btn_frame,
            text="Зарегистрировать",
            fg_color=COLOR_SUCCESS,
            hover_color="#059669",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=self._vault_register
        )
        btn_action.grid(row=0, column=0, padx=(0, 10), sticky="ew")

        btn_cancel = ctk.CTkButton(
            btn_frame,
            text="Назад",
            fg_color="transparent",
            border_width=1,
            border_color=COLOR_TEXT_MUTED,
            text_color=COLOR_TEXT,
            hover_color=COLOR_SIDEBAR,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            command=self._update_vault_ui
        )
        btn_cancel.grid(row=0, column=1, padx=(10, 0), sticky="ew")

    def _vault_register(self) -> None:
        """Выполняет регистрацию нового пользователя."""
        try:
            tg_id_str = self.entry_user_id.get().strip()
            password = self.entry_password.get()

            if not tg_id_str.isdigit():
                messagebox.showerror("Ошибка ввода", "Telegram ID должен быть числом.")
                return

            if len(password) < 12:
                messagebox.showerror("Слишком простой пароль", "Мастер-пароль должен быть длиной не менее 12 символов.")
                return

            tg_id = int(tg_id_str)
            # Проверим, существует ли уже
            user_exists = run_async(self.repo.user_exists(tg_id))
            if user_exists:
                messagebox.showerror("Ошибка", f"Пользователь с Telegram ID {tg_id} уже зарегистрирован.")
                return

            salt = generate_salt()
            password_hash = hash_password(password)

            run_async(self.repo.create_user(tg_id, password_hash, salt))
            messagebox.showinfo("Успех", f"Профиль {tg_id} успешно создан! Теперь вы можете войти.")
            self._update_vault_ui()

        except Exception as e:
            logger.exception("Ошибка при регистрации профиля")
            messagebox.showerror("Ошибка регистрации", str(e))

    def _vault_login(self) -> None:
        """Проверяет мастер-пароль и открывает сейф."""
        try:
            tg_id_str = self.combo_user_id.get().strip()
            password = self.entry_password.get()

            if not tg_id_str:
                return

            tg_id = int(tg_id_str)
            user = run_async(self.repo.get_user(tg_id))
            if not user:
                messagebox.showerror("Ошибка", "Пользователь не найден.")
                return

            if not verify_password(user.password_hash, password):
                messagebox.showerror("Ошибка доступа", "Неверный мастер-пароль.")
                return

            # Успешный вход
            self.vault_unlocked = True
            self.vault_password = password
            self.vault_user_id = tg_id
            self.vault_salt = user.salt
            self.active_wallet = None

            self._update_vault_ui()

        except Exception as e:
            logger.exception("Ошибка авторизации в сейфе")
            messagebox.showerror("Ошибка входа", str(e))

    def _vault_lock(self) -> None:
        """Стирает ключи из памяти и закрывает сейф."""
        self.vault_unlocked = False
        self.vault_password = None
        self.vault_user_id = None
        self.vault_salt = None
        self.active_wallet = None
        self._update_vault_ui()

    def _draw_vault_dashboard(self) -> None:
        """Отрисовывает интерфейс управления кошельками (после входа)."""
        self.vault_frame.grid_columnconfigure(0, weight=1)
        self.vault_frame.grid_columnconfigure(1, weight=1)
        self.vault_frame.grid_rowconfigure(0, weight=0)
        self.vault_frame.grid_rowconfigure(1, weight=1)

        # Верхняя плашка
        header_bar = ctk.CTkFrame(self.vault_frame, fg_color=COLOR_CARD, height=50, corner_radius=8)
        header_bar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 15))
        header_bar.grid_columnconfigure(1, weight=1)

        user_info = ctk.CTkLabel(
            header_bar,
            text=f"🔑 Локальный сейф открыт: Telegram ID = {self.vault_user_id}",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=COLOR_SUCCESS
        )
        user_info.grid(row=0, column=0, padx=15, pady=10)

        btn_lock = ctk.CTkButton(
            header_bar,
            text="🔒 Заблокировать сейф",
            fg_color="transparent",
            border_width=1,
            border_color=COLOR_ERROR,
            text_color=COLOR_ERROR,
            hover_color="#3a1a1a",
            width=150,
            command=self._vault_lock
        )
        btn_lock.grid(row=0, column=2, padx=15, pady=10, sticky="e")

        # Левая колонка: Список кошельков + поиск
        left_pane = ctk.CTkFrame(self.vault_frame, fg_color=COLOR_CARD, corner_radius=10)
        left_pane.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        left_pane.grid_columnconfigure(0, weight=1)
        left_pane.grid_rowconfigure(2, weight=1)

        search_frame = ctk.CTkFrame(left_pane, fg_color="transparent")
        search_frame.grid(row=0, column=0, padx=15, pady=(15, 10), sticky="ew")
        search_frame.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Поиск кошелька..."
        )
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.search_entry.bind("<KeyRelease>", lambda event: self._load_wallets())
        make_entry_context_menu(self.search_entry)

        # Кнопки действий: Добавить, Экспорт .snx, Импорт .snx
        action_btn_frame = ctk.CTkFrame(left_pane, fg_color="transparent")
        action_btn_frame.grid(row=1, column=0, padx=15, pady=(0, 10), sticky="ew")
        action_btn_frame.grid_columnconfigure((0, 1, 2), weight=1)

        btn_add = ctk.CTkButton(
            action_btn_frame,
            text="➕ Добавить",
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=self._show_add_wallet_dialog
        )
        btn_add.grid(row=0, column=0, padx=(0, 3), sticky="ew")

        btn_export = ctk.CTkButton(
            action_btn_frame,
            text="📦 Экспорт .snx",
            fg_color="transparent",
            border_width=1,
            border_color=COLOR_SUCCESS,
            text_color=COLOR_SUCCESS,
            hover_color="#133026",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=self._export_snx_backup
        )
        btn_export.grid(row=0, column=1, padx=2, sticky="ew")

        btn_import = ctk.CTkButton(
            action_btn_frame,
            text="📥 Импорт .snx",
            fg_color="transparent",
            border_width=1,
            border_color=COLOR_WARNING,
            text_color=COLOR_WARNING,
            hover_color="#3a2e18",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=self._import_snx_backup
        )
        btn_import.grid(row=0, column=2, padx=(3, 0), sticky="ew")

        # Список в CTkScrollableFrame
        self.wallets_scrollable = ctk.CTkScrollableFrame(left_pane, fg_color="#181a1d")
        self.wallets_scrollable.grid(row=2, column=0, padx=15, pady=(0, 15), sticky="nsew")

        # Правая колонка: Детальная информация
        self.right_pane = ctk.CTkFrame(self.vault_frame, fg_color=COLOR_CARD, corner_radius=10)
        self.right_pane.grid(row=1, column=1, sticky="nsew", padx=(10, 0))
        self.right_pane.grid_columnconfigure(0, weight=1)
        
        self._update_details_pane()

        # Первичная загрузка списка кошельков
        self._load_wallets()

    def _load_wallets(self) -> None:
        """Считывает кошельки из БД и отрисовывает их в левом меню."""
        for widget in self.wallets_scrollable.winfo_children():
            widget.destroy()

        search_term = self.search_entry.get().strip() or None

        try:
            wallets = run_async(self.repo.get_wallets(self.vault_user_id, search=search_term))
        except Exception as e:
            logger.exception("Ошибка при загрузке списка кошельков")
            return

        if not wallets:
            lbl_empty = ctk.CTkLabel(
                self.wallets_scrollable,
                text="Кошельки не найдены",
                font=ctk.CTkFont(size=12, slant="italic"),
                text_color=COLOR_TEXT_MUTED
            )
            lbl_empty.pack(pady=20)
            return

        for wallet in wallets:
            # Создаем строчку кошелька
            row_frame = ctk.CTkFrame(self.wallets_scrollable, fg_color=COLOR_CARD, height=45, corner_radius=6)
            row_frame.pack(fill="x", pady=4, ipady=5)
            row_frame.pack_propagate(False)

            lbl_name = ctk.CTkLabel(
                row_frame,
                text=wallet.name,
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                text_color=COLOR_TEXT
            )
            lbl_name.pack(side="left", padx=15)

            # Кнопка "Открыть" справа
            btn_open = ctk.CTkButton(
                row_frame,
                text="Открыть",
                fg_color="transparent",
                border_width=1,
                border_color=COLOR_ACCENT,
                text_color=COLOR_TEXT,
                hover_color=COLOR_ACCENT_HOVER,
                width=70,
                height=26,
                command=lambda w=wallet: self._select_wallet(w)
            )
            btn_open.pack(side="right", padx=10)

    def _select_wallet(self, wallet) -> None:
        self.active_wallet = wallet
        self._update_details_pane()

    def _update_details_pane(self) -> None:
        """Перерисовывает правую панель с деталями выбранного кошелька."""
        for widget in self.right_pane.winfo_children():
            widget.destroy()

        if not self.active_wallet:
            # Состояние "Ничего не выбрано"
            self.right_pane.grid_rowconfigure(0, weight=1)
            lbl_select = ctk.CTkLabel(
                self.right_pane,
                text="Выберите кошелёк из списка для просмотра деталей",
                font=ctk.CTkFont(family="Segoe UI", size=12, slant="italic"),
                text_color=COLOR_TEXT_MUTED
            )
            lbl_select.grid(row=0, column=0, sticky="nsew")
            return

        self.right_pane.grid_rowconfigure(0, weight=0)
        self.right_pane.grid_rowconfigure(1, weight=1)

        # Расшифровываем сид и заметку
        try:
            decrypted_seed = decrypt_seed(self.active_wallet.encrypted_seed, self.vault_password, self.vault_salt)
            if self.active_wallet.encrypted_note:
                decrypted_note = decrypt_seed(self.active_wallet.encrypted_note, self.vault_password, self.vault_salt)
            else:
                decrypted_note = ""
        except Exception as e:
            logger.exception("Ошибка расшифрования кошелька")
            decrypted_seed = "❌ Ошибка дешифрования!"
            decrypted_note = "❌ Ошибка дешифрования!"

        # Карточка кошелька
        content_frame = ctk.CTkFrame(self.right_pane, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Название
        name_lbl = ctk.CTkLabel(
            content_frame,
            text=self.active_wallet.name,
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=COLOR_TEXT
        )
        name_lbl.pack(anchor="w", pady=(0, 20))

        # Поле сид-фразы
        ctk.CTkLabel(
            content_frame,
            text="🔑 Сид-фраза:",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=COLOR_TEXT
        ).pack(anchor="w", pady=(0, 5))

        self.seed_textbox = ctk.CTkTextbox(
            content_frame,
            height=80,
            fg_color="#181a1d",
            font=ctk.CTkFont(family="Consolas", size=12),
            wrap="word"
        )
        self.seed_textbox.pack(fill="x", pady=(0, 10))
        self._set_seed_text_hidden(decrypted_seed)

        # Ряд управления показом сид-фразы
        seed_btn_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        seed_btn_frame.pack(fill="x", pady=(0, 20))

        self.seed_visible = False
        self.btn_toggle_seed = ctk.CTkButton(
            seed_btn_frame,
            text="👁 Показать фразу",
            fg_color="transparent",
            border_width=1,
            border_color=COLOR_TEXT_MUTED,
            text_color=COLOR_TEXT,
            hover_color=COLOR_CARD,
            width=130,
            command=lambda: self._toggle_seed_visibility(decrypted_seed)
        )
        self.btn_toggle_seed.pack(side="left")

        btn_copy = ctk.CTkButton(
            seed_btn_frame,
            text="📋 Копировать",
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            width=120,
            command=lambda: self._copy_to_clipboard(decrypted_seed)
        )
        btn_copy.pack(side="left", padx=10)

        # Заметка к кошельку
        ctk.CTkLabel(
            content_frame,
            text="📝 Заметка / Описание:",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=COLOR_TEXT
        ).pack(anchor="w", pady=(0, 5))

        self.note_textbox = ctk.CTkTextbox(
            content_frame,
            height=120,
            fg_color="#181a1d",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            wrap="word"
        )
        self.note_textbox.pack(fill="both", expand=True, pady=(0, 20))
        self.note_textbox.insert("1.0", decrypted_note)

        # Нижняя панель действий (Удаление / Сохранение заметки)
        action_bar = ctk.CTkFrame(content_frame, fg_color="transparent")
        action_bar.pack(fill="x", side="bottom")

        btn_save_note = ctk.CTkButton(
            action_bar,
            text="💾 Сохранить заметку",
            fg_color=COLOR_SUCCESS,
            hover_color="#059669",
            command=lambda: self._save_note(decrypted_note)
        )
        btn_save_note.pack(side="left")

        btn_delete = ctk.CTkButton(
            action_bar,
            text="🗑 Удалить кошелёк",
            fg_color=COLOR_ERROR,
            hover_color="#dc2626",
            command=self._delete_wallet
        )
        btn_delete.pack(side="right")

    def _set_seed_text_hidden(self, phrase: str) -> None:
        self.seed_textbox.configure(state="normal")
        self.seed_textbox.delete("1.0", "end")
        words_count = len(phrase.split())
        self.seed_textbox.insert("1.0", " ".join(["••••••"] * (words_count if words_count > 0 else 12)))
        self.seed_textbox.configure(state="disabled")

    def _toggle_seed_visibility(self, phrase: str) -> None:
        self.seed_visible = not self.seed_visible
        self.seed_textbox.configure(state="normal")
        self.seed_textbox.delete("1.0", "end")
        if self.seed_visible:
            self.seed_textbox.insert("1.0", phrase)
            self.btn_toggle_seed.configure(text="🙈 Скрыть фразу")
        else:
            self._set_seed_text_hidden(phrase)
            self.btn_toggle_seed.configure(text="👁 Показать фразу")
        self.seed_textbox.configure(state="disabled")

    def _copy_to_clipboard(self, text: str) -> None:
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("Успех", "Сид-фраза успешно скопирована в буфер обмена!")

    def _save_note(self, old_note: str) -> None:
        """Перезаписывает зашифрованную заметку в БД."""
        new_note = self.note_textbox.get("1.0", "end-1c").strip()
        if new_note == old_note:
            return

        try:
            enc_note = encrypt_seed(new_note, self.vault_password, self.vault_salt) if new_note else None
            success = run_async(self.repo.update_wallet_note(self.active_wallet.id, self.vault_user_id, enc_note))
            if success:
                # Обновим активный кошелек локально
                self.active_wallet.encrypted_note = enc_note
                messagebox.showinfo("Успех", "Заметка кошелька сохранена!")
                self._update_details_pane()
        except Exception as e:
            logger.exception("Ошибка при сохранении заметки")
            messagebox.showerror("Ошибка", str(e))

    def _delete_wallet(self) -> None:
        """Удаляет кошелек из базы данных после подтверждения."""
        if not messagebox.askyesno(
            "Подтверждение",
            f"Вы уверены, что хотите удалить кошелёк '{self.active_wallet.name}'?\nЭто действие необратимо!"
        ):
            return

        try:
            success = run_async(self.repo.delete_wallet(self.active_wallet.id, self.vault_user_id))
            if success:
                messagebox.showinfo("Успех", "Кошелек удален.")
                self.active_wallet = None
                self._load_wallets()
                self._update_details_pane()
        except Exception as e:
            logger.exception("Ошибка удаления кошелька")
            messagebox.showerror("Ошибка", str(e))

    def _show_add_wallet_dialog(self) -> None:
        """Создает диалоговое окно добавления нового кошелька."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Добавить кошелёк")
        dialog.geometry("450x450")
        dialog.resizable(False, False)
        dialog.grab_set()  # Модальный режим

        # Центрируем диалог относительно главного окна
        x = self.winfo_x() + (self.winfo_width() // 2) - 225
        y = self.winfo_y() + (self.winfo_height() // 2) - 225
        dialog.geometry(f"+{x}+{y}")

        dialog.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            dialog,
            text="➕ Добавить новый кошелёк",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold")
        )
        title.pack(pady=20)

        # Имя кошелька
        ctk.CTkLabel(dialog, text="Название кошелька:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=30, pady=(0, 2))
        name_entry = ctk.CTkEntry(dialog, placeholder_text="My Main Wallet")
        name_entry.pack(fill="x", padx=30, pady=(0, 15))
        make_entry_context_menu(name_entry)

        # Сид фраза
        ctk.CTkLabel(dialog, text="Сид-фраза (12, 18 или 24 слова):", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=30, pady=(0, 2))
        seed_text = ctk.CTkTextbox(dialog, height=80, font=ctk.CTkFont(family="Consolas"), wrap="word")
        seed_text.pack(fill="x", padx=30, pady=(0, 15))
        make_entry_context_menu(seed_text)

        # Заметка
        ctk.CTkLabel(dialog, text="Заметка / Описание (опционально):", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=30, pady=(0, 2))
        note_text = ctk.CTkTextbox(dialog, height=80, wrap="word")
        note_text.pack(fill="x", padx=30, pady=(0, 20))
        make_entry_context_menu(note_text)

        def save_wallet():
            name = name_entry.get().strip()
            seed = seed_text.get("1.0", "end-1c").strip()
            note = note_text.get("1.0", "end-1c").strip()

            if not name:
                messagebox.showerror("Ошибка ввода", "Укажите название кошелька.", parent=dialog)
                return
            if not seed or len(seed.split()) < 12:
                messagebox.showerror("Ошибка ввода", "Сид-фраза должна содержать не менее 12 слов.", parent=dialog)
                return

            try:
                # Шифруем
                enc_seed = encrypt_seed(seed, self.vault_password, self.vault_salt)
                enc_note = encrypt_seed(note, self.vault_password, self.vault_salt) if note else None

                # Добавляем в БД
                run_async(self.repo.add_wallet(
                    telegram_id=self.vault_user_id,
                    name=name,
                    encrypted_seed=enc_seed,
                    encrypted_note=enc_note
                ))

                messagebox.showinfo("Успех", f"Кошелёк '{name}' добавлен!", parent=dialog)
                dialog.destroy()
                self._load_wallets()
            except Exception as ex:
                logger.exception("Ошибка добавления кошелька")
                messagebox.showerror("Ошибка", f"Не удалось добавить кошелёк:\n{ex}", parent=dialog)

        # Кнопки
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=30, pady=10)
        btn_frame.grid_columnconfigure((0, 1), weight=1)

        btn_save = ctk.CTkButton(
            btn_frame,
            text="Сохранить",
            fg_color=COLOR_SUCCESS,
            hover_color="#059669",
            command=save_wallet
        )
        btn_save.grid(row=0, column=0, padx=(0, 10), sticky="ew")

        btn_cancel = ctk.CTkButton(
            btn_frame,
            text="Отмена",
            fg_color="transparent",
            border_width=1,
            border_color=COLOR_TEXT_MUTED,
            text_color=COLOR_TEXT,
            hover_color=COLOR_CARD,
            command=dialog.destroy
        )
        btn_cancel.grid(row=0, column=1, padx=(10, 0), sticky="ew")

    # --- СТРАНИЦА ХОСТИНГА И СЕРВЕРА ---
    def _init_server_page(self, frame: ctk.CTkFrame) -> None:
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        scrollable = ctk.CTkScrollableFrame(frame, fg_color=COLOR_CARD, corner_radius=12)
        scrollable.grid(row=0, column=0, sticky="nsew")
        scrollable.grid_columnconfigure((0, 1), weight=1)

        # 1. Верхняя плашка информации
        top_card = ctk.CTkFrame(scrollable, fg_color=COLOR_BG_DARK, border_color=COLOR_BORDER, border_width=1, corner_radius=12)
        top_card.grid(row=0, column=0, columnspan=2, sticky="ew", padx=15, pady=(15, 15))
        top_card.grid_columnconfigure(1, weight=1)

        if hasattr(self, "logo_small") and self.logo_small:
            lbl_icon = ctk.CTkLabel(top_card, image=self.logo_small, text="")
            lbl_icon.grid(row=0, column=0, padx=20, pady=15)
        else:
            lbl_icon = ctk.CTkLabel(top_card, text="🌐", font=ctk.CTkFont(size=24))
            lbl_icon.grid(row=0, column=0, padx=20, pady=15)

        info_box = ctk.CTkFrame(top_card, fg_color="transparent")
        info_box.grid(row=0, column=1, padx=(0, 20), pady=15, sticky="w")

        ctk.CTkLabel(
            info_box,
            text="🌐  Серверный хостинг и автономный деплой 24/7",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=COLOR_TEXT
        ).pack(anchor="w")

        ctk.CTkLabel(
            info_box,
            text="Вы можете развернуть бота на любом Linux VPS / Docker сервере для круглосуточной работы без ПК.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=COLOR_TEXT_MUTED
        ).pack(anchor="w")

        # 2. Рекомендуемый хостинг (@ohoster в Telegram)
        rec_card = ctk.CTkFrame(scrollable, fg_color="#1E1224", border_color=COLOR_ACCENT, border_width=1, corner_radius=12)
        rec_card.grid(row=1, column=0, columnspan=2, sticky="ew", padx=15, pady=(0, 15))
        rec_card.grid_columnconfigure(1, weight=1)

        lbl_tg_icon = ctk.CTkLabel(rec_card, text="🚀", font=ctk.CTkFont(size=22))
        lbl_tg_icon.grid(row=0, column=0, padx=(20, 10), pady=15)

        rec_box = ctk.CTkFrame(rec_card, fg_color="transparent")
        rec_box.grid(row=0, column=1, padx=(0, 20), pady=15, sticky="w")

        ctk.CTkLabel(
            rec_box,
            text="💡 Рекомендуемый 24/7 VPS-хостинг:  @ohoster в Telegram",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=COLOR_TEXT
        ).pack(anchor="w")

        ctk.CTkLabel(
            rec_box,
            text="Для бесперебойной работы 24/7 и обхода любых блокировок рекомендуем быстрые VPS от @ohoster (Telegram).",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLOR_TEXT_MUTED
        ).pack(anchor="w")

        # 3. Карточка 1: Экспорт VPS / Docker архива
        card1 = ctk.CTkFrame(scrollable, fg_color=COLOR_BG_DARK, border_color=COLOR_BORDER, border_width=1, corner_radius=12)
        card1.grid(row=2, column=0, sticky="nsew", padx=(15, 8), pady=(0, 15))
        card1.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card1,
            text="📦  Пакет для 24/7 Сервера (Docker)",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=COLOR_TEXT
        ).pack(anchor="w", padx=20, pady=(15, 5))

        ctk.CTkLabel(
            card1,
            text="Экспортируйте подготовленный `.zip` архив с `docker-compose.yml`, `.env` и кодом проекта.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLOR_TEXT_MUTED,
            wraplength=320,
            justify="left"
        ).pack(anchor="w", padx=20, pady=(0, 10))

        def export_vps_bundle():
            try:
                import zipfile
                file_path = filedialog.asksaveasfilename(
                    title="Сохранить VPS Пакет",
                    defaultextension=".zip",
                    filetypes=[("ZIP Архив", "*.zip")],
                    initialfile="seednox_vps_deploy.zip"
                )
                if not file_path:
                    return

                with zipfile.ZipFile(file_path, "w", zipfile.ZIP_DEFLATED) as zf:
                    for item in ["Dockerfile", "docker-compose.yml", "requirements.txt", "run.py", ".env.example", ".env"]:
                        p = PROJECT_ROOT / item
                        if p.exists():
                            zf.write(p, item)
                    
                    src_dir = PROJECT_ROOT / "src"
                    if src_dir.exists():
                        for root, _, files in os.walk(src_dir):
                            for f in files:
                                if not f.endswith(('.pyc', '.pyo')):
                                    fp = Path(root) / f
                                    arcname = fp.relative_to(PROJECT_ROOT)
                                    zf.write(fp, arcname)

                messagebox.showinfo("Успех", f"VPS пакет сохранен:\n{file_path}")
            except Exception as ex:
                logger.exception("Ошибка экспорта VPS пакета")
                messagebox.showerror("Ошибка", f"Не удалось экспортировать VPS пакет:\n{ex}")

        btn_exp_vps = ctk.CTkButton(
            card1,
            text="💾  Скачать VPS-пакет (.zip)",
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=export_vps_bundle
        )
        btn_exp_vps.pack(anchor="w", padx=20, pady=(5, 15))

        # 4. Карточка 2: Команда запуска на сервере
        card2 = ctk.CTkFrame(scrollable, fg_color=COLOR_BG_DARK, border_color=COLOR_BORDER, border_width=1, corner_radius=12)
        card2.grid(row=2, column=1, sticky="nsew", padx=(8, 15), pady=(0, 15))
        card2.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card2,
            text="⚡  Запуск на Linux VPS",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=COLOR_TEXT
        ).pack(anchor="w", padx=20, pady=(15, 5))

        ctk.CTkLabel(
            card2,
            text="Запустите следующую команду в консоли SSH вашего VPS сервера:",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLOR_TEXT_MUTED,
            wraplength=320,
            justify="left"
        ).pack(anchor="w", padx=20, pady=(0, 10))

        cmd_box = ctk.CTkTextbox(
            card2,
            height=60,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color="#0D0610",
            text_color="#A7F3D0",
            border_color=COLOR_BORDER,
            border_width=1
        )
        cmd_box.pack(fill="x", padx=20, pady=(0, 10))
        cmd_box.insert("1.0", "docker compose up -d --build")
        make_entry_context_menu(cmd_box)

        def copy_deploy_cmd():
            try:
                self.clipboard_clear()
                self.clipboard_append("docker compose up -d --build")
                messagebox.showinfo("Скопировано", "Команда 'docker compose up -d --build' скопирована!")
            except Exception:
                pass

        btn_copy_cmd = ctk.CTkButton(
            card2,
            text="📋  Скопировать команду Docker",
            fg_color="transparent",
            border_width=1,
            border_color=COLOR_BORDER,
            text_color=COLOR_TEXT,
            hover_color=COLOR_CARD_HOVER,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=copy_deploy_cmd
        )
        btn_copy_cmd.pack(anchor="w", padx=20, pady=(0, 15))

        # 5. Карточка 3: Объяснение Синхронизации между Сервером и ПК
        sync_card = ctk.CTkFrame(scrollable, fg_color=COLOR_BG_DARK, border_color=COLOR_BORDER, border_width=1, corner_radius=12)
        sync_card.grid(row=3, column=0, columnspan=2, sticky="ew", padx=15, pady=(0, 15))
        sync_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            sync_card,
            text="🔄  Как работает синхронизация данных между Сервером (VPS) и ПК:",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=COLOR_TEXT
        ).pack(anchor="w", padx=20, pady=(15, 5))

        sync_text = (
            "1. Единая зашифрованная БД (seednox.db): Бот на сервере и ПК используют одинаковую схему SQLite с Argon2id + AES-256-GCM шифрованием.\n"
            "2. Перенос в 1 клик через .snx Бэкап: Вы можете добавлять кошельки в Telegram-боте на сервере 24/7, а затем выгрузить портативный бэкап `.snx` в разделе 'Бэкапы' и мгновенно открыть его в ПК-приложении.\n"
            "3. Прямая авто-синхронизация файлов БД: Вы также можете примонтировать файл `./data/seednox.db` с VPS сервера по SFTP/SSH или Syncthing, указав путь к нему в '⚙️ Настройках', и ПК-приложение будет автоматически видеть все данные в реальном времени!"
        )

        ctk.CTkLabel(
            sync_card,
            text=sync_text,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLOR_TEXT_MUTED,
            justify="left",
            wraplength=700
        ).pack(anchor="w", padx=20, pady=(0, 15))

    # --- СТРАНИЦА НАСТРОЕК ---
    def _init_settings_page(self, frame: ctk.CTkFrame) -> None:
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        scrollable = ctk.CTkScrollableFrame(frame, fg_color=COLOR_CARD, corner_radius=10)
        scrollable.grid(row=0, column=0, sticky="nsew")
        scrollable.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            scrollable,
            text="⚙️ Настройки бота и окружения",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=COLOR_TEXT
        )
        title.pack(anchor="w", padx=25, pady=20)

        # Конструктор полей настроек
        self.settings_fields = {}

        fields_meta = [
            ("BOT_TOKEN", "Telegram Bot Token (от @BotFather):", "токен вашего бота", True),
            ("ALLOWED_USER_IDS", "Разрешенные Telegram ID (через запятую):", "например: 123456789, 987654321", False),
            ("TELEGRAM_PROXY", "🌐 Обход блокировок: HTTP / SOCKS5 Прокси:", "socks5://user:pass@127.0.0.1:1080 или http://127.0.0.1:8080", False),
            ("TELEGRAM_API_URL", "🌐 Обход блокировок: Кастомное зеркало Telegram API:", "например: https://api.telegram.org", False),
            ("DATABASE_PATH", "Путь к базе данных SQLite:", "./data/seednox.db", False),
            ("DB_ENCRYPTION_KEY", "Ключ шифрования БД (SQLCipher - опционально):", "оставьте пустым для дефолта", True),
            ("SESSION_TIMEOUT", "Таймаут сессии пользователя в боте (в секундах):", "900", False),
            ("MAX_PASSWORD_ATTEMPTS", "Максимальное число попыток ввода пароля:", "5", False),
            ("LOCKOUT_DURATION", "Время блокировки при неверном вводе (сек):", "900", False),
        ]

        # Загружаем текущие значения из Pydantic Settings и .env
        for key, label_text, placeholder, is_secret in fields_meta:
            lbl = ctk.CTkLabel(
                scrollable,
                text=label_text,
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                text_color=COLOR_TEXT
            )
            lbl.pack(anchor="w", padx=25, pady=(10, 2))

            val = ""
            if key == "BOT_TOKEN":
                val = self.settings.bot_token.get_secret_value()
            elif key == "ALLOWED_USER_IDS":
                if self.settings.allowed_user_ids:
                    val = ",".join(map(str, self.settings.allowed_user_ids))
            elif key == "TELEGRAM_PROXY":
                val = self.settings.telegram_proxy or ""
            elif key == "TELEGRAM_API_URL":
                val = self.settings.telegram_api_url or ""
            elif key == "DATABASE_PATH":
                val = str(self.settings.database_path)
            elif key == "DB_ENCRYPTION_KEY":
                if self.settings.db_encryption_key:
                    val = self.settings.db_encryption_key.get_secret_value()
            elif key == "SESSION_TIMEOUT":
                val = str(self.settings.session_timeout)
            elif key == "MAX_PASSWORD_ATTEMPTS":
                val = str(self.settings.max_password_attempts)
            elif key == "LOCKOUT_DURATION":
                val = str(self.settings.lockout_duration)

            # Ряд строки ввода с кнопкой быстрой вставки из буфера обмена
            row_frame = ctk.CTkFrame(scrollable, fg_color="transparent")
            row_frame.pack(fill="x", padx=25, pady=(0, 10))
            row_frame.grid_columnconfigure(0, weight=1)

            entry = ctk.CTkEntry(
                row_frame,
                placeholder_text=placeholder,
                fg_color=COLOR_INPUT,
                border_color=COLOR_BORDER,
                show="•" if is_secret else ""
            )
            entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
            entry.insert(0, val)

            # Привязываем контекстное меню правого клика и хоткеи Ctrl+V
            make_entry_context_menu(entry)

            # Кнопка быстрой вставки из буфера обмена
            def make_paste_cmd(target_entry=entry):
                def paste_cmd():
                    try:
                        clip = self.clipboard_get().strip()
                        if clip:
                            target_entry.delete(0, tk.END)
                            target_entry.insert(0, clip)
                        else:
                            messagebox.showinfo("Буфер обмена", "Буфер обмена пуст.")
                    except Exception:
                        messagebox.showwarning("Буфер обмена", "Не удалось прочитать буфер обмена.")
                return paste_cmd

            btn_paste = ctk.CTkButton(
                row_frame,
                text="📋 Вставить",
                width=95,
                fg_color=COLOR_ACCENT,
                hover_color=COLOR_ACCENT_HOVER,
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                command=make_paste_cmd(entry)
            )
            btn_paste.grid(row=0, column=1, padx=(0, 5 if is_secret else 0))

            # Переключатель видимости для секретных полей
            if is_secret:
                def make_toggle_cmd(target_entry=entry):
                    def toggle_cmd():
                        if target_entry.cget("show") == "•":
                            target_entry.configure(show="")
                        else:
                            target_entry.configure(show="•")
                    return toggle_cmd

                btn_toggle = ctk.CTkButton(
                    row_frame,
                    text="👁",
                    width=36,
                    fg_color="transparent",
                    border_width=1,
                    border_color=COLOR_BORDER,
                    text_color=COLOR_TEXT,
                    hover_color=COLOR_CARD_HOVER,
                    command=make_toggle_cmd(entry)
                )
                btn_toggle.grid(row=0, column=2)

            self.settings_fields[key] = entry

        # Кнопка Сохранить
        btn_save = ctk.CTkButton(
            scrollable,
            text="💾  Сохранить настройки",
            fg_color=COLOR_SUCCESS,
            hover_color="#059669",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            command=self._save_settings
        )
        btn_save.pack(anchor="w", padx=25, pady=25)

    def _save_settings(self) -> None:
        """Считывает поля настроек и перезаписывает .env файл."""
        try:
            # Читаем значения
            token = self.settings_fields["BOT_TOKEN"].get().strip()
            allowed_ids = self.settings_fields["ALLOWED_USER_IDS"].get().strip()
            tg_proxy = self.settings_fields["TELEGRAM_PROXY"].get().strip()
            tg_api_url = self.settings_fields["TELEGRAM_API_URL"].get().strip()
            db_path = self.settings_fields["DATABASE_PATH"].get().strip()
            db_key = self.settings_fields["DB_ENCRYPTION_KEY"].get().strip()
            timeout = self.settings_fields["SESSION_TIMEOUT"].get().strip()
            attempts = self.settings_fields["MAX_PASSWORD_ATTEMPTS"].get().strip()
            lockout = self.settings_fields["LOCKOUT_DURATION"].get().strip()

            # Записываем в .env
            save_env_value("BOT_TOKEN", token)
            save_env_value("ALLOWED_USER_IDS", allowed_ids)
            save_env_value("TELEGRAM_PROXY", tg_proxy)
            save_env_value("TELEGRAM_API_URL", tg_api_url)
            save_env_value("DATABASE_PATH", db_path)
            save_env_value("DB_ENCRYPTION_KEY", db_key)
            save_env_value("SESSION_TIMEOUT", timeout)
            save_env_value("MAX_PASSWORD_ATTEMPTS", attempts)
            save_env_value("LOCKOUT_DURATION", lockout)

            # Перезагружаем переменные окружения и настройки
            from dotenv import load_dotenv
            env_path = _find_env_path()
            load_dotenv(dotenv_path=env_path, override=True)

            # Сбрасываем кэш settings
            from src.config import get_settings
            get_settings.cache_clear()
            self.settings = get_settings()

            messagebox.showinfo("Успех", f"Настройки сохранены!\n{env_path}")

        except Exception as e:
            logger.exception("Ошибка при сохранении настроек")
            messagebox.showerror("Ошибка", f"Не удалось сохранить настройки: {e}")

    # --- СТРАНИЦА БЭКАПОВ ---
    def _init_backup_page(self, frame: ctk.CTkFrame) -> None:
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        scrollable = ctk.CTkScrollableFrame(frame, fg_color=COLOR_CARD, corner_radius=12)
        scrollable.grid(row=0, column=0, sticky="nsew")
        scrollable.grid_columnconfigure((0, 1), weight=1)

        # Карточка 1: Зашифрованный бэкап .snx (Seednox format)
        card_snx = ctk.CTkFrame(scrollable, fg_color=COLOR_BG_DARK, border_color=COLOR_BORDER, border_width=1, corner_radius=12)
        card_snx.grid(row=0, column=0, sticky="nsew", padx=(15, 8), pady=15)
        card_snx.grid_columnconfigure(0, weight=1)

        title_snx = ctk.CTkLabel(
            card_snx,
            text="📦 Бэкапы Seednox (.snx)",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=COLOR_TEXT
        )
        title_snx.grid(row=0, column=0, padx=20, pady=(20, 10))

        desc_snx = ctk.CTkLabel(
            card_snx,
            text="Официальный зашифрованный формат резервных копий Seednox (.snx).\nСовместим с Telegram-ботом. Сохраняет все ваши кошельки в портативный файл.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLOR_TEXT_MUTED,
            wraplength=260
        )
        desc_snx.grid(row=1, column=0, padx=20, pady=(0, 20))

        btn_export_snx = ctk.CTkButton(
            card_snx,
            text="📦 Экспорт кошельков (.snx)",
            fg_color=COLOR_SUCCESS,
            hover_color="#059669",
            height=36,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=self._export_snx_backup
        )
        btn_export_snx.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")

        btn_import_snx = ctk.CTkButton(
            card_snx,
            text="📥 Импорт кошельков (.snx)",
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            height=36,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=self._import_snx_backup
        )
        btn_import_snx.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="ew")

        # Карточка 2: Копия базы данных SQLite (seednox.db)
        card_db = ctk.CTkFrame(scrollable, fg_color=COLOR_BG_DARK, border_color=COLOR_BORDER, border_width=1, corner_radius=12)
        card_db.grid(row=0, column=1, sticky="nsew", padx=(8, 15), pady=15)
        card_db.grid_columnconfigure(0, weight=1)

        title_db = ctk.CTkLabel(
            card_db,
            text="💾 База данных (seednox.db)",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=COLOR_TEXT
        )
        title_db.grid(row=0, column=0, padx=20, pady=(20, 10))

        desc_db = ctk.CTkLabel(
            card_db,
            text="Прямое копирование файла базы данных seednox.db.\nСохраняет полный сырой снимок базы данных локального хранилища.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLOR_TEXT_MUTED,
            wraplength=260
        )
        desc_db.grid(row=1, column=0, padx=20, pady=(0, 20))

        btn_create_backup = ctk.CTkButton(
            card_db,
            text="💾 Сохранить копию seednox.db",
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            height=36,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=self._create_db_backup
        )
        btn_create_backup.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")

        btn_restore_backup = ctk.CTkButton(
            card_db,
            text="🔄 Восстановить seednox.db из файла",
            fg_color="transparent",
            border_width=1,
            border_color=COLOR_ERROR,
            text_color=COLOR_ERROR,
            hover_color="#3a1a1a",
            height=36,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=self._restore_db_backup
        )
        btn_restore_backup.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="ew")

    def _export_snx_backup(self) -> None:
        """Экспортирует кошельки пользователя в зашифрованный файл формата .snx."""
        if not self.vault_unlocked:
            messagebox.showerror("Ошибка доступа", "Сначала откройте локальный сейф для экспорта кошельков!")
            return

        try:
            wallets = run_async(self.repo.get_wallets(self.vault_user_id))
            if not wallets:
                messagebox.showwarning("Предупреждение", "В вашем сейфе пока нет кошельков для экспорта.")
                return

            backup_items = [
                wallet_to_backup_item(w.name, w.encrypted_seed, w.encrypted_note)
                for w in wallets
            ]

            backup_bytes = create_encrypted_backup(
                backup_items,
                self.vault_password,
                self.vault_salt
            )

            file_path = filedialog.asksaveasfilename(
                title="Экспорт бэкапа Seednox (.snx)",
                defaultextension=".snx",
                filetypes=[("Seednox Backup File (*.snx)", "*.snx"), ("All Files", "*.*")],
                initialfile=f"seednox_backup_{self.vault_user_id}.snx"
            )

            if not file_path:
                return

            with open(file_path, "wb") as f:
                f.write(backup_bytes)

            messagebox.showinfo("Успех", f"Зашифрованный .snx бэкап успешно экспортирован!\nПуть: {file_path}\nВсего кошельков: {len(wallets)}")

        except Exception as e:
            logger.exception("Ошибка экспорта .snx бэкапа")
            messagebox.showerror("Ошибка экспорта", str(e))

    def _import_snx_backup(self) -> None:
        """Импортирует кошельки из файла .snx в текущий профиль."""
        if not self.vault_unlocked:
            messagebox.showerror("Ошибка доступа", "Сначала откройте локальный сейф для импорта кошельков!")
            return

        file_path = filedialog.askopenfilename(
            title="Выбрать файл .snx для импорта",
            filetypes=[("Seednox Backup File (*.snx)", "*.snx"), ("All Files", "*.*")]
        )

        if not file_path:
            return

        try:
            with open(file_path, "rb") as f:
                backup_bytes = f.read()

            # Собираем соли всех зарегистрированных профилей из БД на случай старых бэкапов
            candidate_salts = []
            try:
                candidate_salts = run_async(self.repo.get_all_salts())
            except Exception:
                pass

            # Пробуем расшифровать активным мастер-паролем сейфа
            try:
                payload = decrypt_backup_file(
                    backup_bytes,
                    self.vault_password,
                    salt=self.vault_salt,
                    candidate_salts=candidate_salts
                )
            except Exception:
                # Если активный пароль не подошел, запрашиваем пароль в диалоге
                pwd_dialog = ctk.CTkInputDialog(
                    text="Мастер-пароль активного сейфа не подошел.\nВведите пароль, которым зашифрован .snx файл:",
                    title="Расшифровка .snx бэкапа"
                )
                backup_pwd = pwd_dialog.get_input()
                if not backup_pwd:
                    return
                payload = decrypt_backup_file(
                    backup_bytes,
                    backup_pwd,
                    salt=self.vault_salt,
                    candidate_salts=candidate_salts
                )

            items = [backup_item_to_bytes(w) for w in payload.get("wallets", [])]
            if not items:
                messagebox.showwarning("Предупреждение", "Файл бэкапа не содержит кошельков.")
                return

            count = run_async(self.repo.import_wallets(self.vault_user_id, items))
            messagebox.showinfo("Успех", f"Успешно импортировано {count} кошельков из .snx файла!")
            self._load_wallets()

        except Exception as e:
            logger.exception("Ошибка импорта .snx бэкапа")
            messagebox.showerror("Ошибка импорта", f"Не удалось расшифровать файл .snx:\n{e}")

    def _create_db_backup(self) -> None:
        """Копирует текущую базу данных в выбранное пользователем место."""
        db_file = self.settings.database_path
        if not db_file.exists():
            messagebox.showerror("Ошибка", f"Файл базы данных не найден по пути: {db_file}")
            return

        file_path = filedialog.asksaveasfilename(
            title="Сохранить резервную копию",
            defaultextension=".db",
            filetypes=[("SQLite Database", "*.db"), ("All Files", "*.*")],
            initialfile=f"seednox_backup_{self.settings.database_path.name}"
        )

        if not file_path:
            return

        try:
            # Делаем копию файла
            shutil.copy2(db_file, file_path)
            messagebox.showinfo("Успех", f"Резервная копия успешно создана в:\n{file_path}")
        except Exception as e:
            logger.exception("Ошибка копирования базы данных")
            messagebox.showerror("Ошибка резервного копирования", str(e))

    def _restore_db_backup(self) -> None:
        """Заменяет файл базы данных выбранным файлом."""
        if self.launcher.is_running():
            messagebox.showerror("Ошибка", "Остановите Telegram-бот перед восстановлением базы данных.")
            return

        if not messagebox.askyesno(
            "Предупреждение",
            "Вы собираетесь восстановить базу данных из внешнего файла.\nТекущая локальная база данных будет перезаписана! Продолжить?"
        ):
            return

        file_path = filedialog.askopenfilename(
            title="Выбрать резервную копию для восстановления",
            filetypes=[("SQLite Database", "*.db"), ("All Files", "*.*")]
        )

        if not file_path:
            return

        try:
            # Закрываем активное соединение репозитория
            run_async(self.repo.close())

            # Перезаписываем
            db_file = self.settings.database_path
            # Создаем папку data если не существует
            db_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, db_file)

            # Переподключаем репозиторий
            db_key = (
                self.settings.db_encryption_key.get_secret_value()
                if self.settings.db_encryption_key
                else None
            )
            self.repo = Repository(self.settings.database_path, encryption_key=db_key)
            run_async(self.repo.connect())

            # Сбрасываем разблокированное состояние сейфа
            self._vault_lock()

            messagebox.showinfo("Успех", "База данных успешно восстановлена!")

        except Exception as e:
            logger.exception("Ошибка восстановления базы данных")
            messagebox.showerror("Ошибка восстановления", str(e))

    def destroy(self) -> None:
        """Перегрузка для корректной остановки бота при закрытии окна."""
        if self.launcher.is_running():
            self.launcher.stop()
        run_async(self.repo.close())
        super().destroy()

def _find_env_path() -> str:
    """Надёжно находит .env файл: рядом с exe/app или в PROJECT_ROOT."""
    # 1. Рядом с исполняемым файлом (для PyInstaller .exe)
    if getattr(sys, 'frozen', False):
        exe_dir = Path(sys.executable).parent
        candidate = exe_dir / ".env"
        if candidate.exists():
            return str(candidate)
        # Создаём рядом с exe если нет
        return str(candidate)
    # 2. PROJECT_ROOT (при запуске из исходников)
    candidate = Path(PROJECT_ROOT) / ".env"
    return str(candidate)


def save_env_value(key: str, value: str):
    """Вспомогательная функция для добавления/обновления переменных в .env файле."""
    env_path = _find_env_path()
    lines = []
    found = False

    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

    # Очищаем перенос строки и \r
    value_clean = value.replace("\n", "").replace("\r", "")

    for i, line in enumerate(lines):
        line_strip = line.strip()
        if line_strip.startswith(f"{key}=") or line_strip.startswith(f"# {key}=") or line_strip.startswith(f"#{key}="):
            lines[i] = f"{key}={value_clean}\n"
            found = True
            break

    if not found:
        if lines and not lines[-1].endswith("\n"):
            lines.append("\n")
        lines.append(f"{key}={value_clean}\n")

    with open(env_path, "w", encoding="utf-8", newline="\n") as f:
        f.writelines(lines)


def main() -> None:
    # Создаем папку logs, data если нужно
    os.makedirs(os.path.join(PROJECT_ROOT, "data"), exist_ok=True)
    app = SeednoxApp()
    app.mainloop()

if __name__ == "__main__":
    main()
