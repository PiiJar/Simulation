# Dokumentaatio: test_step5.py (STEP 5)

Tämä dokumentaatio kuvaa, miten test_step5.py:n funktiot toimivat ja miten kuljetintehtävät generoidaan, järjestetään ja konfliktit ratkaistaan simulointiputkessa.

## Funktioiden tarkoitus

### generate_transporter_tasks(output_dir)
- Generoi kuljetintehtävät alkuperäisestä line-matriisista (line_matrix_original.csv).
- Tallentaa tehtävät CSV-muotoon (transporter_tasks_raw.csv).
- Kirjaa vaiheen etenemisen simulation_log.csv-tiedostoon.
- Palauttaa tehtävädatan ja tiedostopolun.

### order_transporter_tasks(output_dir)
- Järjestää kuljetintehtävät prioriteetin ja ajoituksen mukaan.
- Tallentaa järjestetyt tehtävät tiedostoon (transporter_tasks_sorted.csv).
- Kirjaa vaiheen etenemisen simulation_log.csv-tiedostoon.
- Palauttaa järjestetyn tehtävädatan ja tiedostopolun.

### resolve_station_conflicts(output_dir)
- Ratkaisee mahdolliset asemakonfliktit kuljetintehtävissä.
- Tallentaa korjatut tehtävät tiedostoon (transporter_tasks_resolved.csv).
- Kirjaa vaiheen etenemisen simulation_log.csv-tiedostoon.
- Palauttaa korjatun tehtävädatan ja tiedostopolun.

### stretch_tasks(output_dir)
- Venyttää tehtävien ajoitusta siirtovälin mukaan (SHIFT_GAP).
- Päivittää tehtävien ajoitukset ja tallentaa venytetyt tehtävät tiedostoon (transporter_tasks_stretched.csv).
- Kirjaa vaiheen etenemisen simulation_log.csv-tiedostoon.

## Vaiheittainen toiminta

1. Lue alkuperäinen line-matriisi (line_matrix_original.csv).
2. Generoi kuljetintehtävät (generate_transporter_tasks).
3. Järjestä tehtävät (order_transporter_tasks).
4. Ratkaise asemakonfliktit (resolve_station_conflicts).
5. Venytä tehtävät siirtovälin mukaan (stretch_tasks).
6. Kirjaa kaikki vaiheet simulation_log.csv-tiedostoon.

## Esimerkkikutsu

```python
hoist_tasks = generate_transporter_tasks(output_dir)
hoist_tasks_sorted = order_transporter_tasks(output_dir)
hoist_tasks_resolved = resolve_station_conflicts(output_dir)
stretch_tasks(output_dir)
```

## Riippuvuudet
- Python standard library: os, sys, datetime
- pandas
- simulation_logger (lokitukseen)

---

## Käyttö test_main.py:ssä

- Kutsu funktioita vaiheittain pipeline-logiikan mukaisesti.
- Käytä aina output_dir-parametria polkujen rakentamiseen.
- Kaikki vaiheet kirjaavat etenemisensä simulation_log.csv-tiedostoon.
