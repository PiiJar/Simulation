# Dokumentaatio: test_step2.py (STEP 2)

Tämä dokumentaatio kuvaa, miten test_step2.py:n funktiot toimivat ja miten eräkohtaiset käsittelyohjelmat luodaan simulointiputkessa.

## Funktioiden tarkoitus

### create_original_programs(output_dir)
- Lukee initialization/Production.csv-tiedoston ja käy läpi jokaisen erän.
- Kopioi oikean Treatment_program_xxx.csv-tiedoston initialization-kansiosta.
- Nimeää kopion muotoon Batch_xxx_Treatment_program_yyy.csv.
- Lisää CalcTime-sarakkeen (aluksi = MinTime), jos sitä ei ole.
- Palauttaa original_programs-kansion polun.

## Vaiheittainen toiminta

1. Lukee Production.csv:n ja käy läpi kaikki erät.
2. Kopioi jokaiselle erälle oikean käsittelyohjelman initialization-kansiosta.
3. Nimeää ohjelmatiedoston muotoon Batch_xxx_Treatment_program_yyy.csv.
4. Lisää CalcTime-sarake (aluksi = MinTime), jos sitä ei ole.
5. Palauttaa original_programs-kansion polun.

## Esimerkkikutsu

```python
original_programs_dir = create_original_programs(output_dir)
# ... voit käyttää original_programs_dir:ia seuraavissa vaiheissa ...
```

## Riippuvuudet
- Python standard library: os, sys, datetime, shutil
- pandas
- generate_batch_treatment_programs_original (oma moduuli)

---

## Käyttö test_main.py:ssä

- Kutsu create_original_programs()-funktiota pipeline-logiikan mukaisesti (vaihe 2).
- Käytä aina output_dir-parametria polkujen rakentamiseen.
- Kaikki vaiheet kirjaavat etenemisensä simulation_log.csv-tiedostoon.

# Päivitetty 2025-06-24

Tämä vaihe muodostaa eräkohtaiset käsittelyohjelmat kansioon original_programs.

Katso myös: documentation/functions_descriptions/generate_batch_treatment_programs_original_README.md
