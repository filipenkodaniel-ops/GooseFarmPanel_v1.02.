import os
import psutil
import json
from tkinter import filedialog
import threading
import time
import customtkinter as ctk
import tkinter as tk
from datetime import datetime
from gfp_ui.system_status_widget import SystemStatusWidget
from core.accounts import AccountsManager
from core.launcher import launch_account_processes, kill_account_processes
import threading

# Theme defaults
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# Helper: fixed sizes and colors
LEFT_WIDTH = 260
RIGHT_WIDTH = 380
GAP_X = 12
GAP_Y = 12
BUTTON_HEIGHT = 34
PANEL_BG = "#2b2b2b"
PANEL_DARK = "#232323"
ACCENT_BLUE = "#2f79b9"
ACCENT_GREEN = "#28a745"
ACCENT_PURPLE = "#5b2bd3"
ACCENT_RED = "#d93025"
TEXT_ORANGE = "#d98b2a"


class FGPPanelUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("FGP Panel")
        self.geometry("1210x710")
        self.minsize(1210, 710)
        self.maxsize(1210, 710)

        # Accounts manager
        self.acc_manager = AccountsManager(path=os.path.join("data", "accounts.txt"))
        self.account_vars = []
        self.account_checkboxes = []
        self.next_index = 0

        # Load config and steam_path
        self.config = self.load_config()
        self.steam_path = self.config.get("steam_path")
        if self.steam_path:
            self.add_log(f"Steam path loaded from config: {self.steam_path}")

        # Root layout
        self._build_left_column()
        self._build_center_column()
        self._build_right_column()

        # Load accounts and start refresh thread
        self.reload_accounts()
        self._stop_refresh = False
        self._refresh_thread = threading.Thread(target=self._periodic_refresh, daemon=True)
        self._refresh_thread.start()

        # Protocol close
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # ----------------- BUILD UI -----------------
    def _build_left_column(self):
        self.left_frame_outer = ctk.CTkFrame(self, width=LEFT_WIDTH, fg_color="#262626", corner_radius=12)
        self.left_frame_outer.pack(side="left", fill="y", padx=(GAP_X, 0), pady=GAP_Y)
        self.left_frame_outer.pack_propagate(False)

        inner_pad = 10
        self.left_col = ctk.CTkFrame(self.left_frame_outer, fg_color=PANEL_BG, corner_radius=8)
        self.left_col.pack(fill="both", expand=True, padx=inner_pad, pady=inner_pad)

        try:
            title_font = ("Segoe UI", 18, "bold")
            normal_font = ("Segoe UI", 12)
            small_font = ("Segoe UI", 11)
        except Exception:
            title_font = ("Arial", 18, "bold")
            normal_font = ("Arial", 12)
            small_font = ("Arial", 11)

        self.left_title = ctk.CTkLabel(
            self.left_col,
            text="Goose Panel",
            font=("Segoe UI", 20, "bold"),
            anchor="center",
            justify="center"
        )
        self.left_title.pack(pady=(10, 8), padx=10, fill="x")

        self.label_farmed = ctk.CTkLabel(
            self.left_col,
            text="Farmed this week: 0",
            font=("Segoe UI", 14, "bold"),
            anchor="center",
            justify="center"
        )
        self.label_farmed.pack(pady=(6, 0), padx=10, fill="x")

        self.label_drop = ctk.CTkLabel(
            self.left_col,
            text="Drop received: 0 [0/0]",
            font=("Segoe UI", 14, "bold"),
            anchor="center",
            justify="center"
        )
        self.label_drop.pack(pady=(6, 10), padx=10, fill="x")

        self.left_bigbox_outer = ctk.CTkFrame(self.left_col, corner_radius=8, fg_color=PANEL_DARK)
        self.left_bigbox_outer.pack(padx=12, pady=6, fill="x")
        self.left_bigbox_outer.configure(height=300)
        self.left_bigbox_outer.pack_propagate(False)

        self.left_bigbox_inner = ctk.CTkFrame(self.left_bigbox_outer, fg_color="#1b1b1b", corner_radius=6)
        self.left_bigbox_inner.pack(fill="both", expand=True, padx=8, pady=8)

        self.telegram_btn = ctk.CTkButton(
            self.left_col,
            text="Telegram",
            fg_color=ACCENT_BLUE,
            hover_color="#3b8ad9",
            corner_radius=8,
            height=36,
            font=normal_font,
            command=self.open_telegram
        )
        self.telegram_btn.pack(padx=12, pady=(12, 8), fill="x")

        ctk.CTkLabel(self.left_col, text="Appearance Mode:", font=small_font).pack(padx=12, pady=(8, 2), anchor="w")
        self.appearance_menu = ctk.CTkOptionMenu(self.left_col, values=["Dark", "Light"], command=self.change_appearance, font=normal_font)
        self.appearance_menu.set("Dark")
        self.appearance_menu.pack(padx=12, fill="x")

        ctk.CTkLabel(self.left_col, text="UI Scaling:", font=small_font).pack(padx=12, pady=(10, 2), anchor="w")
        self.scaling_menu = ctk.CTkOptionMenu(
            self.left_col,
            values=["80%", "90%", "100%", "110%", "120%"],
            command=self.change_scaling,
            font=normal_font
        )
        self.scaling_menu.set("100%")
        self.scaling_menu.pack(padx=12, fill="x")

        self.left_col.pack_propagate(False)

    def _build_center_column(self):
        self.center_col = ctk.CTkFrame(self, fg_color=PANEL_BG)
        self.center_col.pack(side="left", fill="y", expand=False,
                            padx=(GAP_X, GAP_X), pady=GAP_Y)

        self.center_wrap = ctk.CTkFrame(self.center_col, fg_color="transparent", width=650)
        self.center_wrap.pack(fill="both", expand=True, pady=(0, 0))

        self.logs_panel = ctk.CTkFrame(self.center_wrap,
                                    fg_color=PANEL_DARK,
                                    corner_radius=6,
                                    width=450,
                                    height=350)
        self.logs_panel.pack(fill="x", pady=(5, 10))
        self.logs_panel.pack_propagate(False)

        self.logs_label = ctk.CTkLabel(self.logs_panel,
                                    text="Logs",
                                    font=("Segoe UI", 13, "bold"))
        self.logs_label.pack(anchor="w", padx=8, pady=(8, 0))

        self.logs_box = ctk.CTkTextbox(self.logs_panel,
                                    fg_color="#0f0f0f",
                                    text_color="white",
                                    corner_radius=6)
        self.logs_box.pack(fill="both", expand=True, padx=8, pady=8)
        self.logs_box.configure(state="disabled")

        self.accounts_panel = ctk.CTkFrame(
            self.center_wrap,
            fg_color=PANEL_DARK,
            corner_radius=6,
            height=350
        )
        self.accounts_panel.pack(fill="x", pady=(0, 10))
        self.accounts_panel.pack_propagate(False)

        self.acc_header = ctk.CTkLabel(
            self.accounts_panel,
            text="Accs: 0 | Selected: 0 | Launched: 0",
            font=("Segoe UI", 12, "bold")
        )
        self.acc_header.pack(anchor="w", padx=10, pady=(8, 6))

        self.acc_scroll = ctk.CTkScrollableFrame(
            self.accounts_panel,
            fg_color="transparent"
        )
        self.acc_scroll.pack(fill="both", expand=True, padx=8, pady=6)

    def _build_right_column(self):
        self.right_col = ctk.CTkFrame(self, width=RIGHT_WIDTH, fg_color=PANEL_BG)
        self.right_col.pack(side="right", fill="y", padx=(0, GAP_X), pady=GAP_Y)

        top_frame = ctk.CTkFrame(self.right_col, fg_color=PANEL_BG)
        top_frame.pack(fill="x", padx=6, pady=(6, 6))

        main_menu = ctk.CTkFrame(top_frame, fg_color=PANEL_DARK, corner_radius=6)
        main_menu.pack(side="left", fill="both", expand=True, padx=(0, 4))

        ctk.CTkLabel(main_menu, text="Main Menu", font=("Segoe UI", 12, "bold")).pack(pady=(8, 6))
        ctk.CTkButton(main_menu, text="Make lobbies", fg_color=ACCENT_GREEN,
                    command=self.make_lobbies, height=BUTTON_HEIGHT).pack(padx=18, pady=6, fill="x")

        ctk.CTkButton(main_menu, text="Disband lobbies", fg_color=ACCENT_PURPLE,
                    command=self.disband_lobbies, height=BUTTON_HEIGHT).pack(padx=18, pady=6, fill="x")

        ctk.CTkButton(main_menu, text="Shuffle lobbies", fg_color=ACCENT_PURPLE,
                    command=self.shuffle_lobbies, height=BUTTON_HEIGHT).pack(padx=18, pady=6, fill="x")

        ctk.CTkSwitch(main_menu, text="Autodisconnects").pack(padx=18, pady=8, anchor="w")

        ctk.CTkButton(main_menu, text="Make lobbies and search game",
                    command=self.make_and_search, height=BUTTON_HEIGHT).pack(padx=18, pady=6, fill="x")

        farm_mode_btn = ctk.CTkButton(
            main_menu,
            text="Farming Mode: 2vs2 – 8:8",
            fg_color=ACCENT_GREEN,
            hover_color="#24963d",
            height=40,
            font=("Segoe UI", 13, "bold")
        )
        farm_mode_btn.pack(padx=18, pady=(10, 4), fill="x")

        maps_btn = ctk.CTkButton(
            main_menu,
            text="Maps: de_inferno",
            fg_color=ACCENT_RED,
            hover_color="#b32018",
            height=34,
            font=("Segoe UI", 12, "bold")
        )
        maps_btn.pack(padx=18, pady=(0, 10), fill="x")

        config_block = ctk.CTkFrame(top_frame, fg_color=PANEL_DARK, corner_radius=6)
        config_block.pack(side="left", fill="both", expand=True, padx=(4, 0))

        ctk.CTkLabel(config_block, text="Config", font=("Segoe UI", 12, "bold")).pack(pady=(8, 6))
        ctk.CTkSwitch(config_block, text="NO AVAST SANDBOX").pack(pady=6, anchor="w", padx=10)
        ctk.CTkSwitch(config_block, text="Shuffle lobbies after game").pack(pady=6, anchor="w", padx=10)

        # Entry fields, labels, and buttons
        ctk.CTkLabel(config_block, text="Steam path:", font=("Segoe UI", 11)).pack(pady=(5, 0), anchor="w", padx=10)
        self.steam_path_input = ctk.CTkEntry(config_block)
        # Если путь был сохранен, устанавливаем его в поле ввода
        if self.steam_path:
            self.steam_path_input.insert(0, self.steam_path)  # 0 - вставляем в начало
        self.steam_path_input.pack(padx=10, fill="x")
        # Убедитесь, что у вас есть  steam_path_input

        ctk.CTkLabel(config_block, text="CS2 App ID:", font=("Segoe UI", 11)).pack(pady=(5, 0), anchor="w", padx=10)
        self.cs2_app_id_input = ctk.CTkEntry(config_block)
        self.cs2_app_id_input.pack(padx=10, fill="x")

        ctk.CTkLabel(config_block, text="CS2 Launch Options:", font=("Segoe UI", 11)).pack(pady=(5, 0), anchor="w", padx=10)
        self.cs2_launch_options_input = ctk.CTkEntry(config_block)
        self.cs2_launch_options_input.pack(padx=10, fill="x")

        #set_steam_path Command removed to allow the input itself to set the path
        ctk.CTkButton(config_block, text="Looter settings", command=self.looter_settings,
                height=BUTTON_HEIGHT).pack(padx=18, pady=6, fill="x")
        ctk.CTkSwitch(config_block, text="Auto collect and send drop").pack(pady=6, anchor="w", padx=10)
        ctk.CTkSwitch(config_block, text="Start farm when launched").pack(pady=6, anchor="w", padx=10)


        bottom_frame = ctk.CTkFrame(self.right_col, fg_color=PANEL_BG)
        bottom_frame.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        acc_ctrl = ctk.CTkFrame(bottom_frame, fg_color=PANEL_DARK, corner_radius=6)
        acc_ctrl.pack(side="left", fill="both", expand=True, padx=(0, 4), pady=6)

        ctk.CTkLabel(acc_ctrl, text="Accounts Control", font=("Segoe UI", 12, "bold")).pack(pady=(8, 6))

        # Corrected command to use a lambda that takes steam_exe_path from  steam_path_input
        ctk.CTkButton(acc_ctrl, text="Start selected accounts", fg_color=ACCENT_GREEN,
            command=self.start_selected_accounts, height=BUTTON_HEIGHT).pack(padx=18, pady=6, fill="x")

        ctk.CTkButton(acc_ctrl, text="Kill selected accounts", fg_color=ACCENT_RED,
                    command=self.kill_selected_accounts, height=BUTTON_HEIGHT).pack(padx=18, pady=6, fill="x")

        ctk.CTkButton(acc_ctrl, text="Select first 4 unfarmed",
                    command=lambda: self.select_first_n_unfarmed(4),
                    height=BUTTON_HEIGHT).pack(padx=18, pady=6, fill="x")

        ctk.CTkButton(acc_ctrl, text="Get LVL of launched accs",
                    command=self.get_levels, height=BUTTON_HEIGHT).pack(padx=18, pady=6, fill="x")

        acc_ctrl2 = ctk.CTkFrame(bottom_frame, fg_color=PANEL_DARK, corner_radius=6)
        acc_ctrl2.pack(side="left", fill="both", expand=True, padx=(4, 0), pady=6)

        ctk.CTkLabel(acc_ctrl2, text="Accounts Control 2", font=("Segoe UI", 12, "bold")).pack(pady=(8, 6))

        ctk.CTkButton(acc_ctrl2, text="Move all CS windows",
                    command=self.move_all_windows, height=BUTTON_HEIGHT).pack(padx=18, pady=6, fill="x")

        ctk.CTkButton(acc_ctrl2, text="Kill ALL CS & Steam processes", fg_color=ACCENT_RED,
                    command=self.kill_all_cs_steam, height=BUTTON_HEIGHT).pack(padx=18, pady=6, fill="x")

        ctk.CTkButton(acc_ctrl2, text="Drop stats", fg_color=ACCENT_GREEN,
                    command=self.drop_stats, height=BUTTON_HEIGHT).pack(padx=18, pady=6, fill="x")

        ctk.CTkButton(acc_ctrl2, text="Ban checker",
                    command=self.ban_checker, height=BUTTON_HEIGHT).pack(padx=18, pady=6, fill="x")


    # ----------------- CONFIG STORAGE -----------------
    def _cfg_path(self):
        return os.path.join("data", "config.json")

    def load_config(self):
        """Returns a dict with config, or an empty dict if not found."""
        cfg_file = self._cfg_path()
        try:
            if os.path.isfile(cfg_file):
                with open(cfg_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            self.add_log(f"Failed to load config: {e}")
        return {}

    def save_config(self, cfg: dict):
        """Saves cfg to data/config.json."""
        cfg_file = self._cfg_path()
        try:
            os.makedirs(os.path.dirname(cfg_file), exist_ok=True)
            with open(cfg_file, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
            self.add_log("Config saved")
        except Exception as e:
            self.add_log(f"Failed to save config: {e}")

    # ----------------- LOGGING -----------------
    def add_log(self, text: str):
        if not hasattr(self, "logs_box"):
            return
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {text}\n"
        try:
            self.logs_box.configure(state="normal")
            self.logs_box.insert("end", line)
            self.logs_box.see("end")
            self.logs_box.configure(state="disabled")
        except Exception:
            pass

    def _on_account_finished(self, account):
        """Callback from launcher when account process finished."""
        try:
            try:
                idx = self.acc_manager.accounts.index(account)
            except ValueError:
                idx = next((i for i, a in enumerate(self.acc_manager.accounts) if a.login == account.login), None)

            account.launched = False

            def ui_update():
                if idx is not None and idx < len(self.acc_manager.accounts):
                    self._apply_account_style(idx)
                    self._refresh_account_text(idx)
                self.update_header()
                self.add_log(f"Account finished: {account.login} (farmed={account.farmed})")

            try:
                self.after(0, ui_update)
            except Exception:
                ui_update()
        except Exception as e:
            print("Error in _on_account_finished:", e)

    # ----------------- ACCOUNTS UI -----------------
    def reload_accounts(self):
        try:
            self.acc_manager.load_accounts()
        except Exception as e:
            self.add_log(f"Error loading accounts: {e}")

        if not hasattr(self, "acc_scroll") or self.acc_scroll is None:
            self.add_log("Error: acc_scroll not found. Ensure _build_center_column is called before reload_accounts().")
            return

        for item in getattr(self, "account_checkboxes", []):
            try:
                row = item[0]
                row.destroy()
            except Exception:
                pass

        self.account_vars = []
        self.account_checkboxes = []

        accounts = self.acc_manager.get_accounts()
        if not accounts:
            self.add_log("No accounts found in accounts file.")

        for idx, acc in enumerate(accounts):
            try:
                row = ctk.CTkFrame(self.acc_scroll, fg_color="transparent")
                row.pack(fill="x", pady=3, padx=4)

                var = tk.BooleanVar(value=bool(getattr(acc, "selected", False)))

                switch = ctk.CTkSwitch(
                    row,
                    text="",
                    variable=var,
                    command=(lambda i=idx: self._on_toggle(i)),
                )
                switch.pack(side="left", padx=(0, 6), pady=4)

                lbl = ctk.CTkLabel(
                    row,
                    text=self.acc_manager.get_display_text(acc),
                    font=("Segoe UI", 12),
                    anchor="w",
                    justify="left"
                )
                lbl.pack(side="left", fill="x", expand=True, padx=(0, 6))

                self.account_vars.append(var)
                self.account_checkboxes.append((row, switch, lbl))

                self._apply_account_style(idx)
            except Exception as e:
                self.add_log(f"Error creating row for account idx={idx}: {e}")
                continue

        self.update_header()
        self.add_log(f"Loaded {len(self.account_checkboxes)} accounts")

    def _on_toggle(self, index):
        """Toggle selection of account."""
        acc = self.acc_manager.accounts[index]
        acc.selected = not acc.selected

        try:
            self.account_vars[index].set(acc.selected)
        except Exception:
            pass

        self._apply_account_style(index)
        self.update_header()
        self.add_log(f"{'Selected' if acc.selected else 'Unselected'}: {acc.login}")

    def _refresh_account_text(self, index):
        """Refreshes text and style for an account."""
        try:
            acc = self.acc_manager.accounts[index]
            row, cb, lbl = self.account_checkboxes[index]
            lbl.configure(text=self.acc_manager.get_display_text(acc))
            self._apply_account_style(index)
        except Exception:
            pass

    def _apply_account_style(self, index):
        """Applies color scheme to the account labels."""
        try:
            acc = self.acc_manager.accounts[index]
            row, cb, lbl = self.account_checkboxes[index]
        except Exception:
            return

        color = None
        if getattr(acc, "launched", False):
            color = ACCENT_BLUE
        elif getattr(acc, "farmed", False):
            color = ACCENT_GREEN
        elif getattr(acc, "selected", False):
            color = TEXT_ORANGE
        else:
            color = None

        try:
            if color:
                lbl.configure(text_color=color)
            else:
                lbl.configure(text_color=None)
        except Exception:
            try:
                lbl.configure(fg_color=None)
            except Exception:
                pass

    def update_header(self):
        total = len(self.acc_manager.accounts)
        selected = self.acc_manager.count_selected()
        launched = self.acc_manager.count_launched()
        try:
            self.acc_header.configure(text=f"Accs: {total} | Selected: {selected} | Launched: {launched}")
        except Exception:
            pass

    # ----------------- PERIODIC REFRESH -----------------
    def _periodic_refresh(self):
        while not getattr(self, "_stop_refresh", False):
            try:
                for i in range(len(self.acc_manager.accounts)):
                    self._refresh_account_text(i)
                self.update_header()
            except Exception:
                pass
            time.sleep(1.2)

    # ----------------- ACTIONS / STUBS -----------------
    def start_selected_accounts(self):
        # Get data for selected accounts
        selected_accounts = [a for a in self.acc_manager.accounts if a.selected]
        if not selected_accounts:
            self.add_log("No accounts selected to start.")
            return

        # mark launched and refresh UI
        for acc in selected_accounts:
            acc.launched = True
            acc.farmed = False  # reset before starting

        # update UI instantly
        for i, acc in enumerate(self.acc_manager.accounts):
            try:
                self._apply_account_style(i)
                self._refresh_account_text(i)
                if i < len(self.account_vars):
                    self.account_vars[i].set(acc.selected)
            except Exception:
                pass

        self.update_header()
        self.add_log(f"Starting {len(selected_accounts)} accounts...")

        # Launch in background and provide callback
    def some_function(self, selected_account): # Предполагаем, что selected_account передаётся в функцию где вызывается поток
        thread = threading.Thread(
            target=lambda: launch_account_processes(
                steam_exe_path=self.steam_path_input.get(),
                account=selected_account, # Передаем данные аккаунта
                update_ui_callback=self._on_account_finished # Функция обратного вызова
            )
        )
        thread.start()
    


    def kill_selected_accounts(self):
        selected_accounts = [a for a in self.acc_manager.accounts if a.selected]
        if not selected_accounts:
            self.add_log("No accounts selected to kill.")
            return

        threading.Thread(target=lambda: kill_account_processes(selected_accounts), daemon=True).start()
        for acc in selected_accounts:
            acc.launched = False

        # update UI

        for i in range(len(self.acc_manager.accounts)):
            try:
                self._apply_account_style(i)
                self._refresh_account_text(i)
                if i < len(self.account_vars):
                    self.account_vars[i].set(self.acc_manager.accounts[i].selected)
            except Exception:
                pass
        self.update_header()
        self.add_log(f"Killed {len(selected_accounts)} accounts")

    def select_first_n_unfarmed(self, n):
        picked = 0

        for i, acc in enumerate(self.acc_manager.accounts):
            if not acc.farmed and picked < n:
                acc.selected = True
                picked += 1
            else:
                acc.selected = False

        for i, acc in enumerate(self.acc_manager.accounts):
            try:
                self.account_vars[i].set(acc.selected)
                self._refresh_account_text(i)
            except Exception:
                pass

        self.update_header()
        self.add_log(f"Selected {picked} unfarmed accounts")

    def select_next_4(self):
        if not self.acc_manager.accounts:
            self.add_log("No accounts available.")
            return

        total = len(self.acc_manager.accounts)

        if self.next_index >= total:
            self.next_index = 0

        for acc in self.acc_manager.accounts:
            acc.selected = False

        picked = 0
        while picked < 4 and self.next_index < total:
            acc = self.acc_manager.accounts[self.next_index]
            acc.selected = True
            picked += 1
            self.next_index += 1

        self.reload_accounts()
        self.add_log(f"Selected next {picked} accounts")

    def get_levels(self):
        self.add_log("Get levels triggered (stub)")
        for acc in self.acc_manager.accounts[:3]:
            acc.farmed = True
        self.reload_accounts()

    # Lobbies / config / tools actions (stubs)
    def make_lobbies(self):
        self.add_log("Make lobbies")

    def disband_lobbies(self):
        self.add_log("Disband lobbies")

    def shuffle_lobbies(self):
        self.add_log("Shuffle lobbies")

    def make_and_search(self):
        self.add_log("Make lobbies and search game")

    def set_steam_path(self):
        """Opens dialog to select steam.exe and saves the path."""
        initial = r"C:\Program Files (x86)\Steam"
        if not os.path.isdir(initial):
            initial = os.path.expanduser("~")

        path = filedialog.askopenfilename(
            title="Select steam.exe",
            initialdir=initial,
            filetypes=[("Executable", "*.exe"), ("All files", "*.*")]
        )
        if not path:
            self.add_log("Set steam path cancelled")
            return

        self.steam_path = path
        self.config["steam_path"] = path
        try:
            self.save_config(self.config)
            self.add_log(f"Steam path set: {path}")
        except Exception as e:
            self.add_log(f"Error saving steam path: {e}")

    def set_cs2_path(self):
        self.add_log("Set CS2 path (choose dialog)")

    def looter_settings(self):
        self.add_log("Looter settings (open)")

    def move_all_windows(self):
        self.add_log("Move all CS windows (stub)")

    def kill_all_cs_steam(self):
        self.add_log("Kill all CS & Steam processes (stub)")

    def launch_bes(self):
        self.add_log("Launch BES (stub)")

    def drop_stats(self):
        self.add_log("Drop stats (stub)")

    def ban_checker(self):
        self.add_log("Ban checker (stub)")

    def activity_booster(self):
        self.add_log("Activity booster (stub)")

    # ----------------- UTILITIES -----------------
    def open_telegram(self):
        self.add_log("Open Telegram clicked")

    def change_appearance(self, mode):
        try:
            ctk.set_appearance_mode(mode.lower())
            self.add_log(f"Appearance changed to {mode}")
        except Exception:
            pass

    def change_scaling(self, scaling):
        try:
            scaling_float = int(scaling.replace("%", "")) / 100.0
            ctk.set_widget_scaling(scaling_float)
            self.add_log(f"UI scaling set to {scaling}")
        except Exception:
            pass

    def save_accounts(self):
        try:
            self.acc_manager.save_accounts()
            self.add_log("Accounts saved")
        except Exception as e:
            self.add_log(f"Error saving accounts: {e}")

    def reload_accounts_and_keep_selection(self):
        sel_map = {acc.login: acc.selected for acc in self.acc_manager.accounts}
        self.acc_manager.load_accounts()
        for acc in self.acc_manager.accounts:
            acc.selected = sel_map.get(acc.login, False)
        self.reload_accounts()

    def on_close(self):
        self._stop_refresh = True
        try:
            self.save_accounts()
        except Exception:
            pass
        self.destroy()


if __name__ == "__main__":
    app = FGPPanelUI()
    app.mainloop()
