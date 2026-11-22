menu_frame = tk.Frame(root, bg=BACKGROUND)
menu_frame.pack(fill="both", expand=True)

home_content = tk.Frame(menu_frame, bg=BACKGROUND)
home_content.pack(
    fill="both",
    expand=True,
    padx=30,
    pady=(12, 18)
)

header = tk.Label(
    home_content,
    text="SMARTFLOW",
    font=("Arial", 36, "bold"),
    bg=BACKGROUND,
    fg=TEXT
)
header.pack(pady=(4, 0))

traffic_light_label = tk.Label(
    home_content,
    text="🚦",
    font=("Arial", 38),
    bg=BACKGROUND,
    fg=TEXT
)
traffic_light_label.pack(pady=(0, 1))

subtitle = tk.Label(
    home_content,
    text="ADAPTIVE TRAFFIC SIGNAL MANAGEMENT SYSTEM",
    font=("Arial", 15, "bold"),
    bg=BACKGROUND,
    fg="#173B70"
)
subtitle.pack(pady=(0, 8))

main_road_canvas = tk.Canvas(
    home_content,
    height=156,
    bg=BACKGROUND,
    highlightthickness=0,
    bd=0
)
main_road_canvas.pack(
    fill="x",
    padx=30,
    pady=(2, 12)
)

main_road_canvas.bind(
    "<Configure>",
    draw_road_visual
)

root.after(150, draw_road_visual)


menu_options = tk.Frame(home_content, bg=BACKGROUND)
menu_options.pack(pady=(10, 4))

start_button = tk.Button(
    menu_options,
    text="START SIMULATION",
    font=("Arial", 16, "bold"),
    width=25,
    height=2,
    bg="#173B70",
    fg="white",
    activebackground="#24558F",
    activeforeground="white",
    relief="raised",
    bd=3,
    cursor="hand2",
    command=start_simulation
)
start_button.pack(pady=8)

records_button = tk.Button(
    menu_options,
    text="ALL RECORDS",
    font=("Arial", 16, "bold"),
    width=25,
    height=2,
    bg="#FFFFFF",
    fg="#173B70",
    activebackground="#DCEAF7",
    relief="raised",
    bd=3,
    cursor="hand2",
    command=show_all_records
)
records_button.pack(pady=8)

exit_menu_button = tk.Button(
    menu_options,
    text="EXIT",
    font=("Arial", 16, "bold"),
    width=25,
    height=2,
    bg="#343A40",
    fg="white",
    activebackground="#50575E",
    activeforeground="white",
    relief="raised",
    bd=3,
    cursor="hand2",
    command=exit_program
)
exit_menu_button.pack(pady=8)

status_label = tk.Label(
    home_content,
    text="Ready",
    font=("Arial", 12, "bold"),
    bg=BACKGROUND,
    fg="green"
)
status_label.pack(pady=(8, 0))


dashboard_frame = tk.Frame(root, bg=BACKGROUND)

dashboard_graph_frame = tk.Frame(
    dashboard_frame,
    bg=BACKGROUND
)
dashboard_graph_frame.pack(
    fill="both",
    expand=True
)

dashboard_back_button = tk.Button(
    dashboard_frame,
    text="BACK TO MENU",
    font=("Arial", 12, "bold"),
    command=show_main_menu
)
dashboard_back_button.pack(
    side="bottom",
    pady=10,
    before=dashboard_graph_frame
)


records_frame = tk.Frame(root, bg=BACKGROUND)

records_heading = tk.Label(
    records_frame,
    text="SAVED SIMULATION RECORDS",
    font=("Arial", 24, "bold"),
    bg=BACKGROUND,
    fg=TEXT
)
records_heading.pack(pady=(14, 8))

record_body = tk.Frame(
    records_frame,
    bg=BACKGROUND
)
record_body.pack(
    fill="both",
    expand=True,
    padx=18,
    pady=8
)


list_panel = tk.Frame(
    record_body,
    bg="white",
    width=340,
    highlightbackground="#173B70",
    highlightthickness=2
)
list_panel.pack(
    side="left",
    fill="y",
    padx=(0, 14)
)
list_panel.pack_propagate(False)

tk.Label(
    list_panel,
    text="PREVIOUS RUNS",
    font=("Arial", 16, "bold"),
    bg="#173B70",
    fg="white",
    pady=12
).pack(fill="x")


list_container = tk.Frame(
    list_panel,
    bg="white"
)
list_container.pack(
    fill="both",
    expand=True,
    padx=5,
    pady=5
)

record_card_canvas = tk.Canvas(
    list_container,
    bg="white",
    highlightthickness=0,
    bd=0
)

record_card_scrollbar = tk.Scrollbar(
    list_container,
    orient="vertical",
    command=record_card_canvas.yview
)

record_card_container = tk.Frame(
    record_card_canvas,
    bg="white"
)

record_card_container.bind(
    "<Configure>",
    on_record_canvas_configure
)

record_card_window = record_card_canvas.create_window(
    (0, 0),
    window=record_card_container,
    anchor="nw"
)

record_card_canvas.configure(
    yscrollcommand=record_card_scrollbar.set
)

record_card_canvas.pack(
    side="left",
    fill="both",
    expand=True
)

record_card_scrollbar.pack(
    side="right",
    fill="y"
)


def resize_record_cards(event):
    record_card_canvas.itemconfigure(
        record_card_window,
        width=event.width
    )


record_card_canvas.bind(
    "<Configure>",
    resize_record_cards
)

record_card_canvas.bind(
    "<MouseWheel>",
    on_record_mousewheel
)

record_card_canvas.bind(
    "<Button-4>",
    lambda event: record_card_canvas.yview_scroll(-1, "units")
)

record_card_canvas.bind(
    "<Button-5>",
    lambda event: record_card_canvas.yview_scroll(1, "units")
)


details_panel = tk.Frame(
    record_body,
    bg=BACKGROUND
)
details_panel.pack(
    side="right",
    fill="both",
    expand=True
)

record_details_label = tk.Label(
    details_panel,
    text="Performance comparison across all saved records",
    font=("Arial", 14, "bold"),
    bg=BACKGROUND,
    fg=TEXT
)
record_details_label.pack(pady=8)

record_graph_frame = tk.Frame(
    details_panel,
    bg="white",
    highlightbackground="#173B70",
    highlightthickness=2
)
record_graph_frame.pack(
    fill="both",
    expand=True,
    padx=8,
    pady=8
)


record_paths = []

record_view_frame = tk.Frame(
    root,
    bg=BACKGROUND
)

record_view_heading = tk.Label(
    record_view_frame,
    text="SIMULATION RECORD",
    font=("Arial", 19, "bold"),
    bg=BACKGROUND,
    fg=TEXT
)
record_view_heading.pack(
    fill="x",
    padx=15,
    pady=(12, 4)
)

record_view_graph_area = tk.Frame(
    record_view_frame,
    bg=BACKGROUND
)
record_view_graph_area.pack(
    fill="both",
    expand=True,
    padx=12,
    pady=4
)

record_view_back_button = tk.Button(
    record_view_frame,
    text="BACK TO ALL RECORDS",
    font=("Arial", 12, "bold"),
    width=22,
    command=back_to_records
)
record_view_back_button.pack(
    side="bottom",
    pady=(4, 12),
    before=record_view_graph_area
)


records_bottom = tk.Frame(
    records_frame,
    bg=BACKGROUND
)
records_bottom.pack(
    side="bottom",
    fill="x",
    pady=8,
    before=record_body
)

tk.Button(
    records_bottom,
    text="REFRESH",
    font=("Arial", 12, "bold"),
    width=14,
    command=refresh_record_list
).pack(
    side="left",
    padx=15
)

tk.Button(
    records_bottom,
    text="BACK TO MENU",
    font=("Arial", 12, "bold"),
    width=18,
    command=show_main_menu
).pack(
    side="right",
    padx=15
)


root.bind(
    "<Escape>",
    lambda event: root.attributes("-fullscreen", False)
)

root.bind(
    "<F11>",
    lambda event: root.attributes(
        "-fullscreen",
        not root.attributes("-fullscreen")
    )
)

ensure_records_dir()
