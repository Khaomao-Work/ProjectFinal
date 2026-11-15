import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import math

def plot_route_map_static(results, cleaned_places, timetable_data=None, day=None):
    """วาดแผนที่เส้นทาง พร้อมตารางเวลาเดินทาง

    day=None  -> วาดทุกวันรวมกัน (เหมือนเดิม)
    day=0,1,2 -> วาดเฉพาะวันนั้น (นับจาก 0) แสดงเฉพาะจุดที่เกี่ยวข้องและตารางของวันนั้น
    """

    plt.rcParams['font.family'] = 'Tahoma'

    fig = plt.figure(figsize=(9, 10))
    gs = fig.add_gridspec(2, 1, height_ratios=[3, 1])
    ax_map = fig.add_subplot(gs[0])
    ax_table = fig.add_subplot(gs[1])
    ax_table.axis('tight')
    ax_table.axis('off')

    day_colors = ["#f39c12", "black", "#27ae60", "#8e44ad", "#2980b9"]
    H = set(i for i, p in enumerate(cleaned_places) if p.get("is_hotel", False))

    # --- ผลักจุดไม่ให้ทับกัน (ใช้ชุดเดียวกันทุกวัน เพื่อให้ตำแหน่งจุดตรงกับภาพรวม) ---
    coords = [[p['lon'], p['lat']] for p in cleaned_places]
    min_dist = 0.04

    for _ in range(100):
        for i in range(len(coords)):
            for j in range(len(coords)):
                if i != j:
                    dx = coords[i][0] - coords[j][0]
                    dy = coords[i][1] - coords[j][1]
                    dist = math.hypot(dx, dy)

                    if dist < min_dist:
                        if dist == 0:
                            dx, dy = 0.001, 0.001
                            dist = math.hypot(dx, dy)

                        push = (min_dist - dist) / dist * 0.1
                        coords[i][0] += dx * push
                        coords[i][1] += dy * push
                        coords[j][0] -= dx * push
                        coords[j][1] -= dy * push

    # --- อ่านเส้นทางและสร้างตาราง ---
    seq_num = 1
    table_data = []
    used_nodes = set()          # จุดที่ถูกใช้ (ใช้กรองตอนวาดแยกวัน)
    drawn_days = []             # วันที่วาดจริง (ใช้สร้าง legend)
    daily_routes = results.get("daily_routes", [])

    for day_idx, route_info in enumerate(daily_routes):
        if day is not None and day_idx != day:
            continue
        if not route_info:
            continue

        if isinstance(route_info, dict):
            daily_route = route_info.get("route", route_info.get("places", []))
        else:
            daily_route = route_info

        color = day_colors[day_idx % len(day_colors)]
        drawn_days.append(day_idx)

        visited_seq = []   # ลำดับจุดตามเส้นทาง (รวมโรงแรมที่กลับมาจบวัน)

        for segment in daily_route:
            if isinstance(segment, (tuple, list)) and len(segment) >= 2:
                i, j = segment[0], segment[1]
            else:
                continue

            if not visited_seq or visited_seq[-1] != i:
                visited_seq.append(i)
            visited_seq.append(j)
            used_nodes.add(i)
            used_nodes.add(j)

            # วาดเส้น
            x1, y1 = coords[i][0], coords[i][1]
            x2, y2 = coords[j][0], coords[j][1]

            ax_map.annotate("",
                        xy=(x2, y2), xycoords='data',
                        xytext=(x1, y1), textcoords='data',
                        arrowprops=dict(arrowstyle="->", color=color,
                                        shrinkA=10, shrinkB=10,
                                        linestyle="dashed", linewidth=1.5))

            mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
            ax_map.text(mid_x, mid_y, str(seq_num), color='black', fontsize=8,
                    fontweight='bold', ha='center', va='center',
                    bbox=dict(facecolor='white', edgecolor='none', pad=1), zorder=8)
            seq_num += 1

        # --- สร้างแถวตาราง พร้อมเวลา (จับคู่ตามลำดับในวัน ไม่ใช้ชื่อ) ---
        day_schedule = []
        if timetable_data and day_idx < len(timetable_data):
            day_schedule = timetable_data[day_idx] or []

        for pos, idx in enumerate(visited_seq):
            place_name = cleaned_places[idx].get("name", f"จุดที่ {idx+1}")
            arrival, departure = "-", "-"
            if pos < len(day_schedule):
                item = day_schedule[pos]
                # ตรวจชื่อให้ตรงกันก่อน กันกรณีลำดับเพี้ยน
                if item.get("name", item.get("สถานที่", place_name)) == place_name:
                    arrival = item.get("arrival", item.get("ถึง", "-"))
                    departure = item.get("departure", item.get("ออก", "-"))

            table_data.append([
                f"วันที่ {day_idx+1}",
                place_name,
                arrival,
                departure
            ])

    # --- วาดจุดสถานที่ (ถ้าเลือกวัน วาดเฉพาะจุดของวันนั้น) ---
    for idx in range(len(cleaned_places)):
        if day is not None and idx not in used_nodes:
            continue
        is_hotel = idx in H
        node_color = "#27ae60" if is_hotel else "#e74c3c"
        x, y = coords[idx][0], coords[idx][1]
        ax_map.plot(x, y, marker='o', markersize=15, color=node_color, zorder=5)
        ax_map.text(x, y, str(idx + 1), color='white', fontsize=9, fontweight='bold',
                ha='center', va='center', zorder=6)

    # --- คำอธิบายสี ---
    legend_elements = []
    for k in drawn_days:
        color = day_colors[k % len(day_colors)]
        legend_elements.append(Line2D([0], [0], color=color, lw=2,
                                    linestyle='dashed', label=f'วันที่ {k+1}'))

    legend_elements.append(Line2D([0], [0], marker='o', color='w', markerfacecolor='#e74c3c', markersize=8, label='สถานที่เที่ยว'))
    legend_elements.append(Line2D([0], [0], marker='o', color='w', markerfacecolor='#27ae60', markersize=8, label='โรงแรม/จุดพัก'))
    ax_map.legend(handles=legend_elements, loc='upper left', fontsize=9, frameon=True)
    ax_map.axis('off')
    title = "แผนที่เส้นทางเดินทาง" if day is None else f"แผนที่เส้นทางเดินทาง — วันที่ {day+1}"
    ax_map.set_title(title, fontsize=12, pad=10)

    # --- วาดตารางเวลา ---
    col_labels = ["วันที่", "สถานที่", "เวลาถึง", "เวลาออก"]
    if table_data:
        table = ax_table.table(cellText=table_data,
                            colLabels=col_labels,
                            loc='center',
                            cellLoc='left',
                            colWidths=[0.12, 0.55, 0.15, 0.15])
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 1.5)

        for (row, col), cell in table.get_celld().items():
            if row == 0:
                cell.set_facecolor('#34495e')
                cell.set_text_props(color='white', fontweight='bold')
            elif row % 2 == 1:
                cell.set_facecolor('#f8f9fa')
    else:
        ax_table.text(0.5, 0.5, "ไม่มีข้อมูลเส้นทาง", ha='center', va='center', fontsize=10)

    plt.tight_layout()
    return fig