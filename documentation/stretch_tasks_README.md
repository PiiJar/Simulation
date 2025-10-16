# Dokumentaatio: stretch_tasks

Tämä dokumentaatio kuvaa, miten `stretch_tasks(output_dir)`-funktio toimii ja miten kuljetintehtävien ajoitusta venytetään simulointiputkessa.

## Funktioiden tarkoitus

### stretch_tasks(output_dir)
- Venyttää tehtävien ajoitusta siirtovälin mukaan (SHIFT_GAP).
- Päivittää tehtävien ajoitukset ja tallentaa venytetyt tehtävät tiedostoon (transporter_tasks_stretched.csv).
- Kirjaa vaiheen etenemisen simulation_log.csv-tiedostoon.

## Vaiheittainen toiminta

1. Lue korjatut kuljetintehtävät (transporter_tasks_resolved.csv).
2. Venyttää tehtävien ajoitusta siirtovälin (SHIFT_GAP) mukaan.
3. Tallentaa venytetyt tehtävät tiedostoon (transporter_tasks_stretched.csv).
4. Kirjaa vaiheen etenemisen simulation_log.csv-tiedostoon.

## Esimerkkikutsu

```python
stretch_tasks(output_dir)
```

## Riippuvuudet
- Python standard library: os, sys, datetime
- pandas
- simulation_logger (lokitukseen)
