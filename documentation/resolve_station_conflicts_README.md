# Dokumentaatio: resolve_station_conflicts

Tämä dokumentaatio kuvaa, miten `resolve_station_conflicts(output_dir)`-funktio toimii ja miten asemakonfliktit ratkaistaan kuljetintehtävissä simulointiputkessa.

## Funktioiden tarkoitus

### resolve_station_conflicts(output_dir)
- Ratkaisee mahdolliset asemakonfliktit kuljetintehtävissä.
- Tallentaa korjatut tehtävät tiedostoon (transporter_tasks_resolved.csv).
- Kirjaa vaiheen etenemisen simulation_log.csv-tiedostoon.
- Palauttaa korjatun tehtävädatan ja tiedostopolun.

## Vaiheittainen toiminta

1. Lue järjestetyt kuljetintehtävät (transporter_tasks_sorted.csv).
2. Ratkaise mahdolliset asemakonfliktit (esim. päällekkäiset varaukset).
3. Tallentaa korjatut tehtävät tiedostoon (transporter_tasks_resolved.csv).
4. Kirjaa vaiheen etenemisen simulation_log.csv-tiedostoon.
5. Palauttaa korjatun tehtävädatan ja tiedostopolun.

## Esimerkkikutsu

```python
hoist_tasks_resolved = resolve_station_conflicts(output_dir)
```

## Riippuvuudet
- Python standard library: os, sys, datetime
- pandas
- simulation_logger (lokitukseen)
