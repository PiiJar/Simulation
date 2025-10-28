import pandas as pd
from pathlib import Path
from transporter_physics import calculate_physics_transfer_time

root = Path('/home/jarpii/Dev/Simulation/output')
# pick latest snapshot by name
snapshots = sorted([p for p in root.iterdir() if p.is_dir()])
if not snapshots:
    raise SystemExit('No output snapshots found')
latest = snapshots[-1]
logs = latest / 'logs'
init = latest / 'initialization'
print(f'Using snapshot: {latest.name}')

mtx = pd.read_csv(logs/'transporter_tasks_from_matrix.csv')
stations = pd.read_csv(init/'stations.csv').set_index('Number')
trs = pd.read_csv(init/'transporters.csv').set_index('Transporter_id')

violations = []
for t_id, g in mtx.groupby('Transporter'):
    g = g.sort_values('Phase_4_stop').reset_index(drop=True)
    for i in range(len(g)-1):
        prev = g.iloc[i]
        nxt = g.iloc[i+1]
        prev_end = int(prev['Phase_4_stop'])
        # Correct window for travel is arrival (Phase_2_start) of next minus prev end
        next_arrival = int(nxt['Phase_2_start'])
        window = next_arrival - prev_end
        from_stat = int(prev['Sink_stat'])
        to_stat = int(nxt['Lift_Stat'])
        req = calculate_physics_transfer_time(stations.loc[from_stat], stations.loc[to_stat], trs.loc[int(t_id)])
        slack = window - int(req)
        if slack < 0:
            violations.append({
                'Transporter': int(t_id),
                'i_index': i,
                'A_Batch': int(prev['Batch']), 'A_LiftStat': int(prev['Lift_Stat']), 'A_SinkStat': int(prev['Sink_stat']), 'A_end': prev_end,
                'B_Batch': int(nxt['Batch']), 'B_LiftStat': int(nxt['Lift_Stat']), 'B_SinkStat': int(nxt['Sink_stat']), 'B_arrival': next_arrival,
                'Required': int(req), 'Window': int(window), 'Slack': int(slack)
            })

violations_sorted = sorted(violations, key=lambda d: (d['Transporter'], d['A_end']))
print(f'TOTAL_VIOLATIONS={len(violations_sorted)}')
if violations_sorted:
    first = violations_sorted[0]
    print('FIRST_VIOLATION:', first)
else:
    print('NONE')
