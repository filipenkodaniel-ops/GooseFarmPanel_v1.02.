import subprocess
import time
import json
import os
import psutil
import pyautogui
import pygetwindow as gw

#константы
CS2_APPID = "730"
LAUNCH_OPTIONS = "-novid -windowed -w 640 -h 480 -freq 30 -console -low -nosound"

def launch_account_processes(steam_exe_path, accounts_file, mafiles_dir, update_ui_callback):
    """Автоматизирует запуск Steam аккаунтов и CS2."""

    def get_account_data(line): #Извлекает данные из accounts.txt
        try:
            login, password, steam_id = line.strip().split(':')
            return login, password, steam_id
        except ValueError:
            print(f"Ошибка в строке: {line}.  login:password:steamid")
            return None, None, None

    def get_steam_guard_code(mafile_path): #Получает Steam Guard код из mafile
        try: return json.load(open(mafile_path)).get('shared_secret')
        except (FileNotFoundError, KeyError, json.JSONDecodeError) as e:
            print(f"Ошибка чтения mafile: {e}")
            return None

    def open_steam(steam_exe_path): #Запускает Steam
        subprocess.Popen(steam_exe_path)
        time.sleep(5)
        update_ui_callback("Steam запущен")

    def enter_credentials(login, password, steamguard_code): #Вводит данные в Steam
        time.sleep(2)
        pyautogui.write(login)
        pyautogui.press('tab')
        pyautogui.write(password)
        pyautogui.press('enter')
        time.sleep(5)
        if steamguard_code:
            pyautogui.write(steamguard_code)
            pyautogui.press('enter')

    def launch_cs2(steam_exe_path): #Запускает CS2 с параметрами запуска
          subprocess.Popen([steam_exe_path,  "-applaunch", CS2_APPID, LAUNCH_OPTIONS])
          time.sleep(10)

    with open(accounts_file, 'r') as f:
        for line in f:
            login, password, steam_id = get_account_data(line)
            if not login: continue

            mafile_path = os.path.join(mafiles_dir, f"{steam_id}.mafile")
            code = get_steam_guard_code(mafile_path)

            open_steam(steam_exe_path)
            time.sleep(15)
            enter_credentials(login, password, code)
            time.sleep(20)
            # Запускаем игру кс2
            launch_cs2(steam_exe_path)
            time.sleep(10) #ждём запуска

def kill_account_processes():
    """Останавливает процессы Steam."""
    for proc in psutil.process_iter(['name']):
        if 'steam.exe' in proc.info['name'].lower():
            proc.terminate()
            print(f"Закрыт процесс: {proc.info['name']}")
