import pandas as pd
from pathlib import Path
import sys

def main():
    root = Path('/home/jarpii/Dev/Simulation/output')
    cands = sorted([p for p in root.iterdir() if p.is_dir()], key=lambda p: p.stat().st_mtime)
    if not cands:
        print({'status':'error','message':'no output snapshots'})
        return 1
    run = cands[-1]
    logs = run/'logs'
    cp = run/'cp_sat'
    mov_path = logs/'transporters_movement.csv'
    transfers_path = cp/'cp_sat_transfer_tasks.csv'
    if not mov_path.exists():
        print({'status':'error','message':f'missing movements {mov_path}'})
        return 2
    if not transfers_path.exists():
        print({'status':'error','message':f'missing transfers {transfers_path}'})
        return 3

    res = {'snapshot': str(run.name), 'issues': {'phase_order': [], 'lift_too_short': [], 'sink_too_short': []}}

    m = pd.read_csv(mov_path)
    # normalize
    m['Transporter'] = m['Transporter'].astype(int)
    m['Phase'] = m['Phase'].astype(int)
    m['Start_Time'] = m['Start_Time'].astype(int)
    m['End_Time'] = m['End_Time'].astype(int)
    if 'Task_Seq' in m.columns:
        m['Task_Seq'] = m['Task_Seq'].fillna(0).astype(int)
    else:
        m['Task_Seq'] = 0

    # Check phase ordering within a task: ignoring Idle and Avoid, phases should be 1->2->3->4 with non-decreasing times
    for t_id, g in m.groupby('Transporter'):
        gg = g[g['Task_Seq']>0]
        for task_seq, tg in gg.groupby('Task_Seq'):
            core = tg[tg['Phase'].isin([1,2,3,4]) & (tg['Description']!='Avoid')].sort_values(['Start_Time','Phase'])
            phases = core['Phase'].tolist()
            seq = []
            seen = set()
            for p in phases:
                if p not in seen:
                    seq.append(p); seen.add(p)
            if not all(a<b for a,b in zip(seq, seq[1:])):
                res['issues']['phase_order'].append({'Transporter':int(t_id),'Task_Seq':int(task_seq),'Phases':phases})
            per_phase = {}
            for _, r in core.iterrows():
                p = int(r['Phase'])
                if p not in per_phase:
                    per_phase[p] = {'start': int(r['Start_Time']), 'end': int(r['End_Time'])}
            ok = True
            for prev, cur in [(1,2),(2,3),(3,4)]:
                if prev in per_phase and cur in per_phase:
                    if per_phase[cur]['start'] < per_phase[prev]['end']:
                        ok = False
            if not ok:
                res['issues']['phase_order'].append({'Transporter':int(t_id),'Task_Seq':int(task_seq),'phase_times':per_phase})

    # Check lift/sink durations vs expected from cp_sat_transfer_tasks
    tr = pd.read_csv(transfers_path)
    tr[['Transporter','From_Station','To_Station']] = tr[['Transporter','From_Station','To_Station']].astype(int)
    exp = {}
    for _, r in tr.iterrows():
        exp[(int(r['Transporter']), int(r['From_Station']), int(r['To_Station']))] = (float(r['LiftTime']), float(r['SinkTime']))

    # For each task, find its move-to-sink row to get (from,to), then compare its Lift/Sink durations
    for t_id, g in m.groupby('Transporter'):
        gg = g[g['Task_Seq']>0]
        for task_seq, tg in gg.groupby('Task_Seq'):
            move_rows = tg[tg['Description']=='Move to sinking station']
            if move_rows.empty:
                continue
            r = move_rows.sort_values(['Start_Time']).iloc[0]
            lift_stat = int(r['From_Station']); sink_stat = int(r['To_Station'])
            key = (int(t_id), lift_stat, sink_stat)
            if key not in exp:
                continue
            exp_lift, exp_sink = exp[key]
            # observed durations
            lift_obs = tg[tg['Description']=='Lifting']
            if not lift_obs.empty:
                d = int(lift_obs.iloc[0]['End_Time']) - int(lift_obs.iloc[0]['Start_Time'])
                if d + 1 < int(round(exp_lift)):
                    res['issues']['lift_too_short'].append({'Transporter':int(t_id),'Task_Seq':int(task_seq),'expected':round(exp_lift,1),'observed':d,'pair':key})
            sink_obs = tg[tg['Description']=='Sinking']
            if not sink_obs.empty:
                d = int(sink_obs.iloc[0]['End_Time']) - int(sink_obs.iloc[0]['Start_Time'])
                if d + 1 < int(round(exp_sink)):
                    res['issues']['sink_too_short'].append({'Transporter':int(t_id),'Task_Seq':int(task_seq),'expected':round(exp_sink,1),'observed':d,'pair':key})

    summary = {k: len(v) for k,v in res['issues'].items()}
    print({'snapshot': res['snapshot'], 'summary': summary})
    for k,v in res['issues'].items():
        if v:
            print(k, 'sample:', v[:10])

if __name__ == '__main__':
    sys.exit(main() or 0)
