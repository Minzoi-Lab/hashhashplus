"""Terminal interface for Hash++."""

import os
import sys

from code import CommandEngine
from rich.console import Console
from rich.panel import Panel
from rich.text import Text


def main():
	engine = CommandEngine()
	console = Console()
	console.print(Panel("Hash++\n[dim]Type help for commands, or exit to quit.[/dim]", border_style="dark_orange"))
	while True:
		try:
			command = console.input("[dark_orange]hash++>[/dark_orange] ")
		except (EOFError, KeyboardInterrupt):
			console.print("\n[dim]Goodbye.[/dim]")
			break
		result = engine.execute(command)
		if result.output == "\f":
			console.clear()
		elif result.output:
			style = "indian_red" if result.is_error else ""
			console.print(Text(result.output, style=style))
		if result.should_exit:
			if result.restart:
				os.execv(sys.executable, [sys.executable, os.path.abspath(__file__)])
			break


if __name__ == "__main__":
	main()