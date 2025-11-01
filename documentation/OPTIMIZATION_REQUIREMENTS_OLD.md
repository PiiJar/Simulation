# CP-SAT Optimointitehtävän vaatimukset

## Yleiskuvaus

Tässä optimointitehtävässä mallinnetaan teollista tuotantolinjaa, jossa nostin siirtää tuotantoeriä asemalta toiselle käsittelyohjelman mukaisesti. Laitoksessa on useita asemia (esim. altaat, pesurit, kuivurit), joilla kullakin on omat rajoitteensa ja käsittelyajat. Nostimen liikkeet ja siirtoajat perustuvat fysiikkaan ja ne on laskettu etukäteen. 

**Optimoinnin tavoite**: Löytää nostimelle aikataulu, joka minimoi koko tuotantoerän läpimenoajan (makespan) huomioiden kaikki laitoksen rajoitteet, asemien käytön, tehtävien järjestyksen ja siirtymäajat.

**Aikayksiköt**: Kaikki ajat esitetään dokumentaatiossa muodossa hh:mm:ss, mutta optimoinnissa kaikki ajat muunnetaan sekunneiksi. Simulointi alkaa aina ajasta 00:00:00.

## Esikäsittelyn tuotokset CP-SAT-optimointia varten

Esikäsittelyvaihe tuottaa `cp_sat/`-kansioon seuraavat tiedostot optimointia varten:

### Perustiedostot
- **cp_sat_batches.csv**: Erien perustiedot (ID, käsittelyohjelma, aloitusasema, aloitusaika)
- **cp_sat_stations.csv**: Asemien tiedot (numero, ryhmä, sijainti, valutusaika, tyyppi)
- **cp_sat_transporters.csv**: Nostimien tekniset tiedot (nopeudet, kiihdytykset, liikealueet)
- **cp_sat_transporters_start_positions.csv**: Nostimien aloituspaikat (nostin ID, aloitusasema)
- **cp_sat_transfer_tasks.csv**: Kaikki mahdolliset siirtotehtävät ja niiden ajat (nostoaika, siirtoaika, laskuaika, kokonaisaika)

### Käsittelyohjelmat
- **cp_sat_treatment_program_N.csv**: Kunkin erän käsittelyohjelma (vaiheet, asemarajat, aikarajat)
- **treatment_program_optimized/**: Alkuperäiset käsittelyohjelmat ilman stage 0:aa

### Täsmennyksiä määrittelyihin 
- **Nostimen aloituspaikka**: Nostimen aloituspaikka kuvaa sitä paikkaa, missä nostin on simulaation alkuhetkellä 00:00:00, Nostin palaa myös viimeisen tehtävän jälkeen samaan aloituspaikkaan. Simulointi huomioi nostimen siirtymiseen vaadittavat ajan aloituspaikasta ensimmäisen tehtävän nostopaikkaan. Tämä aika on esilasketuna 'cp_sat_transfer_tasks.csv' tiedosssa; From_Station = aloitusasema, To_Station = ensimmäisen tehtävän nostoasema --> Transfer_Time. Tämä on aika kauanko nostimen siirtymiseen kahden aseman välillä kuluu aikaa.

- **Asemaryhmien valintalogiikka**: Käsittelyohjelmassa voi olla yhdelle Stagelle useampi asema (Min --> Max) - proseissin kannalta rinnakkaisia asemia, eli niissää on sama kemia.. Stations tiedostossa määritellään tarkemmin mitkä asemat tuolta väliltä kuuluvat samaan ryhmään (Group). Optimointi voi valita minkä tahansa samaan ryhmään kuuluvan, käsittelyohjelman min/max välillä olevan vapaan aseman. Yleensä se on on järjestysnumeroltaan ensimmäinen vapaa, mutta jos valinnalla on merkitystä nopeimman reitin löytämiseksi voidaan valita myös mikä tahansa muu, sillä hetkellä vapaa asema.

- **Vaihtoaikojen laskenta**: Vaihtoajalla tarkoitetaan sitä aikaa, mikä kuluu nostimelta (tai nostimilta) vaihtaa erä asemalla. Eli edellinen asemalla oleva erä viedään ensin sen erän käsittelyohjlman mukaiseen seuraavaan asemaan, ja sitten haetaan seuraava erä sen edellisestä paikasta, edellä vapautettuun asemaan.

Erä A asemalla x, sen seuraava asema y, Erä B asemalla z, ja sen seuraava asema x. Vaihtoaika (vaihdetaan asemalla x erä A, erään B) koostuu (yhden nostimen tapauksessa); nostin nostaa erän A asemalta x + nostin siirtää erän A asemalta x --> asemallt y + nostin laskee erän A asemalle y + ostin siirtyy asemalta y --> asemalle z + nostin nostaa erän B asemalta z + nostin siirtää erän B asemalta z --> asemalle x + nostin laskee erän B asemalle x.

Kahden nostimen tapausta käsitellään, kun yhden nostimen optimointi on saatu luotettavasti toimimaan!!

- **Nolladurationien käsittely**: SKäsittelyohjelmassa voi olla käsittelyvaiheita, joiden minimi käsittelyaika on asetettu 00:00:00. Käsittelyn 'keskellä' tämä kiristää rajoitteita kyseisessä kohdassa, jos myös maksimiaika on lyhy. Simulaation ensimmäinen ja viimeinen stage (stagen määrittelemä asema) ovat kuitenkin poikkauksia. 'Oikeassa' prosessissa, näihin vaiheisiin liittyy operaattorin toimintaa. Erän alkupaikan prosessissa minimiaka on 00:00:00. Tämä kuvaa olettamaa, että meillä on koko tuotanto valmiina lähtemään prosessiin. Alkupaikan maksimiaika on kuitenkin esiprosessoinnissa asetettu 100:00:00. Tämä kuvaa sitä vapausasetett, mitä optimointi voi käyttää kunkin erän välissä.

Erän viimeinen stage, on se asema, misä operaattori, siirtää erän pois, joten tämä vapauttaa optimoinniss nostimen heti laskun loputtua. Erä tavallaan katoaa simuloinnista, kun se on laskettu viimeiselle asemalle.

- **Siirtoaikojen terminologia**: TransferTime on aika minkä nostin tarvitsee siirtymiseen kahden aseman välillä. TotalTaskTime kuvaa sitä aikaa minkä nostin tarvitsee erän siirtämiseen asemalta toiselle (LifTIme + TransferTime + SinkTime --> TotalTaskTIme)

- **Identtisten erien käsittely**: Samaa käsittelyohjelmaa käyttävät erät ovat optimoinnin kannalta identtisiä, eli niiden järjestyken vaihtaminen ei paranna lopputulosta. Jos on mahdollista välttää näiden tarkastely, niin optimointi tehostuu. Eli jos 'aluksi' laatisi 'listan' tuotantolistan 'aidosti' erilaisista vaihtoehdoista, ja vasta sitten aloittaisi optimoaalisen ratkaisun löytmäisen, niin vartailukerojen määrä vähenisi merkittävästi.

Käyttäjälle olisi kuitenkin hyvä, jos identtiseten erien alkuperäinen järjestys säilyisi.


# Optimointivaatimukset

## Tavoite
Simulointi alkaa aina ajasta 00:00:00, joten aikavyöhykkeillä tai kellonajoilla ei ole merkitystä optimoinnissa.
Etsiä nostimelle ajallisesti optimaalisin reitti, joka minimoi kokonaisajan (makespan) huomioiden kaikki rajoitteet, kuten asemien käyttö, tehtävien järjestys ja siirtymäajat.

**Aikayksiköt:**
Kaikki ajat esitetään dokumentaatiossa muodossa hh:mm:ss, mutta optimoinnissa kaikki ajat muunnetaan sekunneiksi.

## Säännöt

### Sääntö 1
Erien käsittelyohjelman määrittelemää käsittelyjärjestystä on noudatettava. Tämä tarkoittaa, että jokaisen erän vaiheet on suoritettava annetussa järjestyksessä ilman poikkeuksia.

### Sääntö 2
Käsittelyohjelmien ohjelma-askeleiden käsittelyaikoja pitää kunnioittaa. Jokaisen askeleen kesto on vähintään määritelty minimi ja enintään määritelty maksimi.

### Sääntö 3
Asemalla voi olla vain yksi erä kerrallaan. Tämä tarkoittaa, että aseman resurssit ovat varattuja yhden erän käsittelyn aikana, eikä päällekkäisyyksiä sallita.
---> Poikkeuksena aloitusasema (stage 0) tämä lisätään käsittelyohjelmaan vain optimointia varten. kaikkien erien stage 0 minimi aika on 00:00:00 ja maksimia aika 100:00:00. Kuviteellisesti kaikki erät ovat simulaation alkaessa aloitusasemalla, ja lähtevät siiä, kun muiden ehtojen mukaan se on mahdollista.

### Sääntö 3.1 – Aseman vapautuminen ja nostimen käyttö

Seuraava erä ei voi saapua asemalle ennen kuin edellinen erä on kokonaan käsitelty ja siirretty pois asemalta, ja nostin on vapaa. Käytännössä nostin siirtää ensin edellisen erän pois asemalta (tähän kuluu siirtoajaksi laskettu aika), minkä jälkeen nostimen täytyy siirtyä edellisen tehtävän päättymisasemalta seuraavan tehtävän aloitusasemalle ennen kuin uuden erän siirtotehtävä voi alkaa.

Käytetään tämä hallintaan 'Vaihtoaikaa' (batch_change_time). Vaihtoajan laskennaassa on kaksi eri tapausta; jos alueella käytettävissä vain yksi nostin, tai jos alueella on käytössä kaksi nostinta. Vaihtoaika yhden nostimen tapauksessa lasketaan käsittelyohjelman mukaisten siirtojen perusteella; lähtevän erän siirtoaika (noston alku --> laskun loppu) + nostimen siirtyminen laskuasemasta, seuraavan tehtävän nostoasemaan + tulevan erän siirtoaika (noston alku --> laskun loppu). ** Kahden nostimen tapaus määritellään myöhemmin.**. Sääntö 3.1 voidaan muotoilla siis myös niin, että asema pitää olla tyhjänä tuon vaihtoajan. 

### Sääntö 4
Nostimen liikkeet pitää perustua esilaskettuihin (fysiikkaan perustuviin) tietoihin. Liikkeisiin tarvittava aika tulee esikäsittelytiedostosta, ja optimoinnin on käytettävä näitä arvoja sellaisenaan.

### Sääntö 4.1
Nostin ei voi olla kahdessa paikassa yhtäaikaa. Kaikkien siirtotehtävien välissä on oltava riittävästi aikaa siirtymiseen tehtävältä toiselle, ja tämä aika perustuu esikäsittelytiedostossa määriteltyihin arvoihin.

## Vapausasteet

### Vapausaste 1
Käsittelyohjelmien käsittelyajat voivat olla mitä tahansa määritellyn minimi- ja maksimiarvon välillä. Tämä mahdollistaa nostimen tehtävien ajoittamisen ja päällekkäisyyksien eliminoinnin säätämällä käsittelyaikoja.

### Vapausaste 2
Jos käsittelyohjelmassa on vaihe, jossa MinStat < MaxStat, voidaan kyseiseen vaiheeseen valita mikä tahansa asema tältä väliltä, kunhan asema kuuluu samaan Group-numeroon. Näin mahdollistetaan rinnakkaisten asemien käyttö ja resurssien tehokkaampi hyödyntäminen. Jos Group-numero on sama, asemat ovat rinnakkaisia ja niitä voidaan käyttää yhtäaikaisesti.

### Vapausaste 3
Erien keskinäistä käsittelyjärjestystä voidaan vaihtaa, jos sillä on merkitystä paremman lopputuloksen löytämiseksi. Erän sisäinen tehtäväjärjestys pitää kuitenkin säilyä, eli käsittelyohjelma määrittää missä vaihejärjestyksessä erän pitää edetä. Nostimelle voidaan kuitenkin valita mitä erää milloinkin se siirtää. Jos tehtävien välisellä järjestyksen vaihdolla ei kuitenkaan paranneta (siis päästään huonompaan tai samaan kuin edellinen versio) kokonaiskapasiteettia, slilytetään alkuperäinen järjestys.

### Vapausaste 4
Kun erä on laskettu asemaan, voi nostin suoritaa toisiin eriin liittyviä siirtotehtäviä, jos se on mahdollista eränä käsittelyohjlelman kyseisen aseman  min/max aikaikkunassa. Ts. nostimen ei tarvitse toteuttaa vain yhden erän prosessia kerrallaan, vaa rinnakkainen ajo on sallittua, ja parhaan optimointituloksen löytämiseksi tärkeää.

### Vapausaste 5
Erä valmistuu, kun se on siirretty käsittelyohjelman viimeiselle asemalle. Nostin on heti laskun jälkeen vapa muihin tehtäviin. Lisäksi erän 'katoaa' tuotannosta, joten se ei myöskään varaa käsittelyohjelman viimeistä asemaa käsittelyajan jälkeen (käytänössä 0 ekuntia).

## Erien ja nostimien määrä
- Optimointi tukee useita eriä. Yhdellä asemalla voi olla vain yksi erä kerrallaan.
- Tässä vaiheessa keskitytään yhden nostimen optimointiin, mutta malli voidaan laajentaa useammalle nostimelle myöhemmin.

## Kysymykset ongelman ymmärtämiseksi

1. Mikä on optimoinnin tarkka tavoite?
   - Onko kyse vain nostimen reitin optimoinnista, vai pitääkö myös resurssien käyttöä (esim. asemat) optimoida?

   ### Vastaus kysymykseen 1
   Optimoinnin tavoite on minimoida kokonaistuotannon läpimenoaika. Tämä toteutuu, jos nostimelle (tai useammalle nostimelle) löydetään ajallisesti nopein reitti. Tässä vaiheessa keskitytään yhden nostimen optimointiin, mutta malli voidaan laajentaa useammalle nostimelle myöhemmin.

2. Miten askel 0 liittyy ongelman ratkaisuun?
   - Ymmärrän, että askel 0 tarjoaa joustavuutta, mutta miten se käytännössä varmistaa ratkaisun löytymisen?

   ### Vastaus kysymykseen 2
   Tuotantosuunnitelmassa on luettelo eristä. Osoittautui, että sen huomioiminen CP-SAT-optimoinnissa oli vaikeaa. Tämän vuoksi ohjelmaan lisättiin askel 0, joka edustaa erän lähtöä prosessiin. Askeleelle 0 asetetaan mahdollisimman laaja aikaikkuna, jotta optimoinnilla on suurin vapausaste "säätää" mahdollisia nostimen tehtävien päällekkäisyyksiä.

3. Mitä tarkoitat sillä, että optimointi ei ole valjastettu oikein?
   - Onko ongelma rajoitteiden mallinnuksessa, muuttujien rajoissa vai optimoinnin tavoitteessa?

   ### Vastaus kysymykseen 3
   Koska optimointi ei löydä ratkaisua aivan perusongelmaan, tämä paljastaa joko virheen optimointialgoritmissa tai sen parametroinnissa. Koska CP-SAT-algoritmi on laajasti käytetty ja luotettava, ongelman täytyy todennäköisesti olla parametroinnissa. Näiden kysymysten ja vastausten tavoitteena on varmistaa, että ongelman luonne ymmärretään oikein ja että parametrointi vastaa ongelman vaatimuksia.

4. Mitä erityisiä ongelmia olet havainnut optimoinnin tuloksissa?
   - Esimerkiksi: jääkö jokin rajoite täyttymättä, vai eikö ratkaisu löydy lainkaan?

   ### Vastaus kysymykseen 4
   Optimointi ei löydä ratkaisua ongelmaan, joka on luonteeltaan hyvin yksinkertainen. Testitapauksessa on yksi erä, jossa ohjelmassa on kaksi vaihetta. Yksi nostin pystyy suorittamaan nämä tehtävät nopeimmin noudattamalla minimiaikojen mukaisesti. Ratkaisun löytäminen ei siis voi olla mahdotonta. Tämä vahvistaa aiemman analyysin (kysymys 3), että ongelma liittyy todennäköisesti parametrointiin eikä itse algoritmiin.

5. Kaikki aikarajoitteet ja siirtymäsäännöt:

   - Milloin siirtoaika pitää ottaa huomioon (esim. batchien välillä, vaiheiden välillä, vain tietyissä tilanteissa)?
   - Onko siirtoaika aina sama, vai riippuuko se asemasta, batchista, vaiheesta?
   - Onko asemalla oltava tyhjä hetki ennen seuraavaa erää?

    ### Vastaus kysymykseen 5

    Siirtoaika pitää ottaa huomioon kaikkien nostimen tehtävien välissä. Nostin tarvitsee ajan siirtyä tehtävältä toiselle. Nämä ajat on laskettu valmiiksi tiedostoon transfer_tasks.csv sarakkeeseen transfer_time. Kun edellinen tehtävä loppuu, pitää nostimen siirtyä seuraavalle tehtävälle, ja tähän kuluu aikaa. Tiedostosta haetaan laskuasema (edellinen tehtävä) / nostoaasema (seuraavatehtävä) -pari ja sarakkeesta transfer_time saadaan siirtymään tarvittava aika.

6. Resurssirajoitteet:

   - Voiko sama asema käsitellä useampaa erää samanaikaisesti?
   - Voiko nostin siirtää useampaa erää yhtä aikaa?
   - Onko asemien välillä muita riippuvuuksia?

    ### Vastaus kysymykseen 6

    Asemalla voi olla vain yksi erä kerrallaan vrt. sääntö 3. Nostin siirtää vain yhtä erää kerrallaan. Asemien välillä ei ole muita riippuvuuksia, kuin niiden fyysinen etäisyys.

7. Ratkaisun hyväksyttävyys:

   - Mitä tarkoittaa validi ratkaisu? (esim. ei päällekkäisyyksiä, kaikki erät valmistuvat, kaikki siirto- ja käsittelyajat täyttyvät)
   - Onko sallittua, että erä odottaa asemalla, vai pitääkö siirtymien olla mahdollisimman tiiviitä?

   ### Vastaus kysymykseen 7

   Validi ratkaisu on sellainen, että kaikki erän ovat kulkeneet prosessin läpi käsittelyohjelman mukaisessa järjestyksessä, ja käsittelaika kaikissa vaiheissa on in/max aikojen rajoissa. JA. Nostin pystyy fyysikan mukaan suorittamaan kaikki tehtävät ajallisesti kronologisessa järjestyksessä. Kaikki edellä kuvatut ratkaisut ovat 'valideja'. Tavoite on kuitenkin löytää 'valideista' ratkaisuista se, mikä on nostimen kannalta nopein --> kokonaistuotantoaika on lyhin.

8. Optimointikriteeri:

   - Minimoidaanko kokonaisaikaa, siirtojen määrää, odotusaikaa vai jotain muuta?

   ### Vastaus kysymykseen 8

   optimointitavoite on kuvattu dokumentin alussa kohdassa Optimointivaatimukset/Tavoite. Lisäksi asiaa on kuvattu kysymyksen7 vastauksessa. Siirtojen määrä tulee erien määrästä ja ohjelma-askelien määrästä erien käsittelyohjelmissa --> sitä ei voi optimoida. Kun löydetään nostimelle (nostimille) nopein reitti, niin silloin on löydetty lyhin kokonaistuotantoaika --> odotusajat ovat minimissään.

9. Esimerkkiaikataulu:

   - Anna konkreettinen esimerkkiaikataulu, joka on validi, ja toinen, joka ei ole – sekä perustelut miksi.

   Virheellinen optimointitulos: 
   Batch,   Stage,   Station, Start,   End,     Duration
   1,       0,       301,     0,       0,       0
   2,       0,       301,     5,       5,       0
   1,       1,       302,     38,      638,     600
   2,       1,       302,     648,     1248,    600
   1,       2,       303,     676,     976,     300
   1,       3,       304,     1019,    1020,    1 
   2,       2,       303,     1286,    1586,    300
   2,       3,       304,     1624,    1624,    0

   Esimerkkejä rikkeistä (ei kaikki): 
   
   - Erä 2 Stat 301 End 5 s, Start 302 Start 648 s --> siirto kestänyt 643 s, transfer_task tiedostosta siirto 301 --> 302 38 s
   - Erä 1 Stat 302 End 638 s ja Erä 2 Stat 302 Start 648 s --> erä 2 tulee asemalle 10 s erän 1 lopun jälkeen. Nostin tarvitseen kuitenkin viedä   erä 1 302 --> 303 (38 s), siirtyä 303 - 301 (9 s) ja siirtää erä 2 301 --> 302 (38 s), eli nostin tarvitsee yhteensä 85 s --> aikaisin aika erän 2 startille on 85 sekuntia rän 1 Endin jälkeenm eli 723 s.

   Validi tulos (ei vielä välttämättä nopein): 
   Batch,   Stage,   Station, Start,   End,     Duration
   1,       0,       301,     0,       0,       0
   2,       0,       301,     0,       685,     685
   1,       1,       302,     38,      638,     600
   2,       1,       302,     723,     1323,    600
   1,       2,       303,     676,     976,     300
   1,       3,       304,     1014,    1014,    0 
   2,       2,       303,     1361,    1661,    300
   2,       3,       304,     1699,    1699,    0

10. Poikkeustapaukset:

   - Onko tilanteita, joissa sääntöjä saa rikkoa (esim. jos ratkaisua ei muuten löydy)?

   ### Vastaus kysymykseen 10

   Ei ole poikkeuksia. Jos ratkaisua ei oikeasti löydy, on lähtötiedoissa puutteita, ja ne pitää käyttäjän korjata. Jos ratkaisu ei muuten tyydytä käyttäjää (kokonaistuotantoaika liian pitkä) , pitää käyttäjän muuttaa ratkaisua; lisätä nostimia, lisätä rinnakkaisia asemia, lyhentää käsittelyaikoja jne. Tämä on käyttäjän tehtävä, ei optimoinnin.

11. Voiko nostin siirtyä “tyhjänä” asemalta toiselle, vai tekeekö se vain lastattuja siirtoja?

   - Jos nostin joutuu siirtymään tyhjänä, pitääkö nämä siirtymät mallintaa ja aikatauluttaa?

   ### Vastaus kysymykseen 11

   Kyllä nostimen pitää siirtyä tyhjänä tehtävältä toiselle, eli edellinen tehtävä päättyy laskuun asemalle x ja seuraava alkaa nostolla asemalla y, pitää nostimen siirtyä x --> y. Tähän tarvittava aika löytyy tiedostosta transfer_tasks.csv sarakkeesta transfer_time.

12. Onko nostimella aloituspaikka ja/tai “lepopaikka”, jonne se palaa, jos ei ole tehtäviä?

   ### Vastaus kysymykseen 12

   Nostimelle on määritelty aloituspaikka tiedostossa trasnporters_start_poisiton.csv. Mutta tällä hetkellä sille ei ole optimoinnissa käyttöä, koska simulointi alkaa ajassa 00:00:00, ja nostimen 1. tehtävä alkaa siitä, ja simulointi päättyy, kun nostin on laskenut viimeisen erän viimeiseen ohjelmaskeleen mukaiseen asemaan. Simuloinnin sisällä nostin odottaa viimeisen tehtävän lopun kohdalla.

13. Voiko useampi erä olla samassa asemassa yhtä aikaa, jos asema sallii rinnakkaisuuden (esim. useampi paikka yhdellä asemalla)?

   ### Vastaus kysymykseen 13

   Yhdellä asemalla voi olla vain yksi erä kerrallaan vrt kysymys 6. ja sääntö 3. Useampi asema voi kuitenkin muodostaa ryhmän (sama Group numero). Jos käsittelyohjelmassa asetetan min - max asemat, niin tuolta väliltä voidaan käyttää samaan ryhmään kuuluvia asemia samasa ohelma vaiheessa yhtäaaikaa - rinnakkain.

14. Onko siirtojen välillä pakollisia odotusaikoja (esim. nostimen huolto, lataus tms.)?

   ### Vastaus kysymykseen 14

   Simulaatiossa ei tarvitse ottaa huomioon mitään erillisiä odotusaikoja, eikä simulointi saa itsekään 'keksiä' mitään ylimääräisiä viiveitä tai odotuksia.

15. Onko nostimella muita rajoitteita (esim. maksimietäisyys, sallittu reitti, vain tietyt asemat sallittuja)?

   ### Vastaus kysymykseen 15

   Nostimen ominaisuudet on kaikki kuvattu transporters.csv tiedostossa. Tällä hetkellä ei ole mitään muita rajoitteita.

## Esimerkkitapaus

### Lähtötiedot

#### Asemat
- **301**: Ryhmä 1, X-sijainti 1000, Valutussaika 0, Asematyyppi 0, Laitteen viive 0.0
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

### Lähtötiedot erän 1 käsittelyohjelmasta

| Stage | MinStat | MaxStat | MinTime   | MaxTime   | CalcTime   |
|-------|---------|---------|-----------|-----------|------------|
| 0     | 301     | 301     | 00:00:00  | 100:00:00 | 00:00:00   |
| 1     | 302     | 302     | 00:10:00  | 00:12:00  | 00:10:00   |
| 2     | 303     | 303     | 00:00:00  | 00:12:00  | 00:00:00   |

Nämä tiedot on poimittu tiedostosta `Batch_001_Treatment_program_001.csv` ja ne kuvaavat erän 1 käsittelyohjelman vaiheet ja aikarajoitteet.

### Nostimen aloitus- ja lopetuspaikka
Nostimelle on määritelty aloituspaikka erillisessä tiedostossa `transporters_start_positions.csv`. Sama asema toimii myös nostimen lopetuspaikkana. Aloitus- ja lopetuspaikka ovat pakollisia tietoja jokaiselle nostimelle.

### Käsittelyohjelman rakenne
Käsittelyohjelma on vapaasti muokattavissa, joten optimoinnin tulee tukea tilannetta, jossa sama erä voi käydä prosessin aikana samalla asemalla useita kertoja.

### Tehtävä- ja siirtoajat asemille 301, 302 ja 303

**Huom!** Kaikki erilaiset siirrot ja niiden ajat tulee määritellä etukäteen (kaikki mahdolliset asemien väliset siirrot), jotta erilaiset käsittelyohjelmat ja asemavalinnat ovat mahdollisia. Siirtymäajat on laskettava etukäteen. Jos optimointi kohtaa puuttuvan siirtymäajan, siitä annetaan virheilmoitus ja simulointi keskeytyy.
## Useamman nostimen huomioita (tulevaa laajennusta varten)
Jos optimointiin lisätään useampi nostin, tärkein rajoite on, että nostimet eivät saa toimia liian lähellä toisiaan eivätkä toistensa "väärällä puolella". Tiedostoon `transporters_start_positions.csv` (tai vastaavaan) lisätään kenttä `Avoid_limit`, joka kuvaa x-suunnassa minimietäisyyttä, jonka lähemmäs nostimet voivat toisiaan mennä. Useamman nostimen optimointi on huomattavasti haastavampaa, eikä sitä toteuteta tässä vaiheessa.

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

### Kuvaus
Tässä esimerkkitapauksessa on yksi nostin ja kolme asemaa. Erän 1 käsittelyohjelma sisältää kolme vaihetta, jotka tulee suorittaa annetussa järjestyksessä. Optimoinnin tavoitteena on löytää nostimelle ajallisesti optimaalisin reitti, joka minimoi kokonaisajan (makespan) noudattaen kaikkia sääntöjä ja rajoitteita.

### Esimerkki nostimen tehtävistä

1. **301 → 302**: 00:00:00 → 00:00:38  
   - **Lift Time**: 17 s  
   - **Transfer Time**: 5 s  
   - **Sink Time**: 16 s  

2. **302 → 303**: 00:10:38 → 00:11:16  
   - **Käsittelyaika (302)**: 10 min  
   - **Lift Time**: 17 s  
   - **Transfer Time**: 5 s  
   - **Sink Time**: 16 s  

Nämä tehtävät perustuvat käsittelyohjelman vaiheisiin ja siirto- sekä käsittelyaikoihin.

