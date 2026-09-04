def _has_graphical_session():
	import os
	import sys

	if sys.platform.startswith("win") or sys.platform == "darwin":
		return True

	return bool(
		os.environ.get("DISPLAY")
		or os.environ.get("WAYLAND_DISPLAY")
		or os.environ.get("MIR_SOCKET")
	)


def main():
	import subprocess
	import sys

	if not _has_graphical_session():
		subprocess.run([sys.executable, "text.py"])
		return

	print("Hash++")
	print()
	print("Choose an interface:")
	print("  1. Graphical interface")
	print("  2. Text interface")
	print()

	while True:
		choice = input("Select an interface [1/2]: ").strip()

		if choice == "1":
			subprocess.run([sys.executable, "gui.py"])
			return

		if choice == "2":
			subprocess.run([sys.executable, "text.py"])
			return

		print("Please enter 1 or 2.")


if __name__ == "__main__":
	main()
