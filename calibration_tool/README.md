# DJI Gimbal Calibration Assistant

Українська версія нижче. Scroll down for English.

---

## Огляд

Це настільний застосунок для Windows, який надає графічну оболонку над відкритим OGs Service Tool. Програма дозволяє запускати штатні процедури калібрування підвісів (Joint Coarse та Linear Hall) для широкого спектра дронів DJI, використовуючи стандартний USB або USB bulk інтерфейс.

### Можливості

- Виявлення доступних COM‑портів і запуск калібрування в один клік.
- Підтримка режиму USB bulk (наприклад, для лінійки Mavic 3).
- Відображення логів OGs Service Tool у реальному часі.
- Вбудовані покрокові гіди для IMU/компаса/гімбала згідно з DJI Fly.
- Швидкі посилання на офіційні мануали та програми DJI.
- Повністю офлайн: у каталозі `og_tools/` лежать скрипти під GPLv3.

## Вимоги

- Windows 10/11 (теоретично працює і на Linux/macOS, але UI орієнтований на Windows).
- Встановлений Python 3.10–3.12.
- Драйвери DJI/CDC або `libusb` для bulk‑режиму (установка окрема).

## Початок роботи

```bash
cd "C:\Users\<user>\Desktop\DJI\calibration_tool"
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python gui_app.py
```

1. Підключіть дрон по USB, увімкніть його.
2. Оберіть COM‑порт або активуйте USB bulk.
3. Виберіть модель (код відповідає OG Service Tool).
4. Натисніть потрібну процедуру (Joint Coarse чи Linear Hall) і дочекайтесь завершення.
5. За потреби скористайтесь вкладками «Покрокові інструкції» та «Офіційні ресурси».

> **Увага:** використання неофіційних інструментів може призвести до втрати гарантії. Дійте на власний ризик.

## Збірка `.exe`

```bash
.venv\Scripts\activate
python -m pip install pyinstaller
pyinstaller --noconfirm --windowed --name DJI-Gimbal-Calibrator gui_app.py
```

Після збірки:

1. Скопіюйте директорію `og_tools/` та `LICENSE-GPL-3.0.txt` до `dist/DJI-Gimbal-Calibrator/`.
2. Тестуйте на цільовій машині з встановленими драйверами.

## Ліцензія

Включені скрипти OGs Service Tool розповсюджуються під GPLv3. Залишена копія ліцензії в `LICENSE-GPL-3.0.txt`. Ця GUI надбудова також підпадає під GPLv3.

---

## English Summary

This Windows desktop app is a thin GUI layer on top of the open OGs Service Tool. It lets you invoke DJI gimbal calibration routines (Joint Coarse / Linear Hall) for many aircraft.

1. Install Python 3.10–3.12 and the dependencies (`pyserial`, `pyusb`).
2. Run `python gui_app.py`, choose the COM port or bulk mode, pick the aircraft model, and start a calibration.
3. Use the Guides/Resources tabs for official procedures and manuals.
4. Logs from OG Service Tool are streamed into the window.

To build an `.exe`, bundle the OG scripts (`og_tools/`) alongside the PyInstaller output. Both OG scripts and the GUI are GPLv3.

Use at your own risk; unofficial tools can void your DJI warranty.

