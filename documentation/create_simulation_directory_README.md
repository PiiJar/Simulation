# create_simulation_directory – toiminta ja käyttö

## Kuvaus

`create_simulation_directory(base_dir="output")` luo uuden simulaatiokansion, johon kopioidaan kaikki simuloinnin tarvitsemat lähtö- ja dokumentaatiotiedostot. Funktio alustaa myös lokeja ja palauttaa luodun kansion polun.

### Vaiheittainen toiminta:
1. Luo aikaleimapohjainen kansion (esim. `output/2025-06-24_10-30-00/`).
2. Luo kansion sisälle `logs`-alihakemiston.
3. Luo kansion sisälle `reports`-alihakemiston.  <!-- UUSI -->
4. Kopioi juuren `initialization`-kansion simulaatiokansion alle.
5. Kopioi juuren `documentation`-kansion simulaatiokansion alle.
6. Kopioi juuren `programs`-kansion simulaatiokansion alle nimellä `original_programs`.
7. Luo `logs/simulation_log.csv`-tiedoston ja kirjaa sinne perustiedot (aikaleima, kopioidut tiedostot).
8. **UUSI:** Käy simulaatiokansion `initialization/Production.csv`-tiedosto läpi ja listaa kaikki erilaiset käsittelyohjelmat (treatment_programs). Luo tiedosto `logs/used_treatment_programs.csv`, jossa on sarakkeet:
   - `treatment_program_number`: ohjelman nimen lopun kolme numeroa (int)
   - `treatment_program_name`: ohjelmatiedoston nimi
   Jokainen ohjelma esiintyy listalla vain kerran.
9. Palauttaa luodun simulaatiokansion polun.

## Parametrit
- `base_dir` (str, oletus "output"): Kansio, jonka alle simulaatiokansio luodaan.

## Paluuarvo
- (str): Luodun simulaatiokansion polku.

## Esimerkki käytöstä main.py:ssä
```python
from create_simulation_directory import create_simulation_directory

def run_pipeline():
    output_dir = create_simulation_directory()
    # ... jatka pipelinea output_dir:iin ...
```

## Esimerkki käytöstä test_main.py:ssä
```python
from create_simulation_directory import create_simulation_directory

def test_main():
    output_dir = create_simulation_directory()
    # ... testaa pipelinea output_dir:iin ...
```

## Huomioita testauksesta
- Testeissä (test_main.py) funktiota käytetään samalla tavalla kuin tuotantoputkessa.
- Testeissä voidaan ajaa vain osa pipeline-vaiheista, mutta simulaatiokansion luonti toimii identtisesti.
- Jos testissä halutaan käyttää eri pohjakansiota, base_dir-parametria voi muuttaa.

## Yhteenveto
`create_simulation_directory` on pipeline- ja testikäytössä identtinen, ja se varmistaa, että kaikki tarvittavat tiedostot ja kansiot ovat oikeassa paikassa simulaation alussa.

---

### Uusi toiminto: Käytettyjen käsittelyohjelmien listaus

Kun simulaatiokansio ja lokitiedosto on luotu, funktio etsii kansiosta `initialization/Production.csv` kaikki käytetyt käsittelyohjelmat (treatment_programs). Se muodostaa tiedoston `logs/used_treatment_programs.csv`, jossa on seuraavat sarakkeet:
- `treatment_program_number`: ohjelman nimen lopun kolme numeroa (int)
- `treatment_program_name`: ohjelmatiedoston nimi

Jokainen ohjelma esiintyy listalla vain kerran. Tämä helpottaa käytettyjen ohjelmien tunnistamista ja jatkokäsittelyä.
