"""Interface gráfica do Friendly PC Optimizer, feita com Tkinter."""

import io
import random
import queue
import sys
import threading
from contextlib import redirect_stdout

try:
    import tkinter as tk
    from tkinter import ttk
except ImportError as error:
    # Em algumas distribuições Linux, Tk precisa ser instalado pelo gerenciador
    # de pacotes do sistema antes de o módulo Tkinter conseguir abrir a janela.
    tk = None
    ttk = None

from main import scan_system


BACKGROUND = "#100b1c"
PANEL = "#1c1430"
TEXT = "#f7f1ff"
MUTED = "#b3a6c9"
BLUE = "#b48aff"
GREEN = "#e18bff"
ORANGE = "#d4a7ff"
PURPLE = "#a855f7"


class OptimizerApp:
    """Janela principal; a coleta roda numa thread para não travar os controles."""

    def __init__(self, root):
        self.root = root
        self.root.title("Shadow | PC Optimizer")
        self.root.geometry("1000x720")
        self.root.minsize(820, 620)
        self.root.configure(bg=BACKGROUND)
        self.results = queue.Queue()
        self.scan_running = False
        self.cpu_history = []
        self.ram_history = []

        self._configure_styles()
        self._build_welcome()

    def _configure_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background=BACKGROUND)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("TLabel", background=BACKGROUND, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Panel.TLabel", background=PANEL, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=PANEL, foreground=MUTED, font=("Segoe UI", 9))
        style.configure("Value.TLabel", background=PANEL, foreground=TEXT, font=("Segoe UI", 25, "bold"))
        style.configure("Title.TLabel", background=BACKGROUND, foreground=TEXT, font=("Segoe UI", 22, "bold"))
        style.configure("WelcomeTitle.TLabel", background=BACKGROUND, foreground=TEXT, font=("Segoe UI", 27, "bold"))
        style.configure("Welcome.TLabel", background=BACKGROUND, foreground=TEXT, font=("Segoe UI", 12))
        style.configure("WelcomeNote.TLabel", background=PANEL, foreground=MUTED, font=("Segoe UI", 11))
        style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=(14, 9))

    def _build_welcome(self):
        self.welcome_canvas = tk.Canvas(self.root, background=BACKGROUND, highlightthickness=0)
        self.welcome_canvas.pack(fill="both", expand=True)
        self.welcome_canvas.bind("<Configure>", self._draw_welcome)
        self.welcome_canvas.bind("<Motion>", self._welcome_motion)
        self.welcome_canvas.bind("<Button-1>", self._welcome_click)
        self._draw_welcome()
        self._animate_welcome()

    @staticmethod
    def _blend_color(start, end, amount):
        """Mistura duas cores hexadecimais para desenhar o degradê sem pacotes extras."""
        first = tuple(int(start[index:index + 2], 16) for index in (1, 3, 5))
        second = tuple(int(end[index:index + 2], 16) for index in (1, 3, 5))
        mixed = tuple(round(a + (b - a) * amount) for a, b in zip(first, second))
        return "#" + "".join(f"{channel:02x}" for channel in mixed)

    @staticmethod
    def _rounded_rectangle(canvas, x1, y1, x2, y2, radius, **options):
        points = [
            x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
            x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
            x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1,
        ]
        return canvas.create_polygon(points, smooth=True, splinesteps=16, **options)

    def _draw_welcome(self, _event=None):
        canvas = self.welcome_canvas
        width = max(canvas.winfo_width(), 820)
        height = max(canvas.winfo_height(), 620)
        canvas.delete("all")

        # Fundo roxo em degradê, desenhado em faixas para manter o app sem dependências extras.
        for y in range(0, height, 3):
            color = self._blend_color("#090b19", "#321057", y / max(height, 1))
            canvas.create_line(0, y, width, y, fill=color, width=3)

        # Aros luminosos decorativos no fundo.
        canvas.create_oval(width * .68, -height * .55, width * 1.28, height * .45, outline="#32185a", width=2)
        canvas.create_oval(width * .72, -height * .48, width * 1.22, height * .38, outline="#261846", width=2)
        canvas.create_oval(-width * .28, height * .54, width * .25, height * 1.24, outline="#261846", width=2)

        self.particle_items = []
        for _ in range(48):
            x = random.randint(8, width - 8)
            y = random.randint(8, height - 8)
            size = random.choice((1, 1, 2, 3))
            color = random.choice(("#7350a1", "#9b70d0", "#c9a7fa"))
            item = canvas.create_oval(x, y, x + size, y + size, fill=color, outline="")
            self.particle_items.append((item, random.choice((-.35, -.2, .2, .35)), random.choice((-.25, -.15, .15, .25))))

        center_x = width / 2
        canvas.create_text(center_x, height * .115, text="P C   P E R F O R M A N C E   •   S M A R T   A N A L Y S I S",
                           fill="#d6b9ff", font=("Segoe UI", 8, "bold"))

        # Símbolo geométrico e título principal.
        emblem_y = height * .24
        canvas.create_oval(center_x - 34, emblem_y - 34, center_x + 34, emblem_y + 34,
                           fill="#24123e", outline="#9b5de5", width=2)
        canvas.create_polygon(center_x, emblem_y - 22, center_x + 16, emblem_y,
                              center_x, emblem_y + 22, center_x - 16, emblem_y,
                              fill="#c084fc", outline="")
        canvas.create_text(center_x + 1, height * .345 + 2, text="S H A D O W", fill="#6b3c91",
                           font=("Segoe UI", 37, "bold"))
        canvas.create_text(center_x, height * .345, text="S H A D O W", fill=TEXT,
                           font=("Segoe UI", 37, "bold"))
        canvas.create_text(center_x, height * .415, text="Seu PC em foco. Sem promessas mágicas.",
                           fill="#d7c5ec", font=("Segoe UI", 13))

        card_width = min(width - 80, 680)
        card_left, card_right = center_x - card_width / 2, center_x + card_width / 2
        card_top, card_bottom = height * .50, height * .70
        self._rounded_rectangle(canvas, card_left, card_top, card_right, card_bottom, 20,
                                fill="#171225", outline="#553478", width=1)
        canvas.create_text(center_x, card_top + 27, text="A N T E S   D E   C O M E Ç A R", fill="#d8b4fe",
                           font=("Segoe UI", 8, "bold"))
        disclaimer = (
            "O Shadow não faz milagres nem garante mais FPS. Ele mostra o uso de CPU, memória e processos, "
            "sem fechar programas ou alterar o computador. Em PCs muito fracos ou antigos, o software pode "
            "ajudar pouco; às vezes, a melhora necessária depende da troca de peças."
        )
        canvas.create_text(center_x, card_top + 91, text=disclaimer, fill="#d0c5dd",
                           font=("Segoe UI", 10), width=card_width - 54, justify="center")

        button_width, button_height = 250, 58
        button_center_y = height * .805
        self.welcome_button_bounds = (
            center_x - button_width / 2, button_center_y - button_height / 2,
            center_x + button_width / 2, button_center_y + button_height / 2,
        )
        x1, y1, x2, y2 = self.welcome_button_bounds
        self.button_glow = self._rounded_rectangle(canvas, x1 - 5, y1 - 5, x2 + 5, y2 + 5, 22,
                                                   fill="", outline="#8038c7", width=2)
        self._rounded_rectangle(canvas, x1, y1, x2, y2, 18, fill="#8b3dd1", outline="#d4a4ff", width=1)
        canvas.create_text(center_x - 8, button_center_y, text="A N A L I S A R", fill="white",
                           font=("Segoe UI", 10, "bold"))
        canvas.create_text(center_x + 74, button_center_y - 1, text="→", fill="white",
                           font=("Segoe UI", 17, "bold"))
        canvas.create_text(center_x, height * .91, text="L E I T U R A   S E G U R A   •   N E N H U M A   A L T E R A Ç Ã O   A U T O M Á T I C A",
                           fill="#9f8aad", font=("Segoe UI", 7, "bold"))

    def _animate_welcome(self):
        if not hasattr(self, "welcome_canvas") or not self.welcome_canvas.winfo_exists():
            return
        canvas = self.welcome_canvas
        width, height = canvas.winfo_width(), canvas.winfo_height()
        for item, speed_x, speed_y in getattr(self, "particle_items", []):
            canvas.move(item, speed_x, speed_y)
            x1, y1, x2, y2 = canvas.coords(item)
            if x1 < 2:
                canvas.move(item, width - x1, 0)
            elif x2 > width - 2:
                canvas.move(item, -x2, 0)
            if y1 < 2:
                canvas.move(item, 0, height - y1)
            elif y2 > height - 2:
                canvas.move(item, 0, -y2)

        if hasattr(self, "button_glow"):
            self.glow_phase = getattr(self, "glow_phase", 0) + .16
            glow_width = 2 if int(self.glow_phase * 2) % 2 == 0 else 3
            canvas.itemconfigure(self.button_glow, width=glow_width)
        self.root.after(50, self._animate_welcome)

    def _welcome_motion(self, event):
        x1, y1, x2, y2 = self.welcome_button_bounds
        hovering = x1 <= event.x <= x2 and y1 <= event.y <= y2
        self.welcome_canvas.configure(cursor="hand2" if hovering else "")

    def _welcome_click(self, event):
        x1, y1, x2, y2 = self.welcome_button_bounds
        if x1 <= event.x <= x2 and y1 <= event.y <= y2:
            self.start_analysis()

    def start_analysis(self):
        """Sai da tela inicial e começa a primeira leitura após o clique do usuário."""
        self.welcome_canvas.destroy()
        self._build_window()
        self.root.after(200, self._check_results)
        self.refresh()

    def _build_window(self):
        outer = ttk.Frame(self.root, padding=22)
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer)
        header.pack(fill="x", pady=(0, 18))
        title_area = ttk.Frame(header)
        title_area.pack(side="left", fill="x", expand=True)
        ttk.Label(title_area, text="Shadow", style="Title.TLabel").pack(anchor="w")
        self.status_label = ttk.Label(title_area, text="Pronto para analisar", foreground=MUTED)
        self.status_label.pack(anchor="w", pady=(4, 0))
        self.refresh_button = ttk.Button(header, text="Atualizar análise", command=self.refresh)
        self.refresh_button.pack(side="right", anchor="center")

        cards = ttk.Frame(outer)
        cards.pack(fill="x", pady=(0, 14))
        self.cpu_value = self._metric_card(cards, "CPU em uso", BLUE, 0)
        self.ram_value = self._metric_card(cards, "RAM em uso", GREEN, 1)
        self.available_value = self._metric_card(cards, "RAM disponível", ORANGE, 2)

        body = ttk.Frame(outer)
        body.pack(fill="both", expand=True)
        left = ttk.Frame(body, style="Panel.TFrame", padding=16)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))
        right = ttk.Frame(body, style="Panel.TFrame", padding=16)
        right.pack(side="left", fill="both", expand=True, padx=(8, 0))

        ttk.Label(left, text="Histórico de recursos", style="Panel.TLabel", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        ttk.Label(left, text="Amostras recentes de CPU e RAM", style="Muted.TLabel").pack(anchor="w", pady=(3, 10))
        self.chart = tk.Canvas(left, height=250, background=PANEL, highlightthickness=0)
        self.chart.pack(fill="both", expand=True)
        self.chart.bind("<Configure>", lambda _event: self._draw_chart())
        legend = ttk.Frame(left, style="Panel.TFrame")
        legend.pack(anchor="w", pady=(10, 0))
        ttk.Label(legend, text="● CPU", style="Panel.TLabel", foreground=BLUE).pack(side="left", padx=(0, 14))
        ttk.Label(legend, text="● RAM", style="Panel.TLabel", foreground=GREEN).pack(side="left")

        ttk.Label(right, text="Diagnóstico", style="Panel.TLabel", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        self.diagnosis_label = ttk.Label(right, text="Aguardando leitura...", style="Panel.TLabel", wraplength=380, justify="left")
        self.diagnosis_label.pack(anchor="w", pady=(10, 14))
        ttk.Label(right, text="Processos com maior uso de RAM", style="Panel.TLabel", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.processes_label = ttk.Label(right, text="Aguardando leitura...", style="Panel.TLabel", justify="left")
        self.processes_label.pack(anchor="w", pady=(8, 14))
        ttk.Label(right, text="Recomendações", style="Panel.TLabel", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.recommendations_label = ttk.Label(right, text="Aguardando leitura...", style="Panel.TLabel", wraplength=380, justify="left")
        self.recommendations_label.pack(anchor="w", pady=(8, 0))

        self.footer_label = ttk.Label(outer, text="A leitura é informativa e não mede FPS de jogos.", foreground=MUTED)
        self.footer_label.pack(anchor="w", pady=(14, 0))

    @staticmethod
    def _metric_card(parent, title, color, column):
        card = ttk.Frame(parent, style="Panel.TFrame", padding=16)
        card.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 6, 0 if column == 2 else 6))
        parent.columnconfigure(column, weight=1)
        ttk.Label(card, text=title, style="Muted.TLabel").pack(anchor="w")
        value = ttk.Label(card, text="--", style="Value.TLabel", foreground=color)
        value.pack(anchor="w", pady=(4, 0))
        return value

    def refresh(self):
        if self.scan_running:
            return
        self.scan_running = True
        self.refresh_button.configure(state="disabled")
        self.status_label.configure(text="Analisando... isso pode levar alguns segundos")
        threading.Thread(target=self._scan_in_background, daemon=True).start()

    def _scan_in_background(self):
        try:
            # O scanner também imprime seu relatório para uso no terminal. A GUI
            # usa os dados retornados e mantém esse texto fora da janela.
            with redirect_stdout(io.StringIO()):
                report = scan_system(monitor_duration=5)
            self.results.put((report, None))
        except Exception as error:
            self.results.put((None, str(error)))

    def _check_results(self):
        try:
            report, error = self.results.get_nowait()
        except queue.Empty:
            self.root.after(200, self._check_results)
            return

        self.scan_running = False
        self.refresh_button.configure(state="normal")
        if error:
            self.status_label.configure(text="Não foi possível concluir a análise")
            self.diagnosis_label.configure(text=f"Erro durante a leitura: {error}")
        else:
            self._show_report(report)
        self.root.after(200, self._check_results)

    def _show_report(self, report):
        memory = report["memory"]
        self.cpu_value.configure(text=f"{report['cpu_percent']:.1f}%")
        self.ram_value.configure(text=f"{memory['used_percent']:.1f}%")
        self.available_value.configure(text=f"{memory['available_gb']:.1f} GB")

        level = report["diagnosis"]["level"]
        self.diagnosis_label.configure(
            text=f"Nível {level}\n{report['diagnosis']['message']}\n\n"
                f"Sistema: {report['system']['name']} {report['system']['release']}"
        )
        process_lines = [
            f"{item['name']}  ·  {item['ram_mb']:.0f} MB"
            for item in report["top_ram_processes"][:5]
        ]
        self.processes_label.configure(text="\n".join(process_lines) or "Nenhum processo disponível.")
        self.recommendations_label.configure(
            text="\n".join(f"• {item}" for item in report["recommendations"])
        )

        self.cpu_history.extend(report["monitoring"]["cpu_samples"])
        self.ram_history.extend(report["monitoring"]["ram_samples"])
        self.cpu_history = self.cpu_history[-30:]
        self.ram_history = self.ram_history[-30:]
        self._draw_chart()
        mode = "Windows 10/11" if report["system"]["is_windows"] else "modo de desenvolvimento"
        self.status_label.configure(text=f"{report['system']['name']} {report['system']['release']} · {mode}")

    def _draw_chart(self):
        if not hasattr(self, "chart"):
            return
        canvas = self.chart
        canvas.delete("all")
        width = max(canvas.winfo_width(), 200)
        height = max(canvas.winfo_height(), 160)
        left, right, top, bottom = 36, width - 12, 14, height - 26

        for value in (0, 25, 50, 75, 100):
            y = bottom - (bottom - top) * value / 100
            canvas.create_line(left, y, right, y, fill="#2b3748")
            canvas.create_text(left - 8, y, text=str(value), fill=MUTED, anchor="e", font=("Segoe UI", 8))

        self._draw_line(canvas, self.cpu_history, BLUE, left, right, top, bottom)
        self._draw_line(canvas, self.ram_history, GREEN, left, right, top, bottom)

    @staticmethod
    def _draw_line(canvas, values, color, left, right, top, bottom):
        if not values:
            return
        span = max(right - left, 1)
        points = []
        for index, value in enumerate(values):
            x = left + (span * index / max(len(values) - 1, 1))
            y = bottom - (bottom - top) * max(0, min(value, 100)) / 100
            points.extend((x, y))
        if len(points) == 2:
            canvas.create_oval(points[0] - 3, points[1] - 3, points[0] + 3, points[1] + 3, fill=color, outline="")
        else:
            canvas.create_line(*points, fill=color, width=2, smooth=True)


def launch_gui():
    if tk is None:
        print(
            "Não foi possível abrir a interface: a biblioteca gráfica Tk está ausente.\n"
            "No CachyOS/Arch Linux, instale-a com: sudo pacman -S tk\n"
            "Depois, execute novamente: python main.py",
            file=sys.stderr,
        )
        return

    root = tk.Tk()
    OptimizerApp(root)
    root.mainloop()


if __name__ == "__main__":
    launch_gui()
