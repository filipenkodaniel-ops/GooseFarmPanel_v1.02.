# gfp_ui/system_status_widget.py
import time
import threading
import psutil
import customtkinter as ctk


class SystemStatusWidget(ctk.CTkFrame):
    def __init__(self, master, height=140):
        super().__init__(master, fg_color="#1a1a1a", height=height)
        self.pack_propagate(False)

        # Title
        self.title = ctk.CTkLabel(self, text="System Status", font=("Segoe UI", 14, "bold"))
        self.title.pack(pady=(5, 3))

        # CPU
        self.cpu_label = ctk.CTkLabel(self, text="CPU: Loading...")
        self.cpu_label.pack(anchor="w", padx=10)

        # RAM
        self.ram_label = ctk.CTkLabel(self, text="RAM: Loading...")
        self.ram_label.pack(anchor="w", padx=10)

        # Thread
        self.stop_flag = False
        threading.Thread(target=self.update_loop, daemon=True).start()

    def update_loop(self):
        while not self.stop_flag:
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent

            self.cpu_label.configure(text=f"CPU: {cpu}%")
            self.ram_label.configure(text=f"RAM: {ram}%")

            time.sleep(1)

    def stop(self):
        self.stop_flag = True
