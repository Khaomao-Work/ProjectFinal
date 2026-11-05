from optimiser import solve_itinerary, FC, Pfuel

BUDGET = 3000

# --- ชุดข้อมูลทดสอบ เหมือนในหน้าเว็บ ---
DATASETS = {
    "bkk": {
        "label": "กรุงเทพฯ",
        "names": [
            "โรงแรมย่านสุขุมวิท", "โรงแรมย่านบางลำพู", "โรงแรมย่านอารีย์",
            "สวนลุมพินี", "ตลาดปากคลองตลาด", "วัดโพธิ์",
            "พระบรมมหาราชวัง", "ภูเขาทอง วัดสระเกศ", "จิม ทอมป์สัน เฮาส์",
            "สยามพารากอน", "ไอคอนสยาม", "สวนจตุจักร",
        ],
        "coords": [
            (13.7380, 100.5610), (13.7620, 100.4990), (13.7790, 100.5450),
            (13.7314, 100.5414), (13.7435, 100.4968), (13.7465, 100.4927),
            (13.7500, 100.4913), (13.7539, 100.5069), (13.7490, 100.5280),
            (13.7461, 100.5347), (13.7265, 100.5100), (13.8030, 100.5530),
        ],
        "score": [0, 0, 0, 8, 7, 10, 10, 8, 7, 7, 8, 6],
        "visit": [0.0, 0.0, 0.0, 1.5, 1.0, 2.0, 2.5, 1.0, 1.5, 2.0, 2.0, 1.5],
        "cost":  [0, 0, 0, 0, 0, 300, 500, 50, 200, 0, 0, 0],
        "open":  [0.0, 0.0, 0.0, 5.0, 0.0, 8.0, 8.5, 7.5, 9.0, 10.0, 10.0, 5.0],
        "close": [24.0, 24.0, 24.0, 21.0, 24.0, 18.5, 15.5, 19.0, 18.0, 22.0, 22.0, 21.0],
    },
    "phuket": {
        "label": "ภูเก็ต",
        "names": [
            "โรงแรมในตัวเมืองภูเก็ต", "รีสอร์ทหาดป่าตอง", "รีสอร์ทหาดราไวย์",
            "แหลมพรหมเทพ", "หาดป่าตอง", "จุดชมวิวกะรน",
            "พระใหญ่ภูเก็ต", "วัดฉลอง", "ย่านเมืองเก่าภูเก็ต",
            "หาดกะตะ", "หาดกมลา", "หาดไนยาง",
        ],
        "coords": [
            (7.8850, 98.3860), (7.8930, 98.2985), (7.7840, 98.3250),
            (7.7621, 98.3057), (7.8960, 98.2960), (7.7900, 98.3010),
            (7.8278, 98.3125), (7.8460, 98.3380), (7.8840, 98.3880),
            (7.8190, 98.2980), (7.9490, 98.2800), (8.0950, 98.2970),
        ],
        "score": [0, 0, 0, 10, 8, 8, 10, 9, 9, 7, 7, 6],
        "visit": [0.0, 0.0, 0.0, 1.0, 2.0, 1.0, 1.5, 1.0, 2.0, 2.0, 2.0, 2.0],
        "cost":  [0, 0, 0, 0, 200, 0, 0, 0, 200, 100, 100, 40],
        "open":  [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 8.0, 7.0, 9.0, 0.0, 0.0, 0.0],
        "close": [24.0, 24.0, 24.0, 24.0, 24.0, 24.0, 19.0, 17.0, 21.0, 24.0, 24.0, 24.0],
    },
}

hotel_indices = [0, 1, 2]
attraction_indices = [3, 4, 5, 6, 7, 8, 9, 10, 11]

def build_places(ds):
    hotels = [{"name": ds["names"][i], "lat": ds["coords"][i][0], "lon": ds["coords"][i][1]}
              for i in hotel_indices]
    attractions = [{
        "name": ds["names"][i], "lat": ds["coords"][i][0], "lon": ds["coords"][i][1],
        "duration": ds["visit"][i], "score": ds["score"][i], "cost": ds["cost"][i],
        "open_time": ds["open"][i], "close_time": ds["close"][i],
    } for i in attraction_indices]
    return hotels, attractions

# --- เลือกกรณีทดสอบ ---
CASES = {
    "1": {"data": "bkk", "start": 0, "end": 0, "days": 1, "desc": "เที่ยววันเดียว กรุงเทพฯ"},
    "2": {"data": "bkk", "start": 3, "end": 9, "days": 1, "desc": "เริ่ม-จบที่สถานที่ กรุงเทพฯ"},
    "3": {"data": "phuket", "start": 0, "end": 2, "days": 3, "desc": "หลายวัน ภูเก็ต"},
    "4": {"data": "phuket", "start": 3, "end": 8, "days": 3, "desc": "เริ่ม-จบที่สถานที่ ภูเก็ต"},
}

print("เลือกกรณีทดสอบ:")
for k, v in CASES.items():
    print(f"  {k}) {v['desc']}")

choice = input("ป้อนเลข 1-4: ").strip()
if choice not in CASES:
    print("เลือกไม่ถูกต้อง ใช้กรณีที่ 1 แทน")
    choice = "1"

case = CASES[choice]
ds = DATASETS[case["data"]]
potential_hotels, potential_attractions = build_places(ds)

start_point = ds["names"][case["start"]]
end_point = ds["names"][case["end"]]
trip_days = case["days"]

print(f"\n{'='*50}")
print(f"พื้นที่: {ds['label']}")
print(f"เริ่ม: {start_point}")
print(f"จบ: {end_point}")
print(f"จำนวนวัน: {trip_days}")
print(f"งบประมาณ: {BUDGET:,} บาท")
print(f"{'='*50}\nกำลังคำนวณ...\n")

# --- เรียกโมเดล ---
itineraries = solve_itinerary(
    potential_hotels=potential_hotels,
    potential_attractions=potential_attractions,
    start_point_name=start_point,
    end_point_name=end_point,
    trip_duration_days=trip_days,
    max_daily_hours=12,
    is_daily_limit_flexible=True,
    budget=3000,
    objective_weights={"distance_weight": 0.7, "time_balance_weight": 0.3}
)

# --- แสดงผล ---
if not itineraries:
    print("❌ ไม่สามารถจัดเส้นทางได้")
else:
    plan = itineraries[0]
    if not plan["daily_routes"]:
        print("⚠️ ไม่พบคำตอบที่เป็นไปได้")
    else:
        print(f"✅ สำเร็จ! ระยะทางรวม: {plan['total_distance']} กม.\n")
        
        day_costs = plan.get("daily_costs", [])
        fuel_total = plan["fuel_cost"]
        entry_total = plan["entry_cost"]
        used = plan["total_cost"]
        
        print(f"ค่าใช้จ่ายรวม: {used:,.0f} บาท (งบ {BUDGET:,.0f})")
        print(f"  ค่าน้ำมัน: {fuel_total:,.0f} บาท")
        print(f"  ค่าเข้าชม: {entry_total:,.0f} บาท")
        print(f"  คงเหลือ: {BUDGET - used:,.0f} บาท\n")
        
        print("--- แผนการเดินทางรายวัน ---")
        for k, route in enumerate(plan["daily_routes"]):
            cost_info = ""
            if k < len(day_costs):
                c = day_costs[k]
                cost_info = f"  | ใช้ {c['total']:,.0f} บาท"
            print(f"\nวันที่ {k+1} {cost_info}")
            for place in route:
                if isinstance(place, dict):
                    print(f"  - {place['name']}")
                else:
                    print(f"  - {place}")

print("\nจบการทำงาน")
