# generate_matrix_original(output_dir)

Luo alkuperäisen line-matriisin tuotantoerien ja asemien tietojen perusteella.

## Toiminta
- Lukee tuotantoerätiedot ja asemien tiedot (esim. `Production.csv`, `Stations.csv`).
- Laskee siirtoajat vaiheiden välillä (fysiikkapohjaisesti tai oletusarvolla).
- Rakentaa line-matriisin, jossa jokainen rivi kuvaa yhden erän yhden vaiheen asema- ja aikarivin.
- Tallentaa matriisin tiedostoon `output_dir/Logs/line_matrix_original.csv`.
- Kirjaa STEP-tyyppiset aloitus/lopetusviestit terminaaliin ja simulation_log.csv:ään.
- Palauttaa DataFrame-olion line-matriisista.

## Paluuarvo
- `matrix_df`: DataFrame, jossa line-matriisin tiedot

## Käyttö main.py:ssä
```python
from generate_matrix_original import generate_matrix_original
...
matrix = generate_matrix_original(output_dir)
```
- `output_dir` on simulaation tuloskansio.
- Funktio kirjoittaa tulokset automaattisesti oikeaan tiedostoon.

## Esimerkki
```python
matrix = generate_matrix_original(output_dir)
```
