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

    stations = sorted(df["Station"].unique().tolist())
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
