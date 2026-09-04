import os
import sys
import subprocess
import threading
import time
import json
import re
import shlex
import socket
import urllib.request
import urllib.error
from dataclasses import dataclass
from html.parser import HTMLParser


GITHUB_REPO = "https://github.com/Minzoi-Lab/hashhashplus"


@dataclass
class CommandResult:
    output: str = ""
    is_error: bool = False
    should_exit: bool = False
    restart: bool = False
    restart_path: str = ""


class HTMLTextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript", "template", "svg"}:
            self.skip += 1
            return

        if self.skip:
            return

        if tag in {
            "p", "div", "section", "article", "main", "header",
            "footer", "nav", "li", "h1", "h2", "h3", "h4",
            "h5", "h6", "br", "tr"
        }:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript", "template", "svg"}:
            if self.skip:
                self.skip -= 1
            return

        if self.skip:
            return

        if tag in {
            "p", "div", "section", "article", "main", "header",
            "footer", "nav", "li", "h1", "h2", "h3", "h4",
            "h5", "h6", "tr"
        }:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)

    def text(self):
        text = "".join(self.parts)
        lines = []

        for line in text.splitlines():
            line = re.sub(r"\s+", " ", line).strip()
            if line:
                lines.append(line)

        return "\n".join(lines)


class CommandEngine:
    def __init__(self):
        self.cancel_event = threading.Event()
        self._busy = False
        self._busy_lock = threading.Lock()

    @property
    def busy(self):
        with self._busy_lock:
            return self._busy

    def cancel(self):
        self.cancel_event.set()

    def _start(self):
        self.cancel_event.clear()
        with self._busy_lock:
            self._busy = True

    def _finish(self):
        with self._busy_lock:
            self._busy = False

    def _cancelled(self):
        return self.cancel_event.is_set()

    def execute(self, command):
        self._start()

        try:
            command = command.strip()

            if not command:
                return CommandResult()

            try:
                parts = shlex.split(command)
            except ValueError as e:
                return CommandResult(str(e), True)

            name = parts[0].lower()
            args = parts[1:]

            if name == "help":
                return CommandResult(
                    "Commands:\n"
                    "  help                    Show available commands\n"
                    "  man <command>          Show command usage\n"
                    "  clear                   Clear the screen\n"
                    "  request <url>           Make a GET request\n"
                    "  request <url> GET       Make a GET request\n"
                    "  request <url> POST text <body>\n"
                    "  request <url> POST file <path>\n"
                    "  request <url> PUT text <body>\n"
                    "  request <url> PUT file <path>\n"
                    "  request <url> PATCH text <body>\n"
                    "  request <url> PATCH file <path>\n"
                    "  request <url> DELETE    Send a DELETE request\n"
                    "  discord                 Show the Minzoi Lab Discord\n"
                    "  github                  Show the Minzoi Lab GitHub\n"
                    "  update                  Update Hash++\n"
                    "  restart                 Restart Hash++\n"
                    "  exit                    Exit Hash++"
                )

            if name == "man":
                return self._man(args)

            if name == "clear":
                return CommandResult("\f")

            if name == "discord":
                return CommandResult("https://discord.gg/hscSEBa9X")

            if name == "github":
                return CommandResult("https://github.com/Minzoi-Lab")

            if name == "request":
                return self._request(args)

            if name == "update":
                return self._update()

            if name == "restart":
                return CommandResult(
                    "Restarting Hash++...",
                    should_exit=True,
                    restart=True,
                    restart_path=os.path.abspath(__file__)
                )

            if name == "exit":
                return CommandResult("Goodbye.", should_exit=True)

            return CommandResult(
                f"Unknown command: {name}\nType help to see available commands.",
                True
            )

        finally:
            self._finish()

    def _man(self, args):
        if not args:
            return CommandResult(
                "Usage: man <command>\nExample: man request",
                True
            )

        command = args[0].lower()

        manuals = {
            "help":
                "help\n\nShows the list of available Hash++ commands.",

            "man":
                "man <command>\n\nShows the usage information for a command.",

            "clear":
                "clear\n\nClears the current output.",

            "discord":
                "discord\n\nShows the Minzoi Lab Discord invite.",

            "github":
                "github\n\nShows the GitHub organisation for Minzoi Lab.",

            "request":
                "request <url>\n"
                "request <url> GET\n"
                "request <url> POST text <body>\n"
                "request <url> POST file <path>\n\n"
                "Makes an HTTP request.\n"
                "GET is used automatically when no method is provided.\n"
                "POST, PUT and PATCH can send either text or a file.\n"
                "DELETE can be used without a body.",

            "update":
                "update\n\n"
                "If Hash++ is inside a Git repository, pulls the latest changes.\n"
                "If it is not a Git repository, Hash++ clones the Minzoi Lab\n"
                "Hash++ repository using Git's configured authentication.\n"
                "Hash++ then restarts using the updated code.",

            "restart":
                "restart\n\nRestarts Hash++ through code.py.",

            "exit":
                "exit\n\nCloses Hash++."
        }

        if command not in manuals:
            return CommandResult(f"No manual entry for: {command}", True)

        return CommandResult(manuals[command])

    def _request(self, args):
        if not args:
            return CommandResult(
                "Usage: request <url> [METHOD] [text|file] [body]",
                True
            )

        url = args[0]
        method = args[1].upper() if len(args) > 1 else "GET"

        allowed = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}

        if method not in allowed:
            return CommandResult(f"Unsupported HTTP method: {method}", True)

        body = None

        if method in {"POST", "PUT", "PATCH"}:
            if len(args) < 4:
                return CommandResult(
                    f"Usage: request <url> {method} text <body>\n"
                    f"or: request <url> {method} file <path>",
                    True
                )

            body_type = args[2].lower()

            if body_type == "text":
                body = args[3].encode("utf-8")
            elif body_type == "file":
                path = args[3]

                if not os.path.isfile(path):
                    return CommandResult(f"File not found: {path}", True)

                try:
                    with open(path, "rb") as file:
                        body = file.read()
                except OSError as e:
                    return CommandResult(f"Could not read file: {e}", True)
            else:
                return CommandResult(
                    "Body type must be either text or file.",
                    True
                )

        if self._cancelled():
            return CommandResult("Operation cancelled.", True)

        request = urllib.request.Request(
            url,
            data=body,
            method=method
        )

        if body is not None:
            if len(args) > 2 and args[2].lower() == "file":
                extension = os.path.splitext(args[3])[1].lower()

                if extension == ".json":
                    request.add_header("Content-Type", "application/json")
                elif extension in {".txt", ".html", ".htm"}:
                    request.add_header("Content-Type", "text/plain; charset=utf-8")
                else:
                    request.add_header("Content-Type", "application/octet-stream")
            else:
                request.add_header("Content-Type", "text/plain; charset=utf-8")

        try:
            response = urllib.request.urlopen(request, timeout=2)

            status = response.status
            reason = response.reason
            content_type = response.headers.get_content_type()

            data = bytearray()

            while True:
                if self._cancelled():
                    try:
                        response.close()
                    except Exception:
                        pass
                    return CommandResult("Operation cancelled.", True)

                try:
                    chunk = response.read(4096)
                except socket.timeout:
                    continue

                if not chunk:
                    break

                data.extend(chunk)

                if len(data) >= 2 * 1024 * 1024:
                    break

            response.close()

            output = self._format_response(
                bytes(data),
                content_type
            )

            if len(data) >= 2 * 1024 * 1024:
                output += "\n\n[Response truncated after 2 MB.]"

            return CommandResult(
                f"Status: {status} {reason}\n\n{output}".strip(),
                is_error=status >= 400
            )

        except urllib.error.HTTPError as e:
            if self._cancelled():
                return CommandResult("Operation cancelled.", True)

            try:
                data = e.read()
            except Exception:
                data = b""

            content_type = e.headers.get_content_type() if e.headers else ""

            output = self._format_response(data, content_type)

            text = f"Status: {e.code} {e.reason}"

            if output:
                text += f"\n\n{output}"

            return CommandResult(text, True)

        except urllib.error.URLError as e:
            if self._cancelled():
                return CommandResult("Operation cancelled.", True)

            reason = e.reason

            if isinstance(reason, socket.timeout):
                return CommandResult("Request timed out.", True)

            return CommandResult(f"Request failed: {reason}", True)

        except socket.timeout:
            return CommandResult("Request timed out.", True)

        except Exception as e:
            if self._cancelled():
                return CommandResult("Operation cancelled.", True)

            return CommandResult(f"Request failed: {e}", True)

    def _format_response(self, data, content_type):
        if not data:
            return "(No response body)"

        text = data.decode("utf-8", errors="replace")

        if "json" in content_type.lower():
            try:
                parsed = json.loads(text)
                return json.dumps(parsed, indent=2, ensure_ascii=False)
            except json.JSONDecodeError:
                pass

        if "html" in content_type.lower() or "<html" in text.lower():
            parser = HTMLTextParser()

            try:
                parser.feed(text)
                readable = parser.text()

                if readable:
                    return readable
            except Exception:
                pass

        return text

    def _is_git_repo(self, folder):
        try:
            result = subprocess.run(
                [
                    "git",
                    "-C",
                    folder,
                    "rev-parse",
                    "--is-inside-work-tree"
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            return result.returncode == 0 and result.stdout.strip() == "true"

        except FileNotFoundError:
            return None

    def _run_process(self, args, cwd):
        try:
            process = subprocess.Popen(
                args,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace"
            )
        except FileNotFoundError:
            return -1, "Git is not installed."

        output = []

        def read_output():
            try:
                text = process.stdout.read()
                if text:
                    output.append(text)
            except Exception:
                pass

        reader = threading.Thread(target=read_output, daemon=True)
        reader.start()

        while process.poll() is None:
            if self._cancelled():
                try:
                    process.terminate()
                except Exception:
                    pass

                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    try:
                        process.kill()
                    except Exception:
                        pass

                reader.join(timeout=1)
                return -2, "Operation cancelled."

            time.sleep(0.1)

        reader.join(timeout=1)

        return process.returncode, "".join(output).strip()

    def _update(self):
        folder = os.path.dirname(os.path.abspath(__file__))
        git_state = self._is_git_repo(folder)

        if git_state is None:
            return CommandResult("Git is not installed.", True)

        if self._cancelled():
            return CommandResult("Operation cancelled.", True)

        if git_state:
            return_code, output = self._run_process(
                ["git", "pull"],
                folder
            )

            if return_code == -2:
                return CommandResult(output, True)

            if return_code != 0:
                lowered = output.lower()

                if (
                    "authentication failed" in lowered
                    or "could not read username" in lowered
                    or "invalid username or password" in lowered
                    or "permission denied" in lowered
                ):
                    return CommandResult("Auth failed.", True)

                if (
                    "repository not found" in lowered
                    or "not found" in lowered
                    or "access denied" in lowered
                ):
                    return CommandResult("No access.", True)

                return CommandResult(
                    output or "Git pull failed.",
                    True
                )

            return CommandResult(
                output or "Already up to date.",
                should_exit=True,
                restart=True,
                restart_path=os.path.abspath(__file__)
            )

        parent = os.path.dirname(folder)
        current_name = os.path.basename(folder)

        if current_name.lower() == "hashhashplus":
            target = os.path.join(parent, "hashhashplus-update")
        else:
            target = os.path.join(parent, "hashhashplus")

        if os.path.exists(target):
            target_git = self._is_git_repo(target)

            if target_git is None:
                return CommandResult("Git is not installed.", True)

            if not target_git:
                return CommandResult(
                    f"Cannot clone into existing folder:\n{target}",
                    True
                )

            return_code, output = self._run_process(
                ["git", "pull"],
                target
            )

        else:
            return_code, output = self._run_process(
                ["git", "clone", GITHUB_REPO, target],
                parent
            )

        if return_code == -2:
            return CommandResult(output, True)

        if return_code != 0:
            lowered = output.lower()

            if (
                "authentication failed" in lowered
                or "could not read username" in lowered
                or "invalid username or password" in lowered
                or "permission denied" in lowered
            ):
                return CommandResult("Auth failed.", True)

            if (
                "repository not found" in lowered
                or "not found" in lowered
                or "access denied" in lowered
            ):
                return CommandResult("No access.", True)

            return CommandResult(
                output or "Update failed.",
                True
            )

        restart_path = os.path.join(target, "code.py")

        if not os.path.isfile(restart_path):
            return CommandResult(
                "Update succeeded, but code.py was not found.",
                True
            )

        return CommandResult(
            output or "Update complete.",
            should_exit=True,
            restart=True,
            restart_path=restart_path
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
