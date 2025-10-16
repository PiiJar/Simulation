# resolve_station_conflicts(output_dir)

Korjaa asemakonfliktit järjestämällä kuljetintehtäviä uudelleen niin, että siirrot eivät mene päällekkäin.

## Toiminta
- Lukee tiedoston `output_dir/Logs/transporter_tasks_ordered.csv`.
- Käy tehtävät läpi ja järjestää niitä, jotta asemien käyttö ei mene päällekkäin eri erien välillä.
- Tallentaa korjatut tehtävät tiedostoon `output_dir/Logs/transporter_tasks_resolved.csv`.
- Kirjaa STEP-tyyppiset aloitus/lopetusviestit terminaaliin ja simulation_log.csv:ään.
- Palauttaa DataFrame-olion korjatuista tehtävistä.

## Paluuarvo
- `tasks_resolved_df`: DataFrame, jossa korjatut tehtävät

## Käyttö main.py:ssä
```python
from resolve_station_conflicts import resolve_station_conflicts
...
tasks_resolved = resolve_station_conflicts(output_dir)
```
- `output_dir` on simulaation tuloskansio.
- Funktio kirjoittaa tulokset automaattisesti oikeaan tiedostoon.

## Esimerkki
```python
tasks_resolved = resolve_station_conflicts(output_dir)
```
