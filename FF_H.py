#!/usr/bin/env python3

import os
import re
import sys
import time
import socket
import shutil
import subprocess
import threading
from pathlib import Path

# ==============================
# RDCS CONFIGURATION
# ==============================

FB_URL = "https://www.facebook.com/RDCSSOCIETY"
DEFAULT_PORT = 8080

BASE_DIR = Path(__file__).resolve().parent
INDEX_FILE = BASE_DIR / "index.html"

RED = "\033[1;91m"
GREEN = "\033[1;92m"
WHITE = "\033[1;97m"
CYAN = "\033[1;96m"
YELLOW = "\033[1;93m"
RESET = "\033[0m"

server_process = None
tunnel_process = None
public_url_event = threading.Event()


# ==============================
# OPEN FACEBOOK
# ==============================

def open_url(url):
    try:
        subprocess.Popen(
            ["termux-open-url", url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except Exception:
        try:
            subprocess.Popen(
                ["am", "start", "-a",
                 "android.intent.action.VIEW",
                 "-d", url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception:
            pass


def open_rdcs_facebook():
    open_url(FB_URL)


# ==============================
# RDCS BANNER
# ==============================

def banner():

    os.system("clear")

    print(RED + r"""
██████╗  ██████╗  ██████╗███████╗
██╔══██╗██╔══██╗██╔════╝██╔════╝
██████╔╝██║  ██║██║     ███████╗
██╔══██╗██║  ██║██║     ╚════██║
██║  ██║╚██████╔╝╚██████╗███████║
╚═╝  ╚═╝ ╚═════╝  ╚═════╝╚══════╝
""" + RESET)

    print(WHITE + "       READ DRAGON CYBER SECURITY" + RESET)
    print(RED + "  =====================================" + RESET)
    print(CYAN + "              RDCS LAUNCHER" + RESET)
    print(RED + "  =====================================" + RESET)


# ==============================
# FIND AVAILABLE PORT
# ==============================

def find_free_port():

    for port in range(DEFAULT_PORT, DEFAULT_PORT + 20):

        sock = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM
        )

        try:
            sock.bind(("127.0.0.1", port))
            return port

        except OSError:
            continue

        finally:
            sock.close()

    raise RuntimeError("No available port found.")


# ==============================
# TUNNEL OUTPUT READER
# ==============================

def read_tunnel_output(process):

    pattern = re.compile(
        r'https://[a-zA-Z0-9-]+\.lhr\.life\b'
    )

    for line in iter(process.stdout.readline, ''):

        line = line.strip()

        if not line:
            continue

        match = pattern.search(line)

        if match:

            public_url = match.group(0)

            print("\n" + GREEN)
            print("=====================================")
            print("        RDCS PUBLIC WEBSITE")
            print("=====================================" + RESET)

            print(WHITE + "\nLOCAL URL  : " + CYAN +
                  f"http://127.0.0.1:{CURRENT_PORT}" + RESET)

            print(WHITE + "PUBLIC URL : " + GREEN +
                  public_url + RESET)

            print(GREEN + "\n[+] PUBLIC LINK READY!" + RESET)

            try:
                subprocess.run(
                    ["termux-clipboard-set", public_url],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True
                )
                print(GREEN + "[+] LINK COPIED TO CLIPBOARD!" + RESET)

            except Exception:
                print(YELLOW + "[!] Clipboard unavailable." + RESET)

            print()
            public_url_event.set()

        else:
            print(YELLOW + "[TUNNEL] " + line + RESET)


CURRENT_PORT = DEFAULT_PORT


# ==============================
# START SERVER + TUNNEL
# ==============================

def start_server():

    global server_process
    global tunnel_process
    global CURRENT_PORT

    if not INDEX_FILE.is_file():

        print(RED + "\n[!] index.html NOT FOUND!" + RESET)
        input("\nPress Enter...")
        return

    if not shutil.which("ssh"):

        print(RED + "\n[!] OpenSSH NOT INSTALLED!" + RESET)
        input("\nPress Enter...")
        return

    os.chdir(BASE_DIR)

    try:

        CURRENT_PORT = find_free_port()
        public_url_event.clear()

        print(GREEN + "\n[+] STARTING RDCS WEB SERVER..." + RESET)

        server_process = subprocess.Popen([
            sys.executable,
            "-m",
            "http.server",
            str(CURRENT_PORT),
            "--bind",
            "127.0.0.1"
        ])

        time.sleep(1)

        if server_process.poll() is not None:
            raise RuntimeError("HTTP Server failed to start.")

        print(GREEN + "[+] HTTP SERVER STARTED" + RESET)

        print(CYAN +
              f"[+] LOCAL URL: http://127.0.0.1:{CURRENT_PORT}"
              + RESET)

        open_url(f"http://127.0.0.1:{CURRENT_PORT}")

        print(YELLOW + "\n[+] CONNECTING PUBLIC TUNNEL..." + RESET)

        tunnel_process = subprocess.Popen(
            [
                "ssh",
                "-T",
                "-o", "StrictHostKeyChecking=accept-new",
                "-o", "ServerAliveInterval=30",
                "-o", "ExitOnForwardFailure=yes",
                "-R", f"80:127.0.0.1:{CURRENT_PORT}",
                "nokey@localhost.run"
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        reader = threading.Thread(
            target=read_tunnel_output,
            args=(tunnel_process,),
            daemon=True
        )

        reader.start()

        print(WHITE + "\n[+] WAITING FOR PUBLIC URL..." + RESET)
        print(RED + "[!] Press CTRL+C to stop." + RESET)

        while True:

            if server_process.poll() is not None:
                print(RED + "\n[!] HTTP SERVER STOPPED!" + RESET)
                break

            if tunnel_process.poll() is not None:
                print(RED + "\n[!] TUNNEL DISCONNECTED!" + RESET)
                break

            time.sleep(1)

    except KeyboardInterrupt:

        print(YELLOW + "\n[+] STOPPING RDCS..." + RESET)

    except Exception as error:

        print(RED + f"\n[!] ERROR: {error}" + RESET)

    finally:

        for process in [tunnel_process, server_process]:

            if process and process.poll() is None:

                process.terminate()

                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()

        tunnel_process = None
        server_process = None

        print(GREEN + "\n[+] RDCS SERVICES STOPPED." + RESET)
        time.sleep(1)


# ==============================
# MAIN MENU
# ==============================

def main():

    open_rdcs_facebook()

    while True:

        banner()

        print()
        print(GREEN + "  [1] START" + RESET)
        print(RED + "  [0] EXIT" + RESET)

        choice = input(
            WHITE + "\n  Select Option: " + RESET
        ).strip()

        if choice == "1":

            start_server()

        elif choice == "0":

            print(RED + "\n[+] RDCS SYSTEM EXITED." + RESET)
            break

        else:

            print(RED + "\n[!] INVALID OPTION!" + RESET)
            time.sleep(1)


if __name__ == "__main__":
    main()