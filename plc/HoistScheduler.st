(*****************************************************************)
(*  TransporterScheduler.st                                       *)
(*  Lightweight per-transporter online scheduler for PLC          *)
(*  (IEC 61131-3 Structured Text template)                        *)
(*  - Keeps Stage 1 order externally (CP-SAT/MES)                 *)
(*  - Chooses next task locally among ≤5 candidates               *)
(*  - Enforces time window, deadhead gap, station locks           *)
(*  - Optional shared-zone token for collision avoidance          *)
(*                                                                *)
(*  Dialect: generic ST; adapt types and array bounds to your PLC *)
(*****************************************************************)

(* ====== CONFIGURATION LIMITS (ADAPT) ====== *)
CONSTANT
    MAX_CANDIDATES : INT := 8;          (* ≤ 5 in typical use *)
    MAX_STATIONS   : INT := 256;        (* map station numbers to indices [0..MAX_STATIONS-1] *)
END_CONSTANT

(* ====== TYPES ====== *)
TYPE Task_t :
STRUCT
    Valid       : BOOL;  (* candidate present *)
    Transporter : INT;   (* transporter id *)
    Batch       : INT;
    TaskSeq     : INT;   (* sequence within batch *)
    LiftStation : INT;   (* station index [0..MAX_STATIONS-1] *)
    SinkStation : INT;   (* station index [0..MAX_STATIONS-1] *)
    TaskStart   : DINT;  (* seconds from reference epoch/shift start *)
    TaskEnd     : DINT;  (* seconds from reference epoch/shift start *)
    Duration    : DINT;  (* convenience: TaskEnd-TaskStart *)
END_STRUCT
END_TYPE

(* ====== HELPERS ====== *)
FUNCTION CanStartWindow : BOOL
VAR_INPUT
    TaskStart : DINT;
    PreMargin : DINT;
    LateTol   : DINT;
    Now       : DINT;
END_VAR
CanStartWindow := (Now >= TaskStart - PreMargin) AND (Now <= TaskStart + LateTol);

FUNCTION DeadheadOk : BOOL
VAR_INPUT
    PrevEnd     : DINT;  (* previous task end time for this hoist *)
    PrevTo      : INT;   (* previous task sink station index *)
    NextFrom    : INT;   (* next task lift station index *)
    DeadheadSec : DINT;  (* required deadhead seconds from PrevTo->NextFrom *)
    Now         : DINT;
END_VAR
VAR
    earliest : DINT;
END_VAR
earliest := PrevEnd + DeadheadSec;
DeadheadOk := (Now >= earliest);

(* ====== SHARED ZONE TOKEN (OPTIONAL) ====== *)
FUNCTION_BLOCK FB_ZoneToken
VAR_INPUT
    Request       : BOOL;  (* request access *)
    Release       : BOOL;  (* release access *)
    TransporterId : INT;
END_VAR
VAR_OUTPUT
    Granted : BOOL;
END_VAR
VAR
    Occupied : BOOL;
    Owner    : INT;
END_VAR
Granted := FALSE;
IF Release THEN
    IF Occupied AND (Owner = TransporterId) THEN
        Occupied := FALSE; Owner := 0;
    END_IF
END_IF
IF Request THEN
    IF NOT Occupied THEN
        Occupied := TRUE; Owner := TransporterId; Granted := TRUE;
    ELSIF Owner = TransporterId THEN
        Granted := TRUE; (* re-entrant for same owner *)
    END_IF
END_IF

(* ====== PER-HOIST SCHEDULER FB ====== *)
FUNCTION_BLOCK FB_TransporterScheduler
VAR_INPUT
    Now            : DINT;                                  (* seconds *)
    PreMargin      : DINT := 5;                             (* seconds *)
    LateTol        : DINT := 15;                            (* seconds *)
    TransporterId  : INT;
    CandidateCount : INT;                                   (* 0..MAX_CANDIDATES *)
    Candidates     : ARRAY[0..MAX_CANDIDATES-1] OF Task_t;  (* provided by caller *)
    (* Deadhead matrix lookup must be provided by caller as function or table; for portability, pass per-call value *)
    (* Station usage map: TRUE means locked/in use. Caller maps station numbers to [0..MAX_STATIONS-1]. *)
    StationInUse   : ARRAY[0..MAX_STATIONS-1] OF BOOL;
    (* Zone check inputs: set PathNeedsZone to TRUE when Lift->Sink crosses the shared zone. *)
    PathNeedsZone  : BOOL;
END_VAR
VAR_OUTPUT
    StartTask    : BOOL;       (* pulse when a task starts *)
    FinishTask   : BOOL;       (* pulse when a task finishes *)
    Executing    : BOOL;       (* transporter is executing a task *)
    Current      : Task_t;     (* currently executing task *)
END_VAR
VAR_IN_OUT
    Zone         : FB_ZoneToken;          (* shared token instance passed by caller *)
    PrevEndTime  : DINT;                  (* persistent: last end time of this transporter *)
    PrevToStation: INT;                   (* persistent: last sink station index of this transporter *)
END_VAR
VAR
    i, bestIdx  : INT;
    bestStart   : DINT;
    bestDur     : DINT;
    zoneOk      : BOOL;
    dhSec       : DINT;  (* required deadhead for PrevTo->candidate.LiftStation; get via callback input on each eval *)
END_VAR

(* Default outputs *)
StartTask := FALSE; FinishTask := FALSE;

IF NOT Executing THEN
    (* Select best candidate by earliest TaskStart, tie -> shortest Duration *)
    bestIdx := -1; bestStart := 16#7FFFFFFF; bestDur := 16#7FFFFFFF;
    FOR i := 0 TO CandidateCount - 1 DO
        IF Candidates[i].Valid THEN
            (* Caller computes required deadhead seconds for PrevTo->LiftStation and passes here.
               For portability, we reuse Duration as tie-breaker and rely on DeadheadOk with dhSec from external. *)
            dhSec := 0; (* Replace: call a lookup FB/FUNC to get Deadhead[PrevToStation, Candidates[i].LiftStation] *)
            IF CanStartWindow(TaskStart := Candidates[i].TaskStart, PreMargin := PreMargin, LateTol := LateTol, Now := Now)
               AND (NOT StationInUse[Candidates[i].LiftStation])
               AND (NOT StationInUse[Candidates[i].SinkStation])
               AND DeadheadOk(PrevEnd := PrevEndTime, PrevTo := PrevToStation, NextFrom := Candidates[i].LiftStation, DeadheadSec := dhSec, Now := Now) THEN
                IF (Candidates[i].TaskStart < bestStart) OR
                   ((Candidates[i].TaskStart = bestStart) AND (Candidates[i].Duration < bestDur)) THEN
                    bestStart := Candidates[i].TaskStart;
                    bestDur := Candidates[i].Duration;
                    bestIdx := i;
                END_IF
            END_IF
        END_IF
    END_FOR

    IF bestIdx >= 0 THEN
        zoneOk := TRUE;
        IF PathNeedsZone THEN
            Zone.Request := TRUE;
            Zone.TransporterId := TransporterId;
            zoneOk := Zone.Granted; (* Granted is set inside FB_ZoneToken when Request is TRUE *)
        END_IF
        IF zoneOk THEN
            (* Lock stations; note: StationInUse is VAR_INPUT in this portable template -> implement lock outside in caller *)
            Current := Candidates[bestIdx];
            Executing := TRUE;
            StartTask := TRUE;
        END_IF
    END_IF

ELSE
    (* Execution monitoring: finish when Now >= Current.TaskEnd *)
    IF Now >= Current.TaskEnd THEN
        FinishTask := TRUE;
        Executing := FALSE;
        (* Update history *)
        PrevEndTime := Now;
        PrevToStation := Current.SinkStation;
        (* Release zone *)
        Zone.Release := TRUE; Zone.TransporterId := TransporterId; (* pulse release *)
    END_IF
END_IF
