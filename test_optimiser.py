import streamlit as st
from optimiser import solve_itinerary, FC, Pfuel, fmt_time
from export_matrices import generate_styled_matrices_excel
from visualization import plot_route_map_static

st.set_page_config(page_title="ระบบจัดเส้นทาง", layout="wide")
st.title("🚗 ระบบจัดเส้นทางท่องเที่ยวอัจฉริยะ")

def to_timetable(daily_schedule):
    """แปลง daily_schedule จาก optimiser: [[(ชื่อ, ถึง, ออก), ...] ต่อวัน]
    (เวลาเป็นเลขชั่วโมง หรือ None) -> [[{name, arrival, departure}, ...] ต่อวัน] (เวลาเป็นสตริง)"""
    out = []
    for day in daily_schedule or []:
        out.append([
            {
                "name": name,
                "arrival": fmt_time(arr) if arr is not None else "-",
                "departure": fmt_time(dep) if dep is not None else "-",
            }
            for (name, arr, dep) in day
        ])
    return out



def find_unreachable(dist_matrix, names, km_limit=4999.0):
    """คืนชื่อสถานที่ที่ออกไปหาที่อื่นไม่ได้เลย (optimiser แทนค่า inf ด้วย 5000 กม.)
    มักเกิดจากพิกัดอยู่กลางน้ำ/ไม่ติดถนน ทำให้ Geoapify คืนค่า null"""
    n = len(dist_matrix)
    return [names[i] for i in range(n)
            if all(dist_matrix[i][j] >= km_limit for j in range(n) if j != i)]


BUDGET = 1000   # งบรวมทั้งทริป (บาท) ใช้ทั้งส่งเข้าโมเดลและแสดงผล

#  ============================================================
# ชุดข้อมูลทดสอบ 2 ชุด
#   - "bkk"    : กรุงเทพฯ  (ใช้กับทริปวันเดียว)
#   - "phuket" : ภูเก็ต    (ใช้กับทริปหลายวัน / ต่างจังหวัด)
# ทุกชุดเรียงเหมือนกัน: ที่พักมาก่อน (จำนวนระบุใน "n_hotels") ตามด้วยสถานที่ท่องเที่ยว
# หมายเหตุ: สถานที่ที่ใช้เป็น "จุดเริ่มต้น" ต้องเปิดไม่เกินเวลาเริ่มวัน (day_start = 8.0 ในโมเดล)
# ============================================================
DATASETS = {
    "bkk": {
            "label": "กรุงเทพมหานคร",
            "n_hotels": 3,   # index 0-2 = ที่พัก, 3-11 = สถานที่ท่องเที่ยว 9 แห่ง
            "names": [
                # ที่พัก (0-2)
                "สุเนต์ตา โฮสเทล", "โรงแรมที่นี่ ตลาดน้อย", "Vintana Siam Bangkok Hotel",
                # สถานที่ท่องเที่ยว (3-11)
                "วัดพระศรีรัตนศาสดาราม (วัดพระแก้ว)", "วัดอรุณราชวรารามราชวรมหาวิหาร (วัดแจ้ง)", "วัดพระเชตุพนวิมลมังคลาราม (วัดโพธิ์)",
                "มิวเซียมสยาม (Museum Siam)", "ถนนเยาวราช", "ถนนบรรทัดทอง",
                "สยามสแควร์ และ สยามพารากอน", "หอศิลปวัฒนธรรมแห่งกรุงเทพมหานคร (BACC)", "ไอคอนสยาม (ICONSIAM)",
            ],
            "coords": [
                # ที่พัก (0-2)
                (13.7596, 100.4981), (13.7337, 100.5135), (13.7478, 100.5222),
                # สถานที่ท่องเที่ยว (3-11)
                (13.7516, 100.4927), (13.7437, 100.4888), (13.7465, 100.4930),
                (13.7442, 100.4941), (13.7412, 100.5083), (13.7429, 100.5232),
                (13.7462, 100.5347), (13.7468, 100.5303), (13.7266, 100.5105),
            ],
            "score": [0, 0, 0,
                      10, 10, 9, 8, 10, 9, 9, 8, 9],
            "visit": [0.0, 0.0, 0.0,
                      1.5, 1.0, 1.0, 1.5, 1.5, 1.5, 2.0, 1.5, 2.0],
            "cost":  [0, 0, 0,                                      # Fixed cost: ราคาที่พักต่อคืน (บาท)
                      0, 0, 0, 100, 0, 0, 0, 0, 0],                       # Fixed cost: ค่าบัตรเข้าชมสถานที่ (คนไทย)
            "open":  [0.0, 0.0, 0.0,
                      8.5, 8.0, 8.0, 10.0, 17.0, 16.0, 10.0, 10.0, 10.0],
            "close": [24.0, 24.0, 24.0,
                      16.5, 18.0, 19.5, 18.0, 24.0, 24.0, 22.0, 20.0, 22.0],
        },
      "phuket": {

        "label": "ภูเก็ต",
        "n_hotels": 5,   # index 0-4 = ที่พัก, 5-19 = สถานที่ท่องเที่ยว 15 แห่ง
        "names": [
            # ที่พัก (0-4)
            "บลูมังกี้ ฮับ แอนด์ โฮเทล ภูเก็ต", "Xinlor House", "Isara boutique hotel Phuket old town",
            "Aqua Maya Phuket", "โรงแรมโนโวเทล ภูเก็ต กะตะ อวิสต้า รีสอร์ท แอนด์ สปา",
            # สถานที่ท่องเที่ยว (5-19)
            "ย่านเมืองเก่าภูเก็ต (ถนนถลาง - ซอยรมณีย์)", "ถนนคนเดินหลาดใหญ่ (Sunday Walking Street)", "วัดไชยธาราราม (วัดฉลอง)",
            "พระพุทธมิ่งมงคลเอกนาคคีรี (พระใหญ่ภูเก็ต)", "แหลมพรหมเทพ", "จุดชมวิวกังหันลม (Windmill Viewpoint)",
            "แหลมกระทิง", "จุดชมวิวสามอ่าว (Karon Viewpoint)", "หาดป่าตอง",
            "หาดในหาน", "หาดไม้ขาว (จุดชมเครื่องบินลงจอด)", "เกาะเฮ (Coral Island)",
            "Three Monkeys Restaurant", "Ma Doo Bua Phuket (มาดูบัว ภูเก็ต)", "Rock Beach Swing Phuket",
        ],
        "coords": [
            # ที่พัก (0-4)
            (7.8842, 98.3934), (7.8860, 98.3886), (7.8855, 98.3877),
            (7.8936, 98.3033), (7.8263, 98.2965),
            # สถานที่ท่องเที่ยว (5-19)
            (7.8848, 98.3892), (7.8847, 98.3885), (7.8468, 98.3370),
            (7.8276, 98.3128), (7.7621, 98.3057), (7.7697, 98.3065),
            (7.7753, 98.2995), (7.7975, 98.3022), (7.8965, 98.2963),
            (7.7766, 98.3056), (8.1135, 98.3023), (7.7453, 98.3746),
            (7.8961, 98.3526), (8.0268, 98.3338), (7.7981, 98.2925),
        ],

        "score": [0, 0, 0, 0, 0,
                  10, 9, 9, 9, 9, 9, 9, 9, 9,
                  9, 8, 9, 9, 9, 8],
        "visit": [0.0, 0.0, 0.0, 0.0, 0.0,
                  1.0, 1.5, 1.0, 1.0, 1.0, 2.0, 1.5, 1.0, 2.0,
                  2.0, 2.0, 2.0, 2.0, 2.0, 1.0],
        "cost":  [0, 0, 0, 0, 0,             
                  0, 0, 0, 0, 0, 0, 0, 0, 0,           
                  0, 0, 0, 0, 350, 250],             #คาเฟ่/ค่าเข้าจุดถ่ายรูป
        "open":  [0.0, 0.0, 0.0, 0.0, 0.0,
                  8.0, 16.0, 8.0, 9.0, 0.0, 0.0, 6.0, 0.0, 0.0,
                  0.0, 6.0, 8.0, 10.0, 11.0, 9.0],
        "close": [23.5, 22.0, 19.0, 24.0, 24.0,
                  18.0, 22.0, 17.0, 18.0, 24.0, 24.0, 18.0, 24.0, 24.0,
                  24.0, 18.0, 16.5, 22.0, 19.0, 18.0],
    },
}

# ภูเก็ต + สนามบิน: ใช้ชุด phuket เดิม แล้วต่อท้ายด้วยสนามบิน 2 โหนด (index 20 = ขาไป, 21 = ขากลับ)
# แยกเป็น 2 โหนดพิกัดเดียวกัน เพราะโมเดลให้สถานที่เที่ยวถูกเยี่ยมได้ไม่เกิน 1 ครั้งตลอดทริป (สมการ (2))
# ถ้าใช้โหนดเดียวเป็นทั้งจุดเริ่มและจุดจบในทริปหลายวัน โมเดลจะ infeasible
# (ไม่เพิ่มสนามบินใน "phuket" เดิม เพื่อไม่ให้โผล่เป็นสถานที่ลอย ๆ ในเคส 3-4)
_AIRPORT = (8.1132, 98.3169)   # สนามบินนานาชาติภูเก็ต (HKT) พิกัดโดยประมาณ
_p = DATASETS["phuket"]
DATASETS["phuket_airport"] = {
    "label": "ภูเก็ต (เริ่ม-จบที่สนามบิน)",
    "n_hotels": _p["n_hotels"],
    "names": _p["names"] + ["สนามบินภูเก็ต (ขาไป)", "สนามบินภูเก็ต (ขากลับ)"],
    "coords": _p["coords"] + [_AIRPORT, _AIRPORT],
    "score": _p["score"] + [0, 0],          # สนามบินไม่นับคะแนน
    "visit": _p["visit"] + [0.0, 0.0],
    "cost":  _p["cost"] + [0, 0],
    "open":  _p["open"] + [0.0, 0.0],       # เปิด 24 ชม. (จุดเริ่มต้องเปิดไม่เกินเวลาเริ่มวัน)
    "close": _p["close"] + [24.0, 24.0],
}

def build_places(ds):
    hotel_indices = list(range(ds["n_hotels"]))                                   # ที่พักมาก่อน
    attraction_indices = list(range(ds["n_hotels"], len(ds["names"])))           # ที่เหลือคือสถานที่เที่ยว
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
    "1) เที่ยววันเดียว: เริ่ม-จบที่พักเดียวกัน (บ้าน) — กรุงเทพฯ": {
        "data": "bkk", "start": 0, "end": 0, "days": 1,
    },
    "2) เที่ยววันเดียว: เริ่ม-จบที่สถานที่ท่องเที่ยว — กรุงเทพฯ": {
        "data": "bkk", "start": 3, "end": 9, "days": 1,      # สวนลุมพินี -> สยามพารากอน
    },
    "3) เที่ยวหลายวัน: เริ่ม-จบที่ที่พัก — ภูเก็ต": {
        "data": "phuket", "start": 0, "end": 2, "days": 3,   # ในเมืองภูเก็ต -> ราไวย์
    },
    "4) เที่ยวหลายวัน: เริ่ม-จบที่สถานที่ท่องเที่ยว — ภูเก็ต": {
        "data": "phuket", "start": 5, "end": 10, "days": 3,  # แหลมพรหมเทพ -> เมืองเก่าภูเก็ต
    },
    "5) เที่ยวหลายวัน: เริ่ม-จบที่สนามบิน — ภูเก็ต": {
        "data": "phuket_airport", "start": 20, "end": 21, "days": 3,   # สนามบินขาไป -> สนามบินขากลับ
    },
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
BUDGET = ds.get("budget", BUDGET)   # ใช้งบของชุดข้อมูล (ถ้ามี)
potential_hotels, potential_attractions = build_places(ds)

start_point = ds["names"][case["start"]]
end_point = ds["names"][case["end"]]
trip_days = case["days"]

# ============================================================
# ส่วนแสดงผล Streamlit
# ============================================================
if st.button("ประมวลผลเส้นทาง"):
    with st.spinner(f"กำลังคำนวณเส้นทางแบบ {trip_days} วัน..."):
        itineraries = solve_itinerary(
            potential_hotels=potential_hotels,
            potential_attractions=potential_attractions,
            start_point_name=start_point,
            end_point_name=end_point,
            trip_duration_days=trip_days,
            max_daily_hours=8,
            is_daily_limit_flexible=False,
            budget=BUDGET,
        )

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

        if not plan["daily_routes"]:
            st.warning("โมเดลไม่พบคำตอบที่เป็นไปได้ (infeasible) ดูรายละเอียดใน terminal")
            bad = find_unreachable(plan.get("distance_matrix") or [], ds["names"])
            if bad:
                st.error("Geoapify หาเส้นทางถนนไปยังสถานที่เหล่านี้ไม่ได้ "
                         "(พิกัดอาจอยู่กลางน้ำหรือไม่ติดถนน): " + ", ".join(bad))
        else:
            st.success(f"✅ ประมวลผลสำเร็จ! ระยะทางรวมทั้งหมด: {plan['total_distance']} กม.")
# ---------------- สรุปงบประมาณ ----------------
        day_costs = plan.get("daily_costs", []) if plan["daily_routes"] else []
        if day_costs:
            fuel_total = plan["fuel_cost"]
            entry_total = plan["entry_cost"]
            used = plan["total_cost"]
            b1, b2, b3, b4, b5 = st.columns(5)
            b1.metric("งบประมาณที่ตั้งไว้", f"{BUDGET:,.0f} บาท")
            b2.metric("ใช้ไปทั้งหมด", f"{used:,.0f} บาท")
            b3.metric("คงเหลือ", f"{BUDGET - used:,.0f} บาท")
            b4.metric("ค่าน้ำมัน", f"{fuel_total:,.0f} บาท")
            b5.metric("ค่าเข้าชม", f"{entry_total:,.0f} บาท")
            if used > BUDGET + 1e-6:
                st.warning(f"ค่าใช้จ่ายเกินงบ {used - BUDGET:,.0f} บาท")
            st.caption(f"ค่าน้ำมันคิดจากอัตรา {FC} กม./ลิตร ราคา {Pfuel} บาท/ลิตร "
                       "(ไม่รวมค่าทางด่วนและค่าจอดรถ)")

            
        col1, col2 = st.columns([1.2, 1])

        with col1:
            st.subheader("🗺️ กราฟเส้นทางท่องเที่ยว")
            n_days = len(plan["daily_routes"])
            tabs = st.tabs(["ภาพรวม"] + [f"วันที่ {k+1}" for k in range(n_days)])

            for t_idx, tab in enumerate(tabs):
                with tab:
                    fig = plot_route_map_static(
                        results=plan["raw_results"],
                        cleaned_places=plan["cleaned_places"],
                        timetable_data=to_timetable(plan.get("daily_schedule")),
                        day=None if t_idx == 0 else t_idx - 1,
                    )
                    st.pyplot(fig)

        with col2:
            st.subheader("📋 รายละเอียดแผนการเดินทาง")
            for k, route in enumerate(plan["daily_routes"]):
                cost_txt = ""
                if k < len(day_costs):
                    c = day_costs[k]
                    cost_txt = (f" — น้ำมัน {c['fuel']:,.0f} + เข้าชม {c['entry']:,.0f}"
                                f" = {c['total']:,.0f} บาท")
                with st.expander(f"📌 วันที่ {k+1}{cost_txt}", expanded=True):
                    for place in route:
                        if isinstance(place, dict):
                            st.markdown(f"- **{place['name']}**")
                        else:
                            st.write(f"- {place}")

        # ---------------- ส่งออก Excel ----------------
        st.divider()
        st.subheader("📊 ส่งออกข้อมูลระยะทาง")

        dist_matrix = plan.get("distance_matrix")
        time_matrix = plan.get("time_matrix")
        if dist_matrix and time_matrix:
            excel_data = generate_styled_matrices_excel(
                dist_matrix, time_matrix, names=ds["names"]
            )
            st.download_button(
                label="📥 ดาวน์โหลดเมทริกซ์ระยะทาง + เวลาเดินทาง (Excel 3 ชีต)",
                data=excel_data,
                file_name=f"Matrices_{ds['label']}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("ไม่พบข้อมูลเมทริกซ์ระยะทาง/เวลาในผลลัพธ์การคำนวณ")
