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
# ✅ 환경변수 불러오기 (Streamlit Cloud 호환)
# ──────────────────────────────
MAPBOX_TOKEN = "pk.eyJ1IjoiZ3VyMDUxMDgiLCJhIjoiY21lZ2k1Y291MTdoZjJrb2k3bHc3cTJrbSJ9.DElgSQ0rPoRk1eEacPI8uQ"

# ──────────────────────────────
# ✅ 데이터 로드
# ──────────────────────────────
@st.cache_data
def load_data():
    try:
        # 정류장 데이터
        stops = gpd.read_file("./new_drt.shp").to_crs(epsg=4326)
        stops["lon"], stops["lat"] = stops.geometry.x, stops.geometry.y
        stops["name"] = stops["bus_stops"].astype(str)

        # 노선 데이터 (drt_1 ~ drt_4)
        bus_data = {}
        for i in range(1, 5):
            bus_data[f"drt_{i}"] = gpd.read_file(f"./drt_{i}.shp").to_crs(epsg=4326)

        return stops, bus_data
    except Exception as e:
        st.error(f"❌ 데이터 로드 실패: {str(e)}")
        return None, None


# ──────────────────────────────
# ✅ Streamlit 설정
# ──────────────────────────────
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

# ──────────────────────────────
# ✅ 레이아웃
# ──────────────────────────────
col1, col2, col3 = st.columns([1.3, 1.2, 3], gap="large")

# ------------------------------
# [좌] 출발/도착 선택
# ------------------------------
with col1:
    st.markdown("### 🚗 추천경로 설정")
    
    start = st.selectbox("출발 정류장", stops["name"].unique())
    end = st.selectbox("도착 정류장", stops["name"].unique())
    
    time = st.time_input("승차 시간", value=pd.to_datetime("07:30").time())
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        create_clicked = st.button("경로 생성")
    with col_btn2:
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

    if st.session_state["order"]:
        for i, name in enumerate(st.session_state["order"], 1):
            st.markdown(f"- {i}. {name}")
    else:
        st.info("경로 생성 후 표시됩니다")

    st.metric("⏱️ 소요시간", f"{st.session_state['duration']:.1f}분")
    st.metric("📏 이동거리", f"{st.session_state['distance']:.2f}km")

# ------------------------------
# [우] 지도
# ------------------------------
with col3:
    st.markdown("### 🗺️ 추천경로 지도시각화")
    clat, clon = stops["lat"].mean(), stops["lon"].mean()
    m = folium.Map(location=[clat, clon], zoom_start=13, tiles="CartoDB Positron")

    # 모든 정류장 표시
    mc = MarkerCluster().add_to(m)
    for _, row in stops.iterrows():
        folium.Marker([row.lat, row.lon],
                      popup=row["name"],
                      tooltip=row["name"],
                      icon=folium.Icon(color="blue", icon="bus", prefix="fa")
        ).add_to(mc)

    # 출발/도착 선택 후 경로 생성
    if create_clicked:
        try:
            order = [start, end]
            st.session_state["order"] = order

            # 거리 및 소요시간 계산
            p1 = stops[stops["name"] == start].geometry.iloc[0]
            p2 = stops[stops["name"] == end].geometry.iloc[0]
            total_distance = p1.distance(p2) * 111  # km 변환
            st.session_state["distance"] = total_distance
            st.session_state["duration"] = total_distance / 30 * 60  # 평균속도 30km/h

            # 지도 PolyLine
            route_coords = [(stops[stops["name"] == n].lat.values[0], stops[stops["name"] == n].lon.values[0]) for n in order]
            folium.PolyLine(route_coords, color="blue", weight=5).add_to(m)

            # 출발/도착 강조
            folium.Marker(route_coords[0], icon=folium.Icon(color="green", icon="play")).add_to(m)
            folium.Marker(route_coords[-1], icon=folium.Icon(color="red", icon="stop")).add_to(m)

            st.success("✅ 경로가 생성되었습니다!")
        except Exception as e:
            st.error(f"경로 생성 오류: {str(e)}")

    st_folium(m, width="100%", height=520)
