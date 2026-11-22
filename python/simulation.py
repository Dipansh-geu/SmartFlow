def exit_program():
    root.destroy()


def ensure_records_dir():
    os.makedirs(RECORDS_DIR, exist_ok=True)


def next_record_path():
    ensure_records_dir()

    numbers = []

    for name in os.listdir(RECORDS_DIR):
        match = re.fullmatch(r"Record_(\d+)", name)
        full_path = os.path.join(RECORDS_DIR, name)

        if match and os.path.isdir(full_path):
            numbers.append(int(match.group(1)))

    next_number = max(numbers, default=0) + 1
    record_id = f"Record_{next_number:03d}"
    path = os.path.join(RECORDS_DIR, record_id)

    os.makedirs(path)

    return path, record_id


def calculate_improvement(csv_path):
    """Return overall time saved (%) using vehicle-weighted mean queue delay.

    Each interval's mean is weighted by its vehicle throughput. This avoids
    treating a lightly populated final minute as representative of the whole
    simulation. Delay is SUMO waitingTime + departDelay, as written by the
    SUMO runner into the per-interval metrics.
    """
    fixed_avg_col = "Fixed_Cycle_Average_Wait_Seconds"
    smart_avg_col = "SmartFlow_Cycle_Average_Wait_Seconds"
    fixed_count_col = "Fixed_Throughput"
    smart_count_col = "SmartFlow_Throughput"

    fixed_total = 0.0
    smart_total = 0.0
    fixed_count = 0.0
    smart_count = 0.0

    with open(csv_path, "r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        required = {fixed_avg_col, smart_avg_col, fixed_count_col, smart_count_col}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError("comparison.csv is missing per-interval average or throughput columns.")

        for row in reader:
            try:
                f_avg = float(row[fixed_avg_col])
                s_avg = float(row[smart_avg_col])
                f_n = float(row[fixed_count_col])
                s_n = float(row[smart_count_col])
            except (ValueError, TypeError, KeyError):
                continue

            if all(math.isfinite(v) for v in (f_avg, s_avg, f_n, s_n)) and f_n > 0 and s_n > 0:
                fixed_total += f_avg * f_n
                fixed_count += f_n
                smart_total += s_avg * s_n
                smart_count += s_n

    if fixed_count <= 0 or smart_count <= 0:
        return None

    fixed_overall = fixed_total / fixed_count
    smart_overall = smart_total / smart_count
    if fixed_overall <= 0:
        return None

    return ((fixed_overall - smart_overall) / fixed_overall) * 100.0


def write_metadata(record_path, record_id, minutes, status):
    metadata = {
        "record_id": record_id,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": datetime.now().strftime("%H:%M:%S"),
        "duration_minutes": minutes,
        "duration_seconds": minutes * 60,
        "status": status
    }

    metadata_path = os.path.join(record_path, "metadata.json")

    with open(metadata_path, "w", encoding="utf-8") as file:
        json.dump(metadata, file, indent=4)


def set_status(message, color="green"):
    status_label.config(text=message, fg=color)
    root.update_idletasks()


def choose_simulation_mode():
    """Ask the user which SmartFlow traffic source to run."""
    dialog = tk.Toplevel(root)
    dialog.title("Choose Simulation Mode")
    dialog.configure(bg=BACKGROUND)
    dialog.resizable(False, False)
    dialog.transient(root)
    dialog.grab_set()

    tk.Label(
        dialog,
        text="SELECT SIMULATION MODE",
        font=("Arial", 16, "bold"),
        bg=BACKGROUND,
        fg=TEXT
    ).pack(padx=28, pady=(22, 14))

    result = {"mode": None}

    def select(mode):
        result["mode"] = mode
        dialog.destroy()

    tk.Button(
        dialog,
        text="NON-VIRTUAL SIMULATION",
        width=25,
        height=2,
        command=lambda: select("generator")
    ).pack(padx=24, pady=7)

    tk.Button(
        dialog,
        text="VIRTUAL SIMULATION",
        width=25,
        height=2,
        command=lambda: select("sumo")
    ).pack(padx=24, pady=7)

    tk.Button(
        dialog, text="CANCEL", width=25, command=dialog.destroy
    ).pack(padx=24, pady=(7, 20))

    dialog.update_idletasks()
    x = root.winfo_rootx() + (root.winfo_width() - dialog.winfo_width()) // 2
    y = root.winfo_rooty() + (root.winfo_height() - dialog.winfo_height()) // 2
    dialog.geometry(f"+{max(0, x)}+{max(0, y)}")
    root.wait_window(dialog)
    return result["mode"]


def start_simulation():
    mode = choose_simulation_mode()

    if mode is None:
        return

    if mode == "generator":
        start_vehicle_generator_simulation()

    elif mode == "sumo":
        start_sumo_simulation(gui=True)


def start_sumo_simulation(gui=True):
    """Run fixed and SmartFlow SUMO scenarios using exact TraCI observations."""
    mode_title = "SUMO Virtual (GUI)" if gui else "SUMO (Headless)"
    minutes = simpledialog.askinteger(
        "SUMO Virtual Simulation",
        "Enter simulation duration in minutes:",
        parent=root, minvalue=1, maxvalue=240
    )
    if minutes is None:
        return

    runner = os.path.join(PYTHON_DIR, "sumo_mode", "run_sumo.py")
    if not os.path.isfile(runner):
        messagebox.showerror("Missing File", f"SUMO runner not found:\n{runner}")
        return

    record_path = None
    record_id = None
    log_file = None

    try:
        record_path, record_id = next_record_path()
        config_source = os.path.join(PROJECT_DIR, "config.ini")
        if os.path.isfile(config_source):
            shutil.copy2(config_source, os.path.join(record_path, "config.ini"))

        start_button.config(state="disabled")
        records_button.config(state="disabled")
        set_status(f"Starting SUMO TraCI simulation — {record_id}...")

        log_path = os.path.join(record_path, "sumo_engine.log")
        log_file = open(log_path, "w", encoding="utf-8")
        command = [
            sys.executable,
            runner,
            "--minutes", str(minutes),
            "--out", record_path,
            "--render", "gui" if gui else "headless",
            "--delay-ms", "100"
        ]

        process = subprocess.Popen(
            command, cwd=PROJECT_DIR, stdout=log_file,
            stderr=subprocess.STDOUT, text=True
        )

        def poll_sumo():
            code = process.poll()
            if code is None:
                root.after(500, poll_sumo)
                return

            log_file.close()
            required = [
                "comparison.csv",
                "density.csv",
                "queue_length.csv",
                "signal_log.csv",
                "report.txt"
            ]
            missing = [name for name in required if not os.path.isfile(os.path.join(record_path, name))]

            if code != 0 or missing:
                try:
                    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                        details = f.read()[-12000:]
                except OSError:
                    details = ""
                error = details or f"SUMO exited with code {code}."
                if missing:
                    error += "\nMissing output files: " + ", ".join(missing)
                write_metadata(record_path, record_id, minutes, "failed")
                messagebox.showerror("SUMO Simulation Failed", error)
                set_status("SUMO simulation failed.", "red")
                start_button.config(state="normal")
                records_button.config(state="normal")
                return

            try:
                phase_csv = os.path.join(record_path, "smartflow_green_phases.csv")
                with open(os.path.join(record_path, "signal_log.csv"), newline="", encoding="utf-8") as src, open(phase_csv, "w", newline="", encoding="utf-8") as dst:
                    reader = csv.DictReader(src)
                    writer = csv.writer(dst)
                    writer.writerow(["Lane", "Start_Seconds", "End_Seconds"])
                    lane_ids = {"north": 1, "east": 2, "south": 3, "west": 4}
                    for row in reader:
                        if row.get("scenario") != "smart_exact":
                            continue
                        lane = lane_ids.get((row.get("lane") or "").strip().lower())
                        if lane is not None:
                            writer.writerow([lane, row.get("phase_start"), row.get("phase_end")])

                set_status("Preparing SUMO results dashboard...")
                subprocess.run([sys.executable, DENSITY_SCRIPT], check=True, cwd=record_path)
                subprocess.run([sys.executable, GREEN_TIME_SCRIPT], check=True, cwd=record_path)
                subprocess.run([sys.executable, WAIT_COMPARISON_SCRIPT], check=True, cwd=record_path)
                subprocess.run([sys.executable, QUEUE_LENGTH_SCRIPT], check=True, cwd=record_path)

                expected_graphs = [
                    "density.png",
                    "green_time_allocation.png",
                    "green_time_allocation.html",
                    "average_wait_comparison.png",
                    "queue_length_comparison.png",
                ]
                missing_graphs = [
                    name for name in expected_graphs
                    if not os.path.isfile(os.path.join(record_path, name))
                    or os.path.getsize(os.path.join(record_path, name)) == 0
                ]
                if missing_graphs:
                    raise FileNotFoundError(
                        "Graph generation did not produce: "
                        + ", ".join(missing_graphs)
                    )

                write_metadata(record_path, record_id, minutes, "completed")
                metadata_path = os.path.join(record_path, "metadata.json")
                with open(metadata_path, "r+", encoding="utf-8") as f:
                    metadata = json.load(f)
                    metadata["mode"] = mode_title

                    metadata["traffic_data_source"] = (
                        "SUMO TraCI exact observations"
                    )

                    metadata["vehicle_arrival_model"] = "Poisson process"
                    metadata["duration_minutes"] = minutes
                    metadata["duration_seconds"] = minutes * 60
                    f.seek(0)
                    json.dump(metadata, f, indent=4)
                    f.truncate()

                set_status(f"{record_id} completed successfully.")
                show_dashboard(
                    record_path,
                    title=f"{mode_title.upper()} RESULTS — {record_id}",
                    show_improvement=True
                )
            except Exception as error:
                write_metadata(record_path, record_id, minutes, "failed")
                messagebox.showerror("Dashboard Error", str(error))
                set_status("Could not prepare SUMO dashboard.", "red")
            finally:
                start_button.config(state="normal")
                records_button.config(state="normal")

        poll_sumo()

    except Exception as error:
        if log_file and not log_file.closed:
            log_file.close()
        if record_path and record_id:
            write_metadata(record_path, record_id, minutes, "failed")
        messagebox.showerror("SUMO Simulation Error", str(error))
        set_status("SUMO simulation failed.", "red")
        start_button.config(state="normal")
        records_button.config(state="normal")


def start_vehicle_generator_simulation():
    minutes = simpledialog.askinteger(
        "SmartFlow",
        "Enter simulation duration in minutes:",
        parent=root,
        minvalue=1,
        maxvalue=240
    )

    if minutes is None:
        return

    executable = EXE_PATH

    source_files = [
        os.path.join(PROJECT_DIR, "src", name)
        for name in (
            "main.cpp",
            "Lane.cpp",
            "SignalController.cpp",
            "Statistics.cpp",
            "Vehicle.cpp"
        )
    ]

    header_files = [
        os.path.join(PROJECT_DIR, "include", name)
        for name in (
            "Lane.h",
            "SignalController.h",
            "Statistics.h",
            "Vehicle.h"
        )
    ]

    compiler = shutil.which("g++") or shutil.which("clang++")

    existing = [
        f for f in source_files + header_files
        if os.path.isfile(f)
    ]

    exe_exists = os.path.isfile(executable)

    source_is_newer = (
        exe_exists
        and any(
            os.path.getmtime(f) > os.path.getmtime(executable)
            for f in existing
        )
    )
    stale = exe_exists and bool(compiler) and source_is_newer

    if exe_exists and source_is_newer and not compiler:
        messagebox.showerror(
            "C++ Compiler Required",
            "The SmartFlow engine source has changed, but the bundled executable is outdated.\n\n"
            "Install MinGW-w64 (g++) or LLVM (clang++) so the GUI can rebuild the updated engine."
        )
        set_status("Updated C++ engine needs a compiler.", "red")
        return

    if not exe_exists or stale:
        if compiler and all(os.path.isfile(f) for f in source_files):
            set_status("Building SmartFlow C++ engine...")

            command = (
                [compiler, "-std=c++17", "-O2", "-Iinclude"]
                + [
                    os.path.relpath(f, PROJECT_DIR)
                    for f in source_files
                ]
                + ["-o", executable]
            )

            try:
                subprocess.run(
                    command,
                    cwd=PROJECT_DIR,
                    check=True,
                    capture_output=True,
                    text=True
                )

            except subprocess.CalledProcessError as build_error:
                messagebox.showerror(
                    "Build Error",
                    build_error.stderr or str(build_error)
                )
                set_status("Build failed.", "red")
                return

        elif not exe_exists:
            messagebox.showerror(
                "Missing Engine",
                f"{os.path.basename(executable)} was not found in:\n"
                f"{PROJECT_DIR}\n\n"
                "Build it for THIS operating system "
                "(a file built on Linux will not run on Windows):\n"
                "  g++ -std=c++17 -O2 -Iinclude src/*.cpp -o "
                + os.path.basename(executable)
                + "\nor install MinGW-w64 / put g++ on PATH "
                "so the GUI can build it automatically."
            )

            set_status("Engine missing.", "red")
            return

    graph_scripts = [
        DENSITY_SCRIPT,
        GREEN_TIME_SCRIPT,
        WAIT_COMPARISON_SCRIPT,
        QUEUE_LENGTH_SCRIPT,
    ]

    missing_scripts = [
        os.path.basename(script)
        for script in graph_scripts
        if not os.path.isfile(script)
    ]

    if missing_scripts:
        messagebox.showerror(
            "Missing File",
            "The following graph script(s) are missing:\n\n"
            + "\n".join(missing_scripts)
        )
        return

    record_path = None
    record_id = None

    try:
        record_path, record_id = next_record_path()

        config_source = os.path.join(PROJECT_DIR, "config.ini")

        if os.path.isfile(config_source):
            shutil.copy2(
                config_source,
                os.path.join(record_path, "config.ini")
            )

        start_button.config(state="disabled")
        records_button.config(state="disabled")

        set_status(f"Running {record_id}...")

        engine_log_path = os.path.join(record_path, "engine.log")
        engine_log = open(engine_log_path, "w", encoding="utf-8")

        process = subprocess.Popen(
            [executable],
            stdin=subprocess.PIPE,
            stdout=engine_log,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=record_path
        )

        process.stdin.write(f"{minutes}\n")
        process.stdin.flush()
        process.stdin.close()

        def poll_engine():
            return_code = process.poll()

            if return_code is None:
                root.after(150, poll_engine)
                return

            engine_log.close()

            try:
                with open(engine_log_path, "r", encoding="utf-8", errors="replace") as log_file:
                    engine_output = log_file.read().strip()
            except OSError:
                engine_output = ""

            if return_code != 0:
                message = (
                    engine_output
                    or f"Engine exited with code {return_code}"
                )

                try:
                    write_metadata(
                        record_path,
                        record_id,
                        minutes,
                        "failed"
                    )
                except Exception:
                    pass

                messagebox.showerror("Simulation Error", message)
                set_status("Simulation failed.", "red")

                start_button.config(state="normal")
                records_button.config(state="normal")

                return

            continue_after_engine()

        def continue_after_engine():
            try:
                density_csv = os.path.join(record_path, "density.csv")
                comparison_csv = os.path.join(record_path, "comparison.csv")

                if not os.path.isfile(density_csv):
                    raise FileNotFoundError(
                        "The C++ program did not create density.csv."
                    )

                if not os.path.isfile(comparison_csv):
                    raise FileNotFoundError(
                        "The C++ program did not create comparison.csv."
                    )

                set_status("Generating density graph...")

                subprocess.run(
                    [sys.executable, DENSITY_SCRIPT],
                    check=True,
                    cwd=record_path
                )

                set_status("Generating green-time allocation graph...")

                subprocess.run(
                    [sys.executable, GREEN_TIME_SCRIPT],
                    check=True,
                    cwd=record_path
                )

                set_status("Generating average waiting-time comparison...")

                subprocess.run(
                    [sys.executable, WAIT_COMPARISON_SCRIPT],
                    check=True,
                    cwd=record_path
                )

                set_status("Generating queue-length graph...")

                subprocess.run(
                    [sys.executable, QUEUE_LENGTH_SCRIPT],
                    check=True,
                    cwd=record_path
                )

                required_files = [
                    "density.png",
                    "green_time_allocation.png",
                    "green_time_allocation.html",
                    "average_wait_comparison.png",
                    "queue_length_comparison.png",
                    "report.txt"
                ]

                missing = [
                    name
                    for name in required_files
                    if not os.path.isfile(
                        os.path.join(record_path, name)
                    )
                ]

                if missing:
                    raise FileNotFoundError(
                        "Missing output file(s): "
                        + ", ".join(missing)
                    )

                write_metadata(
                    record_path,
                    record_id,
                    minutes,
                    "completed"
                )

                set_status(
                    f"{record_id} completed successfully."
                )

                show_dashboard(
                    record_path,
                    title=f"NON-VIRTUAL SIMULATION RESULTS — {record_id}"
                )

            except Exception as error:
                try:
                    write_metadata(
                        record_path,
                        record_id,
                        minutes,
                        "failed"
                    )
                except Exception:
                    pass

                messagebox.showerror(
                    "Simulation Error",
                    str(error)
                )

                set_status("Simulation failed.", "red")

            finally:
                start_button.config(state="normal")
                records_button.config(state="normal")

        poll_engine()
        return

    except Exception as error:
        if record_path and record_id:
            try:
                write_metadata(
                    record_path,
                    record_id,
                    minutes,
                    "failed"
                )
            except Exception:
                pass

        messagebox.showerror(
            "Simulation Error",
            str(error)
        )

        set_status("Simulation failed.", "red")

        start_button.config(state="normal")
        records_button.config(state="normal")
