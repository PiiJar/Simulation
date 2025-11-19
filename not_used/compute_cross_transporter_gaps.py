import os
import pandas as pd
from typing import List, Tuple

# This script computes cross-transporter minimal time gaps for two given output runs.
# It replicates the conservative segment-overlap heuristic used in cp_sat_phase_2.

RUNS = {
    "5s": "900135_-_Factory_X_-_Nammo_Zinc-Phosphating_2025-11-11_08-15-01",
    "10s": "900135_-_Factory_X_-_Nammo_Zinc-Phosphating_2025-11-11_08-21-29",
    "dyn_0.0005": "900135_-_Factory_X_-_Nammo_Zinc-Phosphating_2025-11-11_08-58-31",
    # New run with tripled dynamic coefficient (0.0015 s/mm)
    "dyn_0.0015": "900135_-_Factory_X_-_Nammo_Zinc-Phosphating_2025-11-11_09-19-08",
    "base12_dyn_0.0015": "900135_-_Factory_X_-_Nammo_Zinc-Phosphating_2025-11-11_09-26-05",
    # Increased dynamic coefficient to 0.003 s/mm (base 12s)
    "base12_dyn_0.003": "900135_-_Factory_X_-_Nammo_Zinc-Phosphating_2025-11-11_09-34-06",
    # Increased dynamic coefficient further to 0.01 s/mm (base 12s)
    "base12_dyn_0.01": "900135_-_Factory_X_-_Nammo_Zinc-Phosphating_2025-11-11_09-42-39",
}

BASE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")


def load_tasks(run_dir: str) -> Tuple[List[Tuple[int,int,int,int,int,int,int,int]], int]:
    cp = os.path.join(BASE, run_dir, "cp_sat")
    transporter_csv = os.path.join(cp, "cp_sat_transporter_schedule.csv")
    stations_csv = os.path.join(cp, "cp_sat_stations.csv")
    transp_csv = os.path.join(cp, "cp_sat_transporters.csv")

    df = pd.read_csv(transporter_csv)
    st = pd.read_csv(stations_csv)
    tr = pd.read_csv(transp_csv)

    # avoid per transporter; limit is max of two
    avoid_by_t = {int(r["Transporter_id"]): int(pd.to_numeric(r.get("Avoid", 0), errors="coerce") or 0) for _, r in tr.iterrows()}

    x_map = {int(r["Number"]): int(r["X Position"]) for _, r in st.iterrows()}
    tasks = []
    for _, r in df.iterrows():
        t = int(r["Transporter"]) ; b = int(r["Batch"]) ; fs = int(r["From_Station"]) ; ts = int(r["To_Station"]) 
        start = int(r["TaskStart"]) ; end = int(r["TaskEnd"]) 
        tasks.append((t,b,fs,ts,start,end,x_map.get(fs,0), x_map.get(ts,0)))
    return tasks, avoid_by_t


def segments_overlap(a1: int, a2: int, b1: int, b2: int, limit: int) -> bool:
    min1, max1 = (a1, a2) if a1 <= a2 else (a2, a1)
    min2, max2 = (b1, b2) if b1 <= b2 else (b2, b1)
    return not (max1 + limit <= min2 or max2 + limit <= min1)


def compute_gaps(tasks, avoid_by_t):
    gaps = []
    pairs = 0
    n = len(tasks)
    for i in range(n):
        t1,b1,fs1,ts1,s1,e1,x1f,x1t = tasks[i]
        for j in range(i+1, n):
            t2,b2,fs2,ts2,s2,e2,x2f,x2t = tasks[j]
            if t1 == t2:
                continue
            limit = max(int(avoid_by_t.get(t1, 0)), int(avoid_by_t.get(t2, 0)))
            if limit <= 0:
                continue
            if not segments_overlap(x1f, x1t, x2f, x2t, limit):
                continue
            pairs += 1
            # compute signed gap: positive means separated in time, negative means overlap
            if e1 <= s2:
                gap = s2 - e1
                order = 1  # t1 before t2
            elif e2 <= s1:
                gap = s1 - e2
                order = 2  # t2 before t1
            else:
                gap = -(min(e1, e2) - max(s1, s2))
                order = 0  # overlap
            gaps.append((gap, order, (t1,b1,fs1,ts1,s1,e1), (t2,b2,fs2,ts2,s2,e2)))
    gaps.sort(key=lambda x: x[0])
    return gaps, pairs


def main():
    for label, rd in RUNS.items():
        # Skip runs whose snapshot files are missing to avoid crashing
        cp = os.path.join(BASE, rd, "cp_sat")
        transporter_csv = os.path.join(cp, "cp_sat_transporter_schedule.csv")
        stations_csv = os.path.join(cp, "cp_sat_stations.csv")
        transp_csv = os.path.join(cp, "cp_sat_transporters.csv")
        if not (os.path.exists(transporter_csv) and os.path.exists(stations_csv) and os.path.exists(transp_csv)):
            print(f"Run {label}: snapshot not found under {cp}, skipping")
            continue

        tasks, avoid_by_t = load_tasks(rd)
        gaps, pairs = compute_gaps(tasks, avoid_by_t)
        if not gaps:
            print(f"{label}: no candidate pairs")
            continue
        min_gap = gaps[0][0]
        mean_gap = sum(g for g, *_ in gaps) / len(gaps)
        nonpos = sum(1 for g, *_ in gaps if g <= 0)
        print(f"Run {label}: pairs={pairs}, measured={len(gaps)}, min_gap={min_gap}s, mean_gap={mean_gap:.2f}s, nonpos={nonpos}")
        print("  5 smallest gaps:")
        for g in gaps[:5]:
            gap, order, a, b = g
            (t1,b1,fs1,ts1,s1,e1) = a
            (t2,b2,fs2,ts2,s2,e2) = b
            ordering = "t1->t2" if order==1 else ("t2->t1" if order==2 else "overlap")
            print(f"    gap={gap:4d}s order={ordering} | t{t1} b{b1} {fs1}->{ts1} [{s1},{e1}]  vs  t{t2} b{b2} {fs2}->{ts2} [{s2},{e2}]")

if __name__ == "__main__":
    main()
