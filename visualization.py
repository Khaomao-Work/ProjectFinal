import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import math

def plot_route_map_static(results, cleaned_places):
    """วาดกราฟเส้นทางแบบมีลูกศรและเลขลำดับ (ปรับขนาดจุดและตัวเลขให้เล็กลง)"""
    
    plt.rcParams['font.family'] = 'Tahoma'
    # ปรับขนาดกรอบรูปให้กะทัดรัดขึ้น
    fig, ax = plt.subplots(figsize=(7, 9)) 
    
    day_colors = ["#f39c12", "black", "#27ae60", "#8e44ad", "#2980b9"] 
    H = set(i for i, p in enumerate(cleaned_places) if p.get("is_hotel", False))
    
    # ระบบผลักจุด (Node Spreading Algorithm)
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

    # 1. วาดเส้นทางและลูกศร
    seq_num = 1
    for k, route in enumerate(results["daily_routes"]):
        if not route:
            continue
        color = day_colors[k % len(day_colors)]
        
        for (i, j) in route:
            x1, y1 = coords[i][0], coords[i][1]
            x2, y2 = coords[j][0], coords[j][1]
            
            # ลด shrink เหลือ 10 เพื่อให้หัวลูกศรพอดีกับวงกลมที่เล็กลง
            ax.annotate("",
                        xy=(x2, y2), xycoords='data',
                        xytext=(x1, y1), textcoords='data',
                        arrowprops=dict(arrowstyle="->", color=color, 
                                        shrinkA=10, shrinkB=10, 
                                        linestyle="dashed", linewidth=1.5))
            
            # ปรับขนาดเลขบนเส้นให้เล็กลง (fontsize=8)
            mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
            ax.text(mid_x, mid_y, str(seq_num), color='black', fontsize=8, 
                    fontweight='bold', ha='center', va='center',
                    bbox=dict(facecolor='white', edgecolor='none', pad=1), zorder=8)
            seq_num += 1

    # 2. วาดจุดสถานที่ (Nodes) - ปรับลดขนาดลง
    for idx in range(len(cleaned_places)):
        is_hotel = idx in H
        node_color = "#27ae60" if is_hotel else "#e74c3c"
        
        x, y = coords[idx][0], coords[idx][1]
        
        # ลด markersize จาก 25 เหลือ 15 เพื่อไม่ให้บังกัน
        ax.plot(x, y, marker='o', markersize=15, color=node_color, zorder=5)
        
        # ลดขนาดตัวเลขข้างในวงกลมเหลือ 9
        ax.text(x, y, str(idx + 1), color='white', fontsize=9, fontweight='bold',
                ha='center', va='center', zorder=6)

    # 3. สร้าง Legend คำอธิบายสีตามวัน
    legend_elements = []
    for k in range(len(results["daily_routes"])):
        if results["daily_routes"][k]:
            color = day_colors[k % len(day_colors)]
            legend_elements.append(Line2D([0], [0], color=color, lw=2, 
                                          linestyle='dashed', label=f'วันที่ {k+1}'))
    
    legend_elements.append(Line2D([0], [0], marker='o', color='w', markerfacecolor='#e74c3c', markersize=8, label='สถานที่เที่ยว'))
    legend_elements.append(Line2D([0], [0], marker='o', color='w', markerfacecolor='#27ae60', markersize=8, label='โรงแรม/จุดพัก'))

    ax.legend(handles=legend_elements, loc='upper left', fontsize=9, frameon=True)
    ax.axis('off')
    
    return fig