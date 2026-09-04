import os
import subprocess
import sys

print("Hash++")
print()

if os.name != "nt" and not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
    subprocess.run([sys.executable, "text.py"])
    sys.exit()

print("How do you want to use Hash++?")
print("  1. UI")
print("  2. In-terminal")
print("  3. IDE")
print("  4. Exit")
print()

choice = input("Type in a choice: ")

if choice == "1":
    if os.name == "nt":
        subprocess.Popen(
            [sys.executable, "gui.py"],
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
    else:
        subprocess.Popen([sys.executable, "gui.py"])

elif choice == "2":
    subprocess.run([sys.executable, "text.py"])

elif choice == "3":
    print("Coming soon..")

elif choice == "4":
    sys.exit()

else:
    print("Not a valid choice, closing..")
