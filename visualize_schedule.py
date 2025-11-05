import os
import sys
import glob
import argparse
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.cm import get_cmap


def find_latest_output_dir(base_output_dir: str = "output") -> str:
    """Find the most recent timestamped output directory under base_output_dir."""
    if not os.path.isdir(base_output_dir):
        raise FileNotFoundError(f"Output base directory not found: {base_output_dir}")
    # Collect only directories
    candidates = [os.path.join(base_output_dir, d) for d in os.listdir(base_output_dir)
                  if os.path.isdir(os.path.join(base_output_dir, d))]
    if not candidates:
        raise FileNotFoundError("No output directories found")
    # Sort by mtime descending
    candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return candidates[0]


def load_schedule_df(output_dir: str) -> pd.DataFrame:
    cp_sat_dir = os.path.join(output_dir, "cp_sat")
    schedule_path = os.path.join(cp_sat_dir, "cp_sat_batch_schedule.csv")
    if not os.path.exists(schedule_path):
        raise FileNotFoundError(f"Schedule file not found: {schedule_path}")
    df = pd.read_csv(schedule_path)
    required = {"Transporter", "Batch", "Treatment_program", "Stage", "Station", "EntryTime", "ExitTime"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in schedule: {missing}")
    return df


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def plot_schedule(df: pd.DataFrame, output_dir: str, filename: str = "schedule_gantt.png") -> str:
    cp_sat_dir = os.path.join(output_dir, "cp_sat")
    ensure_dir(cp_sat_dir)

    # Read start stations and program per batch from production.csv
    prod_path = os.path.join(output_dir, "initialization", "production.csv")
    start_station_by_batch = {}
    program_by_batch = {}
    if os.path.exists(prod_path):
        try:
            prod_df = pd.read_csv(prod_path)
            if {"Batch", "Start_station"}.issubset(set(prod_df.columns)):
                prod_df["Batch"] = pd.to_numeric(prod_df["Batch"], errors="coerce").fillna(0).astype(int)
                prod_df["Start_station"] = pd.to_numeric(prod_df["Start_station"], errors="coerce").fillna(0).astype(int)
                start_station_by_batch = {int(r["Batch"]): int(r["Start_station"]) for _, r in prod_df.iterrows()}
            if {"Batch", "Treatment_program"}.issubset(set(prod_df.columns)):
                prod_df["Treatment_program"] = pd.to_numeric(prod_df["Treatment_program"], errors="coerce").fillna(0).astype(int)
                program_by_batch = {int(r["Batch"]): int(r["Treatment_program"]) for _, r in prod_df.iterrows()}
        except Exception:
            start_station_by_batch = {}
            program_by_batch = {}

    # Compute average_task_time the same way as Phase 1: mean TotalTaskTime from cp_sat_transfer_tasks.csv
    avg_task_time = None
    transfer_tasks_path = os.path.join(cp_sat_dir, "cp_sat_transfer_tasks.csv")
    if os.path.exists(transfer_tasks_path):
        try:
            tt_df = pd.read_csv(transfer_tasks_path)
            if "TotalTaskTime" in tt_df.columns and not tt_df.empty:
                avg_task_time = float(pd.to_numeric(tt_df["TotalTaskTime"], errors="coerce").dropna().mean())
        except Exception:
            avg_task_time = None

    # Stations on Y-axis should also include potential Start_station values so the start marker can be drawn
    stations_in_df = set(df["Station"].unique().tolist())
    start_stations = set(start_station_by_batch.values()) if start_station_by_batch else set()
    stations_all = sorted(stations_in_df.union(start_stations))
    stations = stations_all
    station_to_idx = {s: i for i, s in enumerate(stations)}

    # Prepare colors per batch
    batches = sorted(df["Batch"].unique().tolist())
    cmap = get_cmap("tab10")
    color_map = {b: cmap((i % 10) / 10.0) for i, b in enumerate(batches)}

    fig, ax = plt.subplots(figsize=(12, 0.6 * max(6, len(stations))))

    # For each row, draw a bar at the station index
    bar_height = 0.6  # thickness per station row
    for _, row in df.iterrows():
        y = station_to_idx[row["Station"]]
        start = float(row["EntryTime"]) if pd.notna(row["EntryTime"]) else 0.0
        end = float(row["ExitTime"]) if pd.notna(row["ExitTime"]) else start
        width = max(1.0, end - start)  # ensure visible even if 0s duration
        color = color_map.get(row["Batch"], "gray")
        ax.broken_barh([(start, width)], (y - bar_height/2, bar_height), facecolors=color, edgecolor="black", linewidth=0.5)

    # Y-axis with station labels
    ax.set_yticks(list(range(len(stations))))
    ax.set_yticklabels([str(s) for s in stations])
    ax.set_ylabel("Station")
    ax.set_xlabel("Time (s)")
    ax.set_title("CP-SAT Phase 1 Schedule")

    # Draw a small colored circle at each batch's start time at its Start_station
    # Start time approximation: EntryTime(Stage 1) - average_task_time
    if avg_task_time is not None and avg_task_time >= 0 and start_station_by_batch:
        # Compute per-batch Stage 1 entry times from df
        try:
            stage1 = df[df["Stage"] == 1].copy()
            # Ensure numeric
            stage1["Batch"] = pd.to_numeric(stage1["Batch"], errors="coerce").fillna(0).astype(int)
            stage1["EntryTime"] = pd.to_numeric(stage1["EntryTime"], errors="coerce").fillna(0.0)
            e1_by_batch = {int(r["Batch"]): float(r["EntryTime"]) for _, r in stage1.iterrows()}
            for b in batches:
                if b in start_station_by_batch and b in e1_by_batch:
                    start_station = int(start_station_by_batch[b])
                    if start_station in station_to_idx:
                        y = station_to_idx[start_station]
                        x = max(0.0, float(e1_by_batch[b]) - float(avg_task_time))
                        color = color_map.get(b, "gray")
                        ax.scatter([x], [y], s=30, c=[color], edgecolors="black", zorder=5)
                        # Add Treatment_program label just below the marker
                        # Try to obtain program from production.csv, fallback to df (Stage 1 row)
                        prog = program_by_batch.get(b)
                        if prog is None:
                            try:
                                prog = int(stage1.loc[stage1["Batch"] == b, "Treatment_program"].iloc[0])
                            except Exception:
                                prog = None
                        if prog is not None:
                            # Position slightly below the station row
                            text_y = y - (bar_height/2) - 0.1
                            ax.text(x, text_y, f"{prog}", ha="center", va="top", fontsize=7,
                                    color="black", zorder=6,
                                    bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.7))
        except Exception:
            pass

    # Legend for batches
    handles = [plt.Line2D([0], [0], color=color_map[b], lw=6) for b in batches]
    labels = [f"Batch {b}" for b in batches]
    ax.legend(handles, labels, title="Batches", loc="upper right", bbox_to_anchor=(1.15, 1.0))

    ax.grid(True, axis="x", linestyle=":", linewidth=0.5)
    fig.tight_layout()

    out_path = os.path.join(cp_sat_dir, filename)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def main():
    parser = argparse.ArgumentParser(description="Visualize CP-SAT Phase 1 schedule as a simple Gantt chart.")
    parser.add_argument("--output-dir", dest="output_dir", default=None, help="Path to snapshot output directory containing cp_sat folder. If omitted, uses latest under ./output.")
    parser.add_argument("--filename", dest="filename", default="schedule_gantt.png", help="Output image filename inside cp_sat directory.")
    args = parser.parse_args()

    if args.output_dir is None:
        output_dir = find_latest_output_dir("output")
        print(f"Using latest output directory: {output_dir}")
    else:
        output_dir = args.output_dir
        print(f"Using provided output directory: {output_dir}")

    df = load_schedule_df(output_dir)
    out_path = plot_schedule(df, output_dir, args.filename)
    print(f"Saved schedule visualization: {out_path}")


if __name__ == "__main__":
    main()
