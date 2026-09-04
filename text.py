import os
import sys
import time

from code import CommandEngine
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.live import Live


def show_cancel_warning(console):
    warning = Text(
        "  Use Exit if you are trying to close Hash++  ",
        style="white on dark_orange"
    )

    with Live(warning, console=console, refresh_per_second=10, transient=True):
        time.sleep(5)


def main():
    engine = CommandEngine()
    console = Console()

    console.print(
        Panel(
            "Hash++\n[dim]Type help for commands, or exit to quit.[/dim]",
            border_style="dark_orange"
        )
    )

    while True:
        try:
            command = console.input("[dark_orange]hash++>[/dark_orange] ")
        except (EOFError, KeyboardInterrupt):
            if engine.busy:
                engine.cancel()
                console.print("[dark_orange]Operation cancelled.[/dark_orange]")
            else:
                show_cancel_warning(console)
            continue

        try:
            result = engine.execute(command)
        except KeyboardInterrupt:
            engine.cancel()
            console.print("[dark_orange]Operation cancelled.[/dark_orange]")
            continue

        if result.output == "\f":
            console.clear()
        elif result.output:
            style = "indian_red" if result.is_error else ""
            console.print(Text(result.output, style=style))

        if result.should_exit:
            if result.restart:
                restart_path = result.restart_path

                if not restart_path:
                    restart_path = os.path.join(
                        os.path.dirname(os.path.abspath(__file__)),
                        "code.py"
                    )

                os.execv(sys.executable, [sys.executable, restart_path])

            break


if __name__ == "__main__":
    main()