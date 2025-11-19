# 🧠 GitHub Copilot -ohjeistus tälle projektille

Tämä tiedosto antaa Copilotille lisätietoa projektin rakenteesta, käytännöistä ja toivotusta koodityylistä. Näin Copilot voi ehdottaa parempaa, kontekstiin sopivaa koodia.

---

## 🔧 Projektin rakenne ja simulaatioputki

Tämä projekti on tuotantolinjan simulaatio- ja optimointiputki, joka käyttää CP-SAT-ratkaisijaa. Päälogiikka on `main.py`-tiedostossa.

### Päävaiheet:

1. **Alustus (Initialization)**
   - Luo simulaatiokansio aikaleimalla
   - Generoi `goals.json` ja `production.csv`
   - Luo kaikki eräkohtaiset käsittelyohjelmat
   - Quick mode -tarkistus: Jos yksi ohjelma → rajoita 8 erään

2. **Esikäsittely (Preprocessing)**
   - Valmistele data CP-SAT-optimointia varten (`preprocess_for_cpsat()`)

3. **CP-SAT Phase 1: Asemaoptimointi**
   - Optimoi nostimen valinta jokaiselle erälle ja vaiheelle
   - Luo alustava aikataulu ilman tarkkoja ajoituksia

4. **CP-SAT Phase 2: Transporter + Aikataulu**
   - Optimoi tarkat aloitus- ja lopetusajat
   - Huomioi nostinten fysiikka ja rajoitteet
   - Quick modessa lyhyempi aikaraja (300s)

5. **Pattern Mining (vain quick mode)**
   - Etsi syklisiä tuotantokuvioita Phase 2:n ratkaisusta
   - Palauta täysi production.csv Phase 3:a varten

6. **CP-SAT Phase 3: Laajennettu optimointi (vain quick mode)**
   - Käytä täyttä production.csv:ää
   - Jos pattern löytyi → käytä pattern-rajoitteita
   - Tavoite: OPTIMAL-ratkaisu (aikaraja 7200s)

7. **Tulosten keruu (Results)**
   - Luo matriisit, nostintehtävät, yksityiskohtaiset liikkeet
   - Korjaa raporttidataa

8. **Raportointi ja Visualisointi**
   - Visualisoi matriisit ja luo kaaviot
   - Generoi lopullinen simulaatioraportti

### Kaksi ajotilaa:
- **Normal mode**: Vaiheet 1-4, 7-8 (useita ohjelmia)
- **Quick mode**: Kaikki vaiheet 1-8 (yksi ohjelma, pattern mining)

Kaikki tiedostot tallennetaan aikaleimapohjaiseen kansioon, esim. `output/900135_-_Factory_X_Nammo_Zinc_Phosphating_2025-11-19_14-12/`.

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
- Käytä `config.py`-tiedostosta löytyviä konfiguraatiofunktioita (esim. `get_cpsat_phase2_max_time()`)
- **Käytä aina termiä "transporter" nostimista** – älä käytä "hoist"-termiä

---

## 🧩 Erityispiirteet

- `main.py` ajaa koko putken yhdellä komennolla
- Jokainen vaihe kirjaa etenemisen lokiin (`simulation_logger`)
- Kaikki CSV-tiedostot ja raportit tallennetaan aikaleimapohjaiseen kansioon
- CP-SAT-optimoinnin parametrit ovat säädettävissä `config.py`-tiedostossa
- Pattern mining toimii vain quick modessa (yksi ohjelma)
- Virhetilanteessa putki keskeytyy ja virhe raportoidaan selkeästi

---

## 📚 Lähde

Ohjeet Copilot-instructions-tiedoston luontiin:  
[GitHub Docs – Adding repository custom instructions for GitHub Copilot](https://docs.github.com/en/copilot/customizing-copilot/adding-repository-custom-instructions-for-github-copilot)
