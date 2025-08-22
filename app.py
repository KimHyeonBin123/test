import sys
print(sys.executable)
print(sys.path)

import streamlit as st
import geopandas as gpd
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from shapely.geometry import Point
from streamlit_folium import st_folium

# ────────────────────────────── 
# ✅ 환경변수
# ──────────────────────────────
MAPBOX_TOKEN = "pk.eyJ1IjoiZ3VyMDUxMDgiLCJhIjoiY21lZ2k1Y291MTdoZjJrb2k3bHc3cTJrbSJ9.DElgSQ0rPoRk1eEacPI8uQ"

# ──────────────────────────────
# ✅ 데이터 로드
# ──────────────────────────────
@st.cache_data
def load_data():
    try:
        stops = gpd.read_file("./new_drt.shp").to_crs(epsg=4326)
        stops["lon"], stops["lat"] = stops.geometry.x, stops.geometry.y
        stops["name"] = stops["bus_stops"].astype(str)

        bus_data = {}
        for i in range(1, 5):
            bus_data[f"drt_{i}"] = gpd.read_file(f"./drt_{i}.shp").to_crs(epsg=4326)

        return stops, bus_data
    except Exception as e:
        st.error(f"❌ 데이터 로드 실패: {str(e)}")
        return None, None

st.set_page_config(
    page_title="천안 DRT 최적 노선",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<div class="header-container" style="text-align:center; margin-bottom:1rem;">
    <h1 style="font-size:2.2rem; font-weight:700; color:#202124;">🚌 천안 DRT 최적 노선</h1>
</div>
""", unsafe_allow_html=True)

stops, bus_data = load_data()
if stops is None:
    st.stop()

col1, col2, col3 = st.columns([1.3, 1.2, 3], gap="large")

# ------------------------------
# [좌] 출발/도착 멀티셀렉트
# ------------------------------
with col1:
    st.markdown("### 🚗 추천경로 설정")

    start_list = st.multiselect("출발 정류장 선택", stops["name"].unique())
    end_list = st.multiselect("도착 정류장 선택", stops["name"].unique())

    time = st.time_input("승차 시간", value=pd.to_datetime("07:30").time())

    create_clicked = st.button("경로 생성")
    clear_clicked = st.button("초기화")

# ------------------------------
# [중간] 정보 출력
# ------------------------------
with col2:
    st.markdown("### 📍 정류장 순서")
    if "order" not in st.session_state:
        st.session_state["order"] = []
    if "duration" not in st.session_state:
        st.session_state["duration"] = 0.0
    if "distance" not in st.session_state:
        st.session_state["distance"] = 0.0

# ------------------------------
# [우] 지도
# ------------------------------
with col3:
    st.markdown("### 🗺️ 추천경로 지도시각화")
    clat, clon = stops["lat"].mean(), stops["lon"].mean()
    m = folium.Map(location=[clat, clon], zoom_start=13, tiles="CartoDB Positron")

    mc = MarkerCluster().add_to(m)
    for _, row in stops.iterrows():
        folium.Marker([row.lat, row.lon],
                      popup=row["name"],
                      tooltip=row["name"],
                      icon=folium.Icon(color="blue", icon="bus", prefix="fa")
        ).add_to(mc)

    if create_clicked:
        if not start_list or not end_list:
            st.error("⚠️ 출발/도착 정류장을 최소 1개씩 선택하세요.")
        else:
            try:
                # 출발/도착 모든 조합 경로 생성
                all_order = []
                total_distance = 0

                for s in start_list:
                    for e in end_list:
                        all_order.append((s, e))
                        p1 = stops[stops["name"] == s].geometry.iloc[0]
                        p2 = stops[stops["name"] == e].geometry.iloc[0]
                        total_distance += p1.distance(p2) * 111  # km

                        # 지도 PolyLine
                        coords = [(p1.y, p1.x), (p2.y, p2.x)]
                        folium.PolyLine(coords, color="blue", weight=5).add_to(m)
                        # 출발/도착 마커
                        folium.Marker((p1.y, p1.x), icon=folium.Icon(color="green", icon="play")).add_to(m)
                        folium.Marker((p2.y, p2.x), icon=folium.Icon(color="red", icon="stop")).add_to(m)

                st.session_state["order"] = all_order
                st.session_state["distance"] = total_distance
                st.session_state["duration"] = total_distance / 30 * 60  # 평균속도 30km/h

                st.success("✅ 경로가 생성되었습니다!")
            except Exception as e:
                st.error(f"경로 생성 오류: {str(e)}")

    st_folium(m, width="100%", height=520)

# ------------------------------
# [중간] 경로 정보 출력
# ------------------------------
with col2:
    if st.session_state["order"]:
        for i, (s, e) in enumerate(st.session_state["order"], 1):
            st.markdown(f"- {i}. {s} → {e}")
        st.metric("⏱️ 소요시간", f"{st.session_state['duration']:.1f}분")
        st.metric("📏 이동거리", f"{st.session_state['distance']:.2f}km")
