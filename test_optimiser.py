import streamlit as st
from optimiser import solve_itinerary, FC, Pfuel
from export_matrices import generate_styled_matrices_excel
from visualization import plot_route_map_static

st.set_page_config(page_title="ระบบจัดเส้นทาง", layout="wide")
st.title("🚗 ระบบจัดเส้นทางท่องเที่ยวอัจฉริยะ")
BUDGET = 3000   # งบรวมทั้งทริป (บาท) ใช้ทั้งส่งเข้าโมเดลและแสดงผล

#  ============================================================
# ชุดข้อมูลทดสอบ 2 ชุด
#   - "bkk"    : กรุงเทพฯ  (ใช้กับทริปวันเดียว)
#   - "phuket" : ภูเก็ต    (ใช้กับทริปหลายวัน / ต่างจังหวัด)
# ทุกชุดเรียงเหมือนกัน: index 0-2 = ที่พัก, index 3-11 = สถานที่ท่องเที่ยว
# หมายเหตุ: สถานที่ที่ใช้เป็น "จุดเริ่มต้น" ต้องเปิดไม่เกิน 6.0 น. (day_start = 6.0 ในโมเดล)
# ============================================================
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
        "cost":  [0, 0, 0, 0, 200, 0, 0, 0, 200, 100, 100, 40],  # เพิ่มค่ากิจกรรม/ค่าเตียงผ้าใบ/ค่าเข้าชมในภูเก็ต
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


# ============================================================
# 4 กรณีทดสอบ (เลือกจากเมนู ไม่ต้องคอมเมนต์โค้ด)
# แต่ละกรณีระบุ: ชุดข้อมูล (data), จุดเริ่ม/จุดจบ (เลข index ใน names), จำนวนวัน
# ============================================================
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
        "data": "phuket", "start": 3, "end": 8, "days": 3,   # แหลมพรหมเทพ -> เมืองเก่าภูเก็ต
    },
}

case_name = st.selectbox("เลือกกรณีทดสอบ", list(CASES.keys()))
case = CASES[case_name]
ds = DATASETS[case["data"]]
potential_hotels, potential_attractions = build_places(ds)

start_point = ds["names"][case["start"]]
end_point = ds["names"][case["end"]]
trip_days = case["days"]
st.caption(f"พื้นที่: **{ds['label']}** | เริ่มที่: **{start_point}** → จบที่: **{end_point}** ({trip_days} วัน)")

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
            max_daily_hours=12,
            is_daily_limit_flexible=True,
            budget=3000,
            objective_weights={"distance_weight": 0.7, "time_balance_weight": 0.3}
        )

    if not itineraries:
        st.error("เกิดข้อผิดพลาด: ไม่สามารถจัดเส้นทางได้ หรือ API มีปัญหา")
    else:
        plan = itineraries[0]

        if not plan["daily_routes"]:
            st.warning("โมเดลไม่พบคำตอบที่เป็นไปได้ (infeasible) ดูรายละเอียดใน terminal")
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
            fig = plot_route_map_static(
                results=plan["raw_results"],
                cleaned_places=plan["cleaned_places"]
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