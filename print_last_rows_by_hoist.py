
import pandas as pd
import os

# Lue liikelista

# Oletetaan, että uusin snapshot on käytössä
output_dir = "output/2025-10-23_11-36-40/logs/"
movement_file = os.path.join(output_dir, "transporters_movement.csv")

try:
    df = pd.read_csv(movement_file)
except Exception as e:
    print(f"Virhe tiedoston lukemisessa: {e}")
    exit(1)

# Oletetaan, että transporter-sarake on nimeltään 'Transporter' ja vaihe 'Phase'
# Tulostetaan transporter 1:n viimeiset 10 riviä
transporter1 = df[df['Transporter'] == 1]
print("Viimeiset 10 riviä transporterilta 1:")
for row in transporter1.tail(10).itertuples(index=False):
    print(','.join(str(x) for x in row))

# Tulostetaan muiden transportereiden viimeiset 3 riviä vertailun vuoksi
for transporter in sorted(df['Transporter'].unique()):
    if transporter == 1:
        continue
    transporter_df = df[df['Transporter'] == transporter]
    print(f"\nViimeiset 3 riviä transporterilta {transporter}:")
    for row in transporter_df.tail(3).itertuples(index=False):
        print(','.join(str(x) for x in row))
