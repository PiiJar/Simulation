 # 🧠 GitHub Copilot -ohjeistus tälle projektille

Tämä tiedosto antaa Copilotille lisätietoa projektin rakenteesta, käytännöistä ja toivotusta koodityylistä. Näin Copilot voi ehdottaa parempaa, kontekstiin sopivaa koodia.

---

## 🔧 Projektin rakenne ja ajoputki

Tämä projekti on tuotantolinjan simulointiputki, joka koostuu seuraavista vaiheista:

1. `generate_matrix.py`  
   → Luo alkuperäisen line-matriisin (Station–Stage)

2. `generate_transporter_tasks.py`  
   → Luo transporter-tehtävät

3. `resolve_station_conflicts.py`  
   → Korjaa asema- ja ajoitusristiriidat

4. `stretch_transporter_tasks.py`  
   → Venyttää tehtäviä siirtovälin mukaan  
   → Huomioi myös saman erän myöhemmät vaiheet

5. `update_programs.py`  
   → Päivittää ohjelmien `CalcTime`-kentät

6. `generate_matrix_updated.py`  
   → Luo uusi line-matriisi venytettyjen tehtävien mukaan

7. `visualize_comparison.py`  
   → Piirtää visuaalisen vertailun ennen–jälkeen

Kaikki tiedostot tallennetaan aikaleimapohjaiseen kansioon, esim. `output/2025-06-19_14-12/`.

---

## 🧪 Hyvät käytännöt Python-koodissa

Copilotin tulee noudattaa seuraavia käytäntöjä:

- Käytä **funktiomuotoista rakennetta** (ei pelkkää skriptikoodia)
- Kaikki tiedostot ottavat vastaan `output_dir`-parametrin
- Älä käytä kovakoodattuja polkuja kuten `"output/"`, vaan rakenna polut `os.path.join()`-menetelmällä
- Käytä `os.makedirs(..., exist_ok=True)` ennen tallennusta
- Tulosta selkeät CLI-viestit jokaisesta vaiheesta
- Käytä `pd.to_csv()` ja `pd.to_html()` tallennukseen
- Käytä `pd.to_timedelta(...).dt.total_seconds()` kun käsittelet aikakenttiä
- Käytä `from config import get_shift_gap` ja `get_shift_gap()` siirtovälin hakemiseen
- Venytyksessä huomioi:
  - edellisen tehtävän päättymisaika
  - saman erän myöhempien vaiheiden siirto samalla määrällä

---

## 🧩 Erityispiirteet

- Tehtävien järjestys on tärkeä — älä järjestä `df.sort_values()` ellei erikseen pyydetä
- `stretch_transporter_tasks.py` toimii kumulatiivisesti: jokainen siirto vaikuttaa seuraaviin
- `main.py` ajaa koko putken yhdellä komennolla
- Kaikki CSV-tiedostot tallennetaan snapshot-kansioon

---

## 📚 Lähde

Ohjeet Copilot-instructions-tiedoston luontiin:  
[GitHub Docs – Adding repository custom instructions for GitHub Copilot](https://docs.github.com/en/copilot/customizing-copilot/adding-repository-custom-instructions-for-github-copilot)
