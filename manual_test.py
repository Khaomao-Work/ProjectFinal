import math
import streamlit as st
from visualization import plot_route_map_static

try:
    from optimiser import get_travel_matrices, FC, Pfuel as PFUEL   # ระยะทาง/เวลาจริงจาก Geoapify + ค่าน้ำมันชุดเดียวกับโมเดล
except Exception:
    get_travel_matrices = None
    FC, PFUEL = 15, 40.84

st.set_page_config(page_title="ระบบจัดเส้นทาง (มนุษย์จัดเอง)", layout="wide")
st.title("🚗 ระบบจัดเส้นทางท่องเที่ยว (ออกแบบโดยมนุษย์: จัดโซนและเกลี่ยวัน)")

# ============================================================
# ข้อมูลทดสอบ: ชุดเดียวกับ โมเดล optimiser ทุกประการ
# ทุกชุดเรียงเหมือนกัน: ที่พักมาก่อน (จำนวนระบุใน "n_hotels") ตามด้วยสถานที่ท่องเที่ยว
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
                  0, 0, 0, 0, 350, 250],             # คาเฟ่/ค่าเข้าจุดถ่ายรูป
        "open":  [0.0, 0.0, 0.0, 0.0, 0.0,
                  8.0, 16.0, 8.0, 9.0, 0.0, 0.0, 6.0, 0.0, 0.0,
                  0.0, 6.0, 8.0, 10.0, 11.0, 9.0],
        "close": [23.5, 22.0, 19.0, 24.0, 24.0,
                  18.0, 22.0, 17.0, 18.0, 24.0, 24.0, 18.0, 24.0, 24.0,
                  24.0, 18.0, 16.5, 22.0, 19.0, 18.0],
    },
}

# ภูเก็ต + สนามบิน: ต่อท้ายชุด phuket ด้วยสนามบิน 2 โหนด (index 20 = ขาไป, 21 = ขากลับ) เหมือน app.py
_AIRPORT = (8.1132, 98.3169)   # สนามบินนานาชาติภูเก็ต (HKT) พิกัดโดยประมาณ
_p = DATASETS["phuket"]
DATASETS["phuket_airport"] = {
    "label": "ภูเก็ต (เริ่ม-จบที่สนามบิน)",
    "n_hotels": _p["n_hotels"],
    "names": _p["names"] + ["สนามบินภูเก็ต (ขาไป)", "สนามบินภูเก็ต (ขากลับ)"],
    "coords": _p["coords"] + [_AIRPORT, _AIRPORT],
    "score": _p["score"] + [0, 0],
    "visit": _p["visit"] + [0.0, 0.0],
    "cost":  _p["cost"] + [0, 0],
    "open":  _p["open"] + [0.0, 0.0],
    "close": _p["close"] + [24.0, 24.0],
}

# พารามิเตอร์ให้ตรงกับโมเดล (app.py / optimiser.py)
DAY_START = 8.0     # เวลาออกจากที่พัก / เวลาเริ่มวัน
T_MAX = 12          # ชั่วโมงสูงสุดต่อวัน (นับเวลาเดินทาง + เที่ยว + รอ)
BUDGET = 1000
# ============================================================
# แผนที่มนุษย์จัดเอง (5 กรณี )
# แต่ละวันคือลำดับ index ของสถานที่ (อ้างอิงตาม names ของชุดข้อมูล)
# ============================================================
CASES = {
    "1) เที่ยววันเดียว: เริ่ม-จบที่พักเดียวกัน (บ้าน) — กรุงเทพฯ": {
        "data": "bkk", "start": 0, "end": 0,
        "routes": [
            [0, 3, 4, 5, 6, 7, 8, 9, 0],
        ],
    },
    "2) เที่ยววันเดียว: เริ่ม-จบที่สถานที่ท่องเที่ยว — กรุงเทพฯ": {
        "data": "bkk", "start": 4, "end": 9,
        "routes": [
            [4, 3, 5, 6, 7, 8, 9],
        ],
    },
    "3) เที่ยวหลายวัน: เริ่ม-จบที่ที่พัก — ภูเก็ต": {
        "data": "phuket", "start": 0, "end": 2,
        "routes": [
            [0, 16, 7, 8, 9, 10, 14, 4],      # โซนใต้ (เกาะเฮ-ฉลอง-พระใหญ่-พรหมเทพ-กังหันลม-ในหาน)
            [4, 11, 12, 19, 13, 17, 3],       # โซนตะวันตก (กระทิง-กะรน-ร็อคบีช-ป่าตอง-Three Monkeys)
            [3, 15, 18, 5, 6, 2],             # โซนเหนือ + เมืองเก่า (ไม้ขาว-มาดูบัว-เมืองเก่า-ถนนคนเดิน)
        ],
    },
    "4) เที่ยวหลายวัน: เริ่ม-จบที่สถานที่ท่องเที่ยว — ภูเก็ต": {
        "data": "phuket", "start": 5, "end": 10,
        "routes": [
            [5, 15, 18, 17, 6, 1],            # เหนือ แล้วกลับมาถนนคนเดินช่วงเย็น
            [1, 7, 16, 8, 13, 3],
            [3, 12, 19, 11, 14, 9, 10],       # จบที่กังหันลม
        ],
    },
    "5) เที่ยวหลายวัน: เริ่ม-จบที่สนามบิน — ภูเก็ต": {
        "data": "phuket_airport", "start": 20, "end": 21,
        "routes": [
            [20, 15, 18, 17, 13, 3],
            [3, 12, 19, 11, 14, 9, 10, 4],
            [4, 16, 7, 8, 5, 6, 21],
        ],
    },
}

# ============================================================
# ฟังก์ชันช่วย
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
    v, E, L = ds["visit"], ds["open"], ds["close"]
    sc, cv = ds["score"], ds["cost"]
    H = set(range(ds["n_hotels"]))                          # ที่พัก
    A = set(range(ds["n_hotels"], len(ds["names"])))        # สถานที่เที่ยว (รวมสนามบิน)
    days = len(routes)
    issues, day_info = [], []
    visited = []
    daily_costs = []

    for k, seq in enumerate(routes):
        # --- ตรวจจุดเริ่ม/จุดจบของวัน ---
        if k == 0 and seq[0] != S:
            issues.append(f"วันที่ 1 ต้องเริ่มที่ {ds['names'][S]}")
        if k == days - 1 and seq[-1] != F:
            issues.append(f"วันสุดท้ายต้องจบที่ {ds['names'][F]}")
        if k > 0 and routes[k - 1][-1] != seq[0]:
            issues.append(f"วันที่ {k+1} ต้องเริ่มที่ที่พักที่จบของวันก่อนหน้า")
        if k < days - 1 and seq[-1] not in H:
            issues.append(f"วันที่ {k+1} ต้องจบที่ที่พัก")
        if k > 0 and seq[0] not in H:
            issues.append(f"วันที่ {k+1} ต้องเริ่มที่ที่พัก")
        if seq[0] in H and seq[-1] in H and len(seq) <= 2:
            issues.append(f"วันที่ {k+1} ไม่มีสถานที่เที่ยวเลย")

        rows, dist, travel, visit_t, wait_t = [], 0.0, 0.0, 0.0, 0.0
        depart = DAY_START
        end_clock = DAY_START
        day_visited_nodes = []
        fuel_cost = 0.0

        for idx, node in enumerate(seq):
            name = ds["names"][node]
            if idx == 0:
                if node in A:
                    if E[node] > DAY_START + 1e-9:
                        issues.append(f"{name}: เปิด {hhmm(E[node])} แต่จุดเริ่มต้นต้องถึงตอน {hhmm(DAY_START)}")
                    if DAY_START + v[node] > L[node] + 1e-9:
                        issues.append(f"{name}: เกินเวลาปิด")
                    visit_t += v[node]
                    visited.append(node)
                    day_visited_nodes.append(node)
                    rows.append((name, hhmm(DAY_START), "-", hhmm(DAY_START + v[node])))
                    depart = DAY_START + v[node]
                    end_clock = depart
                else:
                    rows.append((name, "-", "-", hhmm(DAY_START)))
                continue

            prev = seq[idx - 1]
            segment_dist = d[prev][node]
            dist += segment_dist
            travel += t[prev][node]
            fuel_cost += segment_dist / FC * PFUEL

            arr = depart + t[prev][node]
            if node in H:
                rows.append((name, hhmm(arr), "-", "-"))
                end_clock = arr
            else:
                a = max(arr, E[node])
                wait = a - arr
                wait_t += wait
                if a + v[node] > L[node] + 1e-9:
                    issues.append(f"วันที่ {k+1}: {name} ถึง {hhmm(a)} เที่ยว {v[node]} ชม. เกินเวลาปิด {hhmm(L[node])}")
                visit_t += v[node]
                visited.append(node)
                day_visited_nodes.append(node)
                depart = a + v[node]
                end_clock = depart
                rows.append((name, hhmm(a), f"{wait:.1f} ชม." if wait > 0.01 else "-", hhmm(depart)))

        # --- เวลารวมของวัน (เดินทาง + เที่ยว + รอ) ต้องไม่เกิน T_MAX ตามโมเดล ---
        span = end_clock - DAY_START
        if span > T_MAX + 1e-9:
            issues.append(f"วันที่ {k+1}: ใช้เวลา {span:.1f} ชม. เกิน {T_MAX} ชม.")

        # --- ค่าใช้จ่ายรายวัน ---
        entry_cost = sum(cv[node] for node in set(day_visited_nodes))
        daily_costs.append({
            "day": k + 1,
            "fuel_cost": round(fuel_cost, 2),
            "entry_cost": round(entry_cost, 2),
            "total_cost": round(fuel_cost + entry_cost, 2),
        })

        day_info.append({"rows": rows, "dist": dist, "travel": travel, "visit": visit_t,
                         "wait": wait_t, "total": travel + visit_t, "span": span})

    if len(visited) != len(set(visited)):
        issues.append("มีสถานที่ที่ถูกเยี่ยมซ้ำ")

    total_dist = sum(x["dist"] for x in day_info)
    score_set = [a for a in set(visited) if a not in (S, F)]
    total_score = sum(sc[a] for a in score_set)

    total_fuel = sum(dc["fuel_cost"] for dc in daily_costs)
    total_entry = sum(dc["entry_cost"] for dc in daily_costs)
    total_cost = total_fuel + total_entry

    if total_cost > BUDGET:
        issues.append(f"เกินงบประมาณ ({total_cost:.0f} > {BUDGET})")

    return {
        "days": day_info,
        "issues": issues,
        "visited": set(visited),
        "dist": total_dist,
        "score": total_score,
        "cost": total_cost,
        "daily_costs": daily_costs,
        "fuel_cost": total_fuel,
        "entry_cost": total_entry,
    }

# ============================================================
# ส่วนแสดงผล Streamlit
# ============================================================
case_name = st.selectbox("เลือกกรณีทดสอบ", list(CASES.keys()))
case = CASES[case_name]
ds = DATASETS[case["data"]]
BUDGET = ds.get("budget", BUDGET)   # ใช้งบของชุดข้อมูล (ถ้ามี)
S, F, routes = case["start"], case["end"], case["routes"]
N_HOTELS = ds["n_hotels"]
hotel_names = [ds["names"][h] for h in range(N_HOTELS)]
st.caption(f"พื้นที่: **{ds['label']}** | เริ่มที่: **{ds['names'][S]}** → จบที่: **{ds['names'][F]}** ({len(routes)} วัน)")

if st.button("ประมวลผลเส้นทาง (มนุษย์จัดเอง)"):
    places = [{
        "name": ds["names"][i], "lat": ds["coords"][i][0], "lon": ds["coords"][i][1],
        "duration": ds["visit"][i], "score": ds["score"][i], "cost": ds["cost"][i],
        "open_time": ds["open"][i], "close_time": ds["close"][i],
        "E": ds["open"][i], "L": ds["close"][i], "is_hotel": i < N_HOTELS,
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
        plot_results = {"daily_routes": daily_arcs, "total_distance": round(res["dist"], 2)}
        timetable = [
            [{"name": r[0], "arrival": r[1], "departure": r[3]} for r in info["rows"]]
            for info in res["days"]
        ]
        tabs = st.tabs(["ภาพรวม"] + [f"วันที่ {k+1}" for k in range(len(routes))])
        for t_idx, tab in enumerate(tabs):
            with tab:
                fig = plot_route_map_static(
                    results=plot_results,
                    cleaned_places=places,
                    timetable_data=timetable,
                    day=None if t_idx == 0 else t_idx - 1,
                )
                st.pyplot(fig)

    with col2:
        st.subheader("📋 สรุปข้อมูลทริป")
        c1, c2 = st.columns(2)
        c1.metric("ระยะทางรวม", f"{res['dist']:.1f} กม.")
        c2.metric("คะแนนรวม", f"{res['score']}")
        c3, c4 = st.columns(2)
        c3.metric("ค่าใช้จ่ายรวม", f"{res['cost']:.0f} บาท")
        st.metric("งบคงเหลือ", f"{BUDGET - res['cost']:,.0f} บาท",
                  delta=f"{BUDGET - res['cost']:,.0f} บาท",
                  delta_color="inverse" if res['cost'] > BUDGET else "normal")

        st.divider()

        st.subheader("💰 ค่าใช้จ่ายรายวัน")
        cost_table = {
            "วันที่": [dc["day"] for dc in res["daily_costs"]],
            "ค่าน้ำมัน (บาท)": [f"{dc['fuel_cost']:,.2f}" for dc in res["daily_costs"]],
            "ค่าเข้าชม (บาท)": [f"{dc['entry_cost']:,.2f}" for dc in res["daily_costs"]],
            "รวมวันนี้ (บาท)": [f"{dc['total_cost']:,.2f}" for dc in res["daily_costs"]],
        }
        st.table(cost_table)

        st.info(f"""
        **สรุปค่าใช้จ่ายทั้งหมด:**
        - 🚗 ค่าน้ำมันรวม: **{res['fuel_cost']:,.2f} บาท**
        - 🎟️ ค่าเข้าชมรวม: **{res['entry_cost']:,.2f} บาท**
        - 💵 รวมทั้งหมด: **{res['cost']:,.2f} บาท**
        - 💰 งบประมาณ: **{BUDGET:,} บาท**
        - ✅ คงเหลือ: **{BUDGET - res['cost']:,.2f} บาท**
        """)

        st.subheader("📌 รายละเอียดแผนรายวัน")
        for k, info in enumerate(res["days"]):
            n_visit = sum(1 for r in info["rows"] if r[0] not in hotel_names)
            dc = res["daily_costs"][k]
            with st.expander(f"📌 วันที่ {k+1} | เที่ยว {n_visit} แห่ง | ใช้ {dc['total_cost']:,.0f} บาท", expanded=True):
                st.table({
                    "สถานที่": [r[0] for r in info["rows"]],
                    "ถึง": [r[1] for r in info["rows"]],
                    "รอเปิด": [r[2] for r in info["rows"]],
                    "ออก": [r[3] for r in info["rows"]],
                })
                st.caption(f"เดินทาง {info['travel']:.1f} ชม. + เที่ยว {info['visit']:.1f} ชม. "
                           f"+ รอ {info['wait']:.1f} ชม. = {info['span']:.1f} ชม. (จำกัด {T_MAX} ชม.)")
                st.markdown(f"""
                > **ค่าใช้จ่ายวันนี้:** น้ำมัน {dc['fuel_cost']:,.2f} บาท |
                > เข้าชม {dc['entry_cost']:,.2f} บาท | **รวม {dc['total_cost']:,.2f} บาท**
                """)