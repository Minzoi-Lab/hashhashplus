import tkinter as tk
from tkinter import scrolledtext, ttk
import os
import subprocess
import sys
import threading
from code import CommandEngine, CommandResult

THEMES = {
    "light": {
        "bg": "#f1eee8",
        "panel": "#fbfaf7",
        "ink": "#252525",
        "quiet": "#77736d",
        "line": "#d8d2c9",
        "accent": "#c4512d",
        "accent_active": "#a83f22",
        "error": "#a52d2d",
    },
    "dark": {
        "bg": "#1c1d1b",
        "panel": "#252724",
        "ink": "#f1eee8",
        "quiet": "#aaa79f",
        "line": "#3b3d38",
        "accent": "#e07650",
        "accent_active": "#f08a65",
        "error": "#ff9186",
    },
}


class HashGui:
    def __init__(self, root):
        self.root = root
        self.engine = CommandEngine()
        self.theme_name = "dark"
        self.colors = THEMES[self.theme_name]
        self.busy = False
        self.warning_after = None

        self.root.title("HASH++")
        self.root.geometry("860x580")
        self.root.minsize(540, 380)
        self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        self.style = ttk.Style(root)
        self.style.theme_use("clam")

        self._build()
        self._paint()
        self._write("Type help to see what is available.")
        self.command.focus_set()

        self.root.bind_all("<Control-c>", self.handle_ctrl_c)

    def _build(self):
        self.top = tk.Frame(self.root, padx=28, pady=22)
        self.top.grid(row=0, column=0, sticky="ew")

        self.mark = tk.Label(
            self.top,
            text="H+",
            font=("Consolas", 17, "bold")
        )
        self.mark.pack(side=tk.LEFT, padx=(0, 13))

        self.name = tk.Label(
            self.top,
            text="HASH++",
            font=("Segoe UI", 18, "bold")
        )
        self.name.pack(side=tk.LEFT)

        self.session = tk.Label(
            self.top,
            text="LOCAL SESSION",
            font=("Segoe UI", 8, "bold")
        )
        self.session.pack(side=tk.LEFT, padx=(14, 0), pady=(4, 0))

        self.theme_button = ttk.Button(
            self.top,
            text="Light",
            command=self.toggle_theme
        )
        self.theme_button.pack(side=tk.RIGHT)

        self.body = tk.Frame(self.root, padx=28, pady=0)
        self.body.grid(row=1, column=0, sticky="nsew")
        self.body.columnconfigure(0, weight=1)
        self.body.rowconfigure(0, weight=1)

        self.output = scrolledtext.ScrolledText(
            self.body,
            wrap=tk.WORD,
            state="disabled",
            relief=tk.FLAT,
            borderwidth=0,
            padx=18,
            pady=18,
            font=("Cascadia Mono", 11),
        )
        self.output.grid(row=0, column=0, sticky="nsew")

        self.output.tag_configure(
            "prompt",
            font=("Cascadia Mono", 11, "bold")
        )

        self.output.tag_configure(
            "error",
            font=("Cascadia Mono", 11)
        )

        self.bottom = tk.Frame(self.root, padx=28, pady=18)
        self.bottom.grid(row=2, column=0, sticky="ew")

        self.footer = tk.Frame(self.bottom)
        self.footer.pack(fill=tk.X, pady=(0, 14))

        self.rule = tk.Frame(self.footer, height=1)
        self.rule.pack(fill=tk.X, pady=(0, 13))

        self.status = tk.Label(
            self.footer,
            text="READY",
            anchor="w",
            font=("Segoe UI", 8, "bold")
        )
        self.status.pack(side=tk.LEFT)

        self.cancel_hint = tk.Label(
            self.footer,
            text="",
            anchor="w",
            font=("Segoe UI", 8, "bold")
        )
        self.cancel_hint.pack(side=tk.LEFT, padx=(10, 0))

        self.hint = tk.Label(
            self.footer,
            text="Enter to run  |  Ctrl+L to clear  |  Ctrl+C to cancel",
            anchor="e",
            font=("Segoe UI", 8)
        )
        self.hint.pack(side=tk.RIGHT)

        self.input_row = tk.Frame(self.bottom)
        self.input_row.pack(fill=tk.X)

        self.prompt = tk.Label(
            self.input_row,
            text=">",
            font=("Cascadia Mono", 13, "bold")
        )
        self.prompt.pack(side=tk.LEFT, padx=(0, 10))

        self.command = tk.Entry(
            self.input_row,
            relief=tk.FLAT,
            borderwidth=0,
            font=("Cascadia Mono", 11),
            insertwidth=2
        )
        self.command.pack(
            side=tk.LEFT,
            fill=tk.X,
            expand=True,
            ipady=9
        )

        self.run_button = ttk.Button(
            self.input_row,
            text="Run",
            command=self.submit
        )
        self.run_button.pack(
            side=tk.RIGHT,
            padx=(12, 0),
            ipadx=8,
            ipady=3
        )

        self.command.bind("<Return>", self.submit)
        self.command.bind("<Control-l>", self.clear_output)

    def _paint(self):
        colors = self.colors

        self.root.configure(bg=colors["bg"])

        for widget in (
            self.top,
            self.body,
            self.bottom,
            self.footer,
            self.input_row
        ):
            widget.configure(bg=colors["bg"])

        self.mark.configure(
            bg=colors["accent"],
            fg="#ffffff"
        )

        self.name.configure(
            bg=colors["bg"],
            fg=colors["ink"]
        )

        self.session.configure(
            bg=colors["bg"],
            fg=colors["quiet"]
        )

        self.output.configure(
            bg=colors["panel"],
            fg=colors["ink"],
            insertbackground=colors["ink"],
            selectbackground=colors["accent"]
        )

        self.output.tag_configure(
            "prompt",
            foreground=colors["accent"]
        )

        self.output.tag_configure(
            "error",
            foreground=colors["error"]
        )

        self.rule.configure(bg=colors["line"])

        self.status.configure(
            bg=colors["bg"],
            fg=colors["accent"]
        )

        self.cancel_hint.configure(
            bg=colors["bg"],
            fg=colors["accent"]
        )

        self.hint.configure(
            bg=colors["bg"],
            fg=colors["quiet"]
        )

        self.prompt.configure(
            bg=colors["bg"],
            fg=colors["accent"]
        )

        self.command.configure(
            bg=colors["panel"],
            fg=colors["ink"],
            insertbackground=colors["ink"],
            highlightthickness=1,
            highlightbackground=colors["line"],
            highlightcolor=colors["accent"]
        )

        self.style.configure(
            "TButton",
            background=colors["accent"],
            foreground="#ffffff",
            borderwidth=0,
            padding=(11, 7),
            font=("Segoe UI", 9, "bold")
        )

        self.style.map(
            "TButton",
            background=[("active", colors["accent_active"])]
        )

        self.theme_button.configure(
            text="Light" if self.theme_name == "dark" else "Dark"
        )

    def toggle_theme(self):
        self.theme_name = (
            "light"
            if self.theme_name == "dark"
            else "dark"
        )

        self.colors = THEMES[self.theme_name]
        self._paint()
        self.status.configure(text=self.theme_name.upper())

    def _write(self, text, tag=""):
        self.output.configure(state="normal")
        self.output.insert(tk.END, text + "\n", tag)
        self.output.configure(state="disabled")
        self.output.see(tk.END)

    def clear_output(self, event=None):
        self.output.configure(state="normal")
        self.output.delete("1.0", tk.END)
        self.output.configure(state="disabled")
        self.status.configure(text="CLEARED")
        return "break"

    def handle_ctrl_c(self, event=None):
        if self.busy:
            self.engine.cancel()
            self.status.configure(text="CANCELLING")
            self.cancel_hint.configure(text="Cancelling...")
            return "break"

        self.status.configure(text="READY")
        self.cancel_hint.configure(
            text="Use Exit if you are trying to close Hash++"
        )

        if self.warning_after:
            self.root.after_cancel(self.warning_after)

        self.warning_after = self.root.after(
            5000,
            self.clear_cancel_warning
        )

        return "break"

    def clear_cancel_warning(self):
        self.cancel_hint.configure(text="")
        self.warning_after = None

    def submit(self, event=None):
        if self.busy:
            return "break"

        command = self.command.get().strip()

        if not command:
            return "break"

        self._write("> " + command, "prompt")
        self.command.delete(0, tk.END)

        self.busy = True
        self.status.configure(text="RUNNING")
        self.command.configure(state="disabled")
        self.run_button.configure(state="disabled")

        worker = threading.Thread(
            target=self._run_command,
            args=(command,),
            daemon=True
        )
        worker.start()

        return "break"

    def _run_command(self, command):
        try:
            result = self.engine.execute(command)
        except KeyboardInterrupt:
            self.engine.cancel()
            result = CommandResult(
                "Operation cancelled.",
                True
            )
        except Exception as e:
            result = CommandResult(
                f"Error: {e}",
                True
            )

        self.root.after(
            0,
            self._finish_command,
            result
        )

    def _finish_command(self, result):
        self.busy = False

        self.command.configure(state="normal")
        self.run_button.configure(state="normal")

        if result.output == "\f":
            self.clear_output()
        elif result.output:
            self._write(
                result.output,
                "error" if result.is_error else ""
            )

        self.status.configure(
            text="ERROR" if result.is_error else "READY"
        )

        if result.should_exit:
            if result.restart:
                restart_path = result.restart_path

                if restart_path:
                    folder = os.path.dirname(
                        os.path.abspath(restart_path)
                    )
                else:
                    folder = os.path.dirname(
                        os.path.abspath(__file__)
                    )

                gui_path = os.path.join(folder, "gui.py")

                if not os.path.isfile(gui_path):
                    self._write(
                        "Restart failed: gui.py was not found.",
                        "error"
                    )
                    return

                try:
                    subprocess.Popen(
                        [sys.executable, gui_path],
                        cwd=folder
                    )
                except Exception as e:
                    self._write(
                        f"Restart failed: {e}",
                        "error"
                    )
                    return

            self.root.destroy()
            return

        self.command.focus_set()

    def _paint_status(self):
        self.status.configure(
            text="READY" if not self.busy else "RUNNING"
        )


if __name__ == "__main__":
    root = tk.Tk()
    HashGui(root)
    root.mainloop()