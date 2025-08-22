# -*- coding: utf-8 -*-
import streamlit as st
import geopandas as gpd
import pandas as pd
import folium
from shapely.geometry import Point
from streamlit_folium import st_folium

# ------------------------------
# [데이터 불러오기 및 전처리]
# ------------------------------
stops = gpd.read_file("./new_drt.shp").to_crs(epsg=4326)
stops["lon"], stops["lat"] = stops.geometry.x, stops.geometry.y
stops["name"] = stops["bus_stops"].astype(str)  # 이름은 문자열 고정

# ------------------------------
# [좌/중 columns 설정]
# ------------------------------
col1, col2 = st.columns([2.5, 3], gap="large")  # col2를 넓혀 노선표 공간 확보

# ------------------------------
# [좌] 승객 입력
# ------------------------------
with col1:
    st.markdown("### 🚗 승객 등록")

    if "passengers" not in st.session_state:
        st.session_state["passengers"] = []

    with st.form("add_passenger"):
        name = st.text_input("승객 이름")
        start = st.selectbox("출발 정류장", stops["name"].unique())
        end = st.selectbox("도착 정류장", stops["name"].unique())
        board_time = st.time_input("승차 시간", value=pd.to_datetime("07:30").time())
        submitted = st.form_submit_button("추가하기")

        if submitted and name and start and end:
            st.session_state["passengers"].append({
                "name": name,
                "start": start,
                "end": end,
                "time": board_time
            })
            st.success(f"✅ {name} 등록 완료!")

    if st.button("초기화"):
        st.session_state["passengers"] = []

# ------------------------------
# [중] 노선표 출력
# ------------------------------
with col2:
    st.markdown("### 📍 버스 노선표")

    if st.session_state["passengers"]:
        order_list = []
        for i, p in enumerate(st.session_state["passengers"], 1):
            start_stop = stops[stops["name"] == p["start"]].iloc[0]
            end_stop = stops[stops["name"] == p["end"]].iloc[0]

            order_list.append({
                "순서": i*2-1,
                "예상시간": p["time"].strftime("%H:%M"),
                "정류장": str(p["start"]),  # 이름은 문자열로 고정
                "비고": f"{p['name']} 탑승"
            })
            order_list.append({
                "순서": i*2,
                "예상시간": "",
                "정류장": str(p["end"]),  # 이름은 문자열로 고정
                "비고": f"{p['name']} 하차"
            })

        df = pd.DataFrame(order_list)
        st.dataframe(df.style.set_properties(**{'white-space': 'pre'}), use_container_width=True, height=700)
    else:
        st.info("승객을 등록하세요.")

# ------------------------------
# [지도 - 전체 폭으로 표시]
# ------------------------------
st.markdown("### 🗺️ 경로 시각화")
clat, clon = stops["lat"].mean(), stops["lon"].mean()
m = folium.Map(location=[clat, clon], zoom_start=13, tiles="CartoDB Positron")

# 정류장 마커 (좌표만 소숫점 2자리)
for _, row in stops.iterrows():
    lat_rounded = round(row.lat, 2)
    lon_rounded = round(row.lon, 2)
    folium.Marker(
        [lat_rounded, lon_rounded],
        popup=f"{row['name']}",  # 이름만 표시
        tooltip=f"{row['name']}",
        icon=folium.Icon(color="blue", icon="bus", prefix="fa")
    ).add_to(m)

# 탑승객 경로 PolyLine (좌표만 소숫점 2자리)
if st.session_state["passengers"]:
    for p in st.session_state["passengers"]:
        p1 = stops[stops["name"] == p["start"]].geometry.iloc[0]
        p2 = stops[stops["name"] == p["end"]].geometry.iloc[0]
        coords = [(round(p1.y, 2), round(p1.x, 2)), (round(p2.y, 2), round(p2.x, 2))]
        folium.PolyLine(coords, color="blue", weight=4).add_to(m)
        folium.Marker((round(p1.y, 2), round(p1.x, 2)), icon=folium.Icon(color="green", icon="play")).add_to(m)
        folium.Marker((round(p2.y, 2), round(p2.x, 2)), icon=folium.Icon(color="red", icon="stop")).add_to(m)

# 지도 출력 (전체 폭)
st_folium(m, width=1200, height=900)
