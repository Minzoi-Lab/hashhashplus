```python
import os
import sys
import time
from code import CommandEngine, CommandResult
from rich.console import Console
from rich.panel import Panel
from rich.text import Text


class TerminalInput:
    def __init__(self):
        self.history = []
        self.history_index = 0

    def read(self, prompt):
        if os.name == "nt":
            return self._windows(prompt)

        return self._unix(prompt)

    def _draw(self, prompt, text, cursor):
        sys.stdout.write("\r\033[2K")
        sys.stdout.write(prompt + text)

        if len(text) > cursor:
            sys.stdout.write(
                f"\033[{len(text) - cursor}D"
            )

        sys.stdout.flush()

    def _windows(self, prompt):
        import msvcrt

        buffer = ""
        cursor = 0
        self.history_index = len(self.history)

        sys.stdout.write(prompt)
        sys.stdout.flush()

        while True:
            key = msvcrt.getwch()

            if key == "\r":
                sys.stdout.write("\n")
                sys.stdout.flush()

                if buffer:
                    self.history.append(buffer)

                return buffer

            if key == "\x03":
                raise KeyboardInterrupt

            if key == "\x04":
                raise EOFError

            if key == "\x0c":
                os.system("cls")
                self._draw(prompt, buffer, cursor)
                continue

            if key == "\x08":
                if cursor > 0:
                    buffer = (
                        buffer[:cursor - 1]
                        + buffer[cursor:]
                    )
                    cursor -= 1
                    self._draw(prompt, buffer, cursor)

                continue

            if key in ("\x00", "\xe0"):
                key = msvcrt.getwch()

                if key == "H":
                    if self.history:
                        self.history_index = max(
                            0,
                            self.history_index - 1
                        )

                        buffer = self.history[
                            self.history_index
                        ]

                        cursor = len(buffer)
                        self._draw(prompt, buffer, cursor)

                elif key == "P":
                    if self.history:
                        self.history_index = min(
                            len(self.history),
                            self.history_index + 1
                        )

                        if self.history_index < len(self.history):
                            buffer = self.history[
                                self.history_index
                            ]
                        else:
                            buffer = ""

                        cursor = len(buffer)
                        self._draw(prompt, buffer, cursor)

                elif key == "K":
                    if cursor > 0:
                        cursor -= 1
                        self._draw(prompt, buffer, cursor)

                elif key == "M":
                    if cursor < len(buffer):
                        cursor += 1
                        self._draw(prompt, buffer, cursor)

                elif key == "G":
                    cursor = 0
                    self._draw(prompt, buffer, cursor)

                elif key == "O":
                    cursor = len(buffer)
                    self._draw(prompt, buffer, cursor)

                elif key == "S":
                    if cursor < len(buffer):
                        buffer = (
                            buffer[:cursor]
                            + buffer[cursor + 1:]
                        )
                        self._draw(prompt, buffer, cursor)

                continue

            if key.isprintable():
                buffer = (
                    buffer[:cursor]
                    + key
                    + buffer[cursor:]
                )

                cursor += 1
                self._draw(prompt, buffer, cursor)

    def _unix(self, prompt):
        import termios
        import tty

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)

        buffer = ""
        cursor = 0
        self.history_index = len(self.history)

        sys.stdout.write(prompt)
        sys.stdout.flush()

        try:
            tty.setraw(fd)

            while True:
                key = sys.stdin.read(1)

                if key in ("\r", "\n"):
                    sys.stdout.write("\n")
                    sys.stdout.flush()

                    if buffer:
                        self.history.append(buffer)

                    return buffer

                if key == "\x03":
                    raise KeyboardInterrupt

                if key == "\x04":
                    raise EOFError

                if key == "\x0c":
                    sys.stdout.write("\033[2J\033[H")
                    self._draw(prompt, buffer, cursor)
                    continue

                if key == "\x7f":
                    if cursor > 0:
                        buffer = (
                            buffer[:cursor - 1]
                            + buffer[cursor:]
                        )
                        cursor -= 1
                        self._draw(prompt, buffer, cursor)

                    continue

                if key == "\x1b":
                    sequence = sys.stdin.read(2)

                    if sequence == "[A":
                        if self.history:
                            self.history_index = max(
                                0,
                                self.history_index - 1
                            )

                            buffer = self.history[
                                self.history_index
                            ]

                            cursor = len(buffer)
                            self._draw(
                                prompt,
                                buffer,
                                cursor
                            )

                    elif sequence == "[B":
                        if self.history:
                            self.history_index = min(
                                len(self.history),
                                self.history_index + 1
                            )

                            if self.history_index < len(self.history):
                                buffer = self.history[
                                    self.history_index
                                ]
                            else:
                                buffer = ""

                            cursor = len(buffer)
                            self._draw(
                                prompt,
                                buffer,
                                cursor
                            )

                    elif sequence == "[C":
                        if cursor < len(buffer):
                            cursor += 1
                            self._draw(
                                prompt,
                                buffer,
                                cursor
                            )

                    elif sequence == "[D":
                        if cursor > 0:
                            cursor -= 1
                            self._draw(
                                prompt,
                                buffer,
                                cursor
                            )

                    elif sequence == "[H":
                        cursor = 0
                        self._draw(
                            prompt,
                            buffer,
                            cursor
                        )

                    elif sequence == "[F":
                        cursor = len(buffer)
                        self._draw(
                            prompt,
                            buffer,
                            cursor
                        )

                    continue

                if key.isprintable():
                    buffer = (
                        buffer[:cursor]
                        + key
                        + buffer[cursor:]
                    )

                    cursor += 1
                    self._draw(
                        prompt,
                        buffer,
                        cursor
                    )

        finally:
            termios.tcsetattr(
                fd,
                termios.TCSADRAIN,
                old_settings
            )


def show_cancel_warning(console):
    console.print(
        Panel(
            "Use [bold]exit[/bold] if you are trying to close Hash++.",
            border_style="dark_orange",
            padding=(0, 1)
        )
    )

    time.sleep(5)

    console.clear()


def print_result(console, result):
    if result.output == "\f":
        console.clear()
        return

    if not result.output:
        return

    if result.is_error:
        console.print(
            Text(
                result.output,
                style="indian_red"
            )
        )
    else:
        console.print(result.output)


def main():
    console = Console()
    engine = CommandEngine()
    terminal = TerminalInput()

    console.clear()

    console.print(
        Panel(
            "[bold]Hash++[/bold]\n"
            "[dim]Command interface[/dim]\n\n"
            "Type [bold]help[/bold] for commands.",
            border_style="dark_orange",
            padding=(1, 2)
        )
    )

    while True:
        try:
            command = terminal.read(
                "\033[38;5;208mhash++>\033[0m "
            )

        except EOFError:
            console.print()
            break

        except KeyboardInterrupt:
            if engine.busy:
                engine.cancel()
                console.print(
                    "\n[dark_orange]Operation cancelled.[/dark_orange]"
                )
            else:
                console.print()
                show_cancel_warning(console)

            continue

        try:
            result = engine.execute(command)

        except KeyboardInterrupt:
            engine.cancel()

            console.print(
                "[dark_orange]Operation cancelled.[/dark_orange]"
            )

            continue

        except Exception as e:
            result = CommandResult(
                f"Error: {e}",
                True
            )

        print_result(console, result)

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

                text_path = os.path.join(
                    folder,
                    "text.py"
                )

                if not os.path.isfile(text_path):
                    console.print(
                        "[indian_red]Restart failed: "
                        "text.py was not found.[/indian_red]"
                    )
                    continue

                os.chdir(folder)

                os.execv(
                    sys.executable,
                    [
                        sys.executable,
                        text_path
                    ]
                )

            break


if __name__ == "__main__":
    main()
```
