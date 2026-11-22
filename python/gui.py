
import tkinter as tk
from tkinter import simpledialog, messagebox

from PIL import Image, ImageTk

import subprocess
import shutil
import sys
import os
import csv
import math
import json
import re

from datetime import datetime

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg,
    NavigationToolbar2Tk
)


BACKGROUND = "#ADD8E6"
TEXT = "#000080"

PYTHON_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(PYTHON_DIR)

RECORDS_DIR = os.path.join(
    PROJECT_DIR,
    "records"
)

EXE_PATH = os.path.join(
    PROJECT_DIR,
    "smartflow.exe" if os.name == "nt" else "smartflow"
)

DENSITY_SCRIPT = os.path.join(
    PYTHON_DIR,
    "density_graph.py"
)

GREEN_TIME_SCRIPT = os.path.join(
    PYTHON_DIR,
    "green_time_allocation.py"
)

WAIT_COMPARISON_SCRIPT = os.path.join(
    PYTHON_DIR,
    "average_wait_comparison.py"
)

QUEUE_LENGTH_SCRIPT = os.path.join(
    PYTHON_DIR,
    "queue_length_comparison.py"
)



root = tk.Tk()

root.title("SmartFlow")
root.attributes("-fullscreen", True)
root.configure(bg="#25292E")



road_border_canvas = tk.Canvas(
    root,
    bg="#25292E",
    highlightthickness=0,
    bd=0
)

road_border_canvas.place(
    x=0,
    y=0,
    relwidth=1,
    relheight=1
)


def draw_application_road_border(event=None):

    width = max(1, root.winfo_width())
    height = max(1, root.winfo_height())

    road_border_canvas.delete("all")

    road_border_canvas.create_rectangle(
        9,
        9,
        width - 9,
        height - 9,
        outline="white",
        width=2,
        dash=(18, 12)
    )

    road_border_canvas.create_rectangle(
        23,
        23,
        width - 23,
        height - 23,
        outline="#D9DDE2",
        width=1,
        dash=(12, 13)
    )


root.bind(
    "<Configure>",
    draw_application_road_border
)



image_references = []

history_chart_canvas = None



_MODULE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

for _module in (
    "simulation.py",
    "dashboard.py",
    "records.py",
    "layout.py"
):

    module_path = os.path.join(
        _MODULE_DIR,
        _module
    )

    with open(
        module_path,
        "r",
        encoding="utf-8"
    ) as _source:

        exec(
            compile(
                _source.read(),
                _module,
                "exec"
            ),
            globals()
        )



root.mainloop()
