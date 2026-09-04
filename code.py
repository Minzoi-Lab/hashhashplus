import os
import subprocess
import sys


def main():
    folder = os.path.dirname(os.path.abspath(__file__))

    if os.name != "nt" and not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        subprocess.run([sys.executable, os.path.join(folder, "text.py")])
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
        subprocess.run([sys.executable, os.path.join(folder, "text.py")])
    elif choice == "3":
        print("Coming soon..")
    elif choice == "4":
        return
    else:
        print("Not a valid choice, closing..")


if __name__ == "__main__":
    main()
