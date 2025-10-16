# stretch_tasks(output_dir, input_file=None)

Venyttää kuljetintehtävien ajoituksia siirtovälin (SHIFT_GAP) mukaan niin, että tehtävät eivät mene päällekkäin ja myöhemmät vaiheet siirtyvät kumulatiivisesti.

## Toiminta
- Lukee tiedoston `output_dir/Logs/transporter_tasks_resolved.csv` (tai annetun input_file).
- Käy tehtävät läpi ja venyttää niiden ajoituksia niin, että siirtojen väli on vähintään SHIFT_GAP sekuntia.
- Huomioi sekä edellisen tehtävän päättymisajan että saman erän myöhempien vaiheiden siirron kumulatiivisesti.
- Tallentaa venytetyt tehtävät tiedostoon `output_dir/Logs/transporter_tasks_stretched.csv`.
- Kopioi ja päivittää ohjelmatiedostot kansioon `stretched_programs`.
- Kirjaa STEP-tyyppiset aloitus/lopetusviestit terminaaliin ja simulation_log.csv:ään.
- Palauttaa DataFrame-olion venytetyistä tehtävistä.

## Paluuarvo
- `tasks_stretched_df`: DataFrame, jossa venytetyt tehtävät

## Käyttö main.py:ssä
```python
from stretch_transporter_tasks import stretch_tasks
...
tasks_stretched = stretch_tasks(output_dir)
```
- `output_dir` on simulaation tuloskansio.
- Funktio kirjoittaa tulokset automaattisesti oikeaan tiedostoon.

## Esimerkki
```python
tasks_stretched = stretch_tasks(output_dir)
```
