"""Abre a interface web do Shadow dentro de uma janela desktop."""

import io
from contextlib import redirect_stdout
from pathlib import Path
import sys

from main import scan_system, terminate_user_process
from optimizations import (
    activate_power_plan,
    clean_temp_files,
    disk_overview,
    live_system_sample,
    power_plan_overview,
    preview_temp_cleanup,
    set_startup_enabled,
    startup_overview,
)


class ShadowApi:
    """Métodos Python que a interface JavaScript pode chamar."""

    def __init__(self):
        self.window = None
        self.process_cache = {}
        self.previous_disk_io = None
        self.previous_sample_time = None

    def scan(self):
        # A tela recebe o relatório como dados; o texto do modo console fica oculto.
        with redirect_stdout(io.StringIO()):
            return scan_system(monitor_duration=5)

    def terminate_process(self, pid, expected_name, expected_create_time):
        """Encerra somente o processo escolhido e validado pelo usuário na tela."""
        return terminate_user_process(pid, expected_name, expected_create_time)

    def close_app(self):
        """Fecha a janela principal quando a pessoa usa o botão da interface."""
        if self.window is not None:
            self.window.destroy()

    def optimizer_overview(self):
        """Carrega os recursos opcionais sem fazer alterações no computador."""
        return {
            "disks": disk_overview(),
            "temp_cleanup": preview_temp_cleanup(),
            "startup": startup_overview(),
            "power_plans": power_plan_overview(),
        }

    def clean_temp(self, selected_paths):
        return clean_temp_files(selected_paths)

    def set_startup(self, name, enabled):
        return set_startup_enabled(name, bool(enabled))

    def set_power_plan(self, guid):
        return activate_power_plan(guid)

    def live_sample(self):
        sample = live_system_sample(
            self.process_cache,
            self.previous_disk_io,
            self.previous_sample_time,
        )
        self.previous_disk_io = sample["disk_io"]
        self.previous_sample_time = sample["timestamp"]
        return {key: value for key, value in sample.items() if key not in {"disk_io", "timestamp"}}


def launch_gui():
    try:
        import webview
    except ImportError:
        if getattr(sys, "frozen", False) and sys.platform == "win32":
            import ctypes

            ctypes.windll.user32.MessageBoxW(
                None,
                "O Shadow não conseguiu iniciar a interface. Verifique se o Microsoft Edge WebView2 Runtime está instalado.",
                "Shadow | PC Optimizer",
                0x10,
            )
            return
        print(
            "O Shadow precisa do pywebview para abrir a interface HTML/CSS.\n"
            "No CachyOS, use um ambiente virtual para instalar as dependências:\n"
            "  python -m venv .venv\n"
            "  source .venv/bin/activate\n"
            "  python -m pip install -r requirements.txt\n"
            "  python main.py",
            file=sys.stderr,
        )
        return

    page = Path(__file__).parent / "ui" / "index.html"
    api = ShadowApi()
    window = webview.create_window(
        "Shadow | PC Optimizer",
        str(page),
        js_api=api,
        width=1120,
        height=780,
        min_size=(900, 650),
        background_color="#0b0814",
    )
    api.window = window
    if sys.platform == "win32":
        # O pacote Windows usa somente Edge WebView2/WinForms, sem incluir Qt/GTK.
        webview.start(gui="edgechromium")
    else:
        webview.start()


if __name__ == "__main__":
    launch_gui()
