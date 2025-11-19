import pandas as pd
from pathlib import Path
p = Path('/home/jarmo-piipponen/Development/Simulation/output/BGH_CCL-21.002.1_2025-11-04_15-04-34/cp_sat/cp_sat_batch_schedule.csv')
df = pd.read_csv(p)
counts = df.groupby('EntryTime').size().reset_index(name='count')
dups = counts[counts['count'] > 1].sort_values('EntryTime')
print('Total duplicate EntryTime timestamps:', len(dups))
print(dups.head(50).to_string(index=False))
if not dups.empty:
    for t in dups['EntryTime'].head(10):
        rows = df[df['EntryTime'] == t][['Batch','Stage','Station','EntryTime','ExitTime']].sort_values(['Stage','Station'])
        print('\nEntryTime:', t)
        print(rows.to_string(index=False))
