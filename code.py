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
import importlib


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
        if tag.lower() in {"script", "style", "noscript"}:
            self.skip += 1

    def handle_endtag(self, tag):
        if tag.lower() in {"script", "style", "noscript"} and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            text = data.strip()
            if text:
                self.parts.append(text)

    def text(self):
        return "\n".join(self.parts)


def get_playwright():
    try:
        return importlib.import_module("playwright.sync_api")
    except ImportError:
        pass

    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "playwright"],
            check=True
        )
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=True
        )
        return importlib.import_module("playwright.sync_api")
    except Exception:
        return None


def wait_for_process(pid):
    if not pid:
        return

    while True:
        try:
            os.kill(pid, 0)
        except OSError:
            break
        except Exception:
            break

        time.sleep(0.1)


class CommandEngine:
    def __init__(self):
        self.cancel_event = threading.Event()
        self._busy = False
        self._lock = threading.Lock()

    @property
    def busy(self):
        with self._lock:
            return self._busy

    def cancel(self):
        self.cancel_event.set()

    def _start(self):
        self.cancel_event.clear()

        with self._lock:
            self._busy = True

    def _finish(self):
        with self._lock:
            self._busy = False

    def _cancelled(self):
        return self.cancel_event.is_set()

    def execute(self, command):
        command = command.strip()

        if not command:
            return CommandResult()

        self._start()

        try:
            parts = shlex.split(command)
            name = parts[0].lower()
            args = parts[1:]

            commands = {
                "help": self._help,
                "man": self._man,
                "clear": self._clear,
                "discord": self._discord,
                "github": self._github,
                "request": self._request,
                "update": self._update,
                "restart": self._restart,
                "exit": self._exit,
            }

            if name not in commands:
                return CommandResult(
                    f"Unknown command: {name}\n"
                    "Type help to see available commands.",
                    True
                )

            return commands[name](args)

        except ValueError as e:
            return CommandResult(
                f"Error: {e}",
                True
            )

        except Exception as e:
            return CommandResult(
                f"Error: {e}",
                True
            )

        finally:
            self._finish()

    def _help(self, args):
        return CommandResult(
            "Hash++ commands:\n\n"
            "help              Show this list\n"
            "man <command>     Show command information\n"
            "clear             Clear the screen\n"
            "discord           Show the Minzi Lab Discord\n"
            "github            Show the Minzi Lab GitHub\n"
            "request <url>     Make a web request\n"
            "update            Update Hash++\n"
            "restart           Restart Hash++\n"
            "exit              Close Hash++"
        )

    def _man(self, args):
        if not args:
            return CommandResult(
                "Usage: man <command>\n\n"
                "Try: man request",
                True
            )

        command = args[0].lower()

        manuals = {
            "help":
                "help\n"
                "Show the list of available Hash++ commands.",

            "man":
                "man <command>\n"
                "Show information about a Hash++ command.",

            "clear":
                "clear\n"
                "Clear the current Hash++ screen.",

            "discord":
                "discord\n"
                "Show the Minzi Lab Discord server.",

            "github":
                "github\n"
                "Show the Minzi Lab GitHub organization.",

            "request":
                "request <url>\n"
                "Make a GET request using a JavaScript-enabled browser.\n\n"
                "request <url> GET\n"
                "Make an explicit GET request.\n\n"
                "request <url> POST text <body>\n"
                "Send a POST request with text data.\n\n"
                "request <url> POST file <path>\n"
                "Send a POST request using a file as the body.\n\n"
                "PUT and PATCH work the same way.\n\n"
                "request <url> DELETE\n"
                "Send a DELETE request.",

            "update":
                "update\n"
                "Update Hash++ from its Git repository.",

            "restart":
                "restart\n"
                "Restart Hash++.",

            "exit":
                "exit\n"
                "Close Hash++."
        }

        if command not in manuals:
            return CommandResult(
                f"No manual entry for: {command}",
                True
            )

        return CommandResult(manuals[command])

    def _clear(self, args):
        return CommandResult("\f")

    def _discord(self, args):
        return CommandResult(
            "https://discord.gg/hscSEBa9X"
        )

    def _github(self, args):
        return CommandResult(
            "https://github.com/Minzoi-Lab"
        )

    def _request(self, args):
        if not args:
            return CommandResult(
                "Usage: request <url> [GET|POST|PUT|PATCH|DELETE]",
                True
            )

        url = args[0]

        if not re.match(
            r"^https?://",
            url,
            re.IGNORECASE
        ):
            return CommandResult(
                "Invalid URL. Use http:// or https://",
                True
            )

        method = (
            args[1].upper()
            if len(args) >= 2
            else "GET"
        )

        if method == "GET":
            return self._browser_request(url)

        if method == "DELETE":
            return self._simple_request(
                url,
                "DELETE"
            )

        if method not in {"POST", "PUT", "PATCH"}:
            return CommandResult(
                f"Unsupported request method: {method}",
                True
            )

        if len(args) < 3:
            return CommandResult(
                f"Usage: request <url> {method} text <body>\n"
                f"or: request <url> {method} file <path>",
                True
            )

        body_type = args[2].lower()

        if body_type == "text":
            if len(args) < 4:
                return CommandResult(
                    "Missing request body.",
                    True
                )

            body = " ".join(args[3:]).encode()

        elif body_type == "file":
            if len(args) != 4:
                return CommandResult(
                    f"Usage: request <url> {method} file <path>",
                    True
                )

            path = os.path.expanduser(args[3])

            if not os.path.isfile(path):
                return CommandResult(
                    f"File not found: {path}",
                    True
                )

            try:
                with open(path, "rb") as f:
                    body = f.read()
            except Exception as e:
                return CommandResult(
                    f"Could not read file: {e}",
                    True
                )

        else:
            return CommandResult(
                "Body type must be text or file.",
                True
            )

        return self._simple_request(
            url,
            method,
            body
        )

    def _browser_request(self, url):
        if self._cancelled():
            return CommandResult(
                "Operation cancelled.",
                True
            )

        playwright_api = get_playwright()

        if playwright_api is None:
            return CommandResult(
                "Could not install Playwright or Chromium.",
                True
            )

        try:
            with playwright_api.sync_playwright() as p:
                if self._cancelled():
                    return CommandResult(
                        "Operation cancelled.",
                        True
                    )

                browser = p.chromium.launch(
                    headless=True
                )

                page = browser.new_page(
                    java_script_enabled=True,
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/151.0.0.0 Safari/537.36"
                    )
                )

                response = page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=20000
                )

                try:
                    page.wait_for_load_state(
                        "networkidle",
                        timeout=7000
                    )
                except Exception:
                    pass

                page.wait_for_timeout(1500)

                if self._cancelled():
                    browser.close()

                    return CommandResult(
                        "Operation cancelled.",
                        True
                    )

                status = response.status if response else 0
                final_url = page.url

                try:
                    title = page.title()
                except Exception:
                    title = ""

                try:
                    text = page.locator(
                        "body"
                    ).inner_text(
                        timeout=5000
                    ).strip()
                except Exception:
                    text = ""

                browser.close()

                if not text:
                    text = "(No readable page content)"

                output = f"Status: {status}"

                if title:
                    output += f"\nTitle: {title}"

                if final_url != url:
                    output += f"\nURL: {final_url}"

                output += f"\n\n{text}"

                return CommandResult(output)

        except Exception as e:
            return CommandResult(
                f"Request failed: {e}",
                True
            )

    def _simple_request(self, url, method, body=None):
        if self._cancelled():
            return CommandResult(
                "Operation cancelled.",
                True
            )

        try:
            request = urllib.request.Request(
                url,
                data=body,
                method=method,
                headers={
                    "User-Agent": "Hash++"
                }
            )

            with urllib.request.urlopen(
                request,
                timeout=15
            ) as response:
                status = response.status
                reason = response.reason
                content_type = response.headers.get(
                    "Content-Type",
                    ""
                )
                data = response.read()

            if self._cancelled():
                return CommandResult(
                    "Operation cancelled.",
                    True
                )

            text = data.decode(
                "utf-8",
                errors="replace"
            )

            if "application/json" in content_type:
                try:
                    parsed = json.loads(text)
                    text = json.dumps(
                        parsed,
                        indent=2,
                        ensure_ascii=False
                    )
                except Exception:
                    pass

            elif "text/html" in content_type:
                parser = HTMLTextParser()
                parser.feed(text)
                text = parser.text()

            return CommandResult(
                f"Status: {status} {reason}\n\n{text}"
            )

        except urllib.error.HTTPError as e:
            return CommandResult(
                f"Status: {e.code} {e.reason}",
                True
            )

        except urllib.error.URLError as e:
            return CommandResult(
                f"Request failed: {e.reason}",
                True
            )

        except socket.timeout:
            return CommandResult(
                "Request timed out.",
                True
            )

        except Exception as e:
            return CommandResult(
                f"Request failed: {e}",
                True
            )

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

            return result.returncode == 0

        except Exception:
            return False

    def _run_process(self, command, cwd=None):
        process = None
        output = []

        try:
            process = subprocess.Popen(
                command,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            def read_output():
                for line in process.stdout:
                    output.append(line)

            reader = threading.Thread(
                target=read_output,
                daemon=True
            )

            reader.start()

            while process.poll() is None:
                if self._cancelled():
                    process.terminate()

                    try:
                        process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        process.kill()

                    return False, "".join(output)

                time.sleep(0.1)

            reader.join(timeout=1)

            return (
                process.returncode == 0,
                "".join(output)
            )

        except FileNotFoundError:
            return (
                False,
                "Git is not installed or could not be found."
            )

        except Exception as e:
            if process:
                try:
                    process.kill()
                except Exception:
                    pass

            return False, str(e)

    def _git_error(self, output):
        lower = output.lower()

        if (
            "authentication failed" in lower
            or "could not read username" in lower
            or "invalid username" in lower
            or "terminal prompts disabled" in lower
            or "401" in lower
        ):
            return "Auth failed."

        if (
            "repository not found" in lower
            or "access denied" in lower
            or "does not exist" in lower
            or "403" in lower
        ):
            return "No access."

        return None

    def _update(self, args):
        current = os.path.dirname(
            os.path.abspath(__file__)
        )

        if self._is_git_repo(current):
            success, output = self._run_process(
                [
                    "git",
                    "-C",
                    current,
                    "pull"
                ]
            )

            if self._cancelled():
                return CommandResult(
                    "Update cancelled.",
                    True
                )

            git_error = self._git_error(output)

            if git_error:
                return CommandResult(
                    git_error,
                    True
                )

            if not success:
                return CommandResult(
                    output.strip()
                    or "Update failed.",
                    True
                )

            return CommandResult(
                "Update complete. Restarting...",
                should_exit=True,
                restart=True,
                restart_path=os.path.join(
                    current,
                    "code.py"
                )
            )

        parent = os.path.dirname(current)
        current_name = os.path.basename(current)

        if current_name.lower() == "hashhashplus":
            target = os.path.join(
                parent,
                "hashhashplus-update"
            )
        else:
            target = os.path.join(
                parent,
                "hashhashplus"
            )

        if os.path.exists(target):
            if self._is_git_repo(target):
                success, output = self._run_process(
                    [
                        "git",
                        "-C",
                        target,
                        "pull"
                    ]
                )
            else:
                return CommandResult(
                    f"Cannot update because {target} "
                    "already exists and is not a Git repository.",
                    True
                )
        else:
            success, output = self._run_process(
                [
                    "git",
                    "clone",
                    GITHUB_REPO,
                    target
                ]
            )

        if self._cancelled():
            return CommandResult(
                "Update cancelled.",
                True
            )

        git_error = self._git_error(output)

        if git_error:
            return CommandResult(
                git_error,
                True
            )

        if not success:
            return CommandResult(
                output.strip()
                or "Update failed.",
                True
            )

        new_code = os.path.join(
            target,
            "code.py"
        )

        if not os.path.isfile(new_code):
            return CommandResult(
                "Update completed, but code.py was not found.",
                True
            )

        return CommandResult(
            "Update complete. Restarting...",
            should_exit=True,
            restart=True,
            restart_path=new_code
        )

    def _restart(self, args):
        return CommandResult(
            "Restarting...",
            should_exit=True,
            restart=True,
            restart_path=os.path.abspath(__file__)
        )

    def _exit(self, args):
        return CommandResult(
            "Goodbye.",
            should_exit=True
        )


def launch_code(path):
    path = os.path.abspath(path)
    folder = os.path.dirname(path)

    env = os.environ.copy()
    env["HASHPP_WAIT_PID"] = str(os.getpid())

    subprocess.Popen(
        [
            sys.executable,
            path
        ],
        cwd=folder,
        env=env
    )


def run():
    wait_pid = os.environ.pop(
        "HASHPP_WAIT_PID",
        None
    )

    if wait_pid:
        try:
            wait_pid = int(wait_pid)
        except ValueError:
            wait_pid = None

    if wait_pid:
        wait_for_process(wait_pid)

    base = os.path.dirname(
        os.path.abspath(__file__)
    )

    print("Hash++")
    print()

    if sys.platform.startswith("linux"):
        if not os.environ.get("DISPLAY") and not os.environ.get(
            "WAYLAND_DISPLAY"
        ):
            text_path = os.path.join(
                base,
                "text.py"
            )

            os.execv(
                sys.executable,
                [
                    sys.executable,
                    text_path
                ]
            )

            return

    print("1. UI")
    print("2. In-terminal")
    print("3. IDE")
    print("4. Exit")
    print()

    while True:
        try:
            choice = input("> ").strip()

            if choice == "1":
                gui_path = os.path.join(
                    base,
                    "gui.py"
                )

                subprocess.Popen(
                    [
                        sys.executable,
                        gui_path
                    ],
                    cwd=base
                )

                return

            if choice == "2":
                text_path = os.path.join(
                    base,
                    "text.py"
                )

                process = subprocess.Popen(
                    [
                        sys.executable,
                        text_path
                    ],
                    cwd=base
                )

                process.wait()
                return

            if choice == "3":
                print("Coming soon..")
                return

            if choice == "4":
                return

            print(
                "Please choose 1, 2, 3, or 4."
            )

        except KeyboardInterrupt:
            print()
            return


if __name__ == "__main__":
    run()