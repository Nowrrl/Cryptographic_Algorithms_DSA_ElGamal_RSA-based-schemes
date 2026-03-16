# client.py
import socket
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox


class QuizClient:
    def __init__(self, gui):
        self.gui = gui
        self.sock = None
        self.connected = False
        self.listener_thread = None
        self.username = None

    def connect(self, host, port, username):
        if self.connected:
            self.gui.log("Already connected.")
            return

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect((host, port))
            self.sock.settimeout(1.0)  # important: prevents recv from blocking forever
        except OSError as e:
            messagebox.showerror("Error", f"Could not connect to server: {e}")
            return

        # Send handshake immediately
        try:
            self.sock.sendall(f"HELLO|{username}\n".encode("utf-8"))
        except OSError as e:
            messagebox.showerror("Error", f"Could not send HELLO: {e}")
            try:
                self.sock.close()
            except OSError:
                pass
            return

        self.connected = True
        self.username = username
        self.gui.log(f"Connecting to {host}:{port} as {username}...")

        self.listener_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.listener_thread.start()

    def _listen_loop(self):
        buffer = ""

        def recv_line():
            """Return one full line (without newline). Return None if socket closed.
            Return "" if nothing available yet (timeout)."""
            nonlocal buffer
            while "\n" not in buffer:
                try:
                    chunk = self.sock.recv(4096)
                except socket.timeout:
                    return ""
                except OSError:
                    return None

                if not chunk:
                    return None

                buffer += chunk.decode("utf-8", errors="ignore")

            line, buffer = buffer.split("\n", 1)
            return line.strip()

        try:
            # 1) Handshake response
            first = None
            while self.connected and (first is None or first == ""):
                first = recv_line()

            if first is None:
                self.gui.log("Server closed the connection.")
                self.connected = False
                return

            if first.startswith("ERROR|"):
                reason = first.split("|", 1)[1]
                self.gui.log(f"[SERVER] {first}")
                messagebox.showerror("Connection rejected", f"Server rejected connection: {reason}")
                self.connected = False
                try:
                    self.sock.close()
                except OSError:
                    pass
                return

            if first == "WELCOME":
                self.gui.log(f"[SERVER] WELCOME (logged in as {self.username})")
            else:
                self.gui.log(f"[SERVER] Unexpected handshake response: {first}")

            # 2) Main receive loop
            while self.connected:
                line = recv_line()
                if line is None:
                    break
                if line == "":
                    continue  # timeout, nothing received yet

                if line == "GAME_START":
                    self.gui.log("[SERVER] Game started!")
                    continue

                elif line == "GAME_END":
                    self.gui.log("[SERVER] Game ended.")
                    # disable submit button (GUI thread)
                    self.gui.root.after(0, lambda: self.gui.submit_btn.config(state="disabled"))
                    continue

                elif line.startswith("QUESTION|"):
                    parts = line.split("|")
                    # QUESTION|qid|q|A|B|C  => len = 6
                    if len(parts) == 6:
                        try:
                            qid = int(parts[1])
                        except ValueError:
                            self.gui.log(f"[SERVER] Bad QUESTION id: {parts[1]}")
                            continue

                        qtext = parts[2]
                        a = parts[3]
                        b = parts[4]
                        c = parts[5]

                        self.gui.root.after(0, lambda: self.gui.show_question(qid, qtext, a, b, c))
                    else:
                        self.gui.log(f"[SERVER] Malformed QUESTION: {line}")
                    continue

                elif line.startswith("SCOREBOARD|"):
                    self.gui.log(f"[SCOREBOARD] {line[len('SCOREBOARD|'):]}")
                    continue

                elif line.startswith("FEEDBACK|"):
                    # FEEDBACK|qid|correctOption|yourWasCorrect(0/1)|points
                    self.gui.log(f"[FEEDBACK] {line}")
                    continue

                elif line.startswith("RANKING|"):
                    self.gui.log("[FINAL RANKING]")
                    entries = line[len("RANKING|"):].split(";")
                    for e in entries:
                        rank, user, score = e.split(":")
                        self.gui.log(f"{rank}. {user} ({score})")

                elif line.startswith("WINNER|"):
                    winners = line.split("|", 1)[1]
                    self.gui.log(f"🏆 Winner(s): {winners}")

                elif line.startswith("INFO|"):
                    self.gui.log(f"[INFO] {line.split('|', 1)[1]}")

                # default: log anything else
                else:
                    self.gui.log(f"[SERVER] {line}")

        except OSError:
            pass

        self.gui.log("Disconnected from server.")
        self.connected = False
        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass

    def disconnect(self):
        if not self.connected:
            return
        self.connected = False
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            self.sock.close()
        except OSError:
            pass
        self.gui.log("Client closed connection.")

    def send_text(self, text):
        if not self.connected:
            self.gui.log("Not connected.")
            return
        try:
            self.sock.sendall(text.encode("utf-8"))
        except OSError as e:
            self.gui.log(f"Error sending: {e}")
            self.disconnect()


class ClientGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("SUquid Quiz Client")

        top = tk.Frame(root)
        top.pack(padx=10, pady=5, fill="x")

        tk.Label(top, text="Server IP:").grid(row=0, column=0, sticky="w")
        self.ip_entry = tk.Entry(top, width=15)
        self.ip_entry.grid(row=0, column=1, sticky="w")
        self.ip_entry.insert(0, "127.0.0.1")

        tk.Label(top, text="Port:").grid(row=0, column=2, sticky="w")
        self.port_entry = tk.Entry(top, width=8)
        self.port_entry.grid(row=0, column=3, sticky="w")
        self.port_entry.insert(0, "5050")

        tk.Label(top, text="Username:").grid(row=1, column=0, sticky="w")
        self.username_entry = tk.Entry(top, width=20)
        self.username_entry.grid(row=1, column=1, sticky="w")

        btn_frame = tk.Frame(root)
        btn_frame.pack(padx=10, pady=5, fill="x")

        self.connect_btn = tk.Button(btn_frame, text="Connect", command=self.on_connect)
        self.connect_btn.pack(side="left", padx=5)

        self.disconnect_btn = tk.Button(btn_frame, text="Disconnect", command=self.on_disconnect)
        self.disconnect_btn.pack(side="left", padx=5)

        # Question display
        question_frame = tk.LabelFrame(root, text="Question")
        question_frame.pack(padx=10, pady=5, fill="x")

        self.qid_label = tk.Label(question_frame, text="Q: -")
        self.qid_label.pack(anchor="w")

        self.question_label = tk.Label(
            question_frame,
            text="(waiting for question...)",
            wraplength=400,
            justify="left"
        )
        self.question_label.pack(anchor="w")

        self.opt_a_label = tk.Label(question_frame, text="A: -", wraplength=400, justify="left")
        self.opt_b_label = tk.Label(question_frame, text="B: -", wraplength=400, justify="left")
        self.opt_c_label = tk.Label(question_frame, text="C: -", wraplength=400, justify="left")

        self.opt_a_label.pack(anchor="w")
        self.opt_b_label.pack(anchor="w")
        self.opt_c_label.pack(anchor="w")

        self.current_qid = None

        # Answer section
        answer_frame = tk.LabelFrame(root, text="Answer")
        answer_frame.pack(padx=10, pady=5, fill="x")

        self.answer_var = tk.StringVar(value="A")
        tk.Radiobutton(answer_frame, text="A", variable=self.answer_var, value="A").pack(side="left", padx=5)
        tk.Radiobutton(answer_frame, text="B", variable=self.answer_var, value="B").pack(side="left", padx=5)
        tk.Radiobutton(answer_frame, text="C", variable=self.answer_var, value="C").pack(side="left", padx=5)

        self.submit_btn = tk.Button(answer_frame, text="Submit", command=self.on_submit)
        self.submit_btn.pack(side="left", padx=10)
        self.submit_btn.config(state="disabled")

        # Log area
        self.log_box = scrolledtext.ScrolledText(root, height=15, state="disabled")
        self.log_box.pack(padx=10, pady=5, fill="both", expand=True)

        self.client = QuizClient(self)

    def on_connect(self):
        host = self.ip_entry.get().strip()
        try:
            port = int(self.port_entry.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Port must be an integer.")
            return

        username = self.username_entry.get().strip()
        if not username:
            messagebox.showerror("Error", "Please enter a username.")
            return

        self.client.connect(host, port, username)

    def on_disconnect(self):
        self.client.disconnect()

    def on_submit(self):
        if self.current_qid is None:
            self.log("No active question.")
            return

        answer = self.answer_var.get().strip().upper()
        self.client.send_text(f"ANSWER|{self.current_qid}|{answer}\n")
        self.log(f"Sent: ANSWER|{self.current_qid}|{answer}")
        self.submit_btn.config(state="disabled")  # prevent double submit

    def show_question(self, qid, qtext, a, b, c):
        self.current_qid = qid
        self.qid_label.config(text=f"Q: {qid}")
        self.question_label.config(text=qtext)
        self.opt_a_label.config(text=f"A: {a}")
        self.opt_b_label.config(text=f"B: {b}")
        self.opt_c_label.config(text=f"C: {c}")
        self.submit_btn.config(state="normal")

    def log(self, msg):
        self.log_box.configure(state="normal")
        self.log_box.insert(tk.END, msg + "\n")
        self.log_box.see(tk.END)
        self.log_box.configure(state="disabled")


def main():
    root = tk.Tk()
    gui = ClientGUI(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (gui.on_disconnect(), root.destroy()))
    root.mainloop()


if __name__ == "__main__":
    main()