# Vaatimusmäärittely CP-SAT Vaihe 1: Asemaoptimointi

## Tavoite
Muodostaa kokonaiskestoltaan lyhin tuotantosuunnitelma, joka määrittää erien lähtöaikataulun ja -järjestyksen. Optimointi huomioi vain asemavaraukset ja yksinkertaistetut siirtoajat.

## Perusperiaatteet

### 1. Käsittelyohjelmien noudattaminen
- Erän vaiheet on suoritettava käsittelyohjelman määräämässä järjestyksessä
- Jokaisessa vaiheessa käytetään käsittelyohjelman minimiaikaa (MinTime)

### 2. Asemavaraukset
- Yhdellä asemalla voi olla vain yksi erä kerrallaan
- Jos käsittelyohjelma sallii rinnakkaiset asemat (MinStat-MaxStat), valitaan vapaa asema
- Erän siirtyminen asemalta toiselle kestää average_task_time
- Kahden erän välillä samalla asemalla oltava change_time (2 × average_task_time)

### 3. Optimoinnin tavoite
- Minimoidaan kokonaistuotantoaika (viimeisen erän viimeisen vaiheen päättymisaika)
- Yksinkertaistettu malli: käytetään keskimääräisiä siirtoaikoja
- Luodaan pohja vaiheen 2 nostinoptimoinnille

## Toimintaperiaate

### 1. Esikäsittely ja symmetrian poisto
- Tunnistetaan identtiset erät (sama käsittelyohjelma)
- Lukitaan identtisten erien keskinäinen järjestys
- Karsitaan symmetriset vaihtoehdot jo ennen optimointia

### 2. Varsinainen optimointi
- Optimoidaan vain tarvittavat vaihtoehdot
- Hyödynnetään esikäsittelyn karsimia symmetrioita
- Nopeuttaa merkittävästi ratkaisun löytymistä

## Lähtötiedot

### Tiedostorakenne
Optimointi käyttää samoja lähtötietoja kuin nykyinen toteutus:

1. `cp_sat_batches.csv`
   - Lista käsiteltävistä eristä
   - Sarakkeet: Batch, Treatment_program

2. `cp_sat_stations.csv`
   - Asemien tiedot
   - Sarakkeet: Station, Group (asemaryhmä)

3. `cp_sat_treatment_program_{batch_id}.csv`
   - Eräkohtaiset käsittelyohjelmat
   - Sarakkeet: Stage, MinStat, MaxStat, MinTime, MaxTime

4. `cp_sat_transfer_tasks.csv`
   - Käytetään vaihtoajan (batch_change_time) laskentaan
   - Sarakkeet: From_Station, To_Station, TotalTaskTime, ...
   - TotalTaskTime-sarakkeesta lasketaan keskimääräinen siirtoaika

### Siirtoaikojen käsittely

1. Keskimääräinen siirtoaika (average_task_time)
   - Lasketaan `cp_sat_transfer_tasks.csv` tiedoston TotalTaskTime-sarakkeen keskiarvo
   - Kuvaa yhden siirtotehtävän keskimääräistä kestoa

2. Vaihtoaika (change_time)
   - change_time = 2 × average_task_time
   - Huomioi sekä edellisen erän poiston että seuraavan erän tuonnin
   - Käytetään minimiaikana kahden erän välillä samalla asemalla

3. Käyttö optimoinnissa
   - Asemavarausten väliin jätettävä vähintään change_time
   - Varmistaa että nostimella on riittävästi aikaa siirtotehtäville

## Optimoinnin esikäsittely

### 1. Identtisten erien tunnistaminen
- Erät ovat identtisiä, jos niillä on täsmälleen sama käsittelyohjelma
- Vertaillaan kaikki ohjelman parametrit: Stage, MinStat, MaxStat, MinTime, MaxTime
- Ryhmitellään erät identtisten ohjelmien mukaan

### 2. Symmetrian poisto
- Identtisten erien keskinäisen järjestyksen vaihtaminen ei vaikuta kokonaisoptimiin
- Jos erät A ja B ovat identtisiä, niiden järjestyksen vaihtaminen tuottaisi saman tuloksen
- Karsitaan turhat vaihtoehdot säilyttämällä alkuperäinen järjestys

### 3. Optimoinnin tehostaminen
- Lisätään rajoite: identtisen ryhmän sisällä erä N aloittaa ennen erää N+1
- Vähentää merkittävästi tutkittavien vaihtoehtojen määrää
- Nopeuttaa optimaalisen ratkaisun löytymistä

## Optimoinnin muuttujat

### 1. Erien lähtöajat
- Jokaisen erän Stage 0:n lähtöaika
- Rajoite: aika ≥ 0

### 2. Asemavalinnat
- Jokaiselle vaiheelle valittu asema väliltä MinStat-MaxStat
- Huomioitava Group-rajoitteet

### 3. Käsittelyajat
- Käytetään aina käsittelyohjelman minimiaikaa (MinTime)
- Käsittelyaikaa ei säädetä - jätetään se vaiheen 2 optimoinnille

## Rajoitteet

### 1. Asemien yksikäyttöisyys ja vaihtoaika
- Yhdellä asemalla voi olla vain yksi erä kerrallaan
- Poikkeus: Stage 0 (aloitusasema) sallii päällekkäisyydet
- Peräkkäisten erien välillä oltava vähintään change_time (2 × average_task_time)
- Rajoite: Jos erä A poistuu asemalta hetkellä t, seuraava erä B voi saapua aikaisintaan hetkellä t + change_time

### 2. Erän sisäinen järjestys
- Erän vaiheet suoritettava määritellyssä järjestyksessä
- Seuraava vaihe voi alkaa vasta kun edellinen on päättynyt

### 3. Asemaryhmät (Group)
- Asemavalinta sallittu vain saman Group-numeron sisällä
- MinStat-MaxStat määrittelee valittavissa olevat asemat

## Vapausasteet

### 1. Erien järjestys
- Erien keskinäinen käsittelyjärjestys on vapaa
- Poikkeus: identtiset erät käsitellään alkuperäisessä järjestyksessä

### 2. Asemavalinta
- Vapaa valinta MinStat-MaxStat väliltä saman Group-numeron sisällä
- Mahdollistaa rinnakkaisten asemien tehokkaan käytön

### 3. Käsittelyajat
- Käytetään aina käsittelyohjelman minimiaikaa (MinTime)
- Yksinkertaistettu malli: ei käsittelyaikojen optimointia

## Optimoinnin tavoite
1. Minimoi kokonaisläpimenoaika (makespan) käyttäen minimiaikoja
2. Muodosta toteutuskelpoinen aikataulu huomioiden siirto- ja vaihtoajat
3. Luo pohja vaiheen 2 nostinoptimoinnille

## Tulostiedot

### Tulostiedosto: cp_sat_batch_schedule.csv
Optimoitu aikataulu tallennetaan samaan kansioon lähtötietojen kanssa.

Sarakkeet:
- Transporter: Nostimen tunniste
- Batch: Erän numero
- TreatmentProgram: Käsittelyohjelman numero
- Stage: Käsittelyohjelman vaihe
- Station: Valittu asema
- EntryTime: Asemalle saapumisaika (sekunteina)
- ExitTime: Asemalta poistumisaika (sekunteina)

Tiedosto sisältää kaikki asemavaraukset aikajärjestyksessä ja toimii lähtötietona vaiheen 2 nostinoptimoinnille.

### Aikamäärittelyt
- Kaikki ajat ovat sekunteina simulaation alusta (t=0)
- EntryTime: Hetki jolloin erä on asemalla ja käsittely voi alkaa
- ExitTime: Hetki jolloin erän käsittely on päättynyt (ei sisällä nostimen siirtoaikaa)

## Huomioitavaa
1. Vaihe 1 keskittyy vain asemakapasiteetin optimointiin
2. Ratkaisun on oltava toteutuskelpoinen myös nostinrajoitteiden kanssa
3. Käsittelyaikoihin jätettävä riittävästi joustoa vaihetta 2 varten
4. Tulos muodostaa lähtökohdan nostinoptimoinnille
5. Toteutus voi hyödyntää nykyistä cp_sat_optimization.py rakennetta:
   - Sama tiedostorakenne ja nimeämiskäytännöt
   - Sama muuttujien alustuslogiikka
   - Vain rajoitteet ja tavoitefunktio muuttuvat