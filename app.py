# -*- coding: utf-8 -*-
import sys
import os
import streamlit as st
import geopandas as gpd
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from shapely.geometry import Point
from streamlit_folium import st_folium

# ------------------------------
# [데이터 불러오기 및 전처리]
# ------------------------------
stops = gpd.read_file("./new_drt.shp").to_crs(epsg=4326)
stops["lon"], stops["lat"] = stops.geometry.x, stops.geometry.y

# bus_stops 컬럼을 문자열로 변환하여 name 컬럼 생성
stops["name"] = stops["bus_stops"].astype(str)

# ------------------------------
# [컬럼 레이아웃 설정]
# ------------------------------
col1, col2, col3 = st.columns([1.3, 1.2, 3], gap="large")

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
# [중간] 노선표 출력
# ------------------------------
with col2:
    st.markdown("### 📍 버스 노선표")

    if st.session_state["passengers"]:
        order_list = []
        for i, p in enumerate(st.session_state["passengers"], 1):
            order_list.append({
                "순서": i*2-1,
                "예상시간": p["time"].strftime("%H:%M"),
                "정류장": p["start"],
                "비고": f"{p['name']} 탑승"
            })
            order_list.append({
                "순서": i*2,
                "예상시간": "",  # 하차시간은 경로 계산시 채울 수 있음
                "정류장": p["end"],
                "비고": f"{p['name']} 하차"
            })
        df = pd.DataFrame(order_list)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("승객을 등록하세요.")

# ------------------------------
# [우] 지도 시각화
# ------------------------------
with col3:
    st.markdown("### 🗺️ 경로 시각화")
    clat, clon = stops["lat"].mean(), stops["lon"].mean()
    m = folium.Map(location=[clat, clon], zoom_start=13, tiles="CartoDB Positron")

    # 정류장 마커 표시
    for _, row in stops.iterrows():
        folium.Marker([row.lat, row.lon],
                      popup=row["name"],
                      tooltip=row["name"],
                      icon=folium.Icon(color="blue", icon="bus", prefix="fa")
        ).add_to(m)

    # 탑승객 경로 PolyLine
    if st.session_state["passengers"]:
        for p in st.session_state["passengers"]:
            p1 = stops[stops["name"] == p["start"]].geometry.iloc[0]
            p2 = stops[stops["name"] == p["end"]].geometry.iloc[0]
            coords = [(p1.y, p1.x), (p2.y, p2.x)]
            folium.PolyLine(coords, color="blue", weight=4).add_to(m)
            folium.Marker((p1.y, p1.x), icon=folium.Icon(color="green", icon="play")).add_to(m)
            folium.Marker((p2.y, p2.x), icon=folium.Icon(color="red", icon="stop")).add_to(m)

    st_folium(m, width="100%", height=520)

