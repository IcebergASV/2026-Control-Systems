import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
from datetime import datetime
import queue, threading, time

class Interface:
    def __init__(self):
        # GUI Config
        self.root = tk.Tk()
        self.root.title("Iceberg Interface")
        self.root.geometry("600x600")
        padding = 10 # easily scalable

        self.panes = tk.PanedWindow(
            self.root,
            orient="vertical",
            sashwidth=6,
            sashrelief="raised",
            sashpad=1,
        )
        self.panes.pack(fill="both", expand=True)

        # Menubar
        # TODO add in a menubar

        # Top Pane
        self.top = ttk.Frame(self.panes)
        self.label = tk.Label(self.top, text="Welcome to the Iceberg ASV User Interface!", font=("Times New Roman", 20))
        self.label.pack(padx=padding, pady=padding)
        self.panes.add(self.top, minsize=150, stretch="always")

        # Main Pane
        self.main = ttk.Frame(self.panes)
        # TODO put some buttons here or smth

        # Bottom Pane : Status updates
        self.updateframe = ttk.LabelFrame(self.panes, text="Boat Status")
        self.updatebox = ScrolledText(self.updateframe, height=4, state="disabled")
        self.updatebox.pack(fill="both", expand=True)
        self.panes.add(self.updateframe, minsize=80, stretch="always")

        threading.Thread(target=self.worker, daemon=True).start()
        self.poll()
        self.root.mainloop()

    q = queue.Queue()

    # this function will be removed when boat data is connected
    def worker(self):  # This is just a test function that produces timestamps at a constant rate
        i = 0
        while True:
            stamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            self.q.put(f"[{stamp}] reading {i}\n")
            i += 1
            time.sleep(2.5)

    def poll(self):
        try:
            while True:
                line = self.q.get_nowait()
                self.updatebox.configure(state="normal")
                self.updatebox.insert("end", line)
                self.updatebox.configure(state="disabled")
                self.updatebox.see("end")
        except queue.Empty:
            pass
        self.root.after(50, self.poll)

Interface()
