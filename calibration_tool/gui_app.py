#!/usr/bin/env python3
"""
DJI Gimbal Calibration Assistant (GUI shell).

This Windows-oriented GUI wraps the open-source OGs Service Tool modules
to trigger gimbal calibration routines across a wide range of DJI aircraft.
"""

from __future__ import annotations

import json
import queue
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

import webbrowser

try:
    import tkinter as tk
    from tkinter import messagebox, ttk
except ImportError as exc:  # pragma: no cover
    raise SystemExit("tkinter is required to run this application") from exc

try:
    from serial.tools import list_ports
except ImportError as exc:
    raise SystemExit(
        "pyserial is required. Install dependencies with "
        "`python -m pip install -r requirements.txt`."
    ) from exc

try:
    import serial  # type: ignore
except ImportError as exc:
    raise SystemExit(
        "pyserial is required. Install dependencies with "
        "`python -m pip install -r requirements.txt`."
    ) from exc

try:
    import serial  # type: ignore
except ImportError as exc:
    raise SystemExit(
        "pyserial is required. Install dependencies with "
        "`python -m pip install -r requirements.txt`."
    ) from exc


BASE_DIR = Path(__file__).resolve().parent
OG_TOOLS_DIR = BASE_DIR / "og_tools"
SCRIPT_PATH = OG_TOOLS_DIR / "comm_og_service_tool.py"

# Display labels derived from original OG Service Tool comments.
MODEL_LABELS = {
    "A2": "A2 Flight Controller",
    "P330": "Phantom 1 (P330)",
    "P330V": "Phantom 2 Vision (P330V)",
    "P330Z": "Phantom 2 + Zenmuse H3-2D (P330Z)",
    "P330VP": "Phantom 2 Vision+ (P330VP)",
    "WM610": "Inspire 1 (WM610)",
    "P3X": "Phantom 3 Professional (P3X)",
    "P3S": "Phantom 3 Advanced (P3S)",
    "MAT100": "Matrice 100 (MAT100)",
    "P3C": "Phantom 3 Standard (P3C)",
    "MG1": "Agras MG-1 (MG1)",
    "WM325": "Phantom 3 4K (WM325)",
    "WM330": "Phantom 4 Standard (WM330)",
    "MAT600": "Matrice 600 (MAT600)",
    "WM220": "Mavic Pro / Platinum (WM220)",
    "WM620": "Inspire 2 (WM620)",
    "WM331": "Phantom 4 Pro (WM331)",
    "MAT200": "Matrice 200 (MAT200)",
    "MG1S": "Agras MG-1S (MG1S)",
    "WM332": "Phantom 4 Advanced (WM332)",
    "WM100": "Spark (WM100)",
    "WM230": "Mavic Air (WM230)",
    "WM335": "Phantom 4 Pro V2 (WM335)",
    "WM240": "Mavic 2 Pro/Zoom (WM240)",
    "WM245": "Mavic 2 Enterprise (WM245)",
    "WM246": "Mavic 2 Enterprise Dual (WM246)",
    "WM160": "Mavic Mini (WM160)",
    "WM231": "Mavic Air 2 (WM231)",
    "WM232": "Air 2S (WM232)",
    "WM260": "Mavic 3 / 3 Classic (WM260)",
    "WM247": "Mavic 2 Enterprise Advanced (WM247)",
    "WM161": "Mini 2 / SE (WM161)",
    "WM162": "Mini 3 (WM162)",
    "WM170": "Avata (WM170)",
    "WM261": "Mavic 3 Pro (WM261)",
    "WM262": "Mavic 3E/3T/3M (WM262)",
    "WM236": "Air 3 (WM236)",
}

# Alternative product aliases provided by OG Service Tool.
ALT_PRODUCT_CODES = {
    "S800": "A2",
    "S1000": "A2",
    "S900": "A2",
    "PH3PRO": "P3X",
    "PH3ADV": "P3S",
    "PH3STD": "P3C",
    "P3XW": "WM325",
    "P4": "WM330",
    "PH4": "WM330",
    "PH4PRO": "WM331",
    "PH4ADV": "WM332",
    "SPARK": "WM100",
    "MAVIC": "WM220",
    "MAVAIR": "WM230",
    "M2P": "WM240",
    "M2Z": "WM240",
    "M2E": "WM245",
    "M2ED": "WM246",
    "M2EA": "WM247",
    "MMINI": "WM160",
    "MAVAIR2": "WM231",
    "MAVAIR2S": "WM232",
    "MAV3": "WM260",
    "M3P": "WM261",
}

MANUAL_LINKS = [
    (
        "DJI Mini 4 Pro – User Manual (EN)",
        "https://dl.djicdn.com/downloads/DJI_Mini_4_Pro/20240627/DJI_Mini_4_Pro_User_Manual_ENI.pdf",
    ),
    (
        "DJI Mini 3 Pro – User Manual (EN)",
        "https://dl.djicdn.com/downloads/DJI_Mini_3_Pro/20240402/DJI_Mini_3_Pro_User_Manual_v3.4_en.pdf",
    ),
    (
        "DJI Mini 3 – User Manual (EN)",
        "https://dl.djicdn.com/downloads/DJI_Mini_3/20240402/DJI_Mini_3_User_Manual_v1.2_en.pdf",
    ),
    (
        "DJI Air 2S – User Manual (EN)",
        "https://dl.djicdn.com/downloads/DJI_Air_2S/20240528UM/DJI_Air_2S_User_Manual_v1.0_EN.pdf",
    ),
    (
        "DJI Assistant 2 (Consumer Drones Series)",
        "https://www.dji.com/downloads/softwares/assistant-dji-2-consumer-drones-series",
    ),
    (
        "DJI Fly App",
        "https://www.dji.com/global/downloads/djiapp/dji-fly",
    ),
]

IMU_GUIDE = (
    "IMU калібрування (через DJI Fly):\n"
    "  • Дрон на рівній поверхні, гвинти зняті.\n"
    "  • В застосунку DJI Fly відкрийте Налаштування (⋯) → Безпека → IMU → \"Калібрувати\".\n"
    "  • Повертайте дрон у позиції, які підкаже застосунок.\n"
    "  • Після завершення дочекайтесь підтвердження і перезапустіть дрон.\n"
)

COMPASS_GUIDE = (
    "Калібрування компаса:\n"
    "  • Переконайтесь, що поруч немає металевих предметів чи магнітних полів.\n"
    "  • DJI Fly → Налаштування (⋯) → Безпека → Компас → \"Калібрувати\".\n"
    "  • Обертайте дрон горизонтально, потім вертикально (носом вниз) за інструкціями.\n"
    "  • При помилках повторіть процедуру або змініть локацію.\n"
)

GIMBAL_GUIDE = (
    "Автокалібрування гімбала (офіційна процедура):\n"
    "  • Зніміть захист камери, дрон – на рівній поверхні.\n"
    "  • DJI Fly → Налаштування (⋯) → Управління → \"Автокалібрування гімбала\".\n"
    "  • Не торкайтесь дрона ~2 хвилини до завершення процесу.\n"
    "  • Для точного горизонту скористайтесь ручним вирівнюванням у тому ж меню.\n"
)

MODEL_SPECIFIC_HINTS = {
    "WM260": (
        "Mavic 3 / 3 Classic (WM260):\n"
        "  • Калібрування гімбала виконується аналогічно Spark/Mavic Air.\n"
        "  • Для успішного з'єднання потрібні драйвери DJI Assistant 2 (Consumer).\n"
        "  • У разі появи коду 40021 дотримуйтесь офіційної інструкції DJI щодо "
        "перевстановлення гімбала/сервісного центру.\n"
    ),
    "WM100": (
        "Spark (WM100):\n"
        "  • Після JointCoarse виконайте Linear Hall для точнішого центрування.\n"
        "  • Офіційне керівництво рекомендує повторну перевірку IMU перед польотом.\n"
    ),
    "WM220": (
        "Mavic Pro / Platinum (WM220):\n"
        "  • Після калібрування перевірте, чи немає повідомлень щодо візуальних датчиків "
        "у DJI Assistant 2.\n"
        "  • Якщо гімбал «просідає» після автокалібрування, скористайтесь ручним вирівнюванням.\n"
    ),
    "WM231": (
        "Mavic Air 2 (WM231):\n"
        "  • У разі помилок 40021/40023 DJI радить оновити прошивку через Fly App/Assistant 2.\n"
        "  • Антиколізійні датчики необхідно тримати чистими під час автокалібрування.\n"
    ),
    "WM260_BULK": (
        "USB bulk режими (наприклад, Mavic 3):\n"
        "  • Використовуйте офіційні драйвери DJI Assistant 2 (Consumer Drones Series).\n"
        "  • Для сервісних процедур дотримуйтесь інструкцій DJI — не запускайте сторонні утиліти.\n"
    ),
}

EXTERNAL_RESOURCE_FILE = BASE_DIR / "custom_resources.json"


def ensure_resources() -> None:
    """Sanity-check that the OG modules are available next to the GUI."""
    missing = [path for path in [SCRIPT_PATH] if not path.exists()]
    if missing:
        files = ", ".join(str(p.name) for p in missing)
        raise SystemExit(
            f"Missing required OG Service Tool files: {files}. "
            "Make sure you cloned the repository correctly."
        )


def iter_serial_ports() -> List[str]:
    """Return a sorted list of available serial port identifiers."""
    ports = []
    for port in list_ports.comports():
        label = port.device
        if port.description and port.description != port.device:
            label = f"{port.device} – {port.description}"
        ports.append(label)
    return sorted(ports)


@dataclass
class CalibrationCommand:
    port: Optional[str]
    product_code: str
    mode: str
    service: str = "GimbalCalib"
    verbose: int = 1
    timeout_ms: int = 500
    bulk: bool = False
    key: Optional[str] = None
    force: bool = False
    param_name: Optional[str] = None
    param_value: Optional[str] = None
    start: int = 0
    count: int = 100
    alt: bool = False

    def build_subprocess_args(self) -> List[str]:
        base_cmd = [
            sys.executable,
            "-u",
            str(SCRIPT_PATH),
        ]
        if self.bulk:
            base_cmd.append("--bulk")
        else:
            base_cmd.extend(["--port", self.port or "auto"])

        # Verbosity handled by repeating -v flags (compatible with OG tool).
        base_cmd.extend(["-v"] * max(self.verbose, 0))
        base_cmd.extend(["-w", str(self.timeout_ms)])
        base_cmd.append(self.product_code)
        base_cmd.extend([self.service, self.mode])

        if self.service == "CameraCalib" and self.mode == "EncryptPair":
            if self.key:
                base_cmd.extend(["--pairkey", self.key])
            if self.force:
                base_cmd.append("--force")
        elif self.service == "FlycParam":
            if self.mode == "list":
                base_cmd.extend(["--start", str(self.start), "--count", str(self.count)])
            elif self.mode == "get":
                base_cmd.append(self.param_name or "")
            elif self.mode == "set":
                base_cmd.extend([self.param_name or "", self.param_value or ""])
            if self.alt:
                base_cmd.append("--alt")

        return base_cmd


class CalibrationProcess:
    """Wrapper for running OG Service Tool as a subprocess and streaming output."""

    def __init__(self, command: CalibrationCommand, log_queue: "queue.Queue[str]") -> None:
        self.command = command
        self.log_queue = log_queue
        self._proc: Optional[subprocess.Popen[str]] = None
        self._reader_threads: List[threading.Thread] = []

    def start(self) -> None:
        args = self.command.build_subprocess_args()
        self.log_queue.put(
            f"$ {' '.join(args)}\n"
            f"Working directory: {OG_TOOLS_DIR}\n"
        )
        self._proc = subprocess.Popen(
            args,
            cwd=str(OG_TOOLS_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        assert self._proc.stdout and self._proc.stderr  # for type checkers
        self._reader_threads = [
            threading.Thread(
                target=self._stream_reader,
                args=(self._proc.stdout, False),
                daemon=True,
            ),
            threading.Thread(
                target=self._stream_reader,
                args=(self._proc.stderr, True),
                daemon=True,
            ),
        ]
        for thread in self._reader_threads:
            thread.start()

        threading.Thread(target=self._wait_for_completion, daemon=True).start()

    def _stream_reader(self, stream: Iterable[str], is_error: bool) -> None:
        prefix = "[stderr] " if is_error else ""
        for line in stream:
            self.log_queue.put(prefix + line)

    def _wait_for_completion(self) -> None:
        if not self._proc:
            return
        exit_code = self._proc.wait()
        self.log_queue.put(f"\nProcess finished with exit code {exit_code}\n")
        self.log_queue.put("__DONE__")

    def terminate(self) -> None:
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        self.log_queue.put("Process terminated by user.\n")
        self.log_queue.put("__DONE__")


class CalibrationApp(tk.Tk):
    """Tkinter GUI that orchestrates calibration runs."""

    def __init__(self) -> None:
        super().__init__()
        self.title("DJI Gimbal Calibration Assistant")
        self.geometry("920x640")
        self.minsize(820, 520)

        self.log_queue: "queue.Queue[str]" = queue.Queue()
        self.current_process: Optional[CalibrationProcess] = None
        self.status_var = tk.StringVar(value="Готовий до роботи")
        self.resources_data = self._load_custom_resources()

        self._build_widgets()
        self.refresh_ports()
        self.after(200, self._poll_logs)

    def _build_widgets(self) -> None:
        padding = {"padx": 10, "pady": 6}

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        calibration_tab = ttk.Frame(self.notebook)
        guides_tab = ttk.Frame(self.notebook)
        resources_tab = ttk.Frame(self.notebook)

        self.notebook.add(calibration_tab, text="Калібрування гімбала")
        camera_tab = ttk.Frame(self.notebook)
        flyc_tab = ttk.Frame(self.notebook)
        self.notebook.add(camera_tab, text="Калібрування камери (P3X)")
        self.notebook.add(flyc_tab, text="Параметри Flight Controller")
        self.notebook.add(guides_tab, text="Покрокові інструкції")
        self.notebook.add(resources_tab, text="Офіційні ресурси")

        # --- Gimbal Calibration tab
        connection_frame = ttk.LabelFrame(calibration_tab, text="Підключення")
        connection_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(connection_frame, text="COM порт:").grid(row=0, column=0, sticky=tk.W, **padding)
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(
            connection_frame,
            textvariable=self.port_var,
            state="readonly",
            width=35,
        )
        self.port_combo.grid(row=0, column=1, sticky=tk.W, **padding)

        self.bulk_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            connection_frame,
            text="Використовувати USB bulk (для Mavic 3 / новіших)",
            variable=self.bulk_var,
        ).grid(row=0, column=2, sticky=tk.W, **padding)

        ttk.Button(
            connection_frame,
            text="Оновити порти",
            command=self.refresh_ports,
        ).grid(row=0, column=3, sticky=tk.W, **padding)

        ttk.Button(
            connection_frame,
            text="Перевірити підключення",
            command=self.run_connection_diagnostics,
        ).grid(row=0, column=4, sticky=tk.W, **padding)

        ttk.Label(connection_frame, text="Модель / код:").grid(row=1, column=0, sticky=tk.W, **padding)
        self.product_var = tk.StringVar(value="WM100")
        model_choices = self._build_model_choices()
        self.model_combo = ttk.Combobox(
            connection_frame,
            textvariable=self.product_var,
            values=[label for label, _ in model_choices],
            state="readonly",
            width=48,
        )
        self.model_combo.grid(row=1, column=1, columnspan=3, sticky=tk.W, **padding)
        if model_choices:
            self.model_combo.current(0)

        self.diagnostics_var = tk.StringVar(value="Діагностика ще не запускалась.")
        ttk.Label(
            connection_frame,
            textvariable=self.diagnostics_var,
            foreground="#555555",
            wraplength=520,
            justify=tk.LEFT,
        ).grid(row=2, column=0, columnspan=5, sticky=tk.W, padx=10, pady=(4, 0))

        options_frame = ttk.LabelFrame(calibration_tab, text="Налаштування")
        options_frame.pack(fill=tk.X, padx=10, pady=0)

        ttk.Label(options_frame, text="Рівень логування:").grid(row=0, column=0, sticky=tk.W, **padding)
        self.verbose_var = tk.IntVar(value=1)
        ttk.Spinbox(
            options_frame,
            from_=0,
            to=3,
            textvariable=self.verbose_var,
            width=5,
        ).grid(row=0, column=1, sticky=tk.W, **padding)

        ttk.Label(options_frame, text="Таймаут відповіді (мс):").grid(row=0, column=2, sticky=tk.W, **padding)
        self.timeout_var = tk.IntVar(value=500)
        ttk.Spinbox(
            options_frame,
            from_=200,
            to=10000,
            increment=100,
            textvariable=self.timeout_var,
            width=8,
        ).grid(row=0, column=3, sticky=tk.W, **padding)

        action_frame = ttk.LabelFrame(calibration_tab, text="Дії калібрування")
        action_frame.pack(fill=tk.X, padx=10, pady=10)

        self.coarse_btn = ttk.Button(
            action_frame,
            text="Joint Coarse (грубе калібрування)",
            command=lambda: self.start_calibration("JointCoarse"),
        )
        self.coarse_btn.grid(row=0, column=0, sticky=tk.W, **padding)

        self.linear_btn = ttk.Button(
            action_frame,
            text="Linear Hall (сенсори Холла)",
            command=lambda: self.start_calibration("LinearHall"),
        )
        self.linear_btn.grid(row=0, column=1, sticky=tk.W, **padding)

        self.stop_btn = ttk.Button(
            action_frame,
            text="Завершити процес",
            command=self.stop_current_process,
            state=tk.DISABLED,
        )
        self.stop_btn.grid(row=0, column=2, sticky=tk.W, **padding)

        log_frame = ttk.LabelFrame(calibration_tab, text="Логи OG Service Tool")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.log_text = tk.Text(log_frame, wrap=tk.WORD, height=20, state=tk.DISABLED)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.configure(yscrollcommand=scrollbar.set)

        # --- Camera Calibration tab
        cam_action_frame = ttk.LabelFrame(camera_tab, text="Дії калібрування камери")
        cam_action_frame.pack(fill=tk.X, padx=10, pady=10)

        self.check_btn = ttk.Button(
            cam_action_frame,
            text="Перевірка шифрування (EncryptCheck)",
            command=lambda: self.start_calibration("EncryptCheck", "CameraCalib"),
        )
        self.check_btn.grid(row=0, column=0, sticky=tk.W, **padding)

        self.pair_btn = ttk.Button(
            cam_action_frame,
            text="Виконати сполучення (EncryptPair)",
            command=lambda: self.start_calibration("EncryptPair", "CameraCalib"),
        )
        self.pair_btn.grid(row=0, column=1, sticky=tk.W, **padding)

        cam_options_frame = ttk.LabelFrame(camera_tab, text="Налаштування сполучення")
        cam_options_frame.pack(fill=tk.X, padx=10, pady=0)

        ttk.Label(cam_options_frame, text="Ключ (32 байти, hex):").grid(
            row=0, column=0, sticky=tk.W, **padding
        )
        self.key_var = tk.StringVar()
        ttk.Entry(cam_options_frame, textvariable=self.key_var, width=68).grid(
            row=0, column=1, columnspan=2, sticky=tk.W, **padding
        )

        self.force_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            cam_options_frame,
            text="Примусово (force)",
            variable=self.force_var,
        ).grid(row=1, column=0, sticky=tk.W, **padding)

        warning_label = ttk.Label(
            camera_tab,
            text=(
                "УВАГА: Функції калібрування камери призначені лише для Phantom 3 Professional/Advanced. "
                "Неправильне використання, особливо EncryptPair, може назавжди заблокувати камеру. "
                "Використовуйте на свій страх і ризик."
            ),
            wraplength=780,
            justify=tk.LEFT,
            foreground="red",
        )
        warning_label.pack(fill=tk.X, padx=10, pady=10)

        # --- Flight Controller Parameters Tab
        flyc_action_frame = ttk.LabelFrame(flyc_tab, text="Операції з параметрами")
        flyc_action_frame.pack(fill=tk.X, padx=10, pady=10)

        self.list_btn = ttk.Button(
            flyc_action_frame,
            text="Список параметрів (list)",
            command=lambda: self.start_calibration("list", "FlycParam"),
        )
        self.list_btn.grid(row=0, column=0, sticky=tk.W, **padding)

        self.get_btn = ttk.Button(
            flyc_action_frame,
            text="Отримати параметр (get)",
            command=lambda: self.start_calibration("get", "FlycParam"),
        )
        self.get_btn.grid(row=0, column=1, sticky=tk.W, **padding)

        self.set_btn = ttk.Button(
            flyc_action_frame,
            text="Встановити параметр (set)",
            command=lambda: self.start_calibration("set", "FlycParam"),
        )
        self.set_btn.grid(row=0, column=2, sticky=tk.W, **padding)

        flyc_options_frame = ttk.LabelFrame(flyc_tab, text="Налаштування операцій")
        flyc_options_frame.pack(fill=tk.X, padx=10, pady=0)

        ttk.Label(flyc_options_frame, text="Ім'я/хеш:").grid(row=0, column=0, sticky=tk.W, **padding)
        self.param_name_var = tk.StringVar()
        ttk.Entry(flyc_options_frame, textvariable=self.param_name_var, width=40).grid(
            row=0, column=1, sticky=tk.W, **padding
        )

        ttk.Label(flyc_options_frame, text="Значення:").grid(row=1, column=0, sticky=tk.W, **padding)
        self.param_value_var = tk.StringVar()
        ttk.Entry(flyc_options_frame, textvariable=self.param_value_var, width=40).grid(
            row=1, column=1, sticky=tk.W, **padding
        )

        ttk.Label(flyc_options_frame, text="Індекс / кількість:").grid(
            row=0, column=2, sticky=tk.W, **padding
        )
        self.param_start_var = tk.IntVar(value=0)
        self.param_count_var = tk.IntVar(value=100)
        ttk.Spinbox(
            flyc_options_frame, from_=0, to=10000, textvariable=self.param_start_var, width=6
        ).grid(row=0, column=3, sticky=tk.W, **padding)
        ttk.Spinbox(
            flyc_options_frame, from_=1, to=10000, textvariable=self.param_count_var, width=6
        ).grid(row=0, column=4, sticky=tk.W, **padding)

        self.alt_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            flyc_options_frame,
            text="Альтернативний метод (alt)",
            variable=self.alt_var,
        ).grid(row=1, column=2, sticky=tk.W, **padding)

        flyc_warning_label = ttk.Label(
            flyc_tab,
            text=(
                "УВАГА: Неправильна зміна параметрів Flight Controller може призвести до "
                "нестабільної роботи або повної відмови дрона. Використовуйте лише "
                "якщо ви повністю розумієте, що робите."
            ),
            wraplength=780,
            justify=tk.LEFT,
            foreground="orange",
        )
        flyc_warning_label.pack(fill=tk.X, padx=10, pady=10)

        # --- Guides tab
        guides_text = tk.Text(guides_tab, wrap=tk.WORD, state=tk.NORMAL)
        guides_text.insert(
            tk.END,
            "Офіційні процедури калібрування\n"
            "===============================\n\n"
            f"{IMU_GUIDE}\n{COMPASS_GUIDE}\n{GIMBAL_GUIDE}\n"
            "Поради:\n"
            "  • Виконуйте калібрування на відкритій місцевості без перешкод.\n"
            "  • Перед початком повністю зарядьте акумулятор дрона та пульта.\n"
            "  • За необхідності звертайтесь до сервісної підтримки DJI.\n",
        )
        guides_text.configure(state=tk.DISABLED)
        guides_text.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        self.model_hint_var = tk.StringVar(value="Виберіть модель у списку, щоб побачити рекомендації.")
        ttk.Label(
            guides_tab,
            textvariable=self.model_hint_var,
            wraplength=720,
            justify=tk.LEFT,
            foreground="#444444",
        ).pack(fill=tk.X, padx=12, pady=(0, 12))

        # --- Resources tab
        resources_frame = ttk.Frame(resources_tab)
        resources_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        ttk.Label(
            resources_frame,
            text="Офіційні посібники та програмне забезпечення DJI",
        ).pack(anchor=tk.W, pady=(0, 8))

        self.resources_tree = ttk.Treeview(
            resources_frame,
            columns=("link",),
            show="tree",
            selectmode="browse",
            height=14,
        )
        for title, link in MANUAL_LINKS:
            self.resources_tree.insert("", tk.END, iid=link, text=title)
        for title, link in self.resources_data.items():
            iid = f"user::{link}"
            self.resources_tree.insert("", tk.END, iid=iid, text=f"{title} (користувацьке)")
        self.resources_tree.pack(fill=tk.BOTH, expand=True)

        ttk.Button(
            resources_frame,
            text="Відкрити ресурс у браузері",
            command=self._open_selected_resource,
        ).pack(anchor=tk.E, pady=6)

        ttk.Button(
            resources_frame,
            text="Додати власне посилання",
            command=self._open_add_resource_dialog,
        ).pack(anchor=tk.W, pady=(0, 6))

        ttk.Label(
            resources_frame,
            text=(
                "Ці матеріали розміщені на офіційних серверах DJI. Використовуйте лише легальні "
                "методи обслуговування та оновлень, щоб зберегти гарантію і безпеку польотів."
            ),
            wraplength=580,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(6, 0))

        # Status bar
        status_bar = ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    def _build_model_choices(self) -> List[tuple[str, str]]:
        """Prepare combo entries as (display_label, code)."""
        choices = []
        for code, description in MODEL_LABELS.items():
            choices.append((f"{description}", code))
        for alias, target in ALT_PRODUCT_CODES.items():
            choices.append((f"{alias} → {MODEL_LABELS.get(target, target)}", alias))
        # Sort alphabetically for UI clarity.
        choices.sort(key=lambda item: item[0].lower())
        self._model_lookup = {label: code for label, code in choices}
        return choices

    def refresh_ports(self) -> None:
        ports = iter_serial_ports()
        self.port_combo["values"] = ports
        if ports:
            # Keep previous selection if still available.
            current = self.port_var.get()
            if current and current in ports:
                self.port_combo.set(current)
            else:
                self.port_combo.current(0)
        else:
            self.port_combo.set("")
        self.status_var.set(f"Доступні порти: {len(ports)}")

    def start_calibration(self, mode: str, service: str = "GimbalCalib") -> None:
        if self.current_process is not None:
            messagebox.showwarning("Процес вже виконується", "Дочекайтесь завершення поточного процесу.")
            return

        selected_label = self.model_combo.get()
        if not selected_label:
            messagebox.showerror("Не вибрано модель", "Оберіть модель дрона зі списку.")
            return
        product_code = self._model_lookup.get(selected_label, selected_label)
        product_code = ALT_PRODUCT_CODES.get(product_code, product_code)

        bulk_mode = self.bulk_var.get()
        port_value = None
        if not bulk_mode:
            port_value = self.port_var.get().split(" – ")[0]
            if not port_value:
                messagebox.showerror("Не вибрано порт", "Оберіть COM-порт або активуйте режим USB bulk.")
                return

        command = CalibrationCommand(
            port=port_value,
            product_code=product_code,
            mode=mode,
            service=service,
            verbose=int(self.verbose_var.get()),
            timeout_ms=int(self.timeout_var.get()),
            bulk=bulk_mode,
            key=self.key_var.get() or None,
            force=self.force_var.get(),
            param_name=self.param_name_var.get() or None,
            param_value=self.param_value_var.get() or None,
            start=self.param_start_var.get(),
            count=self.param_count_var.get(),
            alt=self.alt_var.get(),
        )

        self._append_log(
            f"\n=== Старт процедури {service}/{mode} для {selected_label} (код {product_code}) "
            f"— {time.strftime('%H:%M:%S')} ===\n"
        )
        self.status_var.set(f"Виконується: {service}/{mode}…")
        self._toggle_buttons(active=False)

        self.current_process = CalibrationProcess(command, self.log_queue)
        self.current_process.start()

        self._update_model_hint(product_code, bulk_mode)

    def stop_current_process(self) -> None:
        if self.current_process is not None:
            self.current_process.terminate()

    def _toggle_buttons(self, active: bool) -> None:
        state_main = tk.NORMAL if active else tk.DISABLED
        state_stop = tk.DISABLED if active else tk.NORMAL

        self.coarse_btn.configure(state=state_main)
        self.linear_btn.configure(state=state_main)
        self.check_btn.configure(state=state_main)
        self.pair_btn.configure(state=state_main)
        self.list_btn.configure(state=state_main)
        self.get_btn.configure(state=state_main)
        self.set_btn.configure(state=state_main)

        self.stop_btn.configure(state=state_stop)

    def _append_log(self, message: str) -> None:
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, message)
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _poll_logs(self) -> None:
        try:
            while True:
                message = self.log_queue.get_nowait()
                if message == "__DONE__":
                    self.current_process = None
                    self._toggle_buttons(active=True)
                    self.status_var.set("Готовий до роботи")
                    continue
                self._append_log(message)
        except queue.Empty:
            pass
        finally:
            self.after(200, self._poll_logs)

    def _update_model_hint(self, product_code: str, bulk_mode: bool) -> None:
        if bulk_mode:
            hint = MODEL_SPECIFIC_HINTS.get("WM260_BULK")
            if hint:
                self.model_hint_var.set(hint)
            return

        hint = MODEL_SPECIFIC_HINTS.get(product_code)
        if hint:
            self.model_hint_var.set(hint)
        else:
            self.model_hint_var.set(
                "Для цієї моделі використовуйте стандартні інструкції IMU/компас/гімбал. "
                "За потреби звертайтесь до мануалів на вкладці «Офіційні ресурси»."
            )

    def _load_custom_resources(self) -> dict[str, str]:
        if not EXTERNAL_RESOURCE_FILE.exists():
            return {}
        try:
            with EXTERNAL_RESOURCE_FILE.open("r", encoding="utf-8") as fp:
                data = json.load(fp)
        except Exception:
            return {}
        resources: dict[str, str] = {}
        for entry in data:
            title = entry.get("title")
            url = entry.get("url")
            if isinstance(title, str) and isinstance(url, str):
                resources[title] = url
        return resources

    def _save_custom_resources(self) -> None:
        payload = [{"title": title, "url": url} for title, url in self.resources_data.items()]
        with EXTERNAL_RESOURCE_FILE.open("w", encoding="utf-8") as fp:
            json.dump(payload, fp, indent=2, ensure_ascii=False)

    def _open_add_resource_dialog(self) -> None:
        dialog = tk.Toplevel(self)
        dialog.title("Додати посилання")
        dialog.geometry("420x180")
        dialog.resizable(False, False)

        ttk.Label(dialog, text="Назва:").pack(anchor=tk.W, padx=12, pady=(12, 0))
        title_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=title_var).pack(fill=tk.X, padx=12)

        ttk.Label(dialog, text="URL:").pack(anchor=tk.W, padx=12, pady=(8, 0))
        url_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=url_var).pack(fill=tk.X, padx=12)

        def add_link() -> None:
            title = title_var.get().strip()
            url = url_var.get().strip()
            if not title or not url:
                messagebox.showerror("Помилка", "Заповніть і назву, і URL.")
                return
            iid = f"user::{url}"
            if iid in self.resources_tree.get_children():
                messagebox.showinfo("Інформація", "Таке посилання вже додано.")
                return
            self.resources_data[title] = url
            self.resources_tree.insert("", tk.END, iid=iid, text=f"{title} (користувацьке)")
            self._save_custom_resources()
            dialog.destroy()

        ttk.Button(dialog, text="Додати", command=add_link).pack(anchor=tk.E, padx=12, pady=12)
        ttk.Button(dialog, text="Скасувати", command=dialog.destroy).pack(anchor=tk.W, padx=12, pady=12)

    def run_connection_diagnostics(self) -> None:
        if self.bulk_var.get():
            message = (
                "Режим USB bulk використовується. Доступність перевіряється через DJI Assistant 2 "
                "або офіційні драйвери. Змініть на COM-порт для детальної діагностики."
            )
            self.diagnostics_var.set(message)
            self._append_log(message + "\n")
            return

        port_label = self.port_var.get()
        if not port_label:
            messagebox.showerror("Немає порту", "Оберіть COM-порт для діагностики.")
            return
        port_name = port_label.split(" – ")[0]

        try:
            with serial.Serial(port_name, baudrate=9600, timeout=0.5) as ser:
                ser.reset_input_buffer()
                ser.reset_output_buffer()
            message = f"Порт {port_name}: успішно відкрито, доступ до пристрою є."
            self.diagnostics_var.set(message)
            self.status_var.set("Порт перевірено")
            self._append_log(message + "\n")
        except serial.SerialException as exc:  # type: ignore[attr-defined]
            message = (
                f"Не вдалося відкрити {port_name}: {exc}. "
                "Перевірте підключення, драйвери та увімкнення дрона."
            )
            self.diagnostics_var.set(message)
            self.status_var.set("Проблема з підключенням")
            self._append_log(message + "\n")
        except Exception as exc:  # pragma: no cover
            message = f"Неочікувана помилка діагностики: {exc}"
            self.diagnostics_var.set(message)
            self.status_var.set("Проблема з підключенням")
            self._append_log(message + "\n")

    def _open_selected_resource(self) -> None:
        selection = self.resources_tree.selection()
        if not selection:
            messagebox.showinfo("Ресурс не обрано", "Будь ласка, виберіть елемент зі списку.")
            return
        self._open_url(selection[0])

    @staticmethod
    def _open_url(url: str) -> None:
        try:
            webbrowser.open(url, new=2)
        except Exception as exc:  # pragma: no cover
            messagebox.showerror("Помилка", f"Не вдалося відкрити посилання:\n{exc}")


def main() -> None:
    ensure_resources()
    app = CalibrationApp()
    app.mainloop()


if __name__ == "__main__":
    main()

