
import tkinter as tk
from tkinter import messagebox

import os
import json
import webbrowser
import pandas as pd

from PIL import Image, ImageTk

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.patches import Patch
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg,
    NavigationToolbar2Tk
)



def clear_frame(frame):

    for widget in frame.winfo_children():
        widget.destroy()


def load_graph_image(path, max_width, max_height):

    image = Image.open(path).convert("RGB")

    image.thumbnail(
        (max_width, max_height),
        Image.Resampling.LANCZOS
    )

    return ImageTk.PhotoImage(image)



def show_interactive_green_timeline(parent, record_path):

    global image_references

    clear_frame(parent)
    image_references = []

    csv_path = os.path.join(
        record_path,
        "smartflow_green_phases.csv"
    )

    if not os.path.isfile(csv_path):

        tk.Label(
            parent,
            text="smartflow_green_phases.csv not found.",
            font=("Arial", 15, "bold"),
            bg=BACKGROUND,
            fg="red"
        ).pack(expand=True)

        return

    try:

        df = pd.read_csv(csv_path)

        required = [
            "Lane",
            "Start_Seconds",
            "End_Seconds"
        ]

        missing = [
            column
            for column in required
            if column not in df.columns
        ]

        if missing:
            raise ValueError(
                f"Missing CSV columns: {missing}"
            )

        for column in required:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

        df = df.dropna(subset=required)

        df = df[
            (df["End_Seconds"] > df["Start_Seconds"]) &
            (df["Lane"] > 0)
        ].copy()

        if df.empty:
            raise ValueError(
                "No valid SmartFlow green phases found."
            )

        df = df.sort_values(
            "Start_Seconds"
        ).reset_index(drop=True)

        df["Duration"] = (
            df["End_Seconds"] - df["Start_Seconds"]
        )

        colors = {
            1: "#3498DB",
            2: "#E76F51",
            3: "#2A9D8F",
            4: "#9467BD"
        }

        total_time = float(
            df["End_Seconds"].max()
        )


        tk.Label(
            parent,
            text="SMARTFLOW - GREEN SIGNAL TIMELINE",
            font=("Arial", 20, "bold"),
            bg=BACKGROUND,
            fg=TEXT
        ).pack(pady=(12, 5))

        tk.Label(
            parent,
            text=(
                f"Total green phases: {len(df)}"
                f"     |     Total green time: "
                f"{df['Duration'].sum():.1f} seconds"
            ),
            font=("Arial", 11),
            bg=BACKGROUND,
            fg=TEXT
        ).pack(pady=(0, 8))


        figure = Figure(
            figsize=(12, 5),
            dpi=100
        )

        axis = figure.add_subplot(111)

        for _, phase in df.iterrows():

            lane = int(phase["Lane"])

            start = float(
                phase["Start_Seconds"]
            )

            end = float(
                phase["End_Seconds"]
            )

            duration = end - start

            color = colors.get(
                lane,
                "#808080"
            )

            axis.broken_barh(
                [(start, duration)],
                (0.25, 0.5),
                facecolors=color,
                edgecolors="white",
                linewidth=1
            )

            if duration >= 8:

                axis.text(
                    start + duration / 2,
                    0.5,
                    f"{duration:.0f}s",
                    ha="center",
                    va="center",
                    fontsize=8,
                    fontweight="bold",
                    color="white"
                )


        lane_handles = []

        for lane, color in colors.items():

            if lane in df["Lane"].astype(int).unique():

                lane_handles.append(
                    Patch(
                        facecolor=color,
                        label=f"Lane {lane}"
                    )
                )

        axis.legend(
            handles=lane_handles,
            loc="upper center",
            bbox_to_anchor=(0.5, -0.18),
            ncol=4,
            frameon=False
        )


        axis.set_xlim(
            0,
            total_time
        )

        axis.set_ylim(
            0,
            1
        )

        axis.set_yticks([])

        axis.set_xlabel(
            "Simulation Time (seconds)",
            fontsize=11
        )

        axis.set_title(
            "Green Signal Sequence",
            fontsize=14,
            fontweight="bold"
        )

        axis.grid(
            axis="x",
            linestyle="--",
            alpha=0.35
        )

        axis.set_axisbelow(True)

        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)
        axis.spines["left"].set_visible(False)

        figure.tight_layout()


        graph_frame = tk.Frame(
            parent,
            bg=BACKGROUND
        )

        graph_frame.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=5
        )

        canvas = FigureCanvasTkAgg(
            figure,
            master=graph_frame
        )

        canvas.draw()

        canvas.get_tk_widget().pack(
            fill="both",
            expand=True
        )


        toolbar_frame = tk.Frame(
            parent,
            bg=BACKGROUND
        )

        toolbar_frame.pack(
            fill="x",
            padx=15,
            pady=5
        )

        toolbar = NavigationToolbar2Tk(
            canvas,
            toolbar_frame
        )

        toolbar.update()


        annotation = axis.annotate(
            "",
            xy=(0, 0),
            xytext=(12, 15),
            textcoords="offset points",
            bbox=dict(
                boxstyle="round,pad=0.5",
                fc="white",
                ec="#555555",
                alpha=0.95
            ),
            fontsize=9
        )

        annotation.set_visible(False)

        def on_hover(event):

            if event.inaxes != axis or event.xdata is None:

                if annotation.get_visible():
                    annotation.set_visible(False)
                    canvas.draw_idle()

                return

            current_time = event.xdata

            matching = df[
                (df["Start_Seconds"] <= current_time) &
                (df["End_Seconds"] >= current_time)
            ]

            if matching.empty:

                annotation.set_visible(False)

            else:

                phase = matching.iloc[0]

                lane = int(phase["Lane"])

                annotation.xy = (
                    current_time,
                    0.5
                )

                annotation.set_text(
                    f"Lane: {lane}\n"
                    f"Start: {phase['Start_Seconds']:.1f} s\n"
                    f"End: {phase['End_Seconds']:.1f} s\n"
                    f"Duration: {phase['Duration']:.1f} s"
                )

                annotation.set_visible(True)

            canvas.draw_idle()

        canvas.mpl_connect(
            "motion_notify_event",
            on_hover
        )


        tk.Button(
            parent,
            text="RETURN TO GRAPH SELECTION",
            font=("Arial", 12, "bold"),
            command=lambda: show_graphs(
                parent,
                record_path,
                "SIMULATION RESULTS"
            )
        ).pack(
            side="bottom",
            pady=10
        )

    except Exception as error:

        tk.Label(
            parent,
            text=f"Could not load interactive graph:\n{error}",
            font=("Arial", 13),
            bg=BACKGROUND,
            fg="red"
        ).pack(expand=True)



def show_graphs(
    parent,
    record_path,
    heading,
    show_improvement=True
):

    global image_references

    clear_frame(parent)

    image_references = []

    tk.Label(
        parent,
        text=heading,
        font=("Arial", 22, "bold"),
        bg=BACKGROUND,
        fg=TEXT
    ).pack(pady=(10, 6))


    if show_improvement:

        comparison_csv = os.path.join(
            record_path,
            "comparison.csv"
        )

        try:

            improvement = calculate_improvement(
                comparison_csv
            )

            improvement_text = (
                (f"Time Saved: {improvement:.2f}%" if improvement >= 0 else f"Average Delay Increased: {abs(improvement):.2f}%")
                if improvement is not None
                else "Time Saved: N/A"
            )

            improvement_color = (
                "green"
                if improvement is not None and improvement >= 0
                else "red"
            )

        except Exception as error:

            improvement_text = (
                f"Could not calculate improvement: {error}"
            )

            improvement_color = "red"

        tk.Label(
            parent,
            text=improvement_text,
            font=("Arial", 16, "bold"),
            bg=BACKGROUND,
            fg=improvement_color
        ).pack(
            side="bottom",
            pady=(0, 8)
        )


    selection_frame = tk.Frame(
        parent,
        bg=BACKGROUND
    )

    selection_frame.pack(
        fill="both",
        expand=True,
        padx=24,
        pady=12
    )

    preview_w = max(
        300,
        (root.winfo_screenwidth() - 160) // 2 - 40
    )

    preview_h = max(
        120,
        (root.winfo_screenheight() - 420) // 2 - 70
    )

    metadata = read_record_metadata(record_path)

    if str(metadata.get("mode", "")).startswith("SUMO"):
        graph_specs = [
            (
                "TRAFFIC DENSITY",
                "density.png",
                "Lane-wise traffic demand (PCU) from the SUMO TraCI comparison runs"
            ),
            (
                "GREEN-TIME ALLOCATION",
                "green_time_allocation.png",
                "Interactive single-lane SmartFlow signal sequence"
            ),
            (
                "AVERAGE WAITING TIME",
                "average_wait_comparison.png",
                "Per-minute average queue delay: fixed-time baseline vs SmartFlow"
            ),
            (
                "QUEUE LENGTH OVER TIME",
                "queue_length_comparison.png",
                "Average vehicles waiting in each lane during each simulated minute"
            )
        ]
    else:
        graph_specs = [
            (
                "TRAFFIC DENSITY",
                "density.png",
                "Generated traffic demand per lane (PCU)"
            ),
            (
                "GREEN-TIME ALLOCATION",
                "green_time_allocation.png",
                "Interactive SmartFlow green-signal sequence"
            ),
            (
                "AVERAGE RED-LIGHT WAIT",
                "average_wait_comparison.png",
                "Grouped comparison of average red-signal waiting time per minute"
            ),
            (
                "QUEUE LENGTH OVER TIME",
                "queue_length_comparison.png",
                "Average vehicles waiting in each lane during every simulated minute"
            )
        ]


    def open_graph(filename, caption):

        if filename == "green_time_allocation.png":

            html_path = os.path.join(
                record_path,
                "green_time_allocation.html"
            )

            if not os.path.isfile(html_path):
                messagebox.showerror(
                    "Interactive Graph Missing",
                    "green_time_allocation.html was not generated."
                )
                return

            webbrowser.open(
                "file://" + os.path.abspath(html_path)
            )
            return

        clear_frame(parent)

        tk.Label(
            parent,
            text=caption,
            font=("Arial", 20, "bold"),
            bg=BACKGROUND,
            fg=TEXT
        ).pack(pady=(10, 6))

        tk.Button(
            parent,
            text="RETURN TO GRAPH SELECTION",
            font=("Arial", 12, "bold"),
            command=lambda: show_graphs(
                parent,
                record_path,
                heading,
                show_improvement
            )
        ).pack(
            side="bottom",
            pady=12
        )

        image_path = os.path.join(
            record_path,
            filename
        )

        if os.path.isfile(image_path):

            photo = load_graph_image(
                image_path,
                max(400, root.winfo_screenwidth() - 100),
                max(300, root.winfo_screenheight() - 260)
            )

            image_references.append(photo)

            tk.Label(
                parent,
                image=photo,
                bg=BACKGROUND
            ).pack(
                fill="both",
                expand=True,
                padx=20,
                pady=8
            )

        else:

            tk.Label(
                parent,
                text=f"Graph file not found: {filename}",
                bg=BACKGROUND,
                fg="red",
                font=("Arial", 14)
            ).pack(expand=True)


    for index, (caption, filename, detail) in enumerate(graph_specs):

        row, column = divmod(index, 2)

        card = tk.Frame(
            selection_frame,
            bg="#F1F6FC",
            highlightbackground="#B7C9DD",
            highlightthickness=2
        )

        card.grid(
            row=row,
            column=column,
            sticky="nsew",
            padx=12,
            pady=12
        )

        selection_frame.grid_rowconfigure(
            row,
            weight=1
        )

        selection_frame.grid_columnconfigure(
            column,
            weight=1
        )

        image_path = os.path.join(
            record_path,
            filename
        )

        callback = (
            lambda f=filename, c=caption:
            open_graph(f, c)
        )

        if os.path.isfile(image_path):

            preview = load_graph_image(
                image_path,
                preview_w,
                preview_h
            )

            image_references.append(preview)

            preview_label = tk.Label(
                card,
                image=preview,
                bg="#F1F6FC",
                cursor="hand2"
            )

            preview_label.pack(
                fill="both",
                expand=True,
                padx=10,
                pady=(10, 4)
            )

            preview_label.bind(
                "<Button-1>",
                lambda event, cb=callback: cb()
            )

        else:

            preview_label = tk.Label(
                card,
                text="Graph preview unavailable",
                bg="#F1F6FC",
                fg="#8B2635"
            )

            preview_label.pack(
                fill="both",
                expand=True,
                padx=10,
                pady=(10, 4)
            )

        caption_label = tk.Label(
            card,
            text=caption,
            font=("Arial", 13, "bold"),
            bg="#F1F6FC",
            fg="#173B70",
            cursor="hand2",
            wraplength=520
        )

        caption_label.pack(
            padx=10,
            pady=(4, 2)
        )

        caption_label.bind(
            "<Button-1>",
            lambda event, cb=callback: cb()
        )

        detail_label = tk.Label(
            card,
            text=detail,
            font=("Arial", 10),
            bg="#F1F6FC",
            fg="#173B70",
            wraplength=520
        )

        detail_label.pack(
            padx=10,
            pady=(0, 10)
        )

        detail_label.bind(
            "<Button-1>",
            lambda event, cb=callback: cb()
        )



def show_dashboard(
    record_path,
    title="SIMULATION RESULTS",
    show_improvement=True
):

    menu_frame.pack_forget()
    records_frame.pack_forget()

    show_graphs(
        dashboard_graph_frame,
        record_path,
        title,
        show_improvement=show_improvement
    )

    dashboard_frame.pack(
        fill="both",
        expand=True,
        padx=30,
        pady=30
    )


def show_main_menu():

    dashboard_frame.pack_forget()
    records_frame.pack_forget()

    menu_frame.pack(
        fill="both",
        expand=True,
        padx=30,
        pady=30
    )

    set_status("Ready")



def read_record_metadata(record_path):

    metadata_path = os.path.join(
        record_path,
        "metadata.json"
    )

    if os.path.isfile(metadata_path):

        try:

            with open(
                metadata_path,
                "r",
                encoding="utf-8"
            ) as file:

                return json.load(file)

        except (json.JSONDecodeError, OSError):

            return {}

    return {}



def show_all_records():

    dashboard_frame.pack_forget()
    menu_frame.pack_forget()

    records_frame.pack(
        fill="both",
        expand=True,
        padx=30,
        pady=30
    )

    refresh_record_list()



def update_history_performance_graph(completed_records):

    global history_chart_canvas

    clear_frame(record_graph_frame)

    history_chart_canvas = None

    values = []

    for name, path, metadata in reversed(completed_records):

        csv_path = os.path.join(
            path,
            "comparison.csv"
        )

        try:

            improvement = calculate_improvement(
                csv_path
            )

            if improvement is not None:
                values.append(
                    (name, improvement)
                )

        except (OSError, ValueError, KeyError, TypeError):

            continue

    if not values:

        tk.Label(
            record_graph_frame,
            text="No valid comparison data is available yet.",
            font=("Arial", 14, "bold"),
            bg="white",
            fg="#526174"
        ).pack(expand=True)

        return

    tk.Label(
        record_graph_frame,
        text="PERFORMANCE IMPROVEMENT BY RECORD",
        font=("Arial", 17, "bold"),
        bg="white",
        fg=TEXT
    ).pack(pady=(8, 0))

    figure = Figure(
        figsize=(8.2, 5.2),
        dpi=100
    )

    axis = figure.add_subplot(111)

    record_names = [
        item[0]
        for item in values
    ]

    percentages = [
        item[1]
        for item in values
    ]

    axis.plot(
        record_names,
        percentages,
        marker="o",
        markersize=7,
        linewidth=2,
        label="SmartFlow improvement"
    )

    axis.axhline(
        0,
        linewidth=1,
        linestyle="--"
    )

    axis.set_title(
        "SmartFlow Performance Across Simulation Records"
    )

    axis.set_xlabel("Simulation Record")
    axis.set_ylabel("Improvement (%)")

    axis.grid(
        True,
        linestyle="--",
        alpha=0.45
    )

    axis.tick_params(
        axis="x",
        rotation=35
    )

    axis.legend(loc="best")

    for index, percentage in enumerate(percentages):

        axis.annotate(
            f"{percentage:.1f}%",
            (index, percentage),
            textcoords="offset points",
            xytext=(0, 8),
            ha="center",
            fontsize=8
        )

    figure.tight_layout()

    history_chart_canvas = FigureCanvasTkAgg(
        figure,
        master=record_graph_frame
    )

    history_chart_canvas.draw()

    history_chart_canvas.get_tk_widget().pack(
        fill="both",
        expand=True,
        padx=12,
        pady=8
    )
