import streamlit as st
from visualization import plot_route_map_static

st.set_page_config(page_title="ระบบจัดเส้นทาง (คนจัดเองแบบสมดุล)", layout="wide")
st.title("🚗 ระบบจัดเส้นทางท่องเที่ยว (ออกแบบโดยมนุษย์: แบบจัดโซนและเกลี่ยวัน)")

# ============================================================
# ข้อมูลทดสอบ (ชุดเดียวกับระบบหลัก)
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

cleaned_places = []
for i in range(len(names)):
    cleaned_places.append({
        "name": names[i], "lat": coords[i][0], "lon": coords[i][1],
        "duration": v_times[i], "score": S_scores[i], "cost": c_costs[i],
        "open_time": E_times[i], "close_time": L_times[i],
        "is_hotel": i in hotel_indices
    })

# ============================================================
# 👤 คนจัดเองแบบตั้งใจเกลี่ยวันให้บาลานซ์ (แบ่งโซนชัดเจน)
# ============================================================
manual_daily_routes_indices = [
    # วันที่ 1: โซนกรุงเทพฯ (เก็บสถานที่ใน กทม. ให้ครบถ้วนและสมดุล)
    [(0, 5), (5, 3), (3, 4), (4, 0)],
    
    # วันที่ 2: โซนนครปฐม (กระจายเที่ยวพระปฐมเจดีย์ สนามจันทร์ และคาเฟ่)
    [(0, 8), (8, 7), (7, 6), (6, 1)],
    
    # วันที่ 3: โซนราชบุรี (เที่ยวตลาดน้ำและสวนหิน แล้วไปจบที่รีสอร์ทราชบุรี)
    [(1, 9), (9, 10), (10, 11), (11, 2)]
]

formatted_daily_routes = []
for day_route in manual_daily_routes_indices:
    formatted_daily_routes.append(day_route)

# คำนวณสรุปผล
total_cost = 0
total_score = 0
visited_places = set()

for day_route in manual_daily_routes_indices:
    for (i, j) in day_route:
        place = cleaned_places[j]
        total_cost += place["cost"]
        if not place["is_hotel"]:
            total_score += place["score"]
            visited_places.add(j)

# ปุ่มกดแสดงผล
if st.button("ประมวลผลเส้นทาง (มนุษย์จัดเองแบบบาลานซ์)"):
    st.success("🎯 โหลดแผนการเดินทางที่คุณจัดสรรเองสำเร็จ!")
    
    col1, col2 = st.columns([1.2, 1])
    
    with col1:
        st.subheader("🗺️ กราฟเส้นทางท่องเที่ยว (Human Designed)")
        manual_results = {
            "daily_routes": formatted_daily_routes,
            "total_distance": 165.2 # ตัวเลขจำลองการจัดโซนที่ดี
        }
        fig = plot_route_map_static(
            results=manual_results,
            cleaned_places=cleaned_places
        )
        st.pyplot(fig)

    with col2:
        st.subheader("📋 สรุปข้อมูลทริป (มนุษย์จัดเอง)")
        st.metric("งบประมาณรวมที่ใช้", f"{total_cost} บาท")
        st.metric("คะแนนความน่าเที่ยวรวม", f"{total_score} คะแนน")
        st.metric("จำนวนสถานที่เที่ยว", f"{len(visited_places)} / {len(attraction_indices)} แห่ง")
        
        st.subheader("📌 รายละเอียดแผนรายวัน")
        for k, route in enumerate(manual_daily_routes_indices):
            with st.expander(f"📌 วันที่ {k+1} (จำนวน {len(route)-1} ที่เที่ยว)", expanded=True):
                for (i, j) in route:
                    st.write(f"- เดินทางจาก **{names[i]}** ➡️ ไปยัง **{names[j]}**")