"""Command engine shared by the Hash++ graphical and text interfaces."""

from __future__ import annotations

import ast
import hashlib
import operator
import subprocess
import shlex
import urllib.error
import urllib.request
from pathlib import Path
from dataclasses import dataclass
from typing import Callable


@dataclass
class CommandResult:
	output: str = ""
	should_exit: bool = False
	is_error: bool = False
	restart: bool = False


class CommandEngine:
	"""Parse and execute Hash++ commands without depending on a user interface."""

	def __init__(self):
		self.commands: dict[str, Callable[[list[str]], CommandResult]] = {
			"help": self._help,
			"calc": self._calc,
			"calculate": self._calc,
			"hash": self._hash,
			"curl": self._curl,
			"update": self._update,
			"echo": self._echo,
			"clear": lambda arguments: CommandResult("\f"),
			"exit": self._exit,
			"quit": self._exit,
		}

	def execute(self, command: str) -> CommandResult:
		command = command.strip()
		if not command:
			return CommandResult()
		try:
			parts = shlex.split(command)
		except ValueError as error:
			return CommandResult(f"Syntax error: {error}", is_error=True)
		handler = self.commands.get(parts[0].lower())
		if handler is None:
			return CommandResult(
				f"Unknown command: {parts[0]}. Type 'help' for available commands.",
				is_error=True,
			)
		try:
			return handler(parts[1:])
		except (ValueError, TypeError) as error:
			return CommandResult(f"Error: {error}", is_error=True)

	def _help(self, arguments: list[str]) -> CommandResult:
		return CommandResult(
			"Available commands:\n"
			"  calc <expression>       Calculate +, -, *, /, %, and **\n"
			"  hash <algorithm> <text> Hash text (sha256 by default)\n"
			"  curl <url>              Fetch a URL\n"
			"  update                  Compare files with the latest Git commit\n"
			"  echo <text>             Print text\n"
			"  clear                   Clear the output\n"
			"  exit                    Close Hash++"
		)

	def _calc(self, arguments: list[str]) -> CommandResult:
		if not arguments:
			raise ValueError("Usage: calc <expression>")
		expression = " ".join(arguments)
		return CommandResult(f"{expression} = {_safe_calculate(expression)}")

	def _hash(self, arguments: list[str]) -> CommandResult:
		if not arguments:
			raise ValueError("Usage: hash [algorithm] <text>")
		algorithms = set(hashlib.algorithms_available)
		algorithm = arguments[0].lower()
		if algorithm in algorithms:
			if len(arguments) < 2:
				raise ValueError("Usage: hash [algorithm] <text>")
			text = " ".join(arguments[1:])
		else:
			algorithm = "sha256"
			text = " ".join(arguments)
		digest = hashlib.new(algorithm, text.encode("utf-8")).hexdigest()
		return CommandResult(digest)

	def _echo(self, arguments: list[str]) -> CommandResult:
		return CommandResult(" ".join(arguments))

	def _curl(self, arguments: list[str]) -> CommandResult:
		if len(arguments) != 1:
			raise ValueError("Usage: curl <url>")
		url = arguments[0]
		if not url.startswith(("http://", "https://")):
			raise ValueError("URL must start with http:// or https://")
		request = urllib.request.Request(url, headers={"User-Agent": "HashPlus/1.0"})
		try:
			with urllib.request.urlopen(request, timeout=10) as response:
				body = response.read().decode("utf-8", errors="replace")
				return CommandResult(f"HTTP {response.status}\n{body}")
		except urllib.error.HTTPError as error:
			raise ValueError(f"HTTP {error.code}: {error.reason}") from error
		except urllib.error.URLError as error:
			raise ValueError(f"Could not reach URL: {error.reason}") from error

	def _update(self, arguments: list[str]) -> CommandResult:
		if arguments:
			raise ValueError("Usage: update")
		repository = _find_repository()
		if repository is None:
			raise ValueError("Could not find the Hash++ Git repository")
		try:
			_git(["fetch", "origin"], repository, 30)
			behind = int(_git(["rev-list", "HEAD..origin/main", "--count"], repository, 10))
			if behind == 0:
				return CommandResult("Hash++ is already up to date.")
			_git(["pull", "--ff-only", "origin", "main"], repository, 30)
		except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
			raise ValueError(f"Git update check failed: {error}") from error
		return CommandResult(
			f"Updated Hash++ with {behind} new commit{'s' if behind != 1 else ''}. Restarting...",
			should_exit=True,
			restart=True,
		)

	def _exit(self, arguments: list[str]) -> CommandResult:
		return CommandResult("Goodbye.", should_exit=True)


_OPERATORS = {
	ast.Add: operator.add,
	ast.Sub: operator.sub,
	ast.Mult: operator.mul,
	ast.Div: operator.truediv,
	ast.FloorDiv: operator.floordiv,
	ast.Mod: operator.mod,
	ast.Pow: operator.pow,
	ast.USub: operator.neg,
	ast.UAdd: operator.pos,
}


def _safe_calculate(expression: str) -> int | float:
	try:
		tree = ast.parse(expression, mode="eval")
	except SyntaxError as error:
		raise ValueError("invalid arithmetic expression") from error
	result = _calculate_node(tree.body)
	if isinstance(result, float) and result.is_integer():
		return int(result)
	return result


def _calculate_node(node: ast.AST) -> int | float:
	if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
		return node.value
	if isinstance(node, ast.BinOp) and type(node.op) in _OPERATORS:
		left = _calculate_node(node.left)
		right = _calculate_node(node.right)
		if isinstance(node.op, ast.Pow) and abs(right) > 1000:
			raise ValueError("exponent is too large")
		try:
			return _OPERATORS[type(node.op)](left, right)
		except ZeroDivisionError as error:
			raise ValueError("cannot divide by zero") from error
	if isinstance(node, ast.UnaryOp) and type(node.op) in _OPERATORS:
		return _OPERATORS[type(node.op)](_calculate_node(node.operand))
	raise ValueError("only numbers and arithmetic operators are allowed")


def run_command(command: str) -> CommandResult:
	return CommandEngine().execute(command)


def _find_repository() -> str | None:
	start = Path(__file__).resolve().parent
	candidates = [start, start / "hashplusplus"]
	candidates.extend(start.parents)
	for candidate in candidates:
		if (candidate / ".git").exists():
			return str(candidate)
	return None


def commits_behind() -> int | None:
	repository = _find_repository()
	if repository is None:
		return None
	try:
		_git(["fetch", "origin"], repository, 30)
		return int(_git(["rev-list", "HEAD..origin/main", "--count"], repository, 10))
	except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError):
		return None


def _git(arguments: list[str], repository: str, timeout: int) -> str:
	result = subprocess.run(
		["git", *arguments],
		cwd=repository,
		check=True,
		capture_output=True,
		text=True,
		timeout=timeout,
	)
	return result.stdout.strip()