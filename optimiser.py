import streamlit as st
import requests
from mip import Model, xsum, OptimizationStatus, maximize, INTEGER, BINARY, CONTINUOUS

FC = 15        # กม./ลิตร
Pfuel = 40     # บาท/ลิตร

def solve_itinerary(
    potential_hotels: list[dict],
    potential_attractions: list[dict],
    start_point_name: str,      # เพิ่ม: จุดเริ่มต้น (ชื่อ)
    end_point_name: str,        # เพิ่ม: จุดสิ้นสุด (ชื่อ)
    trip_duration_days: int,
    max_daily_hours: int,
    is_daily_limit_flexible: bool,
    budget: int,
    objective_weights: dict
    ) -> list[dict]:

    """
    This is a placeholder function that simulates the behavior of the real
    optimization model. It takes all the user inputs and returns a list of
    pre-defined, sample itineraries.

    Args:
        potential_hotels (list[dict]): A list of hotel dictionaries selected by the user.
                                       Each dict contains 'name', 'lat', 'lon'.
        potential_attractions (list[dict]): A list of attraction dictionaries.
                                            Each dict contains 'name', 'lat', 'lon', 'duration'.
        trip_duration_days (int): The total number of days for the trip.
        max_daily_hours (int): The maximum number of hours to travel per day.
        is_daily_limit_flexible (bool): Whether the daily limit is a hard or soft constraint.
        must_see_attractions (list[str]): A list of attraction names that must be included.
        objective_weights (dict): A dict with weights, e.g., {'distance': 0.7, 'balance': 0.3}.

    Returns:
        list[dict]: A list of dictionaries, each representing a complete itinerary.
    """

    # --- 1. Print inputs for debugging (useful for you and your students) ---
    print("--- OPTIMIZATION MODEL CALLED ---")
    print(f"Potential Hotels: {[h.get('name') for h in potential_hotels]}")
    print(f"Number of Potential Attractions: {len(potential_attractions)}")
    print(f"Trip Duration: {trip_duration_days} days")
    print(f"Max Daily Hours: {max_daily_hours}")
    #print(f"Must-See Attractions: {must_see_attractions}")

    print("---------------------------------")

    # --- 2. Data Cleaning and Preparation ---
    cleaned_places = []


    # รวมโรงแรมและสถานที่ทั้งหมด
    for p in potential_hotels + potential_attractions:
        # Ensure each place has a name before adding
        if "name" in p and p["name"]:
            cleaned_places.append({
                "name": p["name"],
                "lat": p.get("lat"),
                "lon": p.get("lon"),
                "duration": p.get("duration", 0) if not p.get("is_hotel", False) else 0,
                "score": p.get("score", 1),     # เพิ่ม ถ้ายังไม่มีคะแนนจะได้ 1
                "cost": p.get("cost", 0),
                "E": p.get("open_time", 0.0),
                "L": p.get("close_time", 24.0),
                "is_hotel": p in potential_hotels  # ถ้ามาจาก potential_hotels ให้ True
            })
        else:
            print(f"Warning: Skipping place with missing name: {p}")


    # ถ้าไม่มีสถานที่เลย ให้ return ว่าง
    if not cleaned_places:
        print("Error: No valid places found after cleaning.")
        return []

    # list[str] ที่มีแค่ name
    hotels_name = [p["name"] for p in cleaned_places if p.get("is_hotel")]
    attractions_name = [p["name"] for p in cleaned_places if not p.get("is_hotel")]
    all_places_name = [p["name"] for p in cleaned_places]

    # Mapping จากชื่อ ไป index
    place_to_index = {p["name"]: i for i, p in enumerate(cleaned_places)}
    # ✅ เพิ่ม: หา index ของจุดเริ่มต้นและจุดสิ้นสุด
    start_idx = place_to_index[start_point_name]
    end_idx = place_to_index[end_point_name]

    # สร้าง index
    hotel_indices = []
    for p in potential_hotels:
        if "name" in p and p["name"] in place_to_index:
            hotel_indices.append(place_to_index[p["name"]])
        else:
            print(f"Warning: Hotel '{p.get('name', 'Unnamed Hotel')}' not found in cleaned_places.")

    attraction_indices = []
    for p in potential_attractions:
        if "name" in p and p["name"] in place_to_index:
            attraction_indices.append(place_to_index[p["name"]])
        else:
             print(f"Warning: Attraction '{p.get('name', 'Unnamed Attraction')}' not found in cleaned_places.")

    all_places_indices = [place_to_index[p["name"]] for p in cleaned_places]


    # สร้าง list ของเวลาที่ใช้ในแต่ละสถานที่
    visiting_time = [p["duration"] for p in cleaned_places]

    # ตรวจสอบ
    print("Hotels:", hotels_name)
    print("Attractions:", attractions_name)
    print("All Places:", all_places_name)
    print("hotel_indices:", hotel_indices)
    print("attraction_indices:", attraction_indices)
    print("Duration:", visiting_time)

    print("Total places after cleaning:", len(cleaned_places))
    print("Cleaned Places:", cleaned_places)

    # cleaned_places ใน matrix
    distance_matrix, time_matrix = get_travel_matrices(cleaned_places)
    print("Distance Matrix:", distance_matrix)
    print("Time Matrix:", time_matrix)

    # ใช้ตอน debug
    print("place_to_index:", place_to_index)
    print("hotel_indices:", hotel_indices)
    print("attraction_indices:", attraction_indices)


    # --- 3. Simulate the Multi-Objective Optimization ---
    # แปลงข้อมูลเป็นรูปแบบที่ run_optimizer ใช้
    data = {
        "all_places_name": all_places_name,
        "hotel_indices": hotel_indices,
        "attraction_indices": attraction_indices,
        "visiting_time": visiting_time,
        "score": [p["score"] for p in cleaned_places],
        "d": distance_matrix,
        "t": time_matrix,
        "day": trip_duration_days,
        "T_max": max_daily_hours,
        "budget": budget,                                  # ต้องเพิ่มเป็นพารามิเตอร์ของ solve_itinerary
        "c_visit": [p["cost"] for p in cleaned_places],
        "E": [p["E"] for p in cleaned_places],
        "L": [p["L"] for p in cleaned_places],
        "day_start": 6.0,   # หรือรับจากผู้ใช้
        "flexible": is_daily_limit_flexible,  
        "start_idx":start_idx,    # ✅ เพิ่ม
        "end_idx":end_idx,        # ✅ เพิ่ม


    }

    # เรียกฟังก์ชัน
    results = run_optimize(data)

    itineraries = []

    #Itinerary 1: "Optimized Route"
    optimized_plan = []
    for k, route in enumerate(results["daily_routes"]):
        # แปลง route จาก index → ชื่อสถานที่
        day_route = []
        if route:
            start_point = all_places_name[route[0][0]]
            day_route.append(start_point)
            for (i, j) in route:
                day_route.append(all_places_name[j])
        else:
            day_route = ["No route available"]

        # รวมข้อมูลต่อวัน
        optimized_plan.append({
            "day": k + 1,
            "route": day_route,
            "travel_time": round(results["daily_travel_time"][k], 2) if len(results["daily_travel_time"]) > k else None,
            "visit_time": round(results["daily_visit_time"][k], 2) if len(results["daily_visit_time"]) > k else None,
            "total_time": round(results["daily_total_time_spent"][k], 2) if len(results["daily_total_time_spent"]) > k else None,
            "distance": round(results["daily_distance"][k], 2) if len(results["daily_distance"]) > k else None
        })
    
    route_plan = []
    for k, route in enumerate(results["daily_routes"]):
        # a list of places from dictionary places (the same order as results["daily_routes"]["route"])
        print("Route for day", k+1, ":", route)
        # handle empty route safely
        if route:
            start_idx = route[0][0]
            start_place = next((place for place in potential_hotels + potential_attractions if place["name"] == all_places_name[start_idx]), None)
            daily_route = [start_place] if start_place is not None else []
            for destination_index in route:
                dest_idx = destination_index[1]
                dest_place = next((place for place in potential_hotels + potential_attractions if place["name"] == all_places_name[dest_idx]), None)
                if dest_place is not None:
                    daily_route.append(dest_place)
        else:
            daily_route = ["No route available"]
        route_plan.append(daily_route)
    # --- สรุปค่าใช้จ่ายรายวัน (สูตรเดียวกับสมการงบประมาณ (21)) ---
    daily_costs = []
    for route in results["daily_routes"]:
        fuel = sum(distance_matrix[i][j] / FC * Pfuel for (i, j) in route)
        visited_nodes = ([route[0][0]] + [j for (_, j) in route]) if route else []
        entry = sum(cleaned_places[n]["cost"] for n in visited_nodes
                    if not cleaned_places[n]["is_hotel"])
        daily_costs.append({"fuel": fuel, "entry": entry, "total": fuel + entry})
    fuel_cost = sum(c["fuel"] for c in daily_costs)
    entry_cost = sum(c["entry"] for c in daily_costs)

    itineraries.append({
        "title": "Optimized Route",
        "total_distance": round(results["total_distance"], 2),
        "total_time": round(sum(results["daily_total_time_spent"]), 2) if "daily_total_time_spent" in results else None,
        #"daily_routes": optimized_plan
        "daily_routes": route_plan,
        "raw_results": results,
        "cleaned_places": cleaned_places,
        "distance_matrix": distance_matrix,
        "time_matrix": time_matrix,
        "daily_costs": daily_costs,                    # [{fuel, entry, total}, ...] ต่อวัน
        "fuel_cost": round(fuel_cost, 2),              # ค่าน้ำมันรวม (บาท)
        "entry_cost": round(entry_cost, 2),            # ค่าเข้าชมรวม (บาท)
        "total_cost": round(fuel_cost + entry_cost, 2),
        "budget": budget,
    })

    print(itineraries)
    return itineraries


# get distance and time travel matrices from Geoapify Route Matrix API
def get_travel_matrices(places: list[dict]) -> tuple[list[list[float]], list[list[float]]]:
    api_key = st.secrets["GEOAPIFY_API_KEY"]
    # Prepare the list of coordinates
    coords = [{"location": [place['lon'], place['lat']]} for place in places]

    # Call the Geoapify Route Matrix API
    api_url = f"https://api.geoapify.com/v1/routematrix?apiKey={api_key}"
    request_body = {
        "mode": "drive",
        "sources": coords,
        "targets": coords
    }
    print(coords)
    print(request_body)
    print(api_url)

    try:
        response = requests.post(api_url, json=request_body)
        response.raise_for_status()  # Raise an exception for bad status codes
        resp_json = response.json()

        # read distance and time matrix from response json
        distance_matrix = []
        time_matrix = []
        for row in resp_json.get('sources_to_targets', []):
            distance_row = []
            time_row = []
            for cell in row:
                dist = cell.get('distance')
                time_val = cell.get('time')
                # ถ้าเป็น None (เส้นทางไม่ถึง) ให้ใช้ inf แทน
                distance_row.append((dist if dist is not None else float('inf')) / 1000)
                time_row.append((time_val if time_val is not None else float('inf')) / 3600)

            distance_matrix.append(distance_row)
            time_matrix.append(time_row)
        return distance_matrix, time_matrix
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to get distance matrix: {e}")
        return [], []
"""
# Mock function for offline testing (no API call)
def get_travel_matrices(places: list[dict]) -> tuple[list[list[float]], list[list[float]]]:
    n = len(places)
    distance_matrix = [[0 if i == j else abs(i - j) * 5 for j in range(n)] for i in range(n)]  # km
    time_matrix = [[0 if i == j else abs(i - j) * 0.5 for j in range(n)] for i in range(n)]    # hr
    print("⚙️ Mocked distance and time matrices generated.")
    return distance_matrix, time_matrix
"""

def run_optimize(data):
    all_places_name = data['all_places_name']
    H = set(data['hotel_indices'])
    A = set(data['attraction_indices'])
    S = data['start_idx']       # จุดเริ่มต้น (index)
    F = data['end_idx']         # จุดสิ้นสุด (index)
    A_score = A - {S, F}        # สถานที่ที่นับคะแนน (ไม่รวมจุดเริ่ม/จบ)
    visiting_time = data['visiting_time']
    E = data['E']
    L = data['L']
    d = data['d']
    t = data['t']
    s = data['score']
    day = data['day']
    T_max = data['T_max']
    flexible = data['flexible']
    B = data['budget']
    c_visit = data['c_visit']
    day_start = data.get('day_start', 6.0)
    n = len(all_places_name)
    N = set(range(n))
    K = set(range(day))
    first_day = 0          # ✅ เพิ่ม (ใช้ในสมการ (5)(6)(7)(8) แต่หายไป)
    last_day = day - 1     # ✅ เพิ่ม (ใช้ในสมการ (3)(4)(6)(8) แต่หายไป)
    v = visiting_time      # ✅ เพิ่ม (สมการ (11) ใช้ v[j] แต่ประกาศชื่อ visiting_time)
    BIG_M = 100

    # (22) ค่าน้ำมัน c_fuel_ij = (d_ij / FC) * Pfuel
    c_travel = [[(d[i][j]/FC)*Pfuel if (i != j and d[i][j] != float("inf")) else 0.0
                 for j in range(n)] for i in range(n)]

    

    model = Model()

    # ==================== Decision Variables ====================
    x = [[[model.add_var(var_type=BINARY) for k in K] for j in N] for i in N]  # (16)
    y = [[model.add_var(var_type=BINARY) for k in K] for i in N]               # (16)
    u = [[model.add_var(var_type=INTEGER, lb=0, ub=n-1) for k in K] for i in N]
    a = [[model.add_var(var_type=CONTINUOUS, lb=0) for _ in K] for _ in N]
    
    # ถ้าเส้นทางเป็น inf ให้ใช้เวลา/ระยะทางมากๆ แทน (โมเดลจะหลีกเลี่ยงเอง)
    for i in N:
        for j in N:
            if i != j and t[i][j] == float('inf'):
                t[i][j] = 100.0   # 100 ชั่วโมง (มากพอที่โมเดลจะไม่เลือก)
                d[i][j] = 5000.0  # 5000 กม.

# ==================== (1) Objective ====================
    # โค้ดเดิม: 
    # model.objective = maximize(xsum(s[i] * y[i][k] for i in A_score for k in K))
    
    # โค้ดที่แก้ไข: เน้นคะแนนเป็นหลัก (คูณ 1000) และลบด้วยระยะทางเดินทางเพื่อบังคับให้เลือกทางที่สั้นที่สุด
    W_score = 1.0  
    W_distance =0.1
    model.objective = maximize(
        (W_score * xsum(s[i] * y[i][k] for i in A_score for k in K)) - 
        (W_distance * xsum(d[i][j] * x[i][j][k] for k in K for i in N for j in N if i != j))
    )
    # ==================== Constraints ====================
    # (2) แต่ละสถานที่เที่ยวถูกเยี่ยมได้ไม่เกิน 1 ครั้งตลอดทริป
    for i in A:
        model += xsum(y[i][k] for k in K) <= 1

    # (3) ออกจาก i = y_ik  (ยกเว้น f ในวันสุดท้าย)
    for k in K:
        for i in A:
            if not (i == F and k == last_day):
                model += xsum(x[i][j][k] for j in N if j != i) == y[i][k]

    # (4) เข้าสู่ i = y_ik  (ยกเว้น s ในวันแรก)
    for k in K:
        for i in A:
            if not (i == S and k == first_day):
                model += xsum(x[j][i][k] for j in N if j != i) == y[i][k]

    # (5) วันแรกออกจากจุดเริ่มต้น s 1 เส้นทาง
    model += xsum(x[S][j][first_day] for j in N if j != S) == 1
    if S in A:   # (5.1) s เป็นสถานที่เที่ยว: ต้องแวะ, ถึงตอนเริ่มวัน, ลำดับ 0
        model += y[S][first_day] == 1
        model += a[S][first_day] == day_start
        model += u[S][first_day] == 0

    # (6) วันสุดท้ายเข้าสู่จุดสิ้นสุด f 1 เส้นทาง
    model += xsum(x[i][F][last_day] for i in N if i != F) == 1
    if F in A:   # (6.1) f เป็นสถานที่เที่ยว: ต้องแวะ
        model += y[F][last_day] == 1

    # (7) วันที่ 2..K เริ่มด้วยการออกจากที่พัก 1 แห่ง
    for k in K:
        if k != first_day:
            model += xsum(x[h][j][k] for h in H for j in N if j != h) == 1
    if S in H:   # (7.1) วันแรกเริ่มที่ที่พัก
        model += xsum(x[h][j][first_day] for h in H for j in N if j != h) == 1
    if S in A:   # (7.2) วันแรกเริ่มที่สถานที่เที่ยว: ห้ามออกจากที่พัก
        model += xsum(x[h][j][first_day] for h in H for j in N if j != h) == 0

    # (8) วันที่ 1..K-1 กลับมาที่ที่พัก 1 แห่ง
    for k in K:
        if k != last_day:
            model += xsum(x[i][h][k] for h in H for i in N if i != h) == 1
    if F in H:   # (8.1) วันสุดท้ายจบที่ที่พัก
        model += xsum(x[i][h][last_day] for h in H for i in N if i != h) == 1
    if F in A:   # (8.2) วันสุดท้ายจบที่สถานที่เที่ยว: ห้ามกลับที่พัก
        model += xsum(x[i][h][last_day] for h in H for i in N if i != h) == 0

    # (9) MTZ ป้องกัน subtour
    for k in K:
        for i in A:
            for j in A:
                if i != j:
                    model += u[i][k] - u[j][k] + n * x[i][j][k] <= n - 1

    # (10) ขอบเขตของ u : y <= u <= (n-1)*y  (ยกเว้น (s, วันแรก))
    for i in A:
        for k in K:
            if not (i == S and k == first_day):
                model += u[i][k] >= y[i][k]
                model += u[i][k] <= (n - 1) * y[i][k]

    # (11) เวลารวมต่อวันไม่เกิน T_max (บังคับเมื่อผู้ใช้ไม่ยอมให้ยืดหยุ่นเวลา)
    if not flexible:
        for k in K:
            model += (xsum(t[i][j] * x[i][j][k] for i in N for j in N if i != j)
                      + xsum(v[j] * y[j][k] for j in N)) <= T_max

    # (12) a_ik >= E_i - M(1 - y_ik)
    for k in K:
        for i in A:
            model += a[i][k] >= E[i] - BIG_M * (1 - y[i][k])

    # (13) a_ik + v_i <= L_i + M(1 - y_ik)
    for k in K:
        for i in A:
            model += a[i][k] + v[i] <= L[i] + BIG_M * (1 - y[i][k])

    # (14) เวลาสะสม: a_jk >= a_ik + v_i + t_ij - M(1 - x_ijk)
    for k in K:
        for i in A:
            for j in A:
                if i != j:
                    model += a[j][k] >= a[i][k] + v[i] + t[i][j] - BIG_M * (1 - x[i][j][k])

    # (15) สถานที่แรกของวัน: a_jk >= day_start + t_ij - M(1 - x_ijk), i in H ∪ {s}
    for k in K:
        for i in (H | {S}):
            for j in A:
                if i != j:
                    model += a[j][k] >= day_start + t[i][j] - BIG_M * (1 - x[i][j][k])

    # (16), (17) x, y เป็นไบนารี -> กำหนดตอนสร้างตัวแปรแล้ว

    # (18) ที่พักต่อเนื่องข้ามวัน: ออกจาก q วัน k = เข้า q วัน k-1
    for k in K:
        if k >= 1:
            for q in H:
                model += xsum(x[q][j][k] for j in A) == xsum(x[i][q][k - 1] for i in A)

    # (20) ห้ามเดินทางที่พัก -> ที่พักโดยตรง
    for k in K:
        for q in H:
            for r in H:
                if q != r:
                    model += x[q][r][k] == 0

    # (21) งบประมาณ: ค่าน้ำมัน + ค่าเข้าชม <= B
    model += (xsum(c_travel[i][j] * x[i][j][k] for k in K for i in N for j in N if i != j)
              + xsum(c_visit[i] * y[i][k] for i in A for k in K)) <= B

    # -------------------------
    #Optimizer
    # -------------------------

    results = {
        "total_distance": 0,
        "objective_value": None,
        "daily_routes": [],        # [(from_place, to_place), ...] ต่อวัน
        "daily_travel_time": [],   # travel time ต่อวัน
        "daily_visit_time": [],    # visit time ต่อวัน
        "daily_total_time_spent": [],    # total time ต่อวัน
        "daily_distance": [],      # distance ต่อวัน
        "daily_arrival": [],  #  เพิ่มเก็บเวลาถึงแต่ละสถานที่
        
        "total_slack": None,
        "penalty_value": None
    }

    status = model.optimize()
    if status == model.status.OPTIMAL or status == model.status.FEASIBLE:

        results["objective_value"] = model.objective_value
        total_dist = 0
        total_fuel = 0.0
        total_entry = 0.0

        print("\n∘₊✧─────✧₊∘ ผลลัพธ์ของโปรแกรมวางแผนเส้นทาง ∘₊✧─────✧₊∘\n")
        print(f"objective value: {model.objective_value:.2f}\n")

        #slack & penalty
        if flexible == True:
            penalty_value = sum((1 - sum(y[i][k].x for k in K if y[i][k].x is not None)) for i in A)
            results["penalty_value"] = penalty_value
            if penalty_value > 0.00:
                print("อาจจะมีทำการตัดสถานที่ท่องเที่ยวออกบางแห่ง เพื่อให้ครอบคลุมการท่องเที่ยวทั้งหมด\n")

        #แสดงเส้นทาง
        for k in K:
            day_dist = sum(d[i][j] * x[i][j][k].x for i in N for j in N if x[i][j][k].x is not None)
            total_dist += day_dist
            total_travel_time = sum(t[i][j]*x[i][j][k].x for i in N for j in N if i!=j and x[i][j][k].x is not None)
            total_visit_time = sum(visiting_time[j]*sum(x[i][j][k].x for i in N if i!=j and x[i][j][k].x is not None) for j in N if j not in H)
            total_time_spent = total_travel_time + total_visit_time
            day_dist = sum(d[i][j] * x[i][j][k].x for i in N for j in N if x[i][j][k].x is not None)

            print(f"Route for day {k+1}:")
            route = []

            # หาโรงแรมเริ่มต้นของวัน k
           # หาจุดเริ่มต้นของวัน k
            start_point = None
            if k == 0:
                start_point = S          # ✅ วันแรกเริ่มที่ S แน่นอน
            else:
                for q in H:               # วันอื่นๆ หาจากโรงแรมเหมือนเดิม
                    for j in N:
                        if j != q and x[q][j][k].x is not None and x[q][j][k].x > 0.5:
                            start_point = q
                            break
                    if start_point is not None:
                        break

            if start_point is None:
                print(f"  No route found for day {k+1}")
                results["daily_routes"].append([])
                results["daily_travel_time"].append(0)
                results["daily_visit_time"].append(0)
                results["daily_total_time_spent"].append(0)
                results["daily_distance"].append(0)
                continue

            current = start_point        # ✅ ใช้ start_point แทน start_hotel

            while True:
                found = False
                for j in N:
                    if j != current and x[current][j][k].x is not None and x[current][j][k].x > 0.5:
                        route.append((current, j))
                        if j in H and j == start_point:
                            found = False
                            break
                        
                        current = j
                        found = True
                        break
                if not found:
                    break

            results["daily_routes"].append(route)

            for i, j in route:
                print(f"  From {all_places_name[i]} to {all_places_name[j]}")
            # แสดงเวลาในแต่ละวัน
            print(f"  Travel time: {total_travel_time:.1f} hr, Visit time: {total_visit_time:.1f} hr, Total time: {total_time_spent:.1f} hr")
            # แสดงระยะทางในแต่ละวัน
            print(f"  ระยะทางรวมวันที่ {k+1}: {day_dist:.2f} km")
            # แสดงค่าใช้จ่ายในแต่ละวัน (ใช้ c_travel / c_visit ชุดเดียวกับสมการงบประมาณ (21))
            day_fuel = sum(c_travel[i][j] * x[i][j][k].x for i in N for j in N
                           if i != j and x[i][j][k].x is not None)
            day_entry = sum(c_visit[i] * y[i][k].x for i in A if y[i][k].x is not None)
            total_fuel += day_fuel
            total_entry += day_entry
            print(f"  ค่าใช้จ่ายวันที่ {k+1}: ค่าน้ำมัน {day_fuel:,.2f} + ค่าเข้าชม {day_entry:,.2f} = {day_fuel + day_entry:,.2f} บาท\n")

            results["daily_travel_time"].append(total_travel_time)
            results["daily_visit_time"].append(total_visit_time)
            results["daily_total_time_spent"].append(total_time_spent)
            results["daily_distance"].append(day_dist)

        results["total_distance"] = total_dist
        print(f"ระยะทางรวมทั้งหมด: {total_dist:.2f} km\n")
        used = total_fuel + total_entry
        print(f"ค่าน้ำมันรวม: {total_fuel:,.2f} บาท")
        print(f"ค่าเข้าชมรวม: {total_entry:,.2f} บาท")
        print(f"ค่าใช้จ่ายรวม: {used:,.2f} บาท (งบ {B:,.0f} บาท คงเหลือ {B - used:,.2f} บาท)\n")

    else:
        print("\nNo feasible solution found or solve failed\n")

    return results


# --- Sample input for testing solve_itinerary() ---

potential_hotels = [
    {"name": "Bangkok Hotel", "lat": 13.7563, "lon": 100.5018},
    {"name": "Second Hotel", "lat": 14.7563, "lon": 100.5018}
    ]
potential_attractions = [
    {"name": "Temple of Dawn", "lat": 13.7436, "lon": 100.4889, "duration": 1,"score": 9,
    "cost": 200,"E": 7.0,  "L": 10.0},
    {"name": "Grand Palace", "lat": 13.7500, "lon": 100.4913, "duration": 2,"score": 7,
    "cost": 250,"E": 8.0,  "L": 12.0},
    {"name": "Chatuchak Market", "lat": 13.7996, "lon": 100.5500, "duration": 3,"score": 8.5,
    "cost": 100,"E": 8.0,  "L": 16.0},
    ]
trip_duration_days = 1
budget = 3000
max_daily_hours = 5
is_daily_limit_flexible = True
objective_weights = {
    "distance_weight": 0.7,
    "time_balance_weight": 0.3
}

# เรียกฟังก์ชันทดสอบ
itineraries = solve_itinerary(
    potential_hotels=potential_hotels,
    potential_attractions=potential_attractions,
    start_point_name="Bangkok Hotel",     # ✅ เพิ่ม
    end_point_name="Bangkok Hotel",       # ✅ เพิ่ม (หรือจะต่างกันก็ได้)
    trip_duration_days=trip_duration_days,
    max_daily_hours=max_daily_hours,
    is_daily_limit_flexible=is_daily_limit_flexible,
    objective_weights=objective_weights,
    budget=budget
)

# ดูผลลัพธ์
print("\n=== TEST RESULT ===")
for itinerary in itineraries:
    print(itinerary)

