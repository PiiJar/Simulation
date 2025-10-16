# order_tasks_README.md

Tämä dokumentaatio kuvaa vaiheen 5 funktiotiedoston order_tasks.py käytön ja rajapinnan.

## Funktio

- `order_tasks(output_dir)`

Järjestää transporter_tasks_raw.csv:n nostoajan (Lift_time) mukaan nousevaan järjestykseen ja tallentaa uuden tiedoston transporter_tasks_ordered.csv.

## Käyttö

```python
from order_tasks import order_tasks

ordered_csv = order_tasks(output_dir)
```

## Lokitus ja tulosteet
- Terminaaliin tulostuu vain STEP-tyyppinen alku- ja loppuviesti.
- simulation_log.csv-tiedostoon kirjataan STEP-tyyppinen alku- ja loppurivi.

## Päivityshistoria
- 2025-06-23: Funktio ja dokumentaatio yhtenäistetty pipeline-tyyliin.
