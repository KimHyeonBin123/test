import requests
from datetime import datetime, timedelta

# ──────────────────────────────
# ✅ Mapbox Directions API 호출 함수
# ──────────────────────────────
def get_route_mapbox(coords, profile="driving"):
    """
    coords: [(lon, lat), (lon, lat), ...]
    profile: "driving", "walking", "cycling"
    """
    coords_str = ";".join([f"{lon},{lat}" for lon, lat in coords])
    url = f"https://api.mapbox.com/directions/v5/mapbox/{profile}/{coords_str}"
    params = {
        "geometries": "geojson",
        "overview": "full",
        "steps": "true",
        "access_token": MAPBOX_TOKEN
    }
    res = requests.get(url, params=params)
    if res.status_code != 200:
        st.error("❌ Mapbox API 호출 실패")
        return None
    data = res.json()
    return data["routes"][0] if data.get("routes") else None


# ──────────────────────────────
# ✅ 노선 생성 함수
# ──────────────────────────────
def generate_bus_route(passengers, base_time):
    """
    passengers: [
        {"name": "지훈", "start": "대림타운", "end": "천안북중학교"},
        {"name": "민지", "start": "대우목화", "end": "상명대"},
    ]
    base_time: datetime (첫 승차 시작 시간)
    """
    order_table = []
    cur_time = base_time

    # 좌표 가져오기
    coords = []
    for p in passengers:
        s_point = stops[stops["name"] == p["start"]].geometry.iloc[0]
        e_point = stops[stops["name"] == p["end"]].geometry.iloc[0]
        coords.append((s_point.x, s_point.y))  # 출발
        coords.append((e_point.x, e_point.y))  # 도착

    # Mapbox 경로 요청
    route = get_route_mapbox(coords)
    if not route:
        return None, None

    geometry = route["geometry"]["coordinates"]
    duration = route["duration"]  # 초 단위
    distance = route["distance"] / 1000  # km

    # 노선표 구성 (순서대로 시간 계산)
    total_time = 0
    for i, (lon, lat) in enumerate(coords):
        stop_name = stops[(stops["lon"] == lon) & (stops["lat"] == lat)]["name"].iloc[0]
        arr_time = cur_time + timedelta(minutes=total_time/60)
        remark = ""
        for p in passengers:
            if stop_name == p["start"]:
                remark = f"{p['name']} 탑승"
            elif stop_name == p["end"]:
                remark = f"{p['name']} 하차"
        order_table.append({
            "순서": i+1,
            "예상시간": arr_time.strftime("%H:%M"),
            "정류장": stop_name,
            "비고": remark
        })
        if i < len(route["legs"]):
            total_time += route["legs"][i]["duration"]  # 초 단위

    return order_table, geometry
