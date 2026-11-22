def refresh_record_list():
    global record_paths

    record_paths = []

    for widget in record_card_container.winfo_children():
        widget.destroy()

    ensure_records_dir()

    folders = []

    for name in os.listdir(RECORDS_DIR):
        path = os.path.join(RECORDS_DIR, name)

        if os.path.isdir(path) and re.fullmatch(r"Record_\d+", name):
            folders.append((name, path))

    folders.sort(
        key=lambda item: int(item[0].split("_")[1]),
        reverse=True
    )

    completed = []

    for name, path in folders:
        metadata = read_record_metadata(path)

        if metadata.get("status") == "completed":
            completed.append((name, path, metadata))

    if not completed:
        tk.Label(
            record_card_container,
            text="No saved simulations yet.\nRun a simulation to create your first record.",
            font=("Arial", 12),
            bg="white",
            fg="#526174",
            justify="center",
            wraplength=260
        ).pack(
            fill="x",
            padx=10,
            pady=25
        )

        record_details_label.config(
            text="No completed records available."
        )

        update_history_performance_graph([])
        return

    for name, path, metadata in completed:
        record_paths.append(path)

        date = metadata.get("date", "Date unavailable")
        time = metadata.get("time", "")
        duration = metadata.get("duration_minutes")
        count_label = f"{duration} minutes" if duration is not None else f"{metadata.get('simulations', '?')} simulations"

        card = tk.Frame(
            record_card_container,
            bg="#F1F6FC",
            highlightbackground="#B7C9DD",
            highlightthickness=1,
            bd=0
        )

        card.pack(
            fill="x",
            padx=8,
            pady=6
        )

        button = tk.Button(
            card,
            text=f"{name}\n{date}  {time}\n{count_label}",
            font=("Arial", 11, "bold"),
            bg="#F1F6FC",
            fg="#173B70",
            activebackground="#D6E7F8",
            activeforeground="#102B50",
            relief="flat",
            bd=0,
            anchor="w",
            justify="left",
            padx=14,
            pady=12,
            cursor="hand2",
            command=lambda selected_path=path: display_selected_record(
                selected_path
            )
        )

        button.pack(fill="x")

    record_card_canvas.yview_moveto(0)

    record_details_label.config(
        text="Performance comparison across all saved records"
    )

    update_history_performance_graph(completed)


def display_selected_record(record_path):
    metadata = read_record_metadata(record_path)

    record_id = metadata.get(
        "record_id",
        os.path.basename(record_path)
    )

    date = metadata.get("date", "Unknown date")
    time = metadata.get("time", "Unknown time")
    duration = metadata.get("duration_minutes")
    run_label = f"{duration} minutes" if duration is not None else f"{metadata.get('simulations', 'Unknown')} simulations"

    records_frame.pack_forget()
    dashboard_frame.pack_forget()

    record_view_heading.config(
        text=f"{record_id}  |  {date} {time}  |  {run_label}"
    )

    show_graphs(
        record_view_graph_area,
        record_path,
        heading=f"SIMULATION RESULTS — {record_id}"
    )

    record_view_frame.pack(
        fill="both",
        expand=True,
        padx=30,
        pady=30
    )


def back_to_records():
    record_view_frame.pack_forget()

    records_frame.pack(
        fill="both",
        expand=True,
        padx=30,
        pady=30
    )


def draw_road_visual(event=None):
    width = max(500, main_road_canvas.winfo_width())
    height = 156

    main_road_canvas.delete("all")

    main_road_canvas.create_rectangle(
        12,
        18,
        width - 12,
        height - 18,
        fill="#20252B",
        outline="#000000",
        width=4
    )

    main_road_canvas.create_line(
        22,
        29,
        width - 22,
        29,
        fill="white",
        width=3
    )

    main_road_canvas.create_line(
        22,
        height - 29,
        width - 22,
        height - 29,
        fill="white",
        width=3
    )

    main_road_canvas.create_line(
        25,
        height // 2,
        width - 25,
        height // 2,
        fill="white",
        width=3,
        dash=(22, 16)
    )

    car_specs = [
        (0.18, 43, "#E74C3C"),
        (0.47, 43, "#F1C40F"),
        (0.77, 43, "#3498DB"),
        (0.31, 91, "#2ECC71"),
        (0.64, 91, "#E67E22"),
        (0.88, 91, "#9B59B6")
    ]

    for position, y, color in car_specs:
        x = int(width * position)

        main_road_canvas.create_rectangle(
            x - 31,
            y - 12,
            x + 31,
            y + 12,
            fill=color,
            outline="#111111",
            width=2
        )

        main_road_canvas.create_rectangle(
            x - 13,
            y - 9,
            x + 12,
            y + 9,
            fill="#D9F0FF",
            outline="#17202A",
            width=1
        )

        for wheel_x in (x - 22, x + 22):
            main_road_canvas.create_rectangle(
                wheel_x - 4,
                y - 15,
                wheel_x + 4,
                y - 10,
                fill="#080808",
                outline="#080808"
            )

            main_road_canvas.create_rectangle(
                wheel_x - 4,
                y + 10,
                wheel_x + 4,
                y + 15,
                fill="#080808",
                outline="#080808"
            )


def on_record_canvas_configure(event=None):
    record_card_canvas.configure(
        scrollregion=record_card_canvas.bbox("all")
    )


def on_record_mousewheel(event):
    record_card_canvas.yview_scroll(
        int(-1 * (event.delta / 120)),
        "units"
      )
