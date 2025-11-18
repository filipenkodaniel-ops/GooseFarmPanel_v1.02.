# core/accounts.py
import os
import json
from typing import List, Optional

from core import mafiles as mafiles_module

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
ACCOUNTS_FILE = os.path.join(DATA_DIR, "accounts.txt")
STATE_FILE = os.path.join(DATA_DIR, "accounts_state.json")
MAFILES_FOLDER = os.path.join(DATA_DIR, "mafiles")


class Account:
    def __init__(self, login: str, password: str):
        self.login = login
        self.password = password

        # statuses
        self.selected = False
        self.launched = False
        self.farmed = False

        # mafile mapping
        self.steamid = None  # integer or None
        self.mafile_path = None
        self.has_mafile = False

        # runtime process handle (set by launcher)
        self.process = None

        # optional additional fields (level/xp)
        self.level = None
        self.xp = None

    def to_state(self) -> dict:
        return {
            "login": self.login,
            "farmed": bool(self.farmed),
            "launched": bool(self.launched),
            "selected": bool(self.selected),
            "steamid": self.steamid,
            "mafile_path": self.mafile_path,
        }


class AccountsManager:
    def __init__(self, path: Optional[str] = None):
        """
        path not used directly; accounts file path is DATA_DIR/accounts.txt by default.
        """
        self.accounts: List[Account] = []
        # load mafiles map
        self.mafiles_map = mafiles_module.load_mafiles(MAFILES_FOLDER)
        self.load_accounts()

    def load_accounts(self):
        # reload mafiles mapping each time (in case files added)
        self.mafiles_map = mafiles_module.load_mafiles(MAFILES_FOLDER)

        self.accounts = []
        if not os.path.isfile(ACCOUNTS_FILE):
            return

        with open(ACCOUNTS_FILE, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split(":", 1)
                if len(parts) != 2:
                    continue
                login, password = parts[0].strip(), parts[1].strip()
                acc = Account(login=login, password=password)

                # try to attach mafile by account_name -> steamid
                key = login.strip().lower()
                mapped = self.mafiles_map.get(key)
                if mapped:
                    acc.steamid = mapped.get("steamid")
                    acc.mafile_path = mapped.get("path")
                    acc.has_mafile = True
                else:
                    acc.has_mafile = False

                self.accounts.append(acc)

        # try to restore state (farmed/launched/selected)
        if os.path.isfile(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as fh:
                    st = json.load(fh)
                # st expected: { login: {farmed:bool, launched:bool, selected:bool} }
                for acc in self.accounts:
                    s = st.get(acc.login)
                    if s:
                        acc.farmed = bool(s.get("farmed", False))
                        acc.launched = bool(s.get("launched", False))
                        acc.selected = bool(s.get("selected", False))
            except Exception:
                pass

    def save_accounts(self):
        # We write two files:
        # 1) accounts.txt (login:password) — keep original list unchanged
        # 2) accounts_state.json — statuses
        # Save state
        state = {}
        for acc in self.accounts:
            state[acc.login] = {
                "farmed": bool(acc.farmed),
                "launched": bool(acc.launched),
                "selected": bool(acc.selected),
                "steamid": acc.steamid,
                "mafile_path": acc.mafile_path,
            }

        try:
            os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
            with open(STATE_FILE, "w", encoding="utf-8") as fh:
                json.dump(state, fh, indent=2, ensure_ascii=False)
        except Exception:
            pass

    # helpers for UI
    def get_accounts(self) -> List[Account]:
        return self.accounts

    def count_selected(self) -> int:
        return sum(1 for a in self.accounts if getattr(a, "selected", False))

    def count_launched(self) -> int:
        return sum(1 for a in self.accounts if getattr(a, "launched", False))

    def get_display_text(self, acc: Account) -> str:
        # Format: login — [LVL | XP | Farmed/Not]
        lvl = str(acc.level) if acc.level is not None else "-"
        xp = str(acc.xp) if acc.xp is not None else "-"
        farmed = "Farmed" if getattr(acc, "farmed", False) else "Not"
        steamid = f" | {acc.steamid}" if acc.steamid else ""
        return f"{acc.login} — [{lvl} | {xp} | {farmed}]{steamid}"
