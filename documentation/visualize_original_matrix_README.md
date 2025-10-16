# Dokumentaatio: visualize_original_matrix.py (STEP 4)

Tämä dokumentaatio kuvaa, miten `visualize_original_matrix.py`-tiedoston funktio(t) toimivat ja miten alkuperäisen line-matriisin visualisointi tuotetaan simulointiputkessa.

## Funktioiden tarkoitus

### visualize_original_matrix(output_dir)
- Visualisoi alkuperäisen line-matriisin (line_matrix_original.csv) erien kulun asemilla aikajanalla.
- Tallentaa visualisointikuvan simulaatiokansioon (Logs/).
- Palauttaa polun luotuun visualisointikuvaan.

## Vaiheittainen toiminta

1. Lue alkuperäinen line-matriisi (Logs/line_matrix_original.csv).
2. Luo timeline-visualisointi erien liikkeestä asemilla.
3. Tallentaa visualisoinnin tiedostoon (esim. Logs/original_matrix_timeline.png).
4. Palauttaa visualisointikuvan polun.

## Esimerkkikutsu

```python
visualization_file = visualize_original_matrix(output_dir)
```

## Riippuvuudet
- Python standard library: os
- pandas
- matplotlib

---

## Käyttö test_step4.py:ssä

- Kutsu `visualize_original_matrix` vasta sen jälkeen, kun alkuperäinen line-matriisi on luotu.
- Käytä aina output_dir-parametria polkujen rakentamiseen.
- Funktio palauttaa polun luotuun kuvaan – käytä tätä polkua tarvittaessa seuraavissa pipeline-vaiheissa.
