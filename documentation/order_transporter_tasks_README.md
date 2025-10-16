# Dokumentaatio: order_transporter_tasks

Tämä dokumentaatio kuvaa, miten `order_transporter_tasks(output_dir)`-funktio toimii ja miten kuljetintehtävät järjestetään simulointiputkessa.

## Funktioiden tarkoitus

### order_transporter_tasks(output_dir)
- Järjestää kuljetintehtävät prioriteetin ja ajoituksen mukaan.
- Tallentaa järjestetyt tehtävät tiedostoon (transporter_tasks_sorted.csv).
- Kirjaa vaiheen etenemisen simulation_log.csv-tiedostoon.
- Palauttaa järjestetyn tehtävädatan ja tiedostopolun.

## Vaiheittainen toiminta

1. Lue kuljetintehtävät (transporter_tasks_raw.csv).
2. Järjestä tehtävät prioriteetin ja ajoituksen mukaan.
3. Tallentaa järjestetyt tehtävät tiedostoon (transporter_tasks_sorted.csv).
4. Kirjaa vaiheen etenemisen simulation_log.csv-tiedostoon.
5. Palauttaa järjestetyn tehtävädatan ja tiedostopolun.

## Esimerkkikutsu

```python
hoist_tasks_sorted = order_transporter_tasks(output_dir)
```

## Riippuvuudet
- Python standard library: os, sys, datetime
- pandas
- simulation_logger (lokitukseen)
