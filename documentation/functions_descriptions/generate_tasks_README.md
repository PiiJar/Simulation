# generate_tasks(output_dir)

Luo kuljetintehtävät (transporter tasks) line-matriisin perusteella. Jokainen siirto asemalta toiselle muodostaa tehtävän, jossa on tiedot erästä, vaiheesta, asemista ja ajoista.

## Toiminta
- Lukee tiedoston `output_dir/Logs/line_matrix_original.csv`.
- Luo jokaiselle siirrolle tehtävän, jossa on mm. Batch, Stage, Lift_stat, Lift_time, Sink_stat, Sink_time.
- Tallentaa tehtävät kahteen tiedostoon:
  - `transporter_tasks_raw.csv` (alkuperäinen järjestys)
  - `transporter_tasks_sorted.csv` (järjestetty nostoajan mukaan)
- Kirjaa STEP-tyyppiset aloitus/lopetusviestit terminaaliin ja simulation_log.csv:ään.
- Palauttaa kaksi DataFramea: (tasks_df, sorted_df)

## Paluuarvo
- `tasks_df`: DataFrame, jossa kaikki kuljetintehtävät alkuperäisessä järjestyksessä
- `sorted_df`: DataFrame, jossa tehtävät järjestetty nostoajan mukaan

## Käyttö main.py:ssä
```python
from generate_tasks import generate_tasks
...
tasks_raw, tasks_sorted = generate_tasks(output_dir)
```
- `output_dir` on simulaation tuloskansio, jonka luo esim. `create_simulation_directory()`.
- Funktio kirjoittaa tulokset automaattisesti oikeisiin tiedostoihin.

## Esimerkki
```python
tasks_raw, tasks_sorted = generate_tasks(output_dir)
```
