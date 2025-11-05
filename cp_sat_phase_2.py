"""
CP-SAT Optimoinnin vaihe 2: Transporter- ja aikatauluoptimointi

Vaatimusdokumentin REKQUIREMENTS_FOR_CPSAT_2 mukainen toteutusrunko:
- Syöte: Vaiheen 1 snapshot (cp_sat_batch_schedule.csv) + siirtoajat + alkuperäiset ohjelmat (Min/Max)
- Päätökset: Transporterin tehtäväjärjestys, Stage 0 -odotus, CalcTime ∈ [MinTime, MaxTime]
- Rajoitteet: ei päällekkäisiä tehtäviä per transporter (deadhead huomioiden), aseman vaihto (change_time), Stage 1 -järjestys identtisille erille
- Tavoite: Leksikografinen (approx.): makespan → CalcTime venytys; deadhead huomioitu rajoitteena (voi lisätä 2. prioriteetiksi myöhemmin)
- Tulosteet: cp_sat_hoist_schedule.csv, (infeasible: cp_sat_hoist_conflicts.csv), production.csv Start_optimized, cp_sat/treatment_program_optimized/* CalcTime
"""

import os
from typing import Dict, Tuple, List
import pandas as pd
from ortools.sat.python import cp_model

# Valinnainen logger, jos käytettävissä
try:
    from simulation_logger import get_logger
except Exception:
    def get_logger():
        return None

# ---------- Apurit ----------

def _hms(seconds: int) -> str:
    seconds = max(0, int(round(seconds)))
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def _ensure_dirs(*paths: str) -> None:
    for p in paths:
        os.makedirs(p, exist_ok=True)


def _calculate_change_time(transfer_df: pd.DataFrame) -> int:
    # Sama sääntö kuin vaiheessa 1: change_time = 2 * average_task_time
    avg = int(round(float(transfer_df["TotalTaskTime"].mean())))
    return 2 * avg


# ---------- Datan luku ----------

def _load_phase1_snapshot(output_dir: str):
    cp_dir = os.path.join(output_dir, "cp_sat")
    batch_sched = pd.read_csv(os.path.join(cp_dir, "cp_sat_batch_schedule.csv"))
    transfers = pd.read_csv(os.path.join(cp_dir, "cp_sat_transfer_tasks.csv"))
    batches = pd.read_csv(os.path.join(cp_dir, "cp_sat_batches.csv"))
    stations = pd.read_csv(os.path.join(cp_dir, "cp_sat_stations.csv"))
    transporters = pd.read_csv(os.path.join(cp_dir, "cp_sat_transporters.csv"))

    # Lue batch-kohtaiset ohjelmat (Min/Max) → sekunneiksi helpompaa mallinnusta varten
    treatment_programs: Dict[int, pd.DataFrame] = {}
    for _, row in batches.iterrows():
        b = int(row["Batch"])
        f = os.path.join(cp_dir, f"cp_sat_treatment_program_{b}.csv")
        if not os.path.exists(f):
            raise FileNotFoundError(f"Puuttuu ohjelmatiedosto: {f}")
        df = pd.read_csv(f)
        # Aikakentät sekunneiksi, säilytä myös alkuperäinen merkkijono myöhempää tallennusta varten
        df["MinTime_sec"] = pd.to_timedelta(df["MinTime"]).dt.total_seconds().astype(int)
        df["MaxTime_sec"] = pd.to_timedelta(df["MaxTime"]).dt.total_seconds().astype(int)
        treatment_programs[b] = df

    # Tyypit ja normalisointi
    for c in ("Transporter", "Batch", "Stage", "Station"):
        if c in batch_sched.columns:
            batch_sched[c] = batch_sched[c].astype(int)
    for c in ("Transporter", "From_Station", "To_Station"):
        if c in transfers.columns:
            transfers[c] = transfers[c].astype(int)

    # Luo apumappi siirtoajoille: (t, from, to) -> (TotalTaskTime, TransferTime)
    key = ["Transporter", "From_Station", "To_Station"]
    transfers_map: Dict[Tuple[int, int, int], Tuple[int, int]] = {}
    for _, r in transfers.iterrows():
        tt = int(round(float(r.get("TotalTaskTime", 0))))
        dh = int(round(float(r.get("TransferTime", 0))))
        t = int(r["Transporter"])
        a = int(r["From_Station"])  # lift station
        b = int(r["To_Station"])    # sink station
        # Etukäteis-siirto (kuorman kanssa): a -> b
        transfers_map[(t, a, b)] = (tt, dh)
        # Deadhead (tyhjänä) tarvitsee myös b -> a siirtoajan; käytä samaa vaakasuoran siirron kestoa
        # Huom: (TotalTaskTime) ei ole merkityksellinen deadheadille, mutta säilytetään tt sellaisenaan,
        # sillä validointilogiikka käyttää vain dh-osaa.
        if (t, b, a) not in transfers_map:
            transfers_map[(t, b, a)] = (tt, dh)

    # Luo apumappi asemien X-koordinaateille (tarvittaessa)
    # Käytä kelluvia arvoja ilman karkeaa pyöristystä, jotta lähiarviot ovat täsmällisempiä
    stations_pos = stations.set_index("Number")["X Position"].astype(float).to_dict()

    return batch_sched, transfers, transfers_map, batches, treatment_programs, stations_pos, transporters


# ---------- Optimointiluokka ----------

class CpSatPhase2Optimizer:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        (
            self.batch_sched,
            self.transfers_df,
            self.transfers_map,
            self.batches_df,
            self.programs,
            self.station_positions,
            self.transporters_df,
        ) = _load_phase1_snapshot(output_dir)

        self.change_time = _calculate_change_time(self.transfers_df)
        # Lataa maksimiaikaikkunat ja johda eräkohtaiset ikkunat (vaihe 1 entryjen pohjalta)
        self.max_window_by_prog = self._load_max_windows()
        # Liukuva (alku=0) informatiiviseksi; ankkuroidut ikkunat karsintaan
        self.batch_windows = self._compute_batch_windows()  # sliding/informative
        self.batch_windows_anchored = self._compute_anchored_windows()  # käytetään karsintaan
        self.batch_windows_phase1 = self._compute_phase1_with_margin_windows()  # Vaihe 1 runkoon ankkuroitu
        self.stage_windows_phase1 = self._compute_stage_windows_with_margin()  # Stage-tason ikkunat karsintaan
        # Transporter-tehtävien (s-1 -> s) aikarungot Vaihe 1:stä + marginaali turvalliseen karsintaan
        self.transporter_windows_phase1 = self._compute_transporter_windows_with_margin()

        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()

        # Muuttujat
        self.stage0_exit: Dict[int, cp_model.IntVar] = {}
        self.entry: Dict[Tuple[int, int], cp_model.IntVar] = {}
        self.exit: Dict[Tuple[int, int], cp_model.IntVar] = {}
        self.calc: Dict[Tuple[int, int], cp_model.IntVar] = {}

        # Transporter-tehtävät (siirrot): s>0 varten, myös s=1 (Start_station -> Station_1)
        self.transporter_starts: Dict[Tuple[int, int], cp_model.IntVar] = {}
        self.transporter_ends: Dict[Tuple[int, int], cp_model.IntVar] = {}
        self.transporter_durations: Dict[Tuple[int, int], int] = {}
        self.transporter_by_task: Dict[Tuple[int, int], int] = {}
        self.transporter_from_to: Dict[Tuple[int, int], Tuple[int, int]] = {}

    def _load_max_windows(self) -> Dict[int, int]:
        """Lue cp_sat_maximum_process_time.csv ja palauta mappi: Treatment_program -> TotalMaxWindow (sek)."""
        cp_dir = os.path.join(self.output_dir, "cp_sat")
        path = os.path.join(cp_dir, "cp_sat_maximum_process_time.csv")
        res: Dict[int, int] = {}
        try:
            if os.path.exists(path):
                df = pd.read_csv(path)
                # Ota maksimi per ohjelma siltä varalta, että rivejä on useampi
                for prog, grp in df.groupby("Treatment_program"):
                    try:
                        p = int(prog)
                        mx = int(pd.to_numeric(grp["TotalMaxWindow"], errors="coerce").fillna(0).max())
                        if mx > 0:
                            res[p] = mx
                    except Exception:
                        continue
        except Exception:
            pass
        return res

    def _compute_batch_windows(self) -> Dict[int, Tuple[int, int]]:
        """Palauta eräkohtaiset aikaikkunat.

        Oletus: liukuva ikkuna per erä ilman ankkurointia (alku=0), pituus = TotalMaxWindow(program).
        Tämä on konservatiivinen (ikkunat lähes aina leikkaavat), joten se ei väärin poista rajoitteita.

        Jos ympäristömuuttuja CPSAT_PHASE2_ANCHOR_STAGE1=1, käytä Vaihe 1 Stage 1 EntryTime -ankkurointia:
          [Stage1_EntryTime, Stage1_EntryTime + TotalMaxWindow(program)].

        Jos ohjelmakohtainen maksimi puuttuu, käytä 48h fallbackia.
        """
        windows: Dict[int, Tuple[int, int]] = {}
        use_anchor = os.getenv("CPSAT_PHASE2_ANCHOR_STAGE1", "0") in ("1", "true", "True")
        s1_map: Dict[int, int] = {}
        if use_anchor:
            # Etsi Stage 1 EntryTime per erä Vaihe 1 snapshotista
            stage1 = self.batch_sched[self.batch_sched["Stage"] == 1].copy()
            if not stage1.empty and "EntryTime" in stage1.columns:
                for _, r in stage1.iterrows():
                    try:
                        s1_map[int(r["Batch"])] = int(r["EntryTime"]) 
                    except Exception:
                        continue

        # Luo ikkunat
        for _, b in self.batches_df.iterrows():
            b_id = int(b["Batch"]) 
            prog = int(b["Treatment_program"]) if "Treatment_program" in b else None
            total = int(self.max_window_by_prog.get(prog, 48*3600))
            if use_anchor:
                start = int(s1_map.get(b_id, 0))
            else:
                start = 0  # liukuva (ankkuroimaton) alku
            windows[b_id] = (start, start + total)
        return windows

    def _compute_anchored_windows(self) -> Dict[int, Tuple[int, int]]:
        """Anchoroidut aikaikkunat karsintaa varten: Stage1_EntryTime .. + TotalMaxWindow.

        Näitä käytetään vain rajoitteiden parikarsintaan, ei kovina rajoina.
        Jos Stage1 EntryTime puuttuu, käytetään [0, 48h] fallbackia.
        """
        windows: Dict[int, Tuple[int, int]] = {}
        # Stage 1 EntryTime per erä
        stage1 = self.batch_sched[self.batch_sched["Stage"] == 1].copy()
        s1_map: Dict[int, int] = {}
        if not stage1.empty and "EntryTime" in stage1.columns:
            for _, r in stage1.iterrows():
                try:
                    s1_map[int(r["Batch"])] = int(r["EntryTime"]) 
                except Exception:
                    continue
        for _, b in self.batches_df.iterrows():
            b_id = int(b["Batch"]) 
            prog = int(b.get("Treatment_program", 0)) if "Treatment_program" in b else 0
            total = int(self.max_window_by_prog.get(prog, 48*3600))
            start = int(s1_map.get(b_id, 0))
            windows[b_id] = (start, start + total)
        return windows

    def _compute_phase1_with_margin_windows(self) -> Dict[int, Tuple[int, int]]:
        """Rakenna eräkohtaiset ikkunat Vaiheen 1 toteutuneesta snapshotista + marginaali.

        Ikkuna(b) = [Entry_phase1(b,1) - M, Exit_phase1(b,last) + M], rajoitettu [0, 48h].
        M luetaan ympäristöstä CPSAT_PHASE2_WINDOW_MARGIN_SEC (oletus 600 sek).
        Jos data puuttuu, fallback ankkuroidun laskentaan tai [0,48h].
        """
        try:
            margin = int(float(os.getenv("CPSAT_PHASE2_WINDOW_MARGIN_SEC", "600")))
        except Exception:
            margin = 600
        margin = max(0, margin)

        # Hae entry ja exit Vaihe 1:stä
        s1 = self.batch_sched[self.batch_sched["Stage"] == 1].copy()
        last_per_b = self.batch_sched.groupby("Batch")["Stage"].max().to_dict()
        exit_map: Dict[int, int] = {}
        if "ExitTime" in self.batch_sched.columns:
            for b, last_s in last_per_b.items():
                try:
                    row = self.batch_sched[(self.batch_sched["Batch"] == b) & (self.batch_sched["Stage"] == last_s)].iloc[0]
                    exit_map[int(b)] = int(row["ExitTime"])
                except Exception:
                    continue
        entry_map: Dict[int, int] = {}
        if not s1.empty and "EntryTime" in s1.columns:
            for _, r in s1.iterrows():
                try:
                    entry_map[int(r["Batch"])] = int(r["EntryTime"]) 
                except Exception:
                    continue

        windows: Dict[int, Tuple[int, int]] = {}
        for _, b in self.batches_df.iterrows():
            b_id = int(b["Batch"])
            start = int(entry_map.get(b_id, 0)) - margin
            end = int(exit_map.get(b_id, 48*3600)) + margin
            start = max(0, start)
            end = min(48*3600, max(start + 1, end))
            windows[b_id] = (start, end)
        return windows

    def _compute_stage_windows_with_margin(self) -> Dict[Tuple[int, int], Tuple[int, int]]:
        """Stage-tason ikkunat Vaiheen 1 snapshotista + marginaali.

        Window(b,s) = [Entry_phase1(b,s) - m, Exit_phase1(b,s) + m]
        m = CPSAT_PHASE2_WINDOW_STAGE_MARGIN_SEC (oletus 300s).
        """
        try:
            m = int(float(os.getenv("CPSAT_PHASE2_WINDOW_STAGE_MARGIN_SEC", "300")))
        except Exception:
            m = 300
        m = max(0, m)
        win: Dict[Tuple[int, int], Tuple[int, int]] = {}
        if not self.batch_sched.empty and "EntryTime" in self.batch_sched.columns and "ExitTime" in self.batch_sched.columns:
            for _, r in self.batch_sched.iterrows():
                try:
                    b = int(r["Batch"]); s = int(r["Stage"])
                    if s <= 0:
                        continue
                    e = int(r["EntryTime"]); x = int(r["ExitTime"])
                    a = max(0, e - m)
                    bnd = min(48*3600, max(a+1, x + m))
                    win[(b, s)] = (a, bnd)
                except Exception:
                    continue
        return win

    def _windows_overlap(self, b1: int, b2: int) -> bool:
        """Tarkista erien aikaikkunoiden leikkaus karsintaa varten.

        Käytetään oletuksena Vaiheen 1 runkoon ankkuroitu ikkuna marginaalilla,
        jotta vältetään O(N^2) turhat parit ja parannetaan suorituskykyä.

        Ympäristömuuttuja CPSAT_PHASE2_OVERLAP_MODE voi olla: phase1_with_margin (oletus) | anchored | sliding.
        """
        mode = os.getenv("CPSAT_PHASE2_OVERLAP_MODE", "phase1_with_margin").lower()
        if mode == "sliding":
            source = self.batch_windows
        elif mode == "anchored":
            source = self.batch_windows_anchored
        else:  # phase1_with_margin
            source = self.batch_windows_phase1
        w1 = source.get(int(b1))
        w2 = source.get(int(b2))
        if not w1 or not w2:
            return True  # varmuuden vuoksi älä karsi jos puuttuu
        a1, b1e = w1
        a2, b2e = w2
        return (a1 < b2e) and (a2 < b1e)

    def _stage_windows_overlap(self, b1: int, s1: int, b2: int, s2: int) -> bool:
        """Tarkista kahden stage-tehtävän aikaikkunoiden leikkaus.

        Käytä ensisijaisesti Vaihe 1 stage-ikkunoita marginaalilla; jos puuttuu, pudota eräikkunaan.
        """
        a = self.stage_windows_phase1.get((int(b1), int(s1)))
        b = self.stage_windows_phase1.get((int(b2), int(s2)))
        if a and b:
            a1, a2 = a; b1e, b2e = b
            return (a1 < b2e) and (b1e < a2)
        # Fallback eräikkunaan
        return self._windows_overlap(b1, b2)

    def _compute_transporter_windows_with_margin(self) -> Dict[Tuple[int, int], Tuple[int, int]]:
        """Johda transporter-tehtävien ikkunat Vaiheen 1 snapshotista + marginaali.

        TransWindow(b,s) = [PrevExit_phase1(b,s) - m, Entry_phase1(b,s) + m],
        missä PrevExit_phase1(b,1) = Stage0Exit(b) Vaihe 1 -aikataulusta.

        m = CPSAT_PHASE2_TRANSPORTER_SAFE_MARGIN_SEC (oletus 600s).
        """
        try:
            m = int(float(os.getenv("CPSAT_PHASE2_TRANSPORTER_SAFE_MARGIN_SEC", "600")))
        except Exception:
            m = 600
        m = max(0, m)

        # Rakenna apukartat Vaiheen 1 aikataulusta
        stage_map: Dict[Tuple[int, int], Tuple[int, int]] = {}
        # (b,s) -> (Entry, Exit)
        if not self.batch_sched.empty and "EntryTime" in self.batch_sched.columns and "ExitTime" in self.batch_sched.columns:
            for _, r in self.batch_sched.iterrows():
                try:
                    b = int(r["Batch"]); s = int(r["Stage"])
                    if s <= 0:
                        continue
                    stage_map[(b, s)] = (int(r["EntryTime"]), int(r["ExitTime"]))
                except Exception:
                    continue

        # Stage0 exitit Vaihe 1:stä (otetaan erän ensimmäisen stage=1 rivin Entry - siirtoaika)
        # Meillä on jo self.stage0_exit muuttuja mallissa, mutta tässä käytämme snapshotin aikoja pruningiin → lue CSV:stä
        stage0: Dict[int, int] = {}
        s1 = self.batch_sched[self.batch_sched["Stage"] == 1]
        if not s1.empty and "EntryTime" in s1.columns:
            for _, r in s1.iterrows():
                try:
                    b = int(r["Batch"])
                    # Approksimoi Stage0Exit(b) siten, että transporter-task(1) loppuu Entry(1): prevExit = Entry(1) - kesto(start->st1)
                    # Mutta kesto riippuu nostimesta, jota ei tässä tiedetä luotettavasti → käytetään konservatiivisesti Entry(1) itseä.
                    # Tämä tekee ikkunasta hieman leveämmän (turvallisempi prunaus).
                    stage0[b] = int(r["EntryTime"])  # yläraja prevExitille
                except Exception:
                    continue

        win: Dict[Tuple[int, int], Tuple[int, int]] = {}
        # Tarvitsemme ohjelmat, jotta löydämme olemassa olevat staget
        for b in self.batches_df["Batch"].astype(int).tolist():
            # listaa staget, joille on olemassa entry
            stages = [s for (bb, s) in stage_map.keys() if bb == int(b)]
            for s in stages:
                entry = stage_map.get((int(b), int(s)))
                if not entry:
                    continue
                entry_t = int(entry[0])
                if int(s) == 1:
                    prev_exit = int(stage0.get(int(b), entry_t))
                else:
                    prev = stage_map.get((int(b), int(s) - 1))
                    if not prev:
                        prev_exit = entry_t
                    else:
                        prev_exit = int(prev[1])
                a = max(0, prev_exit - m)
                bnd = min(48*3600, max(a + 1, entry_t + m))
                win[(int(b), int(s))] = (a, bnd)
        return win

    def _transporter_windows_overlap(self, b1: int, s1: int, b2: int, s2: int) -> bool:
        """Tarkista kahden transporter-tehtävän (s-1->s) ikkunaleikkaus konservatiivisesti.

        Käyttää Vaiheen 1 rungosta johdettuja transporter-ikkunoita, jotka on laajennettu
        CPSAT_PHASE2_TRANSPORTER_SAFE_MARGIN_SEC:llä, jotta karsinta on turvallista.
        Jos jokin ikkuna puuttuu, älä karsi (palauta True).
        """
        a = self.transporter_windows_phase1.get((int(b1), int(s1)))
        b = self.transporter_windows_phase1.get((int(b2), int(s2)))
        if not a or not b:
            return True
        a1, a2 = a; b1e, b2e = b
        return (a1 < b2e) and (b1e < a2)

    # --------- Mallin rakentaminen ---------
    def create_variables(self):
        MAX_T = 48 * 3600  # 48h yläraja varmuudella

        # Ryhmite Stage 1 -järjestystä varten (identtiset ohjelmat)
        # Käytetään treatment_program -kenttää
        self.batch_sched = self.batch_sched.sort_values(["Batch", "Stage"]).reset_index(drop=True)

        # Luo batch-kohtaiset Stage 0 ExitTime muuttujat
        for _, brow in self.batches_df.iterrows():
            b = int(brow["Batch"])
            self.stage0_exit[b] = self.model.NewIntVar(0, MAX_T, f"stage0_exit_{b}")

        # Luo päätösmuuttujat kaikille käsittelyvaiheille (Stage > 0)
        # Station ja Transporter on jo sidottu Vaiheessa 1 → luetaan sieltä
        for b in self.batch_sched["Batch"].unique():
            b = int(b)
            prog = self.programs[b]
            stages = sorted([int(s) for s in prog[prog["Stage"] > 0]["Stage"].tolist()])

            for s in stages:
                min_t = int(prog.loc[prog["Stage"] == s, "MinTime_sec"].iloc[0])
                max_t = int(prog.loc[prog["Stage"] == s, "MaxTime_sec"].iloc[0])

                e = self.model.NewIntVar(0, MAX_T, f"entry_{b}_{s}")
                x = self.model.NewIntVar(0, MAX_T, f"exit_{b}_{s}")
                c = self.model.NewIntVar(min_t, max_t, f"calc_{b}_{s}")
                self.entry[(b, s)] = e
                self.exit[(b, s)] = x
                self.calc[(b, s)] = c

                # Exit = Entry + Calc
                self.model.Add(x == e + c)

    # Luo transporter-tehtävät jokaiselle siirtymälle (s-1 -> s), s >= 1
        # Lue sidotut asemat ja nostimet Vaihe 1 aikataulusta
        # Rakennetaan apumappi: (b,s) -> (transporter, station)
        bs_map: Dict[Tuple[int, int], Tuple[int, int]] = {}
        for _, r in self.batch_sched.iterrows():
            bs_map[(int(r["Batch"]), int(r["Stage"]))] = (int(r["Transporter"]), int(r["Station"]))

        # Production.csv: tarvitaan start_station, jotta s=1 siirto voidaan muodostaa
        prod_path = os.path.join(self.output_dir, "initialization", "production.csv")
        if not os.path.exists(prod_path):
            raise FileNotFoundError(f"Production.csv ei löydy: {prod_path}")
        prod_df = pd.read_csv(prod_path)
        prod_df["Batch"] = prod_df["Batch"].astype(int)
        prod_df["Treatment_program"] = prod_df["Treatment_program"].astype(int)
        batch_start_station = {
            int(r["Batch"]): int(r["Start_station"]) for _, r in prod_df.iterrows()
        }

        for b in self.batch_sched["Batch"].unique():
            b = int(b)
            prog = self.programs[b]
            stages = sorted([int(s) for s in prog[prog["Stage"] > 0]["Stage"].tolist()])
            for idx, s in enumerate(stages):
                t_id, to_station = bs_map[(b, s)]
                if idx == 0:
                    # s=1: from = start_station
                    from_station = int(batch_start_station[b])
                    h_start = self.stage0_exit[b]
                else:
                    prev_s = stages[idx - 1]
                    _, from_station = bs_map[(b, prev_s)]
                    h_start = self.exit[(b, prev_s)]  # alkaa kun käsittely edellisellä asemalla päättyy

                # Kesto haetaan siirtotaulukosta
                dur, _ = self.transfers_map.get((int(t_id), int(from_station), int(to_station)), (None, None))
                if dur is None:
                    raise ValueError(f"Siirtoaika puuttuu: T={t_id}, {from_station}->{to_station}")

                # Luo transporter-interval: start var, end var, fixed duration
                h_end = self.model.NewIntVar(0, MAX_T, f"transporter_end_{b}_{s}")
                self.transporter_starts[(b, s)] = h_start
                self.transporter_ends[(b, s)] = h_end
                self.transporter_durations[(b, s)] = int(dur)
                self.transporter_by_task[(b, s)] = int(t_id)
                self.transporter_from_to[(b, s)] = (int(from_station), int(to_station))

                # End = Start + Duration
                self.model.Add(h_end == h_start + int(dur))

                # Sekvenssiliitos: Entry(s) = h_end
                self.model.Add(self.entry[(b, s)] == h_end)

    def add_station_change_constraints(self):
        """Disjunktio samaa asemaa käyttäville eri erille + change_time väli."""
        # Kerää kaikki käsittelyintervallit per station
        # Koska kesto on päätösmuuttuja (calc), käytämme pairwise-disjunktiota
        # station_map: station -> list[(b,s)]
        station_map: Dict[int, List[Tuple[int, int]]] = {}
        for (b, s), e_var in self.entry.items():
            # Selvitä asema Vaihe 1:stä
            row = self.batch_sched[(self.batch_sched["Batch"] == b) & (self.batch_sched["Stage"] == s)]
            if row.empty:
                continue
            station = int(row.iloc[0]["Station"])
            station_map.setdefault(station, []).append((b, s))

        M = 10**7
        total_pairs = 0
        pruned_pairs = 0
        for station, pairs in station_map.items():
            n = len(pairs)
            for i in range(n):
                for j in range(i + 1, n):
                    b1, s1 = pairs[i]
                    b2, s2 = pairs[j]
                    if b1 == b2:
                        continue
                    total_pairs += 1
                    # Ei karsintaa: kaikki samaa asemaa koskevat parit pidetään
                    e1, x1 = self.entry[(b1, s1)], self.exit[(b1, s1)]
                    e2, x2 = self.entry[(b2, s2)], self.exit[(b2, s2)]
                    b1_before = self.model.NewBoolVar(f"st{station}_b{b1}s{s1}_before_b{b2}s{s2}")
                    # b1 ennen b2
                    self.model.Add(e2 >= x1 + self.change_time).OnlyEnforceIf(b1_before)
                    # b2 ennen b1
                    self.model.Add(e1 >= x2 + self.change_time).OnlyEnforceIf(b1_before.Not())
        print(f" - Asema-disjunktiot: parit={total_pairs}, karsittu={pruned_pairs}")

    def add_transporter_no_overlap_with_deadhead(self):
        """Ei päällekkäisiä tehtäviä per transporter ja deadhead (TransferTime-only) väli peräkkäisten välillä.
        Toteutus: pairwise-disjunktio big-M:llä (yksinkertainen, mutta toimiva pieneen N:ään).
        """
        M = 10**7
        # Ryhmittele tehtävät transportereittain
        by_t: Dict[int, List[Tuple[int, int]]] = {}
        for (b, s), t_id in self.transporter_by_task.items():
            by_t.setdefault(int(t_id), []).append((b, s))

        total_pairs = 0
        pruned_pairs = 0
        for t_id, tasks in by_t.items():
            for i in range(len(tasks)):
                b1, s1 = tasks[i]
                start1 = self.transporter_starts[(b1, s1)]
                end1 = self.transporter_ends[(b1, s1)]
                (_, to1) = self.transporter_from_to[(b1, s1)]
                for j in range(i + 1, len(tasks)):
                    b2, s2 = tasks[j]
                    total_pairs += 1
                    # Ei karsintaa: pidä kaikki samaa asemaa koskevat parit turvallisuuden varmistamiseksi
                    start2 = self.transporter_starts[(b2, s2)]
                    end2 = self.transporter_ends[(b2, s2)]
                    (from2, _) = self.transporter_from_to[(b2, s2)]

                    # deadhead time i->j
                    _, dh_ij = self.transfers_map.get((int(t_id), int(to1), int(from2)), (0, 0))
                    _, dh_ji = self._deadhead_between_tasks(t_id, (b2, s2), (b1, s1))

                    i_before = self.model.NewBoolVar(f"t{t_id}_b{b1}s{s1}_before_b{b2}s{s2}")
                    # i ennen j: start2 >= end1 + deadhead(i->j)
                    self.model.Add(start2 >= end1 + int(dh_ij)).OnlyEnforceIf(i_before)
                    # j ennen i: start1 >= end2 + deadhead(j->i)
                    self.model.Add(start1 >= end2 + int(dh_ji)).OnlyEnforceIf(i_before.Not())
        print(f" - Saman nostimen disjunktiot: parit={total_pairs}, karsittu={pruned_pairs}")

    def add_cross_transporter_avoid_constraints(self):
        """
        Vältä kahden eri nostimen samanaikainen toiminta liian lähekkäin.

        Sääntö: jos kahden tehtävän (eri transportereilla) päätepisteiden pienin etäisyys
        asemakoordinaateissa (X Position) on alle avoid_pair = max(Avoid_i, Avoid_j),
        niiden aikavälit eivät saa mennä päällekkäin.

        Huom: konservatiivinen approksimaatio – tarkistetaan vain from/to päätepisteiden
        etäisyydet, ei koko liikeradan lähentymistä.
        """
        # Kerää Avoid-arvot
        avoid_by_t: Dict[int, int] = {}
        if "Transporter_id" in self.transporters_df.columns:
            for _, r in self.transporters_df.iterrows():
                t = int(r.get("Transporter_id"))
                avoid_val = int(pd.to_numeric(r.get("Avoid", 0), errors="coerce") if "Avoid" in r else 0)
                avoid_by_t[t] = max(0, avoid_val)

        # Apufunktio asemien X-koordinaatille
        def x(station: int) -> int:
            return int(self.station_positions.get(int(station), 0))

        # Listaa kaikki tehtävät
        tasks: List[Tuple[int, int, int, int, cp_model.IntVar, cp_model.IntVar]] = []
        # (t_id, b, s, from_station, start_var, end_var) + to_station via map
        for (b, s), t_id in self.transporter_by_task.items():
            tasks.append((int(t_id), int(b), int(s), int(self.transporter_from_to[(b, s)][0]), self.transporter_starts[(b, s)], self.transporter_ends[(b, s)]))

        # Pari-parilta eri transportereiden välillä
        n = len(tasks)
        for i in range(n):
            t1, b1, s1, from1, start1, end1 = tasks[i]
            to1 = int(self.transporter_from_to[(b1, s1)][1])
            x_from1, x_to1 = x(from1), x(to1)
            for j in range(i + 1, n):
                t2, b2, s2, from2, start2, end2 = tasks[j]
                if t1 == t2:
                    continue  # sama transporter käsitellään toisaalla
                # Aikaikkunakarsinta: jos erien ikkunat eivät leikkaa, ohita
                if not self._windows_overlap(b1, b2):
                    continue
                to2 = int(self.transporter_from_to[(b2, s2)][1])
                x_from2, x_to2 = x(from2), x(to2)

                avoid_limit = max(avoid_by_t.get(t1, 0), avoid_by_t.get(t2, 0))
                if avoid_limit <= 0:
                    continue

                # Lasketaan reittien välinen minimietäisyys koko siirron ajalta
                # Oletetaan lineaarinen liike from -> to
                # Tarkistetaan, leikkaavatko reitit avoid_limitin sisällä
                # Jos reitit menevät päällekkäin avoid-alueella, estetään päällekkäisyys
                # (Tämä on konservatiivinen, mutta kattaa kaikki risteävät tapaukset)
                def segments_overlap(a1, a2, b1, b2, limit):
                    # Palauttaa True jos segmentit [a1,a2] ja [b1,b2] ovat limitin sisällä jollain välillä
                    # Eli jos niiden välinen etäisyys käy < limit jossain kohtaa
                    # Ratkaistaan yhtälö: |(a1 + t*(a2-a1)) - (b1 + t*(b2-b1))| < limit jollekin t∈[0,1]
                    # Tämä on tosi jos segmentit leikkaavat tai menevät läheltä toisiaan
                    # Yksinkertaistetaan: jos segmenttien väli [min(a1,a2),max(a1,a2)] ja [min(b1,b2),max(b1,b2)] menevät limitin sisään
                    min1, max1 = min(a1, a2), max(a1, a2)
                    min2, max2 = min(b1, b2), max(b1, b2)
                    return not (max1 + limit <= min2 or max2 + limit <= min1)

                if segments_overlap(x_from1, x_to1, x_from2, x_to2, avoid_limit):
                    # Pakota ei-päällekkäisyys marginaalilla (1 sekunti)
                    margin = 1  # sekuntia
                    i_before = self.model.NewBoolVar(f"avoid_t{t1}_b{b1}s{s1}_vs_t{t2}_b{b2}s{s2}")
                    # i ennen j, marginaalilla
                    self.model.Add(start2 >= end1 + margin).OnlyEnforceIf(i_before)
                    # j ennen i, marginaalilla
                    self.model.Add(start1 >= end2 + margin).OnlyEnforceIf(i_before.Not())

    def _validate_transporter_no_overlap(self) -> List[Dict[str, int]]:
        """Validate after solving that no two tasks of the same transporter overlap,
        and that required deadhead time between consecutive tasks is respected.

        Returns a list of violations (empty if none)."""
        violations: List[Dict[str, int]] = []
        # Group tasks by transporter
        by_t: Dict[int, List[Tuple[int, int]]] = {}
        for (b, s), t_id in self.transporter_by_task.items():
            by_t.setdefault(int(t_id), []).append((int(b), int(s)))

        for t_id, tasks in by_t.items():
            # sort by realized start times
            tasks_sorted = sorted(
                tasks,
                key=lambda bs: int(self.solver.Value(self.transporter_starts[(bs[0], bs[1])]))
            )
            for i in range(len(tasks_sorted) - 1):
                b1, s1 = tasks_sorted[i]
                b2, s2 = tasks_sorted[i + 1]
                start1 = int(self.solver.Value(self.transporter_starts[(b1, s1)]))
                end1 = int(self.solver.Value(self.transporter_ends[(b1, s1)]))
                start2 = int(self.solver.Value(self.transporter_starts[(b2, s2)]))
                end2 = int(self.solver.Value(self.transporter_ends[(b2, s2)]))
                (_, to1) = self.transporter_from_to[(b1, s1)]
                (from2, _) = self.transporter_from_to[(b2, s2)]
                _, dh_ij = self.transfers_map.get((int(t_id), int(to1), int(from2)), (0, 0))
                # Check basic non-overlap and deadhead compliance
                if start2 < end1 + int(dh_ij):
                    violations.append({
                        "Transporter": int(t_id),
                        "b1": int(b1),
                        "s1": int(s1),
                        "end1": int(end1),
                        "b2": int(b2),
                        "s2": int(s2),
                        "start2": int(start2),
                        "required_gap": int(dh_ij),
                    })
        return violations

    def _validate_cross_transporter_collisions(self) -> List[Dict[str, int]]:
        """Validate after solving that different transporters do not operate too close simultaneously.

        Uses the same conservative segment overlap heuristic as in the model: if the X-intervals of
        the two tasks overlap within avoid_limit and the time intervals overlap, it's a violation.

        Returns a list of violations (empty if none)."""
        def x(station: int) -> float:
            return float(self.station_positions.get(int(station), 0.0))

        # Avoid distances per transporter (fallback 0)
        avoid_by_t: Dict[int, int] = {}
        if "Transporter_id" in self.transporters_df.columns:
            for _, r in self.transporters_df.iterrows():
                t = int(r.get("Transporter_id"))
                avoid_val = int(pd.to_numeric(r.get("Avoid", 0), errors="coerce") if "Avoid" in r else 0)
                avoid_by_t[t] = max(0, avoid_val)

        # Collect realized tasks
        tasks: List[Tuple[int, int, int, int, int, float, float]] = []
        # (t_id, b, s, start, end, x_from, x_to)
        for (b, s), t_id in self.transporter_by_task.items():
            start = int(self.solver.Value(self.transporter_starts[(b, s)]))
            end = int(self.solver.Value(self.transporter_ends[(b, s)]))
            f, t = self.transporter_from_to[(b, s)]
            tasks.append((int(t_id), int(b), int(s), start, end, x(int(f)), x(int(t))))

        def segments_overlap(a1: float, a2: float, b1: float, b2: float, limit: float) -> bool:
            min1, max1 = (a1, a2) if a1 <= a2 else (a2, a1)
            min2, max2 = (b1, b2) if b1 <= b2 else (b2, b1)
            return not (max1 + limit <= min2 or max2 + limit <= min1)

        violations: List[Dict[str, int]] = []
        n = len(tasks)
        for i in range(n):
            t1, b1, s1, s_start, s_end, x1_from, x1_to = tasks[i]
            for j in range(i + 1, n):
                t2, b2, s2, t_start, t_end, x2_from, x2_to = tasks[j]
                if t1 == t2:
                    continue
                avoid_limit = float(max(avoid_by_t.get(t1, 0), avoid_by_t.get(t2, 0)))
                if avoid_limit <= 0:
                    continue
                time_overlap = (s_start < t_end) and (t_start < s_end)
                if not time_overlap:
                    continue
                if segments_overlap(x1_from, x1_to, x2_from, x2_to, avoid_limit):
                    violations.append({
                        "T1": int(t1), "B1": int(b1), "S1": int(s1),
                        "Start1": int(s_start), "End1": int(s_end),
                        "T2": int(t2), "B2": int(b2), "S2": int(s2),
                        "Start2": int(t_start), "End2": int(t_end),
                        "Avoid_Limit": int(avoid_limit)
                    })
        return violations

    def _validate_station_non_overlap(self) -> List[Dict[str, int]]:
        """Validate that no two tasks at the same station overlap in time less than change_time.

        Uses realized Entry/Exit from solver and the Phase 2 change_time gap.
        Returns a list of violations with details.
        """
        station_map: Dict[int, List[Tuple[int, int]]] = {}
        for (b, s), _ in self.entry.items():
            row = self.batch_sched[(self.batch_sched["Batch"] == b) & (self.batch_sched["Stage"] == s)]
            if row.empty:
                continue
            st = int(row.iloc[0]["Station"])
            station_map.setdefault(st, []).append((int(b), int(s)))

        violations: List[Dict[str, int]] = []
        for st, items in station_map.items():
            # sort by realized entry times
            items_sorted = sorted(items, key=lambda bs: int(self.solver.Value(self.entry[(bs[0], bs[1])])))
            for i in range(len(items_sorted) - 1):
                b1, s1 = items_sorted[i]
                b2, s2 = items_sorted[i + 1]
                e1 = int(self.solver.Value(self.entry[(b1, s1)]))
                x1 = int(self.solver.Value(self.exit[(b1, s1)]))
                e2 = int(self.solver.Value(self.entry[(b2, s2)]))
                # require e2 >= x1 + change_time
                if e2 < x1 + int(self.change_time):
                    violations.append({
                        "Station": int(st),
                        "b1": int(b1), "s1": int(s1), "exit1": int(x1),
                        "b2": int(b2), "s2": int(s2), "entry2": int(e2),
                        "required_gap": int(self.change_time)
                    })
        return violations

    def _deadhead_between_tasks(self, t_id: int, task_from: Tuple[int, int], task_to: Tuple[int, int]) -> Tuple[int, int]:
        """Palauta (TotalTaskTime, TransferTime) deadheadille task_from → task_to (tyhjänä)."""
        b_from, s_from = task_from
        b_to, s_to = task_to
        _, to_station = self.transporter_from_to[(b_from, s_from)]
        from_station, _ = self.transporter_from_to[(b_to, s_to)]
        return self.transfers_map.get((int(t_id), int(to_station), int(from_station)), (0, 0))

    def add_stage1_anchor_for_identical_programs(self):
        """Lukitse Vaihe 1:stä johdettu järjestys identtisille ohjelmille Stage 1 -ankkurissa."""
        # Ryhmittele treatment_programin mukaan ja määritä Vaihe 1 -järjestys cp_sat_batch_schedule.csv:n perusteella
        stage1 = self.batch_sched[self.batch_sched["Stage"] == 1].copy()
        if stage1.empty:
            return
        # order by EntryTime (Vaihe 1)
        if "EntryTime" in stage1.columns:
            stage1 = stage1.sort_values("EntryTime").reset_index(drop=True)
        groups = stage1.groupby("Treatment_program")
        for prog, df in groups:
            b_list = df["Batch"].astype(int).tolist()
            for i in range(len(b_list) - 1):
                b_prev = b_list[i]
                b_next = b_list[i + 1]
                # Entry_2(b_prev,1) <= Entry_2(b_next,1)
                if (b_prev, 1) in self.entry and (b_next, 1) in self.entry:
                    self.model.Add(self.entry[(b_prev, 1)] <= self.entry[(b_next, 1)])

    def set_objective(self):
        # Leksikografinen approksimaatio: w1*makespan + w3*stretch
        last_exits = []
        for b in self.batches_df["Batch"].astype(int).tolist():
            prog = self.programs[int(b)]
            max_stage = int(prog[prog["Stage"] > 0]["Stage"].max())
            last_exits.append(self.exit[(int(b), max_stage)])
        makespan = self.model.NewIntVar(0, 48 * 3600, "makespan")
        self.model.AddMaxEquality(makespan, last_exits)

        # CalcTime venytys
        stretch_vars = []
        for (b, s), c in self.calc.items():
            min_t = int(self.programs[b].loc[self.programs[b]["Stage"] == s, "MinTime_sec"].iloc[0])
            d = self.model.NewIntVar(0, 48 * 3600, f"stretch_{b}_{s}")
            self.model.Add(d == c - min_t)
            stretch_vars.append(d)
        total_stretch = self.model.NewIntVar(0, 10**9, "total_stretch")
        if stretch_vars:
            self.model.Add(total_stretch == sum(stretch_vars))
        else:
            self.model.Add(total_stretch == 0)

        w1, w3 = 10**6, 1
        objective = self.model.NewIntVar(0, 10**12, "objective")
        self.model.Add(objective == w1 * makespan + w3 * total_stretch)
        self.model.Minimize(objective)

    # --------- Ratkaisu ja tallennus ---------
    def solve(self):
        logger = get_logger()
        if logger:
            logger.log("STEP", "STEP 2 STARTED: CP-SAT PHASE 2")
        print("Ratkaistaan CP-SAT Vaihe 2...")

        self.create_variables()
        print(" - Muuttujat luotu")
        self.add_station_change_constraints()
        print(" - Asemien change_time -rajoitteet lisätty")
        self.add_transporter_no_overlap_with_deadhead()
        print(" - Nostinkohtaiset ei-päällekkäisyydet + deadhead lisätty")
        self.add_cross_transporter_avoid_constraints()
        print(" - Ristikkäisten nostimien Avoid-rajoitteet lisätty")
        self.add_stage1_anchor_for_identical_programs()
        print(" - Stage 1 -ankkuri identtisille ohjelmille lisätty")
        self.set_objective()
        print(" - Tavoite asetettu")

        # Aikaraja: luettavissa ympäristömuuttujasta CPSAT_PHASE2_MAX_TIME (sekunteina), oletus 300 s
        try:
            _time_limit = float(os.getenv("CPSAT_PHASE2_MAX_TIME", "300"))
        except Exception:
            _time_limit = 300.0
        self.solver.parameters.max_time_in_seconds = _time_limit
        # Valinnainen: säikeiden määrä ja hakulokin tulostus
        try:
            _threads = int(os.getenv("CPSAT_PHASE2_THREADS", "0") or "0")
        except Exception:
            _threads = 0
        if _threads > 0:
            self.solver.parameters.num_search_workers = _threads
            print(f" - Säikeet: {_threads}")
        # Yleinen kytkin hakulokille (molemmille vaiheille): CPSAT_LOG_PROGRESS=1
        _log_progress = os.getenv("CPSAT_LOG_PROGRESS", "0") in ("1", "true", "True")
        if _log_progress:
            self.solver.parameters.log_search_progress = True
            self.solver.parameters.log_to_stdout = True
            print(" - Hakuloki: päällä (log_search_progress)")
        print(f" - Aikaraja asetettu: {int(_time_limit)} s")
        status = self.solver.Solve(self.model)

        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            if status == cp_model.INFEASIBLE:
                print("CP-SAT Vaihe 2: infeasible (ei ratkaisua olemassa)")
                self._write_conflicts()
            elif status == cp_model.UNKNOWN:
                print("CP-SAT Vaihe 2: ei löydetty ratkaisua aikarajan puitteissa (UNKNOWN)")
            else:
                print(f"CP-SAT Vaihe 2: solver status {status} (ei ratkaisua)")
            if logger:
                logger.log("ERROR", "cp-sat phase 2 infeasible")
            return None

        print("CP-SAT Vaihe 2: ratkaisu löytyi")

        # Post-validate that there are no overlaps per transporter
        violations = self._validate_transporter_no_overlap()
        if violations:
            print("[ERROR] Validointi epäonnistui: transportereilla päällekkäisiä tehtäviä tai deadhead-väliä ei kunnioiteta.")
            # Kirjoita konfliktiraportti ja keskeytä
            cp_dir = os.path.join(self.output_dir, "cp_sat")
            _ensure_dirs(cp_dir)
            path = os.path.join(cp_dir, "cp_sat_hoist_conflicts.csv")
            vdf = pd.DataFrame(violations)
            vdf.to_csv(path, index=False)
            print(f"Tallennettu konfliktiraportti: {path}")
            return None

        # Post-validate station non-overlap with change_time
        st_violations = self._validate_station_non_overlap()
        if st_violations:
            print("[ERROR] Validointi epäonnistui: asema-aikataulussa päällekkäisyyksiä (change_time ei toteudu).")
            cp_dir = os.path.join(self.output_dir, "cp_sat")
            _ensure_dirs(cp_dir)
            path = os.path.join(cp_dir, "cp_sat_station_conflicts.csv")
            pd.DataFrame(st_violations).to_csv(path, index=False)
            print(f"Tallennettu asema-konfliktiraportti: {path}")
            return None

        # Post-validate that there are no cross-transporter collisions in space-time
        x_violations = self._validate_cross_transporter_collisions()
        if x_violations:
            print("[ERROR] Validointi epäonnistui: eri nostimien liikkeet liian lähellä samanaikaisesti (törmäysriski).")
            cp_dir = os.path.join(self.output_dir, "cp_sat")
            _ensure_dirs(cp_dir)
            path = os.path.join(cp_dir, "cp_sat_cross_conflicts.csv")
            pd.DataFrame(x_violations).to_csv(path, index=False)
            print(f"Tallennettu ristikäisten nostimien konfliktiraportti: {path}")
            return None
        # Luo snapshot ja pysyvät päivitykset
        self._write_transporter_schedule_snapshot()
        self._update_production_start_optimized()
        self._write_treatment_programs_optimized()

        if logger:
            logger.log("STEP", "STEP 2 COMPLETED: CP-SAT PHASE 2")
        return True

    def _write_conflicts(self):
        cp_dir = os.path.join(self.output_dir, "cp_sat")
        _ensure_dirs(cp_dir)
        path = os.path.join(cp_dir, "cp_sat_hoist_conflicts.csv")
        df = pd.DataFrame([
            {"Message": "CP-SAT Phase 2 infeasible", "Hint": "Tarkista aseman vaihtoajat (change_time), deadhead-matriisi ja sidotut asemat/nostimet."}
        ])
        df.to_csv(path, index=False)
        print(f"Tallennettu konfliktiraportti: {path}")

    def _write_transporter_schedule_snapshot(self):
        cp_dir = os.path.join(self.output_dir, "cp_sat")
        _ensure_dirs(cp_dir)
        rows = []
        # Kulje kaikki transporter-tehtävät (b,s)
        for (b, s), start_var in self.transporter_starts.items():
            t_id = self.transporter_by_task[(b, s)]
            from_station, to_station = self.transporter_from_to[(b, s)]
            start_val = int(self.solver.Value(start_var))
            end_val = int(self.solver.Value(self.transporter_ends[(b, s)]))
            duration = int(self.transporter_durations[(b, s)])
            entry_to = int(self.solver.Value(self.entry[(b, s)]))
            rows.append({
                "Transporter": int(t_id),
                "Batch": int(b),
                "From_Station": int(from_station),
                "To_Station": int(to_station),
                "TaskStart": start_val,
                "TaskEnd": end_val,
                "Duration": duration,
                "EntryTime_2(To)": entry_to,
            })
        df = pd.DataFrame(rows).sort_values(["Transporter", "TaskStart", "Batch"]).reset_index(drop=True)
        out = os.path.join(cp_dir, "cp_sat_hoist_schedule.csv")
        df.to_csv(out, index=False)
        print(f"Tallennettu snapshot: {out} ({len(df)} riviä)")
        # Kirjoita myös asema-aikataulun snapshot validointia varten
        station_rows = []
        for (b, s), e_var in self.entry.items():
            st_row = self.batch_sched[(self.batch_sched["Batch"] == b) & (self.batch_sched["Stage"] == s)]
            if st_row.empty:
                continue
            station = int(st_row.iloc[0]["Station"])
            entry_val = int(self.solver.Value(self.entry[(b, s)]))
            exit_val = int(self.solver.Value(self.exit[(b, s)]))
            station_rows.append({
                "Batch": int(b),
                "Stage": int(s),
                "Station": int(station),
                "EntryTime": entry_val,
                "ExitTime": exit_val,
            })
        sdf = pd.DataFrame(station_rows).sort_values(["Station", "EntryTime", "Batch"]).reset_index(drop=True)
        sout = os.path.join(cp_dir, "cp_sat_station_schedule.csv")
        sdf.to_csv(sout, index=False)
        print(f"Tallennettu station snapshot: {sout} ({len(sdf)} riviä)")

    def _update_production_start_optimized(self):
        # Start_optimized = Stage 0 ExitTime = Entry_2(b,1) - siirto(start_station -> station_1)
        prod_path = os.path.join(self.output_dir, "initialization", "production.csv")
        if not os.path.exists(prod_path):
            print(f"Production.csv puuttuu: {prod_path}")
            return
        df = pd.read_csv(prod_path)
        df["Batch"] = df["Batch"].astype(int)
        # Hae Vaihe 1 sidottu station_1 + transporter
        stage1 = self.batch_sched[self.batch_sched["Stage"] == 1].copy()
        for _, row in stage1.iterrows():
            b = int(row["Batch"])
            t_id = int(row["Transporter"])
            to_station = int(row["Station"])
            # entry_2(b,1)
            if (b, 1) not in self.entry:
                continue
            entry1 = int(self.solver.Value(self.entry[(b, 1)]))
            start_station = int(df[df["Batch"] == b].iloc[0]["Start_station"]) if (df["Batch"] == b).any() else to_station
            tt, _ = self.transfers_map.get((t_id, start_station, to_station), (0, 0))
            stage0_exit = max(0, entry1 - int(tt))
            df.loc[df["Batch"] == b, "Start_optimized"] = _hms(stage0_exit)
        # Järjestä rivejä Start_optimized-ajan mukaan nousevasti (puuttuvat viimeiseksi)
        if "Start_optimized" in df.columns:
            secs = pd.to_timedelta(df["Start_optimized"], errors="coerce").dt.total_seconds()
            df["__start_opt_sec"] = secs
            df = df.sort_values(["__start_opt_sec", "Batch"], na_position="last").drop(columns=["__start_opt_sec"]).reset_index(drop=True)
        df.to_csv(prod_path, index=False)
        print(f"Päivitetty production.csv: {prod_path}")

    def _write_treatment_programs_optimized(self):
        # Kirjoita jokaiselle erälle optimoitu ohjelma: Stage, Transporter, Station, MinTime, MaxTime, CalcTime (hh:mm:ss)
        cp_dir = os.path.join(self.output_dir, "cp_sat")
        out_dir = os.path.join(cp_dir, "treatment_program_optimized")
        _ensure_dirs(out_dir)

        # Rakenna apumappi Vaihe 1: (b,s) -> (t, station)
        bs_map: Dict[Tuple[int, int], Tuple[int, int]] = {}
        for _, r in self.batch_sched.iterrows():
            bs_map[(int(r["Batch"]), int(r["Stage"]))] = (int(r["Transporter"]), int(r["Station"]))

        # Tallenna batch-kohtaisesti
        for _, brow in self.batches_df.iterrows():
            b = int(brow["Batch"])
            prog = self.programs[b]
            rows = []
            for _, srow in prog.iterrows():
                s = int(srow["Stage"])
                if s == 0:
                    continue
                t_id, station = bs_map[(b, s)]
                e = int(self.solver.Value(self.entry[(b, s)]))
                x = int(self.solver.Value(self.exit[(b, s)]))
                calc = max(0, x - e)
                rows.append({
                    "Stage": s,
                    "Transporter": int(t_id),
                    "Station": int(station),
                    "MinTime": srow["MinTime"],  # säilytä merkkijonona
                    "MaxTime": srow["MaxTime"],
                    "CalcTime": _hms(calc),
                })
            out_file = os.path.join(out_dir, f"Batch_{b:03d}_Treatment_program_{int(brow['Treatment_program']):03d}.csv")
            pd.DataFrame(rows).to_csv(out_file, index=False)
            print(f"Tallennettu optimoitu ohjelma: {out_file}")


def optimize_phase_2(output_dir: str):
    """Pääfunktio Vaiheen 2 optimoinnille."""
    optimizer = CpSatPhase2Optimizer(output_dir)
    return optimizer.solve()
