import os
import sys
import subprocess
import hashlib
from dataclasses import dataclass


@dataclass
class CommandResult:
    output: str = ""
    is_error: bool = False
    should_exit: bool = False
    restart: bool = False


class CommandEngine:
    def execute(self, command):
        command = command.strip()

        if not command:
            return CommandResult()

        parts = command.split(maxsplit=1)
        name = parts[0].lower()
        argument = parts[1] if len(parts) > 1 else ""

        if name == "help":
            return CommandResult(
                "Available commands:\n"
                "  help                 Show this help message\n"
                "  hash <text>          Hash text using SHA-256\n"
                "  clear                Clear the screen\n"
                "  restart              Restart Hash++\n"
                "  exit                 Exit Hash++"
            )

        if name == "hash":
            if not argument:
                return CommandResult(
                    "Usage: hash <text>",
                    True
                )

            result = hashlib.sha256(argument.encode()).hexdigest()
            return CommandResult(result)

        if name == "clear":
            return CommandResult("\f")

        if name == "restart":
            return CommandResult(
                "Restarting...",
                should_exit=True,
                restart=True
            )

        if name in ("exit", "quit"):
            return CommandResult(
                "Goodbye.",
                should_exit=True
            )

        return CommandResult(
            f"Unknown command: {name}\nType help to see available commands.",
            True
        )


def run():
    folder = os.path.dirname(os.path.abspath(__file__))

    if os.name != "nt" and not (
        os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
    ):
        subprocess.call([sys.executable, os.path.join(folder, "text.py")])
        return

    print("Hash++")
    print()
    print("How do you want to use Hash++?")
    print("  1. UI")
    print("  2. In-terminal")
    print("  3. IDE")
    print("  4. Exit")
    print()

    choice = input("Type in a choice: ")

    if choice == "1":
        subprocess.Popen(
            [sys.executable, os.path.join(folder, "gui.py")],
            creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0
        )
    elif choice == "2":
        subprocess.call([sys.executable, os.path.join(folder, "text.py")])
    elif choice == "3":
        print("Coming soon..")
    elif choice == "4":
        return
    else:
        print("Not a valid choice, closing..")


if __name__ == "__main__":
    run()
