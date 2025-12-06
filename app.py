import streamlit as st
import requests
from datetime import datetime
import pandas as pd
import sqlite3
import os


st.set_page_config(
    page_title="Időjárás App",
    page_icon="🌤️",
    layout="wide"
)

try:
    API_KEY = st.secrets["openweather"]["api_key"]
except Exception as e:
    st.error(f"Hiba az API key betöltésekor: {e}")
    st.stop()

@st.cache_data(ttl=600)
def get_current_weather(city):
    url = f'http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric'
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Aktuális időjárás API hiba: {e}")
        return None


@st.cache_data(ttl=600) # 10 perc cache
def get_weather_forecast(city):
    url = f'http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={API_KEY}&units=metric'
    try:
        response = requests.get(url)
        return response.json()
    except Exception as e:
        st.error(f"Előrejelzés API hiba: {e}")
        return None


def init_database():
    try:
        conn = sqlite3.connect('weather_searches.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS searches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city_name TEXT,
                temperature REAL,
                humidity INTEGER,
                wind_speed REAL,
                search_time TEXT
            )
        ''')
        conn.commit()
        conn.close()
    except Exception as e:
        st.warning(f"Adatbázis hiba: {e}")

def log_search(city, temp, humidity, wind_speed):
    """Elmenti a keresést az adatbázisba"""
    try:
        conn = sqlite3.connect('weather_searches.db')
        cursor = conn.cursor()
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('''
            INSERT INTO searches (city_name, temperature, humidity, wind_speed, search_time)
            VALUES (?, ?, ?, ?, ?)
        ''', (city, temp, humidity, wind_speed, current_time))
        conn.commit()
        conn.close()
    except Exception as e:
        st.warning(f"Logolási hiba: {e}")

init_database()


# Streamlit alkalmazás kezdete

# Főoldal
st.title("Időjárás Alkalmazás")

# Oldalsáv
st.sidebar.header("Beállítások")
city = st.sidebar.text_input(
    "Város neve:",
    value="Budapest",
    help="Add meg a város nevét"
)

if st.sidebar.button("Keresés"):
    st.rerun()

# Törzs oldal
if city:
    st.header(f"Időjárás: {city}")
    
    with st.spinner("Adatok betöltése..."):
        weather_data = get_current_weather(city)
    
    if weather_data is None:
        st.warning("Nem sikerült lekérni az adatokat!")
        st.stop()
    
    temp = weather_data['main']['temp']
    humidity = weather_data['main']['humidity']
    wind_speed = weather_data['wind']['speed']
    lat = weather_data['coord']['lat']
    lon = weather_data['coord']['lon']
    description = weather_data['weather'][0]['description']
    
    log_search(city, temp, humidity, wind_speed)
    
    # KPI-ok
    st.subheader(f"Jelenlegi időjárás: {description.capitalize()}")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            label="Hőmérséklet",
            value=f"{temp:.1f} °C"
        )
    
    with col2:
        st.metric(
            label="Páratartalom",
            value=f"{humidity} %"
        )
    
    with col3:
        st.metric(
            label="Szél",
            value=f"{wind_speed} m/s"
        )
    
    st.divider()
    
    st.subheader(f"{city} helyzete")
    map_data = pd.DataFrame({
        'lat': [lat],
        'lon': [lon]
    })
    st.map(map_data, zoom=10)
    
    st.divider()
    
    st.subheader("5 napos hőmérséklet előrejelzés")
    
    with st.spinner("Előrejelzés betöltése..."):
        forecast_data = get_weather_forecast(city)
    
    if forecast_data and forecast_data.get('cod') == '200':
        forecast_list = []
        for item in forecast_data['list'][:40]:  # 5 nap x 8 mérés
            forecast_list.append({
                'Dátum': datetime.fromtimestamp(item['dt']).strftime('%m-%d %H:%M'),
                'Hőmérséklet': item['main']['temp'],
                'Páratartalom': item['main']['humidity']
            })
        
        df_forecast = pd.DataFrame(forecast_list)
        
        # Chart
        st.line_chart(
            df_forecast.set_index('Dátum')['Hőmérséklet'],
            use_container_width=True
        )
        
    else:
        st.info("Az előrejelzés jelenleg nem elérhető.")

