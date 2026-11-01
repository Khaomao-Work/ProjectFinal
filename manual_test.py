import math
import streamlit as st
from visualization import plot_route_map_static

try:
    from optimiser import get_travel_matrices   # ระยะทาง/เวลาจริงจาก Geoapify (ชุดเดียวกับโมเดล)
except Exception:
    get_travel_matrices = None

st.set_page_config(page_title="ระบบจัดเส้นทาง (มนุษย์จัดเอง)", layout="wide")
st.title("🚗 ระบบจัดเส้นทางท่องเที่ยว (ออกแบบโดยมนุษย์: จัดโซนและเกลี่ยวัน)")

# ============================================================
# ข้อมูลทดสอบ (ชุดเดียวกับ app.py: index 0-2 = ที่พัก, 3-11 = สถานที่ท่องเที่ยว)
# ============================================================
DATASETS = {
    "bkk": {
        "label": "กรุงเทพฯ",
        "names": ["โรงแรมย่านสุขุมวิท", "โรงแรมย่านบางลำพู", "โรงแรมย่านอารีย์",
                  "สวนลุมพินี", "ตลาดปากคลองตลาด", "วัดโพธิ์",
                  "พระบรมมหาราชวัง", "ภูเขาทอง วัดสระเกศ", "จิม ทอมป์สัน เฮาส์",
                  "สยามพารากอน", "ไอคอนสยาม", "สวนจตุจักร"],
        "coords": [(13.7380, 100.5610), (13.7620, 100.4990), (13.7790, 100.5450),
                   (13.7314, 100.5414), (13.7435, 100.4968), (13.7465, 100.4927),
                   (13.7500, 100.4913), (13.7539, 100.5069), (13.7490, 100.5280),
                   (13.7461, 100.5347), (13.7265, 100.5100), (13.8030, 100.5530)],
        "score": [0, 0, 0, 8, 7, 10, 10, 8, 7, 7, 8, 6],
        "visit": [0.0, 0.0, 0.0, 1.5, 1.0, 2.0, 2.5, 1.0, 1.5, 2.0, 2.0, 1.5],
        "cost":  [0, 0, 0, 0, 0, 300, 500, 50, 200, 0, 0, 0],
        "open":  [0.0, 0.0, 0.0, 5.0, 0.0, 8.0, 8.5, 7.5, 9.0, 10.0, 10.0, 5.0],
        "close": [24.0, 24.0, 24.0, 21.0, 24.0, 18.5, 15.5, 19.0, 18.0, 22.0, 22.0, 21.0],
    },
    "phuket": {
        "label": "ภูเก็ต",
        "names": ["โรงแรมในตัวเมืองภูเก็ต", "รีสอร์ทหาดป่าตอง", "รีสอร์ทหาดราไวย์",
                  "แหลมพรหมเทพ", "หาดป่าตอง", "จุดชมวิวกะรน",
                  "พระใหญ่ภูเก็ต", "วัดฉลอง", "ย่านเมืองเก่าภูเก็ต",
                  "หาดกะตะ", "หาดกมลา", "หาดไนยาง"],
        "coords": [(7.8850, 98.3860), (7.8930, 98.2985), (7.7840, 98.3250),
                   (7.7621, 98.3057), (7.8960, 98.2960), (7.7900, 98.3010),
                   (7.8278, 98.3125), (7.8460, 98.3380), (7.8840, 98.3880),
                   (7.8190, 98.2980), (7.9490, 98.2800), (8.0950, 98.2970)],
        "score": [0, 0, 0, 10, 8, 8, 10, 9, 9, 7, 7, 6],
        "visit": [0.0, 0.0, 0.0, 1.0, 2.0, 1.0, 1.5, 1.0, 2.0, 2.0, 2.0, 2.0],
        "cost":  [0] * 12,
        "open":  [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 8.0, 7.0, 9.0, 0.0, 0.0, 0.0],
        "close": [24.0, 24.0, 24.0, 24.0, 24.0, 24.0, 19.0, 17.0, 21.0, 24.0, 24.0, 24.0],
    },
}
HOTELS = [0, 1, 2]
ATTR = [3, 4, 5, 6, 7, 8, 9, 10, 11]

DAY_START = 6.0     # เหมือน day_start ในโมเดล
FC, PFUEL = 15, 40  # กม./ลิตร, บาท/ลิตร (เหมือน optimiser.py)
BUDGET = 3000
W_DIST = 0.1        # น้ำหนักระยะทางในฟังก์ชันจุดประสงค์ (เหมือน optimiser.py)

# ============================================================
# 👤 แผนที่มนุษย์จัดเอง: ลำดับจุดของแต่ละวัน (รวมจุดเริ่มวัน/จุดจบวัน)
#    จัดตามโซนและเกลี่ยจำนวนที่เที่ยวให้แต่ละวันใกล้เคียงกัน
# ============================================================
CASES = {
    "1) เที่ยววันเดียว: เริ่ม-จบที่พักเดียวกัน (บ้าน) — กรุงเทพฯ": {
        "data": "bkk", "start": 0, "end": 0,
        "routes": [
            # ลุมพินีตอนเช้า -> ย่านเมืองเก่า (ปากคลองฯ วัดโพธิ์ วัง ภูเขาทอง) -> จิม ทอมป์สัน -> พารากอน
            [0, 3, 4, 5, 6, 7, 8, 9, 0],
        ],
    },
    "2) เที่ยววันเดียว: เริ่ม-จบที่สถานที่ท่องเที่ยว — กรุงเทพฯ": {
        "data": "bkk", "start": 3, "end": 9,
        "routes": [
            [3, 4, 5, 6, 7, 8, 9],
        ],
    },
    "3) เที่ยวหลายวัน: เริ่ม-จบที่ที่พัก — ภูเก็ต": {
        "data": "phuket", "start": 0, "end": 2,
        "routes": [
            [0, 7, 6, 8, 0],       # วันที่ 1 โซนตัวเมือง: วัดฉลอง -> พระใหญ่ -> เมืองเก่า
            [0, 11, 10, 4, 1],     # วันที่ 2 โซนเหนือ-ตะวันตก: ไนยาง -> กมลา -> ป่าตอง (พักป่าตอง)
            [1, 9, 5, 3, 2],       # วันที่ 3 โซนใต้: กะตะ -> จุดชมวิวกะรน -> แหลมพรหมเทพ (พักราไวย์)
        ],
    },
    "4) เที่ยวหลายวัน: เริ่ม-จบที่สถานที่ท่องเที่ยว — ภูเก็ต": {
        "data": "phuket", "start": 3, "end": 8,
        "routes": [
            [3, 5, 9, 1],          # วันที่ 1 โซนใต้: พรหมเทพ -> กะรน -> กะตะ (พักป่าตอง)
            [1, 4, 10, 11, 0],     # วันที่ 2 โซนเหนือ-ตะวันตก: ป่าตอง -> กมลา -> ไนยาง (พักตัวเมือง)
            [0, 7, 6, 8],          # วันที่ 3 โซนตัวเมือง: วัดฉลอง -> พระใหญ่ -> เมืองเก่า (จบ)
        ],
    },
}


# ============================================================
# ตรรกะตรวจแผน (ไม่พึ่ง Streamlit)
# ============================================================
def haversine_matrices(ds, speed=45.0, factor=1.4):
    n = len(ds["names"])
    d = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            a, b = ds["coords"][i], ds["coords"][j]
            p1, p2 = math.radians(a[0]), math.radians(b[0])
            h = (math.sin((p2 - p1) / 2) ** 2
                 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(b[1] - a[1]) / 2) ** 2)
            d[i][j] = 2 * 6371.0 * math.asin(math.sqrt(h)) * factor
    t = [[d[i][j] / speed for j in range(n)] for i in range(n)]
    return d, t


def hhmm(x):
    h = int(x)
    m = int(round((x - h) * 60))
    if m == 60:
        h, m = h + 1, 0
    return f"{h:02d}:{m:02d}"


def evaluate_plan(ds, routes, S, F, d, t):
    """ตรวจแผนด้วยเงื่อนไขเดียวกับโมเดล แล้วคืนสรุปผลและรายการข้อที่ขัดกัน"""
    v, E, L = ds["visit"], ds["open"], ds["close"]
    sc, cv = ds["score"], ds["cost"]
    days = len(routes)
    issues, day_info = [], []
    visited = []

    for k, seq in enumerate(routes):
        # --- ตรวจจุดเริ่ม/จุดจบของวัน ---
        if k == 0 and seq[0] != S:
            issues.append(f"วันที่ 1 ต้องเริ่มที่ {ds['names'][S]}")
        if k == days - 1 and seq[-1] != F:
            issues.append(f"วันสุดท้ายต้องจบที่ {ds['names'][F]}")
        if k > 0 and routes[k - 1][-1] != seq[0]:
            issues.append(f"วันที่ {k+1} ต้องเริ่มที่ที่พักที่จบของวันก่อนหน้า")
        if k < days - 1 and seq[-1] not in HOTELS:
            issues.append(f"วันที่ {k+1} ต้องจบที่ที่พัก")
        if k > 0 and seq[0] not in HOTELS:
            issues.append(f"วันที่ {k+1} ต้องเริ่มที่ที่พัก")
        if seq[0] in HOTELS and seq[-1] in HOTELS and len(seq) <= 2:
            issues.append(f"วันที่ {k+1} ไม่มีสถานที่เที่ยวเลย")

        rows, dist, travel, visit_t, wait_t = [], 0.0, 0.0, 0.0, 0.0
        depart = DAY_START
        for idx, node in enumerate(seq):
            name = ds["names"][node]
            if idx == 0:
                if node in ATTR:        # เริ่มที่สถานที่เที่ยว: ถึงตอน 06:00 พอดี (เหมือนโมเดล)
                    if E[node] > DAY_START + 1e-9:
                        issues.append(f"{name}: เปิด {hhmm(E[node])} แต่จุดเริ่มต้นต้องถึงตอน {hhmm(DAY_START)}")
                    if DAY_START + v[node] > L[node] + 1e-9:
                        issues.append(f"{name}: เกินเวลาปิด")
                    visit_t += v[node]
                    visited.append(node)
                    rows.append((name, hhmm(DAY_START), "-", hhmm(DAY_START + v[node])))
                    depart = DAY_START + v[node]
                else:
                    rows.append((name, "-", "-", hhmm(DAY_START)))
                continue

            prev = seq[idx - 1]
            dist += d[prev][node]
            travel += t[prev][node]
            arr = depart + t[prev][node]
            if node in HOTELS:
                rows.append((name, hhmm(arr), "-", "-"))
                continue
            a = max(arr, E[node])
            wait = a - arr
            wait_t += wait
            if a + v[node] > L[node] + 1e-9:
                issues.append(f"วันที่ {k+1}: {name} ถึง {hhmm(a)} เที่ยว {v[node]} ชม. เกินเวลาปิด {hhmm(L[node])}")
            visit_t += v[node]
            visited.append(node)
            depart = a + v[node]
            rows.append((name, hhmm(a), f"{wait:.1f} ชม." if wait > 0.01 else "-", hhmm(depart)))
        day_info.append({"rows": rows, "dist": dist, "travel": travel, "visit": visit_t,
                         "wait": wait_t, "total": travel + visit_t})

    if len(visited) != len(set(visited)):
        issues.append("มีสถานที่ที่ถูกเยี่ยมซ้ำ")

    total_dist = sum(x["dist"] for x in day_info)
    score_set = [a for a in set(visited) if a not in (S, F)]      # ไม่นับจุดเริ่ม/จบ เหมือนโมเดล
    total_score = sum(sc[a] for a in score_set)
    fuel = total_dist / FC * PFUEL
    entry = sum(cv[a] for a in set(visited))
    total_cost = fuel + entry
    if total_cost > BUDGET:
        issues.append(f"เกินงบประมาณ ({total_cost:.0f} > {BUDGET})")
    return {
        "days": day_info, "issues": issues, "visited": set(visited),
        "dist": total_dist, "score": total_score, "cost": total_cost,
        "objective": total_score - W_DIST * total_dist,
    }


# ============================================================
# ส่วนแสดงผล Streamlit
# ============================================================
case_name = st.selectbox("เลือกกรณีทดสอบ", list(CASES.keys()))
case = CASES[case_name]
ds = DATASETS[case["data"]]
S, F, routes = case["start"], case["end"], case["routes"]
st.caption(f"พื้นที่: **{ds['label']}** | เริ่มที่: **{ds['names'][S]}** → จบที่: **{ds['names'][F]}** ({len(routes)} วัน)")

if st.button("ประมวลผลเส้นทาง (มนุษย์จัดเอง)"):
    places = [{
        "name": ds["names"][i], "lat": ds["coords"][i][0], "lon": ds["coords"][i][1],
        "duration": ds["visit"][i], "score": ds["score"][i], "cost": ds["cost"][i],
        "open_time": ds["open"][i], "close_time": ds["close"][i],
        "E": ds["open"][i], "L": ds["close"][i], "is_hotel": i in HOTELS,
    } for i in range(len(ds["names"]))]

    d, t = [], []
    if get_travel_matrices is not None:
        d, t = get_travel_matrices(places)
    if not d:
        st.info("ใช้ระยะทาง/เวลาโดยประมาณจากพิกัดแทน (ดึงข้อมูลจาก Geoapify ไม่ได้)")
        d, t = haversine_matrices(ds)

    res = evaluate_plan(ds, routes, S, F, d, t)

    if res["issues"]:
        st.warning("แผนนี้ขัดกับเงื่อนไขของโมเดล:\n\n" + "\n".join(f"- {x}" for x in res["issues"]))
    else:
        st.success("🎯 แผนที่จัดเองผ่านทุกเงื่อนไขของโมเดล")

    col1, col2 = st.columns([1.2, 1])

    with col1:
        st.subheader("🗺️ กราฟเส้นทางท่องเที่ยว (Human Designed)")
        daily_arcs = [list(zip(seq[:-1], seq[1:])) for seq in routes]
        fig = plot_route_map_static(
            results={"daily_routes": daily_arcs, "total_distance": round(res["dist"], 2)},
            cleaned_places=places,
        )
        st.pyplot(fig)

    with col2:
        st.subheader("📋 สรุปข้อมูลทริป (มนุษย์จัดเอง)")
        c1, c2 = st.columns(2)
        c1.metric("ระยะทางรวม", f"{res['dist']:.1f} กม.")
        c2.metric("คะแนนรวม (ไม่นับจุดเริ่ม/จบ)", f"{res['score']}")
        c3, c4 = st.columns(2)
        c3.metric("ค่าใช้จ่ายรวม (น้ำมัน+เข้าชม)", f"{res['cost']:.0f} บาท")
        c4.metric("Objective (คะแนน − 0.1×กม.)", f"{res['objective']:.2f}")
        st.metric("จำนวนสถานที่เที่ยว", f"{len(res['visited'])} / {len(ATTR)} แห่ง")

        st.subheader("📌 รายละเอียดแผนรายวัน")
        for k, info in enumerate(res["days"]):
            n_visit = sum(1 for r in info["rows"] if r[0] not in [ds["names"][h] for h in HOTELS])
            with st.expander(f"📌 วันที่ {k+1} (เที่ยว {n_visit} แห่ง | "
                             f"{info['dist']:.1f} กม. | รวม {info['total']:.1f} ชม.)", expanded=True):
                st.table({
                    "สถานที่": [r[0] for r in info["rows"]],
                    "ถึง": [r[1] for r in info["rows"]],
                    "รอเปิด": [r[2] for r in info["rows"]],
                    "ออก": [r[3] for r in info["rows"]],
                })
                st.caption(f"เดินทาง {info['travel']:.1f} ชม. + เที่ยว {info['visit']:.1f} ชม."
                           + (f" (ยังไม่รวมรอเปิด {info['wait']:.1f} ชม.)" if info["wait"] > 0.01 else ""))