# create_simulation_directory(base_dir="output")

Luo simulaatiolle uuden tuloskansion, kopioi tarvittavat lähtötiedot ja alustaa logitiedoston.

## Toiminta
- Luo aikaleimapohjaisen kansion (esim. `output/2025-06-23_14-12-00/`).
- Luo `logs`-kansion ja alustaa `simulation_log.csv`-tiedoston.
- Kopioi initialization-, documentation- ja programs-kansiot simulaatiokansioon.
- Kirjaa STEP- ja INIT-tyyppiset tapahtumat logiin.
- Palauttaa luodun simulaatiokansion polun.

## Paluuarvo
- `output_dir`: Polku luotuun simulaatiokansioon

## Käyttö main.py:ssä
```python
from create_simulation_directory import create_simulation_directory
...
output_dir = create_simulation_directory()
```
- Tätä polkua käytetään kaikissa pipeline-vaiheissa.

## Esimerkki
```python
output_dir = create_simulation_directory()
```

# Päivitetty 2024-06-19

Simulaatiokansion ja original_programs-kansion luonti sekä käsittelyohjelmien kopiointi tehdään tässä vaiheessa.

- Luo aikaleimapohjainen simulaatiokansio (output/YYYY-MM-DD_HH-MM-SS)
- Kopioi initialization, documentation ja programs (nimellä original_programs)
- Luo logs- ja reports-kansiot
- Luo simulation_log.csv ja kirjaa STEP- ja INIT-tapahtumat
- Luo käytettyjen käsittelyohjelmien lista (used_treatment_programs.csv)

Kaikki polut rakennetaan os.path.join-metodilla. Kaikki CLI-viestit ja logitus noudattavat STEP X STARTED/COMPLETED -tyyliä.

Tämä vaihe korvaa aiemman generate_batch_treatment_programs_original.py:n.
