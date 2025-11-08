# DJI Calibration Toolkit

Цей репозиторій містить настільний застосунок **DJI Gimbal Calibration Assistant**.  
Програма надає графічну оболонку над відкритими скриптами OGs Service Tool та дозволяє безпечно запускати штатні процедури калібрування гімбала для підтримуваних дронів DJI.

## Структура

- `calibration_tool/` – код GUI, залежності та вбудовані OGs Service Tool скрипти.
- `calibration_tool/gui_app.py` – основний застосунок Tkinter.
- `calibration_tool/README.md` – детальна інструкція з використання.

## Швидкий старт

```bash
cd calibration_tool
python3 -m venv .venv
. .venv/bin/activate  # або .venv\Scripts\activate на Windows
python -m pip install -r requirements.txt
python gui_app.py
```

## Ліцензія

GUI поширюється під GPLv3. Всі включені модулі OGs Service Tool також ліцензовані за GPLv3 (`calibration_tool/og_tools/LICENSE-GPL-3.0.txt`).

