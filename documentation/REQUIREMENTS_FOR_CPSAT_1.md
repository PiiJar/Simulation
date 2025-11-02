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

### 2. Identtisten erien tunnistaminen ja symmetrian poisto
- Erät ovat identtisiä, jos niillä on sama käsittelyohjelma
  - Treatment_program määrittää identtisyyden
  - Kaikki käsittelyohjelman parametrit tulevat samasta tiedostosta
  - Ohjelma määrää kaikki vaiheet, ajat ja asemavalinnat
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

- Vaihtoajan käyttö:
  - Vaihtoaikaa tarvitaan VAIN kun erä B on tulossa SAMALLE asemalle, jolla erä A on
  - Tässä tilanteessa:
    1. Erä A pitää ensin viedä pois asemalta
    2. Vaihtoajan (change_time) verran aikaa kuluu
    3. Vasta sitten erä B voi tulla asemalle
  - Vaihtoaika = 2 × average_task_time
  - Rajoite: Jos erä A poistuu asemalta hetkellä t, seuraava erä B voi saapua samalle asemalle aikaisintaan hetkellä t + change_time

- Rinnakkaisasemien käyttö:
  - Jos löytyy vapaa rinnakkainen asema (sama Group), erä B voi mennä sille välittömästi
  - Vaihtoaikaa EI tarvita, koska kyseessä on eri asema
  - Rinnakkaisasemat toimivat täysin itsenäisesti
- Stage 0 on poikkeus:
  - On virtuaalinen aloitusasema, ei fyysinen asema
  - Sallii erien päällekkäisen läsnäolon
  - ExitTime määrittää erän todellisen lähtöhetken prosessiin
  - Koska Stage 0:aan ei tulla mistään, siihen ei sovelleta vaihtoaikaa
  - Toimii optimoinnin työkaluna erien ajoituksen suunnittelussa

### 2. Erän sisäinen järjestys
- Erän vaiheet suoritettava määritellyssä järjestyksessä
- Seuraava vaihe voi alkaa vasta kun edellinen on päättynyt

### 3. Asemaryhmät (Group)
- Asemavalinta sallittu vain saman Group-numeron sisällä
- MinStat-MaxStat määrittelee valittavissa olevat asemat

## Optimoinnin vapausasteet

Optimointi voi hyödyntää seuraavia vapausasteita parhaan ratkaisun löytämiseksi:

### 1. Erien lähtöjärjestys ja -ajat
- Erien keskinäinen suoritusjärjestys on täysin vapaasti valittavissa
- Poikkeus: identtiset erät (sama käsittelyohjelma) käsitellään alkuperäisessä järjestyksessä

### 2. Stage 0:n rooli optimoinnissa
- Stage 0:n ExitTime on optimoinnin keskeinen säätömuuttuja
  - Määrittää kunkin erän todellisen lähtöhetken prosessiin
  - Voidaan valita vapaasti väliltä [0, MAX_TIME]
  - Säätämällä näitä aikoja voidaan välttää päällekkäisyydet muilla asemilla
- Stage 0 on virtuaalinen aloitusasema
  - Erät voivat olla Stage 0:lla päällekkäin
  - ExitTime-arvot määräävät erien todellisen prosessiin lähtöjärjestyksen
  - Toimii optimoinnin työkaluna asemavarausten ajoituksessa

### 2. Rinnakkaisten asemien käyttö
- Jos käsittelyohjelma sallii useamman aseman (MinStat < MaxStat):
  - Voidaan valita mikä tahansa asema väliltä MinStat-MaxStat
  - Valinnan pitää huomioida aseman Group-numero (vain saman ryhmän asemat)
  - Valinta tehdään yksinkertaisella kierrätyksellä (round-robin)
    - Valitaan seuraava vapaa asema MinStat-MaxStat väliltä
    - Jos ryhmässä on asemat 101, 102, 103 ja edellinen käytti 102:ta, seuraava käyttää 103:a jne.
  - Mahdollistaa kuormituksen tasaamisen rinnakkaisten asemien välillä

### 3. Nostimen valinta
- Siirtotehtävän suorittajaksi valitaan sopiva nostin toiminta-alueiden perusteella
- Nostimen toiminta-alueen tulee kattaa sekä lähtö- että kohdeasema
- Tulostiedostossa rivillä oleva Transporter kertoo nostimen, joka on tuonut erän kyseiselle asemalle
- Nostinvalinta huomioi kunkin nostimen käytettävissä olevat asemat

### 4. Aikataulutuksen optimointi
- Voidaan suunnitella rinnakkaisia käsittelyjä eri asemilla
- Voidaan minimoida asemien tyhjäkäyntiaikaa
- Voidaan optimoida siirtymät huomioiden average_task_time ja change_time

### 4. Nostimen tehtävien ajoitus
- Ei tarvitse huomioida nostimen mahdollisia päällekkäisiä tehtäviä
- Riittää että asemavarausten välissä on change_time
- Nostimen todellinen reititys ja kapasiteetti ratkaistaan vaiheessa 2
- Mahdollistaa yksinkertaisemman optimointimallin vaiheessa 1

### Rajoitetut vapausasteet (ei optimoida vaiheessa 1)
1. Käsittelyajat: käytetään aina MinTime-arvoja
2. Erän sisäinen vaihejärjestys: noudatetaan käsittelyohjelmaa
3. Nostimen reititys: käytetään keskimääräisiä siirtoaikoja
4. Identtisten erien järjestys: säilytetään alkuperäinen järjestys

## Optimoinnin tavoite

Päätavoite on löytää lyhin mahdollinen kokonaistuotantoaika siten, että:

1. Kokonaistuotantoajan määritelmä:
   - Alkaa hetkestä 00:00:00 (simulaation alku)
   - Päättyy tulostiedoston suurimpaan ExitTime-arvoon
   - Kokonaistuotantoaika = max(ExitTime) kaikista tulostiedoston riveistä
   - Optimoinnin tavoite on minimoida tämä maksimiarvo
   
   Huom: Suurin ExitTime ei välttämättä ole:
   - Viimeisenä linjaan lähteneen erän
   - Pisimmän käsittelyohjelman erän
   - Viimeisen aseman tapahtuma
   
   Optimointi etsii sellaisen erien ajoituksen, jossa tämä suurin ExitTime on mahdollisimman pieni.

2. Tuotantojärjestyksen optimointi:
   - Stage 0:n ExitTime-arvoja säätämällä voidaan välttää päällekkäisyydet muilla asemilla
   - Jokaisella asemalla voi olla vain yksi erä kerrallaan (pois lukien Stage 0)
   - Erien erilaisten käsittelyohjelmien pituudet huomioidaan lähtöjärjestyksessä

3. Käsittelyaikoja ei optimoida vaiheessa 1:
   - Käytetään käsittelyohjelman MinTime-arvoja
   - Käsittelyaikojen säätö jätetään vaiheen 2 optimoinnille

4. Tulos toimii pohjana vaiheen 2 nostinoptimoinnille:
   - Varmistetaan asemavarausten toteutuskelpoisuus
   - Huomioidaan siirto- ja vaihtoajat

## Tulostiedot

### Tulostiedosto: cp_sat_batch_schedule.csv
Optimoitu aikataulu tallennetaan samaan kansioon lähtötietojen kanssa.

Sarakkeet:
- Transporter: Nostimen tunniste
- Batch: Erän numero
- Treatment_program: Käsittelyohjelman numero
- Stage: Käsittelyohjelman vaihe (0 = aloitusasema)
- Station: Valittu asema
- EntryTime: Asemalle saapumisaika (sekunteina)
- ExitTime: Asemalta poistumisaika (sekunteina)

Rivit järjestetään ensisijaisesti Transporter-kentän ja toissijaisesti ExitTime-kentän mukaan nousevaan järjestykseen. Tämä järjestys on optimaalinen koska:
1. Nostinkohtainen ryhmittely (Transporter) selkeyttää kunkin nostimen työjonoa
2. Nostimen sisällä ExitTime määrittää milloin erä on valmis siirrettäväksi seuraavaan vaiheeseen
3. Järjestys tukee vaiheen 2 nostinkohtaista reittioptimointia

Tiedosto toimii lähtötietona vaiheen 2 nostinoptimoinnille.

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