# CP-SAT Optimoinnin vaatimukset ja tavoitteet

## 🎯 TAVOITE

**Minimoi KOKONAISLÄPIMENOAIKA** - kaikki erät valmiiksi mahdollisimman nopeasti

- Kokonaisläpimenoaika = viimeisen erän valmistuminen - ensimmäisen erän aloitus
- Ei turhia odotuksia erien välillä
- Nostin käytössä jatkuvasti (ei tyhjänä seisomista)

---

## 🔒 RAJOITTEET

### 1. Käsittelyohjelman järjestys säilyy
- Jokainen erä kulkee vaiheittain: Stage 1 → 2 → 3 → ... → 8
- Vaihe N+1 ei voi alkaa ennen kuin vaihe N on valmis

### 2. Käsittelyajat rajoissa
- CalcTime (käsittelyaika) välillä **[MinTime, MaxTime]** jokaisella vaiheella
- Esim. Stage 1: CalcTime ∈ [00:10:00, 00:12:00]

### 3. Asemarajoitteet
- Yhdellä asemalla voi olla vain **yksi erä kerrallaan**
- Asema on varattu kun nostin saapuu kunnes erä on **VIETY POIS** (ei vain nostin lähtee)
- Koska erä pitää nostaa kokonaan pois ennen kuin seuraava voidaan tuoda:
  - Asema vapautuu vasta kun erä on **laskettu seuraavan askeleen asemalle**
  - Varaustila: [Nostin saapuu, Seuraava Sink valmis]
  - Käytännössä: Asema X varattu kunnes erä on asemalla X+1

### 4. Nostinrajoitteet
- Nostin voi olla vain **yhdessä paikassa kerrallaan**
- Nostimen tehtävä on atominen: Sink → CalcTime → Lift
- Tyhjä siirtymä: Jos nostin on asemalla A ja seuraava tehtävä alkaa asemalta B,
  nostimen pitää ehtiä siirtyä: `A.end + transfer(A→B) ≤ B.start`

### 5. Fysiikan mukaiset siirtoajat
- Kaikki siirtoajat, nostoajat, laskuajat lasketaan fysiikan mukaan
- Funktiot: `calculate_lift_time()`, `calculate_sink_time()`, `calculate_physics_transfer_time()`
- Nämä ovat **kiinteitä** - ei optimoitavia

---

## 🔓 VAPAUDET (Optimoitavat muuttujat)

### 1. Tuotantojärjestys voi vaihtua
- Alkuperäinen: [1, 2, 3]
- CP-SAT voi valita parhaan järjestyksen: esim. [3, 2, 1]

### 2. Erien aloitusajat voivat muuttua
- Erät voivat alkaa **eri aikoina** (ei pakko aloittaa yhtäaikaa)
- **HUOM:** Ensimmäisen erän pitäisi alkaa heti (time=0) turhan odotuksen välttämiseksi

### 3. CalcTime vapaasti välillä [MinTime, MaxTime]
- CP-SAT valitsee **optimaalisen** CalcTime:n jokaiselle vaiheelle
- Esim. Stage 1: CalcTime = 00:10:06 (välillä 00:10:00 - 00:12:00)

### 4. Ryhmä-asemat käytettävissä
- Jos `MinStat = 305, MaxStat = 306` (sama Group), CP-SAT voi valita kumman tahansa
- Optimoi asemien käyttöä päällekkäisyyksien välttämiseksi

---

## 📤 LOPPUTULOS

### 1. `production.csv` (initialization/)
Päivitetään seuraavat kentät:
- **Start_optimized** (HH:MM:SS) - optimoitu lähtöaika
- **Start_time_seconds** (float) - sama sekunneissa

### 2. `Batch_XXX_Treatment_program_YYY.csv` (optimized_programs/)
Luodaan eräkohtaiset käsittelyohjelmat:
- **CalcTime** (HH:MM:SS) - optimoitu käsittelyaika kullekin vaiheelle

### 3. CalcTime laskenta
**CalcTime lasketaan CP-SAT:n sisäisestä aikataulusta:**

```
CalcTime = Lift_time - Sink_time
```

Missä:
- **Sink_time** = aika kun nostin on laskenut erän asemalle (Sink valmis)
- **Lift_time** = aika kun nostin alkaa nostaa erää pois (Lift alkaa)
- **CalcTime** = aika joka erä viettää asemalla käsittelyssä

**HUOM:** CalcTime on **johdettu** arvo, ei suoraan optimoitu!

CP-SAT optimoi:
1. Tehtävien start- ja end-ajat
2. `duration = sink_time + calc_time_var + lift_time`
3. Sitten: `CalcTime = duration - sink_time - lift_time`

---

## ⚠️ HUOMIOT

### Nykyinen ongelma
CP-SAT minimoi **makespan** (viimeinen tehtävä valmis), mutta ei vaadi että erät alkavat heti.

**Tulos:** Erät voivat odottaa turhaan:
- Erä 3: alkaa 00:00:00
- Erä 2: alkaa 00:19:54 (20 min odotus!)
- Erä 1: alkaa 00:40:38 (40 min odotus!)


### Ehdotettu korjaus
Pakota **optimoidun järjestyksen ensimmäinen erä** alkamaan heti (ajassa nolla):
```python
# Löydä erä, jonka Stage 0 alkaa ensimmäisenä (eli pienin Stage 0 start optimoidussa järjestyksessä)
model.Add(min_batch_stage0_start == 0)
```

**Huom:** Tämä ei välttämättä tarkoita pienintä eränumeroa, vaan sitä erää, joka optimoidussa järjestyksessä alkaa ensimmäisenä. Näin CP-SAT lomittaa erät mahdollisimman tiukasti ilman turhia odotuksia.

---

## 📊 ESIMERKKITULOS (tavoite)

```
Erä 3: 0s → 5121s      (85 min)
Erä 2: alkaa kun nostin vapaa → päättyy
Erä 1: alkaa kun nostin vapaa → päättyy

Kokonaisläpimenoaika: ~5200-6000s (optimaalinen lomitus)
```

Ei näin:
```
Erä 3: 0s → 5121s
Erä 2: 1194s (ODOTTAA 20 MIN!) → 6639s
Erä 1: 2438s (ODOTTAA 40 MIN!) → 7601s

Kokonaisläpimenoaika: 7601s (turhia odotuksia!)
```
