"""
VRPTW-BASED OPTIMIZATION FOR HOIST SCHEDULING
Vehicle Routing Problem with Time Windows approach for production line optimization.

Malli:
- Nostin = Vehicle (ajoneuvo)
- Erä+Stage = Customer (asiakas) tietyssä lokaatiossa
- Käsittelyohjelman järjestys = Precedence constraints
- Min/max käsittelyajat = Time windows
- Siirtoajat = Travel times between locations
"""

import os
import pandas as pd
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp


def vrptw_optimization(output_dir, treatment_programs, batches_df, stations_df, transfers_df, transporters_df):
    """
    VRPTW-pohjainen optimointi hoist scheduling ongelmalle
    """
    print("🚀 VRPTW-optimointi aloitetaan...")
    
    # 1. LUO ASIAKKAAT (Customers) = (Erä, Stage) parit
    customers = []
    customer_id = 0
    batch_stage_to_customer = {}  # Mapping (batch, stage) -> customer_id
    
    # Depot (nostimen aloituspaikka)
    depot_station = 301  # Oletetaan depot asemalla 301
    customers.append({
        'id': customer_id,
        'batch': None,
        'stage': None,
        'station': depot_station,
        'min_time': 0,
        'max_time': 0,
        'service_time': 0,
        'is_depot': True
    })
    depot_id = customer_id
    customer_id += 1
    
    # Luo asiakkaat kaikille (batch, stage) pareille
    for batch_id, program in treatment_programs.items():
        for _, row in program.iterrows():
            stage = row['Stage']
            if stage == 0:  # Ohita Stage 0 jos sellainen on
                continue
                
            station = row['MinStat']  # Yksinkertaistus: käytä MinStat
            min_time = pd.to_timedelta(row['MinTime']).total_seconds()
            max_time = pd.to_timedelta(row['MaxTime']).total_seconds()
            
            # Hae siirtoaika transfers_df:stä (service time = nostimen työskentelyaika)
            mask = (transfers_df["From_Station"] == station) & (transfers_df["To_Station"] == station)
            service_time = int(transfers_df[mask]["TotalTaskTime"].iloc[0]) if mask.any() else 60
            
            customers.append({
                'id': customer_id,
                'batch': batch_id,
                'stage': stage,
                'station': station,
                'min_time': int(min_time),
                'max_time': int(max_time),
                'service_time': service_time,
                'is_depot': False
            })
            
            batch_stage_to_customer[(batch_id, stage)] = customer_id
            customer_id += 1
    
    num_customers = len(customers)
    print(f"   📍 Luotu {num_customers} asiakasta (sisältää depot)")
    
    # 2. LUO ETÄISYYSMATRIISI (Distance Matrix)
    def create_distance_matrix():
        """Luo etäisyysmatriisi asiakkaiden välille (siirtoajat sekunneissa)"""
        matrix = [[0 for _ in range(num_customers)] for _ in range(num_customers)]
        
        for i in range(num_customers):
            for j in range(num_customers):
                if i == j:
                    matrix[i][j] = 0
                else:
                    from_station = customers[i]['station']
                    to_station = customers[j]['station']
                    
                    # Hae siirtoaika transfers_df:stä
                    mask = (transfers_df["From_Station"] == from_station) & \
                           (transfers_df["To_Station"] == to_station)
                    
                    if mask.any():
                        travel_time = int(transfers_df[mask]["TotalTaskTime"].iloc[0])
                    else:
                        # Oletus: 60s jos ei löydy
                        travel_time = 60
                    
                    matrix[i][j] = travel_time
        
        return matrix
    
    distance_matrix = create_distance_matrix()
    print(f"   🗺️ Etäisyysmatriisi luotu ({num_customers}x{num_customers})")
    
    # 3. LUO AIKAIKKUNA-RAJOITTEET (Time Windows)
    def create_time_windows():
        """Luo aikaikkuna jokaiselle asiakkaalle"""
        time_windows = []
        
        for customer in customers:
            if customer['is_depot']:
                # Depot: aina auki
                time_windows.append((0, 7200))  # 2h maksimi
            else:
                # Asiakas: min/max käsittelyajat
                # Tässä yksinkertaistetusti: asiakas voi aloittaa milloin tahansa
                # mutta käsittelyn on kestettävä min-max ajan
                time_windows.append((0, 7200 - customer['max_time']))
        
        return time_windows
    
    time_windows = create_time_windows()
    print(f"   ⏰ Aikaikkuna-rajoitteet luotu")
    
    # 4. LUO VRPTW MALLI
    # Luo routing manager
    manager = pywrapcp.RoutingIndexManager(
        len(distance_matrix),  # Asiakkaiden määrä
        1,  # Ajoneuvojen määrä (1 nostin)
        depot_id  # Depot index
    )
    
    # Luo routing model
    routing = pywrapcp.RoutingModel(manager)
    
    # 5. MÄÄRITÄ KUSTANNUSFUNKTIO (siirtoajat)
    def distance_callback(from_index, to_index):
        """Palauttaa siirtoajan kahden asiakkaan välillä"""
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return distance_matrix[from_node][to_node]
    
    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
    
    # 6. LISÄÄ AIKARAJOITTEET
    def time_callback(from_index, to_index):
        """Palauttaa ajan joka kuluu siirtymiseen + palveluun"""
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        travel_time = distance_matrix[from_node][to_node]
        service_time = customers[to_node]['service_time']
        return travel_time + service_time
    
    time_callback_index = routing.RegisterTransitCallback(time_callback)
    
    # Lisää aikaikkuna-rajoitteet
    time_dimension_name = 'Time'
    routing.AddDimension(
        time_callback_index,
        7200,  # Slack max (2h)
        7200,  # Maksimiaika
        False,  # Start cumul to zero
        time_dimension_name
    )
    time_dimension = routing.GetDimensionOrDie(time_dimension_name)
    
    # Aseta aikaikkuna-rajoitteet
    for location_idx, time_window in enumerate(time_windows):
        index = manager.NodeToIndex(location_idx)
        time_dimension.CumulVar(index).SetRange(time_window[0], time_window[1])
    
    print("   ⚖️ VRPTW-rajoitteet lisätty")
    
    # 7. LISÄÄ PRECEDENCE CONSTRAINTS (käsittelyohjelman järjestys)
    for batch_id, program in treatment_programs.items():
        stages = sorted(program["Stage"].tolist())
        stages = [s for s in stages if s != 0]  # Poista Stage 0
        
        for i in range(len(stages) - 1):
            current_stage = stages[i]
            next_stage = stages[i + 1]
            
            if (batch_id, current_stage) in batch_stage_to_customer and \
               (batch_id, next_stage) in batch_stage_to_customer:
                
                current_customer = batch_stage_to_customer[(batch_id, current_stage)]
                next_customer = batch_stage_to_customer[(batch_id, next_stage)]
                
                current_index = manager.NodeToIndex(current_customer)
                next_index = manager.NodeToIndex(next_customer)
                
                # Lisää precedence constraint
                routing.solver().Add(
                    time_dimension.CumulVar(current_index) + customers[current_customer]['service_time'] 
                    <= time_dimension.CumulVar(next_index)
                )
        
        print(f"     🔗 Erä {batch_id}: {len(stages)} vaihetta, precedence constraints lisätty")
    
    # 8. OPTIMOINTIASETUKSET
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    search_parameters.time_limit.FromSeconds(120)  # 2 min optimointiaika
    
    print("🔍 Ratkaistaan VRPTW-mallia...")
    
    # 9. RATKAISE
    solution = routing.SolveWithParameters(search_parameters)
    
    if solution:
        print("📊 Optimoinnin tila: SOLUTION FOUND")
        
        # 10. KERÄÄ RATKAISU
        schedule = []
        
        # Nostimen reitti
        vehicle_id = 0
        index = routing.Start(vehicle_id)
        route_distance = 0
        current_time = 0
        
        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            customer = customers[node]
            
            if not customer['is_depot']:
                # Laske saapumisaika ja lähtöaika
                arrival_time = current_time
                start_time = max(arrival_time, customer['min_time'])
                end_time = start_time + customer['service_time']
                
                schedule.append({
                    'Batch': customer['batch'],
                    'Stage': customer['stage'],
                    'Station': customer['station'],
                    'Start': start_time,
                    'End': end_time,
                    'Duration': customer['service_time']
                })
                
                current_time = end_time
                
                print(f"   📦 Erä {customer['batch']} Stage {customer['stage']}: "
                      f"Asema {customer['station']}, {start_time}→{end_time}s")
            
            # Siirry seuraavaan
            previous_index = index
            index = solution.Value(routing.NextVar(index))
            route_distance += routing.GetArcCostForVehicle(previous_index, index, vehicle_id)
        
        total_time = solution.ObjectiveValue()
        print(f"🎯 Kokonaisaika: {total_time} sekuntia ({total_time/60:.1f} minuuttia)")
        
        # 11. TALLENNA RATKAISU
        if schedule:
            schedule_df = pd.DataFrame(schedule).sort_values(['Batch', 'Stage'])
            
            logs_dir = os.path.join(output_dir, "logs")
            os.makedirs(logs_dir, exist_ok=True)
            
            output_file = os.path.join(logs_dir, "vrptw_optimization_schedule.csv")
            schedule_df.to_csv(output_file, index=False)
            print(f"💾 Tulokset tallennettu: {output_file}")
            
            return True
        
    else:
        print("❌ VRPTW-optimointi epäonnistui: Ratkaisua ei löytynyt")
        return False

    return False