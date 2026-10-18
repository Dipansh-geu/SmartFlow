import tkinter as tk
from tkinter import simpledialog, messagebox
from PIL import Image, ImageTk
import subprocess
import os

BACKGROUND = "#ADD8E6"
TEXT = "#000080"

root = tk.Tk()
root.title("SmartFlow")
root.attributes("-fullscreen", True)
root.configure(bg=BACKGROUND)

density_photo = None
comparison_photo = None

def exit_program():
    root.destroy()

def start_simulation():

    simulations = simpledialog.askinteger(
        "SmartFlow",
        "Enter Number of Simulations:"
    )

    if simulations is None:
        return

    try:

        status_label.config(
            text="Running SmartFlow..."
        )

        root.update()

        subprocess.run(
            ["smartflow.exe"],
            input=f"{simulations}\n",
            text=True,
            check=True
        )

        status_label.config(
            text="Generating Density Graph..."
        )

        root.update()

        subprocess.run(
            ["python", "density_graph.py"],
            check=True
        )

        status_label.config(
            text="Generating Comparison Graph..."
        )

        root.update()

        subprocess.run(
            ["python", "graph.py"],
            check=True
        )

        status_label.config(
            text="Loading Dashboard..."
        )

        root.update()

        show_dashboard()

    except Exception as e:

        messagebox.showerror(
            "Error",
            str(e)
        )

def show_dashboard():

    global density_photo
    global comparison_photo

    if not os.path.exists("density.png"):
        messagebox.showerror(
            "Error",
            "density.png not found"
        )
        return

    if not os.path.exists("comparison.png"):
        messagebox.showerror(
            "Error",
            "comparison.png not found"
        )
        return

    menu_frame.pack_forget()

    density_img = Image.open("density.png")
    comparison_img = Image.open("comparison.png")

    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    graph_width = screen_width // 2 - 40
    graph_height = int(screen_height * 0.50)

    density_img = density_img.resize(
        (graph_width, graph_height)
    )

    comparison_img = comparison_img.resize(
        (graph_width, graph_height)
    )

    density_photo = ImageTk.PhotoImage(
        density_img
    )

    comparison_photo = ImageTk.PhotoImage(
        comparison_img
    )

    density_label.config(
        image=density_photo
    )

    comparison_label.config(
        image=comparison_photo
    )

    result_frame.pack(
        fill="both",
        expand=True
    )

title = tk.Label(
    root,
    text="SMARTFLOW",
    font=("Arial", 36, "bold"),
    bg=BACKGROUND,
    fg=TEXT
)

title.pack(
    pady=15
)

traffic = tk.Label(
    root,
    text="🚦",
    font=("Arial", 60),
    bg=BACKGROUND
)

traffic.pack()

status_label = tk.Label(
    root,
    text="Ready",
    font=("Arial",14),
    bg=BACKGROUND,
    fg="green"
)

status_label.pack(
    pady=10
)

menu_frame = tk.Frame(
    root,
    bg=BACKGROUND
)

menu_frame.pack(
    expand=True
)

start_button = tk.Button(
    menu_frame,
    text="START SIMULATION",
    font=("Arial",18,"bold"),
    width=25,
    height=2,
    command=start_simulation
)

start_button.pack(
    pady=20
)

exit_button = tk.Button(
    menu_frame,
    text="EXIT",
    font=("Arial",18,"bold"),
    width=25,
    height=2,
    command=exit_program
)

exit_button.pack(
    pady=20
)

result_frame = tk.Frame(
    root,
    bg=BACKGROUND
)

graphs_frame = tk.Frame(
    result_frame,
    bg=BACKGROUND
)

graphs_frame.pack(
    fill="both",
    expand=True,
    padx=20,
    pady=20
)

left_frame = tk.Frame(
    graphs_frame,
    bg=BACKGROUND
)

left_frame.pack(
    side="left",
    fill="both",
    expand=True
)

right_frame = tk.Frame(
    graphs_frame,
    bg=BACKGROUND
)

right_frame.pack(
    side="right",
    fill="both",
    expand=True
)

density_title = tk.Label(
    left_frame,
    text="DENSITY GRAPH",
    font=("Arial",16,"bold"),
    bg=BACKGROUND
)

density_title.pack(
    pady=10
)

density_label = tk.Label(
    left_frame,
    bg=BACKGROUND
)

density_label.pack()

comparison_title = tk.Label(
    right_frame,
    text="COMPARISON GRAPH",
    font=("Arial",16,"bold"),
    bg=BACKGROUND
)

comparison_title.pack(
    pady=10
)

comparison_label = tk.Label(
    right_frame,
    bg=BACKGROUND
)

comparison_label.pack()

exit_button_2 = tk.Button(
    result_frame,
    text="EXIT",
    font=("Arial",18,"bold"),
    width=20,
    height=2,
    command=exit_program
)

exit_button_2.pack(
    pady=20
)

root.mainloop()
