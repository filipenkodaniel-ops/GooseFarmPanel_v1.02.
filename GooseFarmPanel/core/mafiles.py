# core/mafiles.py
import os
import json
from typing import Dict, Optional

def load_mafiles(folder_path: str) -> Dict[str, dict]:
    """
    Сканирует папку с mafiles и возвращает словарь:
      account_name.lower() -> {"steamid": <int>, "path": <fullpath>}
    Если парсинг не удался — файл пропускается.
    """
    result = {}
    if not os.path.isdir(folder_path):
        return result

    for name in os.listdir(folder_path):
        full = os.path.join(folder_path, name)
        if not os.path.isfile(full):
            continue
        # поддерживаем расширения .mafile, .json и т.д.
        try:
            with open(full, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception:
            # не JSON — пропускаем
            continue

        # пробуем достать account_name / steamid
        acct_name = None
        steamid = None
        # common keys in example: "account_name", "steamid", "Session"->"SteamID"
        acct_name = data.get("account_name") or data.get("AccountName") or data.get("account")
        if not acct_name:
            # try Session->SteamID map to file name fallback
            try:
                session = data.get("Session", {})
                maybe = session.get("SteamID")
                if maybe:
                    steamid = int(maybe)
            except Exception:
                pass

        if "steamid" in data and not steamid:
            try:
                steamid = int(data.get("steamid"))
            except Exception:
                steamid = steamid

        # final steamid attempt from Session
        if not steamid:
            try:
                session = data.get("Session", {})
                maybe = session.get("SteamID")
                if maybe:
                    steamid = int(maybe)
            except Exception:
                pass

        if acct_name:
            key = acct_name.strip().lower()
            result[key] = {"steamid": steamid, "path": full}
        else:
            # fallback: if filename is like <steamid>.mafile, derive account by steamid string
            # We'll store numeric key as string too for potential lookup by steamid
            basename = os.path.splitext(os.path.basename(full))[0]
            if basename.isdigit():
                result[basename] = {"steamid": int(basename), "path": full}

    return result
