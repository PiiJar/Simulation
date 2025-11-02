# CP-SAT Vaihe 2 — Tavoite- ja tuloslähtöinen määrittely (nostinoptimointi)

Tämä dokumentti määrittelee Vaiheen 2 niin, että tavoitteet ja toivotut tulokset ohjaavat vaatimuksia. Määrittely on ristiriidaton, tiivis ja suoraan toteutettavissa.

## Yhdellä silmäyksellä (selkokielinen yhteenveto)
- Mitä Vaihe 1:stä käytetään: erien lähtöjärjestys (vain Stage 1 -ankkuri), sekä sitovat asemavalinnat (myös rinnakkaisista) ja nostinvalinnat.
- Mitä Vaihe 2 tekee: laskee lopulliset ajat realistisilla siirtoajoilla (TotalTaskTime), ketjuttaa nostinten tehtävät ilman päällekkäisyyksiä ja lisää väliin nostimen siirtymät (deadhead). Asemien käsittelyajat ovat sallituissa rajoissa [Min, Max], ja tarvittaessa käytetään Stage 0 -odotusta.
- Mitä ei tehdä: ei muuteta Vaihe 1:n valitsemia asemia eikä nostimia; ei lisätä keinotekoisia rajoitteita eri asemien välillä; ei pidetä erien globaalia järjestystä väkisin myöhemmissä vaiheissa.

## Mitä pysyy muuttumattomana (ihmislukijalle)
- Vaihe 1:n valitsema asema jokaiselle vaiheelle (ml. rinnakkaisista) säilyy.
- Vaihe 1:n valitsema nostin jokaiselle siirrolle säilyy.
- Vaihe 1:n erien järjestys säilyy vain Stage 1 -sisääntulossa (A ennen B:tä → A aloittaa Stage 1:n ennen B:tä tai yhtä aikaa). Myöhemmissä vaiheissa ohi meneminen on sallittua luonnollisten kestoerojen takia.
- Kunkin erän käsittelyohjelman vaihejärjestys (1,2,…,n) säilyy.

## Mitä Vaihe 2 päättää (ihmislukijalle)
- Lopulliset Entry/Exit-ajat kullekin vaiheelle realististen siirtojen perusteella.
- Joustot: ensin Stage 0 -odotus, sen jälkeen asemakäsittelyaikojen venytys CalcTime ∈ [MinTime, MaxTime] mahdollisimman vähän.
- Nostinten tehtävien ketjutus: ei päällekkäisyyksiä samalla nostimella; tehtävien väliin lisätään deadhead-siirtymä.
- Asemien säännöt: sama asema eri erille vaatii vähintään change_time -välin; eri asemien välillä ei lisätä keinotekoista rajoitetta.

## Säännöt ilman symboleja
- Erien järjestys: vain Stage 1 -ankkuri. Jos A on ennen B:tä Vaiheessa 1, A saa aloittaa Stage 1:n ennen B:tä (tai yhtä aikaa). Myöhemmissä vaiheissa järjestys voi vaihtua luonnollisten kestoerojen takia.
- Vaihejärjestys: erän vaiheet tehdään ohjelman mukaisessa järjestyksessä; seuraava vaihe alkaa vasta kun siirto on päättynyt ja edellinen vaihe on valmis.
- Nostimet: sama nostin tekee yhtä tehtävää kerrallaan; tehtävien väliin lisätään nostimen siirtymä (deadhead), jotta seuraava tehtävä alkaa vasta kun nostin ehtii paikalle.
- Toiminta-alue: nostin voi palvella vain oman alueensa asemia.
- Asemien vaihtoväli: kun kaksi eri erää varaa saman aseman peräkkäin, varausten väliin jätetään vähintään change_time.

## 1) Tavoitteet (priorisoitu)
- Ensisijainen: Tuottaa toteuttamiskelpoinen nostinajo, joka minimoi tuotantolinjan valmistumisajan (makespan), käyttäen realistisia siirtoaikoja ja nostimien kapasiteettia/toiminta-alueita.
- Toissijainen: Säilyttää Vaihe 1:ssä valitut päätökset (asema per vaihe, erien järjestys, valittu nostin jos annettu) ja estää nostinpäällekkäisyydet; minimoida tyhjäsiirrot (deadhead).
- Kolmas: Poikkea Vaihe 1:n ajoista vain tarvittaessa. Jos muutoksia tarvitaan, toteuta ne ensisijaisesti odottamalla Stage 0:ssa; sen jälkeen venytä asemien käsittelyaikoja CalcTime ∈ [MinTime, MaxTime] mahdollisimman vähän.

Huom: Vaihe 2 on ensisijaisesti “reschedule realistisilla siirroilla” –malli. Erillinen “pelkkä verifiointi ilman ajansiirtoja” voidaan toteuttaa laajennuksena (ks. Liite A), mutta ei ole oletusmoodi.

## 2) Toivotut tulokset (deliverables)
- Tulosteet on koottu lukuun 9 (Tulosteet). Tämä luku kuvaa vain lyhyesti, mitä tuotetaan: hoist-aikataulu, mahdolliset konfliktit, visualisointi ja loki sekä pysyvät päivitykset. Yksityiskohdat (tiedostonimet ja polut): ks. luku 9.

Kaikki välitulokset talletetaan ajon snapshot-kansioon `output/{timestamp}/cp_sat/` projektikäytännön mukaisesti; pysyvät päivitykset tehdään tämän jälkeen (ks. luku 9).

## 3) Menestyskriteerit (acceptance)
- Feasibility: ei nostinpäällekkäisyyksiä; reposition (deadhead) huomioitu; nostimet pysyvät toiminta-alueellaan
- Prosessirajoitteet: Vaihe 1:n asemapäätökset ja erien järjestys säilyvät; saman aseman varaukset täyttävät change_time-rajan myös uusilla ajoilla
- Ajoitukset: siirrot käyttävät täsmällistä TotalTaskTime(From,To,Transporter); jokaisen vaiheen Entry/Exit voidaan laskea johdonmukaisesti
- Tavoitteet: ks. luku 1 (priorisoitu tavoitejärjestys); validoinnissa raportoidaan lopullinen makespan, deadhead-summa ja CalcTime-venytys

## 4) Rajaukset ja oletukset
- Asemat ja järjestys: Vaihe 1:n valinta pysyy muuttumattomana (ei asemanvaihtoja eikä erien ohituksia), ml. rinnakkaisista asemista tehty valinta.
- Nostin: nostin valitaan Vaiheessa 1 ja valinta on sitova Vaiheessa 2 (binding).
- Siirtoajat: käytetään taulukosta `cp_sat_transfer_tasks.csv` (transporter-kohtaiset arvot, jos saatavilla). Aikayksikkö sekunneissa.
- Deadhead: käytä pelkkää siirtymäaikaa (TransferTime-only). Jos siirtymäparia ei löydy, käytä etäisyys–nopeus -arviota (konfiguroitava). Tämä on dokumentin ainoa deadhead-sääntö.
- Snapshot-polku: `output/{YYYY-MM-DD_HH-MM}/cp_sat/` (rakennetaan os.path.join:lla, ei kovakoodata)

## 5) Data-sopimukset (syötteet)
1) `cp_sat_batch_schedule.csv`
   - Sarakkeet: Transporter, Batch, Treatment_program, Stage, Station, EntryTime, ExitTime
   - Semantiikka: “erä asemalla” -varaus [EntryTime, ExitTime]. Entry/Exit ovat Vaihe 1:n suunnitelma (EntryTime_target/ExitTime_target).
2) `cp_sat_transfer_tasks.csv`
   - Sarakkeet: Transporter, From_Station, To_Station, LiftTime, TransferTime, SinkTime, TotalTaskTime
   - Jos Transporter puuttuu → käytä yleisiä arvoja kaikille nostimille.
3) `cp_sat_stations.csv` ja `cp_sat_transporters.csv`
   - Asemien X-koordinaatit/ryhmät; nostimien min_x, max_x
4) CalcTime-min/max per vaihe (lähde: ohjelmataulut)
   - Tarvitaan, jos asemakäsittelyaikaa venytetään ∈ [MinTime, MaxTime]

## 6) Johdetut siirtotehtävät
Muodosta siirtotehtävä jokaisesta peräkkäisestä vaiheparista k → k+1 (ml. Stage 0 → 1):
- From = Station(k), To = Station(k+1)
- Transporter = Vaihe 1:stä (jos binding) muuten päätetään Vaiheessa 2
- Kesto: TotalTaskTime(From,To,Transporter)
- Aikavaatimus: tehtävä päättyy hetkeen, jolloin erä saapuu seuraavan vaiheen asemalle

## 7) Ajoituksen laskenta (reschedule-periaate)
Koska Vaihe 1 käytti siirroissa keskiarvoa, Vaihe 2 laskee ajoitukset uudelleen täsmällisillä siirroilla:
- EntryTime_target(b,s): Vaihe 1:n suunniteltu sisääntulo; käytetään vertailuun
- EntryTime_2(b,s): Vaihe 2:n laskema sisääntulo = TaskEnd(b, s-1→s)
- ExitTime_2(b,s) = EntryTime_2(b,s) + CalcTime(b,s), missä CalcTime(b,s) ∈ [MinTime, MaxTime]
- Konfliktien purkujärjestys:
  1) Siirrä ensisijaisesti Stage 0 ExitTimea (odotus Stage 0:ssa)
   2) Tarvittaessa venytä CalcTime kohti MaxTimea (minimoi poikkeama MinTimeen)

## 8) Optimointimalli
Muuttujat:
- Jos nostin ei ole binding: binääriset valinnat tehtävälle (yksi nostin/tehtävä) (ei käytössä tässä versiossa; ks. luku 4, jossa nostin on sitova)
- Tehtävien aloitus/päättymisajat per nostin (TaskStart, TaskEnd)
- CalcTime(b,s) ∈ [MinTime, MaxTime]

Rajoitteet:
- Hoist-kapasiteetti: tehtävät eivät mene päällekkäin samalla nostimella; peräkkäisten väliin deadhead(Prev.To, Next.From)
- Toiminta-alue: min_x ≤ X(From), X(To) ≤ max_x valitulla nostimella
- Sekvenssi: EntryTime_2(b,s+1) = TaskEnd(b, s→s+1)
- Asema (sama asema): disjunktio, jossa varausvälin väli ≥ change_time (kuten Vaihe 1)
- Asema (eri asemat): ei keinotekoista disjunktiota
- Ei-yliohitus (Vaihe 1:n järjestys): jos b1 ≺ b2 Vaiheessa 1, niin EntryTime_2(b1, 1) ≤ EntryTime_2(b2, 1). (Tarvittaessa voidaan konfiguroida vahvempi muoto kaikille vaiheille s.)

Tavoite (leksikografinen):
1) Minimize makespan = max_b ExitTime_2(b, last_stage)
2) Minimize deadhead-summa
3) Minimize Σ(b,s) (CalcTime(b,s) − MinTime(b,s))

## 9) Tulosteet (snapshot ja pysyvät)
Snapshot `output/{timestamp}/cp_sat/`:
- `cp_sat_hoist_schedule.csv`: Transporter, Batch, From_Station, To_Station, TaskStart, TaskEnd, Duration, EntryTime_2(To)
- `cp_sat_hoist_conflicts.csv` (jos tarpeen)
- Visualisointi + loki
## Sanasto (selkokielinen)
- Entry (sisääntulo): hetki, jolloin erä saapuu asemalle.
- Exit (ulos): hetki, jolloin erän käsittely asemalla päättyy.
- Stage 0 -odotus: mahdollinen lähtöä edeltävä odotus, jota käytetään joustona ennen venytyksiä.
- Deadhead: nostimen tyhjä siirtymä kahden tehtävän välillä (ilman nostoja/uppoja); tässä dokumentissa deadhead = TransferTime-only.
- change_time: pakollinen vähimmäisväli kahden eri erän peräkkäisille varauksille samalla asemalla.
- CalcTime: aseman käsittelyaika erälle; Vaihe 2 voi venyttää tätä arvoa vaiheittain rajojen puitteissa, eli CalcTime ∈ [MinTime, MaxTime] (rajat tulevat ohjelmatauluista).


Pysyvät päivitykset ajon valmistuttua:
- `initialization/production.csv`: `Start_optimized` = Stage 0 ExitTime (hh:mm:ss)
- `cp_sat/treatment_program_optimized/treatment_program_{batch_id}.csv`: `CalcTime` = ExitTime_2 − EntryTime_2 (hh:mm:ss), Stage > 0

## 10) Prosessi (korkean tason)
1) Lue Vaihe 1 snapshotista `cp_sat_batch_schedule.csv` ja muut syötteet
2) Johda siirtotehtävät ja niiden kestot
3) Rakenna CP-SAT-malli (muuttujat, rajoitteet, tavoite)
4) Ratkaise; jos infeasible → tulosta `cp_sat_hoist_conflicts.csv` ja lopeta (ei pysyviä päivityksiä)
5) Tallenna snapshot-tulokset ja visualisointi (ks. luku 9)
6) Päivitä pysyvät tietolähteet (ks. luku 9)

## 11) Validointi
- Ei päällekkäisiä tehtäviä per nostin; deadhead huomioitu
- Toiminta-alue- ja asemarajoitteet täyttyvät (change_time)
- Identtisten erien järjestys säilyy (Stage 0 ja 1)
- Aikamuunnokset (hh:mm:ss) oikein; polut noudattavat projektikäytäntöä
- Tavoitearvot raportoidaan (makespan, deadhead-summa, venytysten summa)

## 12) Yhteensopivuus Vaiheen 1 kanssa
- Vaihe 1:n asemavalinnat säilyvät; erien lähtöjärjestys säilyy Stage 1 -ankkurina (ks. luku 8)
- Ajoitukset voivat muuttua (EntryTime_2/ExitTime_2) täsmällisten siirtojen ja sääntöjen mukaisesti
- Asemarajoitteet ja change_time: ks. luku 8 (rajoitteet)

---

### Liite A: Verifiointimoodi (valinnainen)
Jos halutaan vain todentaa Vaihe 1:n EntryTime_target -ajoitukset nostimille muuttamatta aikoja:
- Kiinnitä TaskEnd == EntryTime_target(To)
- Salli vain nostinvalinta ja tehtäväjärjestys (ei CalcTime- eikä Entry/Exit-muutoksia)
- Jos infeasible → raportoi konfliktit ja tarvittavat vähimmäisviiveet, mutta älä kirjoita pysyviä päivityksiä