import streamlit as st
from optimiser import solve_itinerary
from export_utils import generate_styled_distance_matrix_excel
from visualization import plot_route_map_static

st.set_page_config(page_title="ระบบจัดเส้นทาง", layout="wide")
st.title("🚗 ระบบจัดเส้นทางท่องเที่ยวอัจฉริยะ")

# ============================================================
# ข้อมูลทดสอบ
# ============================================================
names = [
    "โรงแรมในกรุงเทพ", "โรงแรมในนครปฐม", "รีสอร์ทในราชบุรี",
    "วัดอรุณราชวราราม (กรุงเทพ)", "เอเชียทีค (กรุงเทพ)", "มิวเซียมสยาม (กรุงเทพ)",
    "องค์พระปฐมเจดีย์ (นครปฐม)", "พระราชวังสนามจันทร์ (นครปฐม)", "คาเฟ่ริมน้ำนครชัยศรี (นครปฐม)",
    "ตลาดน้ำดำเนินสะดวก (ราชบุรี)", "อุทยานหินเขางู (ราชบุรี)", "เถ้าฮงไถ่ (ราชบุรี)"
]
coords = [ 
    (13.7563, 100.5018), (13.8199, 100.0620), (13.5283,  99.8134),
    (13.7437, 100.4888), (13.7048, 100.5030), (13.7442, 100.4947),
    (13.8196, 100.0607), (13.8179, 100.0415), (13.7900, 100.2500),
    (13.5199,  99.9566), (13.5905,  99.7346), (13.5333,  99.8167)
]
S_scores = [0, 0, 0, 9, 8, 8, 10, 8, 7, 9, 8, 7]
v_times  = [0.0, 0.0, 0.0, 1.5, 2.0, 1.5, 1.0, 2.0, 1.0, 2.0, 1.5, 1.0]
c_costs  = [0, 0, 0, 100, 0, 100, 20, 50, 0, 0, 0, 0]
E_times  = [0.0, 0.0, 0.0, 8.0, 16.0, 10.0, 8.0, 8.0, 9.0, 8.0, 8.0, 8.0]
L_times  = [24.0, 24.0, 24.0, 18.0, 22.0, 18.0, 18.0, 16.0, 18.0, 14.0, 18.0, 17.0]

hotel_indices = [0, 1, 2]
attraction_indices = [3, 4, 5, 6, 7, 8, 9, 10, 11]

potential_hotels = [{"name": names[i], "lat": coords[i][0], "lon": coords[i][1]} for i in hotel_indices]
potential_attractions = [{
    "name": names[i], "lat": coords[i][0], "lon": coords[i][1], "duration": v_times[i],
    "score": S_scores[i], "cost": c_costs[i], "open_time": E_times[i], "close_time": L_times[i],
} for i in attraction_indices]

start_point = names[0] # เริ่มกรุงเทพ
end_point = names[2]   # จบราชบุรี

if st.button("ประมวลผลเส้นทาง"):
    with st.spinner("กำลังดึงข้อมูลแผนที่และคำนวณเส้นทาง..."):
        itineraries = solve_itinerary(
            potential_hotels=potential_hotels,
            potential_attractions=potential_attractions,
            start_point_name=start_point,
            end_point_name=end_point,
            trip_duration_days=3,
            max_daily_hours=12,
            is_daily_limit_flexible=True,
            budget=3000,
            objective_weights={"distance_weight": 0.7, "time_balance_weight": 0.3}
        )

        if not itineraries:
            st.error("เกิดข้อผิดพลาด: ไม่สามารถจัดเส้นทางได้ หรือ API มีปัญหา")
        else:
            plan = itineraries[0] 
            st.success(f"✅ ประมวลผลสำเร็จ! ระยะทางรวมทั้งหมด: {plan['total_distance']} กม.")
            
            col1, col2 = st.columns([1.2, 1])
            
            with col1:
                st.subheader("🗺️ กราฟเส้นทางท่องเที่ยว")
                # เรียกฟังก์ชันวาดกราฟ (Matplotlib)
                fig = plot_route_map_static(
                    results=plan["raw_results"],
                    cleaned_places=plan["cleaned_places"]
                )
                st.pyplot(fig)

            with col2:
                st.subheader("📋 รายละเอียดแผนการเดินทาง")
                for k, route in enumerate(plan["daily_routes"]):
                    with st.expander(f"📌 วันที่ {k+1}", expanded=True):
                        for place in route:
                            if isinstance(place, dict):
                                st.markdown(f"- **{place['name']}**")
                            else:
                                st.write(f"- {place}")
            
            # =========================================================
            # === เพิ่มส่วนการส่งออกข้อมูล Excel ตรงนี้ (ใต้ col1, col2) ===
            # =========================================================
            st.divider() # เส้นคั่นเพื่อความสวยงาม
            st.subheader("📊 ส่งออกข้อมูลระยะทาง")
            
            # ตรวจสอบว่า plan มีข้อมูล distance_matrix หรือไม่
            if "raw_results" in plan and "distance_matrix" in plan["raw_results"]:
                dist_matrix = plan["raw_results"]["distance_matrix"]
                
                # สร้างไฟล์ Excel บนหน่วยความจำ
                excel_data = generate_styled_distance_matrix_excel(dist_matrix)

                # สร้างปุ่มดาวน์โหลดให้ผู้ใช้
                st.download_button(
                    label="📥 ดาวน์โหลดตาราง Distance Matrix (Excel ตกแต่งแล้ว)",
                    data=excel_data,
                    file_name="Project_Distance_Matrix.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.info("ไม่พบข้อมูลเมทริกซ์ระยะทางในผลลัพธ์การคำนวณ")