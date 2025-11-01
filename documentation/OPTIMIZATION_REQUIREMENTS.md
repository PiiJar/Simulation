# CP-SAT Optimointitehtävän vaatimukset

## 1. Yleiskuvaus

Tässä optimointitehtävässä mallinnetaan teollista tuotantolinjaa, jossa nostin siirtää tuotantoeriä asemalta toiselle käsittelyohjelman mukaisesti. Laitoksessa on useita asemia (esim. altaat, pesurit, kuivurit), joilla kullakin on omat rajoitteensa ja käsittelyajat. Nostimen liikkeet ja siirtoajat perustuvat fysiikkaan ja ne on laskettu etukäteen. 

**Optimoinnin tavoite**: Löytää nostimelle aikataulu, joka minimoi koko tuotantoerän läpimenoajan (makespan) huomioiden kaikki laitoksen rajoitteet, asemien käytön, tehtävien järjestyksen ja siirtymäajat.

**Aikayksiköt**: Kaikki ajat esitetään dokumentaatiossa muodossa hh:mm:ss, mutta optimoinnissa kaikki ajat muunnetaan sekunneiksi. Simulointi alkaa aina ajasta 00:00:00.

## 2. Lähtötiedot ja esikäsittely

### 2.1 Esikäsittelyn tuotokset CP-SAT-optimointia varten

Esikäsittelyvaihe tuottaa `cp_sat/`-kansioon seuraavat tiedostot optimointia varten:

#### Perustiedostot
- **cp_sat_batches.csv**: Erien perustiedot (ID, käsittelyohjelma, aloitusasema, aloitusaika)
- **cp_sat_stations.csv**: Asemien tiedot (numero, ryhmä, sijainti, valutusaika, tyyppi)
- **cp_sat_transporters.csv**: Nostimien tekniset tiedot (nopeudet, kiihdytykset, liikealueet)
- **cp_sat_transporters_start_positions.csv**: Nostimien aloituspaikat (nostin ID, aloitusasema)
- **cp_sat_transfer_tasks.csv**: Kaikki mahdolliset siirtotehtävät ja niiden ajat (nostoaika, siirtoaika, laskuaika, kokonaisaika)

#### Käsittelyohjelmat
- **cp_sat_treatment_program_N.csv**: Kunkin erän käsittelyohjelma (vaiheet, asemarajat, aikarajat)
- **treatment_program_optimized/**: Alkuperäiset käsittelyohjelmat ilman stage 0:aa

### 2.2 Keskeiset käsitteet ja määrittelyt

#### 2.2.1 Nostimen aloituspaikka

**Yhden nostimen optimoinnissa**: Aloituspaikan vaikutus voidaan jättää huomioimatta, koska optimoinnin fokus on tehtävien välisten siirtojen optimoinnissa. Simulaatio alkaa ajasta 00:00:00 ja päättyy viimeisen erän viimeiseen laskuun.

**Useamman nostimen tapauksessa** (tulevaisuudessa): Aloituspaikka tulee merkitykselliseksi nostimien välisten konfliktien välttämiseksi.

#### 2.2.2 Asemaryhmien valintalogiikka

Käsittelyohjelmassa voi olla yhdelle Stagelle useampi asema (Min --> Max) - prosessin kannalta rinnakkaisia asemia, eli niissä on sama kemia. Stations tiedostossa määritellään tarkemmin mitkä asemat tuolta väliltä kuuluvat samaan ryhmään (Group). 

**CP-SAT-optimointivapausaste**: Optimointi voi valita minkä tahansa samaan ryhmään kuuluvan, käsittelyohjelman min/max välillä olevan vapaan aseman. Valinta tehdään siten, että se tukee parhaiten kokonaistavoitetta (nopein reitti kaikille erille). Optimointi voi siis vapaasti valita sen rinnakkaisen aseman, joka johtaa nopeimpaan kokonaisratkaisuun.

#### 2.2.3 Vaihtoaikojen laskenta (batch_change_time)

Vaihtoajalla tarkoitetaan erän vaihtumiseen asemalla kuluvaa aikaa. Erä A pitää viedä ensin pois, ja sitten voidaan tuoda erä B tilalle.

**Vaihtoajan komponentit**:
Asemalla x vaihtuu erä A → erä B

1. **Erän A poisvienti**: Total_Task_Time(x → y)
   - Erän A nosto asemalta x + siirtyminen laskuasemalle y + erän A lasku asemalle y
   
2. **Nostimen tyhjäsiirto**: Transfer_Time(y → z)  
   - Nostimen siirtyminen erän A laskuasemalta y erän B nostoasemalle z
   
3. **Erän B tuonti**: Total_Task_Time(z → x)
   - Erän B nosto asemalta z + siirtyminen asemalle x + erän B lasku asemalle x

**Kokonaisvaihtoaika** = Total_Task_Time(x→y) + Transfer_Time(y→z) + Total_Task_Time(z→x)

Kaikki komponentit löytyvät esilaskettuina `cp_sat_transfer_tasks.csv` tiedostosta, joten CP-SAT voi laskea vaihtoajan dynaamisesti riippuen siitä, mistä erä B haetaan ja mihin erä A viedään.

#### 2.2.4 Nolladurationien käsittely
Käsittelyohjelmassa voi olla käsittelyvaiheita, joiden minimi käsittelyaika on asetettu 00:00:00. Käsittelyn 'keskellä' tämä kiristää rajoitteita kyseisessä kohdassa, jos myös maksimiaika on lyhy. 

**Erityistapaukset**:
- **Ensimmäinen stage (stage 0)**: Minimi 00:00:00, maksimi 100:00:00. Kuvaa vapausastetta optimoinnille erien välillä.
- **Viimeinen stage**: Operaattori siirtää erän pois, joten nostin vapautuu heti laskun jälkeen.

#### 2.2.5 Siirtoaikojen terminologia
- **TransferTime**: Aika minkä nostin tarvitsee siirtymiseen kahden aseman välillä (tyhjänä)
- **TotalTaskTime**: Koko tehtävän kesto (LiftTime + TransferTime + SinkTime)
- **batch_change_time**: Vaihtoajan kokonaisaika (lasketaan dynaamisesti komponenteista)

#### 2.2.6 Identtisten erien käsittely

Samaa käsittelyohjelmaa käyttävät erät ovat optimoinnin kannalta identtisiä, eli niiden järjestyksen vaihtaminen ei paranna lopputulosta.

**CP-SAT-implementaatio**: 
- Ensimmäisessä vaiheessa optimoidaan kaikkien erien järjestys normaalisti
- Jos halutaan säilyttää alkuperäinen järjestys identtisille erille, voidaan lisätä preferenssirajoite
- Optimointitehokkuutta voi parantaa tunnistamalla identtiset erät ja käsittelemällä niitä ryhminä

**Käyttäjätoiminnallisuus**: Identtisten erien alkuperäinen järjestys säilytetään tuloksissa käyttäjäystävällisyyttä varten.

## 3. Optimointisäännöt ja -rajoitteet

### 3.1 Pakolliset säännöt

#### Sääntö 1: Käsittelyjärjestys
Erien käsittelyohjelman määrittelemää käsittelyjärjestystä on noudatettava. Tämä tarkoittaa, että jokaisen erän vaiheet on suoritettava annetussa järjestyksessä ilman poikkeuksia.

#### Sääntö 2: Käsittelyajat
Käsittelyohjelmien ohjelma-askeleiden käsittelyaikoja pitää kunnioittaa. Jokaisen askeleen kesto on vähintään määritelty minimi ja enintään määritelty maksimi.

#### Sääntö 3: Asemien käyttö
Asemalla voi olla vain yksi erä kerrallaan. Tämä tarkoittaa, että aseman resurssit ovat varattuja yhden erän käsittelyn aikana, eikä päällekkäisyyksiä sallita.

**Poikkeus**: Aloitusasema (stage 0) - tämä lisätään käsittelyohjelmaan vain optimointia varten. Kaikkien erien stage 0 minimi aika on 00:00:00 ja maksimi aika 100:00:00. Kuvitteellisesti kaikki erät ovat simulaation alkaessa aloitusasemalla, ja lähtevät siitä, kun muiden ehtojen mukaan se on mahdollista.

#### Sääntö 3.1: Aseman vapautuminen ja nostimen käyttö

Seuraava erä ei voi saapua asemalle ennen kuin edellinen erä on kokonaan käsitelty ja siirretty pois asemalta, ja nostin on vapaa. 

**CP-SAT-rajoite**: Käytetään vaihtoaikaa (batch_change_time) hallintaan. Asema pitää olla tyhjänä koko vaihtoajan.

```
seuraava_erä_alku ≥ edellinen_erä_loppu + batch_change_time
```

Missä `batch_change_time` lasketaan dynaamisesti:
- Total_Task_Time(poisvietävä_erä) + Transfer_Time(tyhjäsiirto) + Total_Task_Time(tuotava_erä)

Vaihtoajan komponentit riippuvat siitä, mihin edellinen erä viedään ja mistä seuraava erä haetaan, joten CP-SAT:n on laskettava tämä dynaamisesti optimoinnin aikana.

#### Sääntö 4: Nostimen liikkeet
Nostimen liikkeet pitää perustua esilaskettuihin (fysiikkaan perustuviin) tietoihin. Liikkeisiin tarvittava aika tulee esikäsittelytiedostosta, ja optimoinnin on käytettävä näitä arvoja sellaisenaan.

#### Sääntö 4.1: Nostimen fysikaaliset rajoitteet
Nostin ei voi olla kahdessa paikassa yhtäaikaa. Kaikkien siirtotehtävien välissä on oltava riittävästi aikaa siirtymiseen tehtävältä toiselle, ja tämä aika perustuu esikäsittelytiedostossa määriteltyihin arvoihin.

### 3.2 Vapausasteet

#### Vapausaste 1: Käsittelyajat
Käsittelyohjelmien käsittelyajat voivat olla mitä tahansa määritellyn minimi- ja maksimiarvon välillä. Tämä mahdollistaa nostimen tehtävien ajoittamisen ja päällekkäisyyksien eliminoinnin säätämällä käsittelyaikoja.

#### Vapausaste 2: Asemavalinta
Jos käsittelyohjelmassa on vaihe, jossa MinStat < MaxStat, voidaan kyseiseen vaiheeseen valita mikä tahansa asema tältä väliltä, kunhan asema kuuluu samaan Group-numeroon. Näin mahdollistetaan rinnakkaisten asemien käyttö ja resurssien tehokkaampi hyödyntäminen. Jos Group-numero on sama, asemat ovat rinnakkaisia ja niitä voidaan käyttää yhtäaikaisesti.

#### Vapausaste 3: Erien järjestys
Erien keskinäistä käsittelyjärjestystä voidaan vaihtaa, jos sillä on merkitystä paremman lopputuloksen löytämiseksi. Erän sisäinen tehtäväjärjestys pitää kuitenkin säilyä, eli käsittelyohjelma määrittää missä vaihejärjestyksessä erän pitää edetä. Nostimelle voidaan kuitenkin valita mitä erää milloinkin se siirtää. Jos tehtävien välisellä järjestyksen vaihdolla ei kuitenkaan paranneta (siis päästään huonompaan tai samaan kuin edellinen versio) kokonaiskapasiteettia, säilytetään alkuperäinen järjestys.

#### Vapausaste 4: Rinnakkaisuus
Kun erä on laskettu asemaan, voi nostin suorittaa toisiin eriin liittyviä siirtotehtäviä, jos se on mahdollista erän käsittelyohjelman kyseisen aseman min/max aikaikkunassa. Ts. nostimen ei tarvitse toteuttaa vain yhden erän prosessia kerrallaan, vaan rinnakkainen ajo on sallittua, ja parhaan optimointituloksen löytämiseksi tärkeää.

#### Vapausaste 5: Valmistuminen
Erä valmistuu, kun se on siirretty käsittelyohjelman viimeiselle asemalle. Nostin on heti laskun jälkeen vapaa muihin tehtäviin. Lisäksi erä 'katoaa' tuotannosta, joten se ei myöskään varaa käsittelyohjelman viimeistä asemaa käsittelyajan jälkeen (käytännössä 0 sekuntia).

## 4. CP-SAT Implementaatiovaatimukset

### 4.1 Muuttujien määrittely

#### 4.1.1 Aikamuuttujat
Jokaiselle erän vaiheelle (batch, stage) määritellään:
- **start_time[batch][stage]**: Vaiheen aloitusaika (sekunteina)
- **end_time[batch][stage]**: Vaiheen päättymisaika (sekunteina)
- **duration[batch][stage]**: Vaiheen kesto (min_time ≤ duration ≤ max_time)

#### 4.1.2 Asemamuuttujat
Kun MinStat < MaxStat (asemavalinta):
- **selected_station[batch][stage]**: Valittu asema kyseiselle vaiheelle
- **station_usage[station][time]**: Boolean - onko asema käytössä hetkellä t

#### 4.1.3 Nostimen tehtävät
Jokaiselle siirtotehtävälle:
- **task_start[task_id]**: Siirtotehtävän aloitusaika
- **task_end[task_id]**: Siirtotehtävän päättymisaika
- **task_assignment[task_id][batch][stage]**: Boolean - kuuluuko tehtävä kyseiseen vaiheeseen

#### 4.1.4 Makespan-muuttuja
- **makespan**: Kokonaistuotantoajan maksimiarvo (optimoitava)

### 4.2 Rajoitteiden mallintaminen

#### 4.2.1 Käsittelyjärjestysrajoite (Sääntö 1)
```python
# Jokaiselle erälle: vaihe i+1 alkaa vasta kun vaihe i on päättynyt
for batch in batches:
    for stage in range(len(treatment_program[batch])-1):
        model.Add(start_time[batch][stage+1] >= end_time[batch][stage])
```

#### 4.2.2 Käsittelyaikarajoite (Sääntö 2)
```python
# Jokaisen vaiheen kesto min ja max rajoissa
for batch in batches:
    for stage in stages[batch]:
        model.Add(duration[batch][stage] >= min_time[batch][stage])
        model.Add(duration[batch][stage] <= max_time[batch][stage])
        model.Add(end_time[batch][stage] == start_time[batch][stage] + duration[batch][stage])
```

#### 4.2.3 Aseman yksinomaisuusrajoite (Sääntö 3)
```python
# Yhdellä asemalla vain yksi erä kerrallaan (ei päällekkäisyyttä)
for station in stations:
    for t1, t2 in all_time_intervals:
        tasks_on_station = [task for task in tasks if task.station == station]
        model.AddNoOverlap([interval_var[task] for task in tasks_on_station])
```

#### 4.2.4 Vaihtoaikarajoite (Sääntö 3.1)
```python
# Seuraava erä asemalle vasta vaihtoajan jälkeen
for station in stations:
    for consecutive_tasks in consecutive_station_tasks[station]:
        task_prev, task_next = consecutive_tasks
        batch_change_time = calculate_batch_change_time(task_prev, task_next)
        model.Add(start_time[task_next] >= end_time[task_prev] + batch_change_time)

def calculate_batch_change_time(task_prev, task_next):
    # task_prev: erä A poisvienti (x → y)
    # task_next: erä B tuonti (z → x)
    total_task_time_prev = get_total_task_time(task_prev.from_station, task_prev.to_station)
    transfer_time_empty = get_transfer_time(task_prev.to_station, task_next.from_station)  
    total_task_time_next = get_total_task_time(task_next.from_station, task_next.to_station)
    return total_task_time_prev + transfer_time_empty + total_task_time_next
```

#### 4.2.5 Nostimen järjestysrajoite (Sääntö 4.1)
```python
# Nostin ei voi olla kahdessa paikassa yhtäaikaa
# Peräkkäisten tehtävien välissä riittävästi aikaa siirtymiseen
for i in range(len(hoist_tasks)-1):
    task_current = hoist_tasks[i]
    task_next = hoist_tasks[i+1]
    transfer_time = get_transfer_time(task_current.end_station, task_next.start_station)
    model.Add(start_time[task_next] >= end_time[task_current] + transfer_time)
```

#### 4.2.6 Asemavalintarajoite (Vapausaste 2)
```python
# Jos MinStat < MaxStat, valittu asema oltava sallitulla välillä ja samassa ryhmässä
for batch in batches:
    for stage in stages[batch]:
        if min_station[batch][stage] < max_station[batch][stage]:
            model.Add(selected_station[batch][stage] >= min_station[batch][stage])
            model.Add(selected_station[batch][stage] <= max_station[batch][stage])
            # Lisäksi: sama ryhmä
            allowed_stations = get_stations_in_group(group[batch][stage])
            model.AddAllowedAssignments([selected_station[batch][stage]], 
                                       [(s,) for s in allowed_stations])
```

### 4.3 Optimointitavoitteen implementaatio

#### 4.3.1 Makespan-minimointi
```python
# Makespan = viimeisen tehtävän päättymisaika
for batch in batches:
    final_stage = len(treatment_program[batch]) - 1
    model.Add(makespan >= end_time[batch][final_stage])

# Optimointitavoite
model.Minimize(makespan)
```

#### 4.3.2 Ratkaisun hakeminen
```python
solver = cp_model.CpSolver()
solver.parameters.max_time_in_seconds = 300.0  # 5 minuuttia
status = solver.Solve(model)

if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
    print(f"Optimal makespan: {solver.Value(makespan)} seconds")
    # Tulosta tehtävien aikataulu
    for batch in batches:
        for stage in stages[batch]:
            start = solver.Value(start_time[batch][stage])
            end = solver.Value(end_time[batch][stage])
            station = solver.Value(selected_station[batch][stage])
            print(f"Batch {batch}, Stage {stage}: Station {station}, {start}-{end}")
else:
    print("No solution found!")
    print(f"Status: {status}")
```

### 4.4 Implementaation vaiheistus

#### Vaihe 1: Perusoptimiointi
1. Implementoi muuttujat 4.1.1 ja 4.1.4
2. Implementoi rajoitteet 4.2.1, 4.2.2, 4.2.3
3. Implementoi makespan-minimointi 4.3.1
4. Testaa yksinkertaisella datalla

#### Vaihe 2: Nostimen rajoitteet
1. Lisää tehtävämuuttujat 4.1.3
2. Implementoi nostimen järjestysrajoite 4.2.5
3. Testaa realistisella datalla

#### Vaihe 3: Vaihtoajat
1. Implementoi vaihtoaikarajoite 4.2.4
2. Optimoi batch_change_time-laskenta
3. Validoi tulokset esimerkkitapauksilla

#### Vaihe 4: Asemavalinta
1. Lisää asemamuuttujat 4.1.2
2. Implementoi asemavalintarajoite 4.2.6
3. Testaa monimutkaisen asemavalinnan kanssa

### 4.5 Debuggaus ja validointi

#### 4.5.1 INFEASIBLE-ongelman diagnosointi
```python
if status == cp_model.INFEASIBLE:
    print("Problem is infeasible. Checking relaxed constraints...")
    
    # Poista rajoitteita yksi kerrallaan ja katso mikä aiheuttaa infeasibility
    # 1. Kokeile ilman vaihtoaikarajoitteita
    # 2. Kokeile ilman nostimen järjestysrajoitteita  
    # 3. Kokeile suuremmilla käsittelyaika-aloilla
    # 4. Tarkista lähtödatan loogisuus
```

#### 4.5.2 Ratkaisun validointi
```python
def validate_solution(solver, model):
    # Tarkista että kaikki rajoitteet täyttyvät
    # Tarkista että makespan on oikein
    # Tarkista että aikataulut ovat loogisia
    # Vertaa tulosta esimerkkitapaukseen
```

## 5. Validointikriteerit

### 5.1 Validi ratkaisu
Validi ratkaisu on sellainen, että kaikki erät ovat kulkeneet prosessin läpi käsittelyohjelman mukaisessa järjestyksessä, ja käsittelyaika kaikissa vaiheissa on min/max aikojen rajoissa. JA. Nostin pystyy fyysisen mukaan suorittamaan kaikki tehtävät ajallisesti kronologisessa järjestyksessä. Kaikki edellä kuvatut ratkaisut ovat 'valideja'. Tavoite on kuitenkin löytää 'valideista' ratkaisuista se, mikä on nostimen kannalta nopein --> kokonaistuotantoaika on lyhin.

### 5.2 Optimointikriteeri
Optimointitavoite on minimoida kokonaistuotannon läpimenoaika (makespan). Siirtojen määrä tulee erien määrästä ja ohjelma-askelien määrästä erien käsittelyohjelmissa --> sitä ei voi optimoida. Kun löydetään nostimelle (nostimille) nopein reitti, niin silloin on löydetty lyhin kokonaistuotantoaika --> odotusajat ovat minimissään.

## 6. Erien ja nostimien määrä

- Optimointi tukee useita eriä. Yhdellä asemalla voi olla vain yksi erä kerrallaan.
- Tässä vaiheessa keskitytään yhden nostimen optimointiin, mutta malli voidaan laajentaa useammalle nostimelle myöhemmin.

## 7. Esimerkkitapaus

### 7.1 Lähtötiedot

#### Asemat
- **301**: Ryhmä 1, X-sijainti 1000, Valutusaika 0, Asematyyppi 0, Laitteen viive 0.0
- **302**: Ryhmä 2, X-sijainti 2000, Valutusaika 0, Asematyyppi 0, Laitteen viive 0.0
- **303**: Ryhmä 3, X-sijainti 3000, Valutusaika 0, Asematyyppi 0, Laitteen viive 0.0

#### Nostin 1
- **Minimi X-sijainti**: 900 mm
- **Maksimi X-sijainti**: 10200 mm
- **Kiihdytysaika**: 2.0 s
- **Hidastusaika**: 2.0 s
- **Maksiminopeus**: 300 mm/s
- **Z-akselin kokonaismatka**: 1800 mm
- **Z-akselin hidas matka (kuiva)**: 300 mm
- **Z-akselin hidas matka (märkä)**: 1500 mm
- **Z-akselin hidas loppumatka**: 50 mm
- **Z-akselin hidas nopeus**: 100 mm/s
- **Z-akselin nopea nopeus**: 200 mm/s

### 7.2 Lähtötiedot erän 1 käsittelyohjelmasta

| Stage | MinStat | MaxStat | MinTime   | MaxTime   | CalcTime   |
|-------|---------|---------|-----------|-----------|------------|
| 0     | 301     | 301     | 00:00:00  | 100:00:00 | 00:00:00   |
| 1     | 302     | 302     | 00:10:00  | 00:12:00  | 00:10:00   |
| 2     | 303     | 303     | 00:00:00  | 00:12:00  | 00:00:00   |

Nämä tiedot on poimittu tiedostosta `Batch_001_Treatment_program_001.csv` ja ne kuvaavat erän 1 käsittelyohjelman vaiheet ja aikarajoitteet.

### 7.3 Nostimen aloitus- ja lopetuspaikka

Yhden nostimen optimoinnissa aloitus- ja lopetuspaikka ei vaikuta optimointiin, koska fokus on tehtävien välisten siirtojen optimoinnissa. Tieto löytyy tiedostosta `transporters_start_positions.csv` teknistä täydellisyyttä varten.

### 7.4 Tehtävä- ja siirtoajat asemille 301, 302 ja 303

**Huom!** Kaikki erilaiset siirrot ja niiden ajat tulee määritellä etukäteen (kaikki mahdolliset asemien väliset siirrot), jotta erilaiset käsittelyohjelmat ja asemavalinnat ovat mahdollisia. Siirtymäajat on laskettava etukäteen. Jos optimointi kohtaa puuttuvan siirtymäajan, siitä annetaan virheilmoitus ja simulointi keskeytyy.

- **301 → 301**: Lift Time: 17 s, Transfer Time: 0.0 s, Sink Time: 16 s, Total Task Time: 33.0 s
- **301 → 302**: Lift Time: 17 s, Transfer Time: 5.0 s, Sink Time: 16 s, Total Task Time: 38.0 s
- **301 → 303**: Lift Time: 17 s, Transfer Time: 9.0 s, Sink Time: 16 s, Total Task Time: 42.0 s
- **302 → 301**: Lift Time: 17 s, Transfer Time: 5.0 s, Sink Time: 16 s, Total Task Time: 38.0 s
- **302 → 302**: Lift Time: 17 s, Transfer Time: 0.0 s, Sink Time: 16 s, Total Task Time: 33.0 s
- **302 → 303**: Lift Time: 17 s, Transfer Time: 5.0 s, Sink Time: 16 s, Total Task Time: 38.0 s
- **303 → 301**: Lift Time: 17 s, Transfer Time: 9.0 s, Sink Time: 16 s, Total Task Time: 42.0 s
- **303 → 302**: Lift Time: 17 s, Transfer Time: 5.0 s, Sink Time: 16 s, Total Task Time: 38.0 s
- **303 → 303**: Lift Time: 17 s, Transfer Time: 0.0 s, Sink Time: 16 s, Total Task Time: 33.0 s

Nämä tiedot on poimittu tiedostosta `transfer_tasks.csv` ja ne kuvaavat siirto- ja tehtäväaikoja asemien välillä.

### 7.5 Esimerkki validista vs. virheellisestä tuloksesta

#### Virheellinen optimointitulos: 
```
Batch,   Stage,   Station, Start,   End,     Duration
1,       0,       301,     0,       0,       0
2,       0,       301,     5,       5,       0
1,       1,       302,     38,      638,     600
2,       1,       302,     648,     1248,    600
1,       2,       303,     676,     976,     300
1,       3,       304,     1019,    1020,    1 
2,       2,       303,     1286,    1586,    300
2,       3,       304,     1624,    1624,    0
```

**Esimerkkejä rikkeistä**:
- Erä 2 Stat 301 End 5 s, Start 302 Start 648 s --> siirto kestänyt 643 s, transfer_task tiedostosta siirto 301 → 302 38 s
- Erä 1 Stat 302 End 638 s ja Erä 2 Stat 302 Start 648 s --> erä 2 tulee asemalle 10 s erän 1 lopun jälkeen. Nostin tarvitsee kuitenkin viedä erä 1 302 → 303 (38 s), siirtyä 303 - 301 (9 s) ja siirtää erä 2 301 → 302 (38 s), eli nostin tarvitsee yhteensä 85 s --> aikaisin aika erän 2 startille on 85 sekuntia erän 1 Endin jälkeen, eli 723 s.

#### Validi tulos (ei vielä välttämättä nopein): 
```
Batch,   Stage,   Station, Start,   End,     Duration
1,       0,       301,     0,       0,       0
2,       0,       301,     0,       685,     685
1,       1,       302,     38,      638,     600
2,       1,       302,     723,     1323,    600
1,       2,       303,     676,     976,     300
1,       3,       304,     1014,    1014,    0 
2,       2,       303,     1361,    1661,    300
2,       3,       304,     1699,    1699,    0
```

## 8. Useamman nostimen huomioita (tulevaa laajennusta varten)

Jos optimointiin lisätään useampi nostin, tärkein rajoite on, että nostimet eivät saa toimia liian lähellä toisiaan eivätkä toistensa "väärällä puolella". Tiedostoon `transporters_start_positions.csv` (tai vastaavaan) lisätään kenttä `Avoid_limit`, joka kuvaa x-suunnassa minimietäisyyttä, jonka lähemmäs nostimet voivat toisiaan mennä. Useamman nostimen optimointi on huomattavasti haastavampaa, eikä sitä toteuteta tässä vaiheessa.

## 9. Poikkeustapaukset

Ei ole poikkeuksia. Jos ratkaisua ei oikeasti löydy, on lähtötiedoissa puutteita, ja ne pitää käyttäjän korjata. Jos ratkaisu ei muuten tyydytä käyttäjää (kokonaistuotantoaika liian pitkä), pitää käyttäjän muuttaa ratkaisua; lisätä nostimia, lisätä rinnakkaisia asemia, lyhentää käsittelyaikoja jne. Tämä on käyttäjän tehtävä, ei optimoinnin.

## 10. Lisäkysymykset ja -vaatimukset

### Nostimen tyhjäsiirrot
Kyllä nostimen pitää siirtyä tyhjänä tehtävältä toiselle, eli edellinen tehtävä päättyy laskuun asemalle x ja seuraava alkaa nostolla asemalla y, pitää nostimen siirtyä x → y. Tähän tarvittava aika löytyy tiedostosta transfer_tasks.csv sarakkeesta transfer_time.

### Nostimen lepopaikka
Yhden nostimen optimoinnissa aloituspaikka ei vaikuta optimointiratkaisuun, koska simulointi fokusoi tehtävien välisiin siirtoihin optimaalisessa järjestyksessä.

### Rinnakkaisuus asemilla
Yhdellä asemalla voi olla vain yksi erä kerrallaan vrt kysymys 6. ja sääntö 3. Useampi asema voi kuitenkin muodostaa ryhmän (sama Group numero). Jos käsittelyohjelmassa asetetaan min - max asemat, niin tuolta väliltä voidaan käyttää samaan ryhmään kuuluvia asemia samassa ohjelma vaiheessa yhtä aikaa - rinnakkain.

### Odotusajat
Simulaatiossa ei tarvitse ottaa huomioon mitään erillisiä odotusaikoja, eikä simulointi saa itsekään 'keksiä' mitään ylimääräisiä viiveitä tai odotuksia.

### Nostimen rajoitteet
Nostimen ominaisuudet on kaikki kuvattu transporters.csv tiedostossa. Tällä hetkellä ei ole mitään muita rajoitteita.