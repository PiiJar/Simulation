# generate_tasks_README.md

Tämä dokumentaatio kuvaa vaiheen 5 funktiotiedoston generate_tasks.py käytön ja rajapinnan.

Korvaa aiemman generate_transporter_tasks.py:n. Kaikki pipeline- ja testiputken vaiheet käyttävät nyt generate_tasks.py-tiedostoa.

## Funktiot

- `generate_tasks(output_dir)`

## Käyttö

```python
from generate_tasks import generate_tasks
from order_tasks import order_tasks

tasks_raw, tasks_sorted = generate_tasks(output_dir)
tasks_sorted = order_tasks(output_dir)
```

## Päivityshistoria
- 2024-06-19: Tiedosto uudelleennimetty generate_transporter_tasks.py → generate_tasks.py ja dokumentaatio päivitetty.
- 2025-06-23: order_transporter_tasks siirretty omaksi tiedostoksi order_tasks.py ja funktioksi order_tasks.
