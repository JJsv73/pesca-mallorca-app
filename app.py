import streamlit as st
import requests
from datetime import datetime, timedelta
import statistics

st.set_page_config(page_title="Zonas de Pesca en Mallorca", page_icon="🎣")

# Título y descripción
st.title("🎣 Zonas de Pesca Recomendadas en Mallorca")
st.write("Esta aplicación muestra las zonas recomendadas para pescar según las condiciones meteorológicas actuales.")

# Parámetros ajustables, pero con los valores predeterminados específicos
col1, col2 = st.columns(2)
with col1:
    viento_max = st.slider("Viento máximo (m/s)", 0.0, 10.0, 4.0, 0.5)  # Valor predeterminado de 4 m/s
with col2:
    olas_max = st.slider("Altura de olas máxima (m)", 0.0, 2.0, 0.4, 0.1)  # Valor predeterminado de 0.4 m

# Mensaje de advertencia sobre los límites recomendados
if viento_max > 4.0 or olas_max > 0.4:
    st.warning("⚠️ Advertencia: Los valores recomendados son viento máximo de 4 m/s y olas máximas de 0.4 m. Con valores superiores, la pesca puede ser peligrosa o poco efectiva.")

# Zonas costeras de Mallorca
zonas = {
    "Cala de San Vicente": {"lat": 39.9197, "lon": 3.0441, "region": "Norte"},
    "Camp de Mar": {"lat": 39.5436, "lon": 2.4219, "region": "Suroeste"},
    "Bahía de Pollença": {"lat": 39.9079, "lon": 3.0935, "region": "Norte"},
    "Portocolom": {"lat": 39.4178, "lon": 3.2673, "region": "Este"},
    "Cala Figuera": {"lat": 39.3315, "lon": 3.1671, "region": "Sureste"},
    "Palma (Can Pastilla)": {"lat": 39.5322, "lon": 2.7389, "region": "Sur"},
    "Colònia de Sant Jordi": {"lat": 39.3221, "lon": 3.0145, "region": "Sur"},
    "Son Serra de Marina": {"lat": 39.7100, "lon": 3.2601, "region": "Noreste"}
}

# Días a consultar
hoy = datetime.now().date()
fechas_consulta = [hoy + timedelta(days=i) for i in range(3)]

# Pestañas para los diferentes días
tabs = st.tabs([
    "Hoy" if i == 0 else "Mañana" if i == 1 else f"{fecha.strftime('%A, %d %B')}" 
    for i, fecha in enumerate(fechas_consulta)
])

# Función para agrupar datos en paquetes de 6 horas
def agrupar_por_paquetes(datos_dia):
    if not datos_dia:
        return []
    
    # Definimos 4 paquetes de 6 horas
    paquetes = [
        {"nombre": "Madrugada (00:00-06:00)", "datos": []},
        {"nombre": "Mañana (06:00-12:00)", "datos": []},
        {"nombre": "Tarde (12:00-18:00)", "datos": []},
        {"nombre": "Noche (18:00-00:00)", "datos": []}
    ]
    
    for dato in datos_dia:
        hora = int(dato["hora"].split(":")[0])
        if 0 <= hora < 6:
            paquetes[0]["datos"].append(dato)
        elif 6 <= hora < 12:
            paquetes[1]["datos"].append(dato)
        elif 12 <= hora < 18:
            paquetes[2]["datos"].append(dato)
        else:
            paquetes[3]["datos"].append(dato)
    
    # Calcular resumen para cada paquete
    for paquete in paquetes:
        if paquete["datos"]:
            vientos = [d["viento"] for d in paquete["datos"]]
            olas = [d["olas"] for d in paquete["datos"]]
            
            paquete["viento_min"] = min(vientos)
            paquete["viento_max"] = max(vientos)
            paquete["viento_promedio"] = statistics.mean(vientos)
            
            paquete["olas_min"] = min(olas)
            paquete["olas_max"] = max(olas)
            paquete["olas_promedio"] = statistics.mean(olas)
            
            # Un paquete es apto si al menos una hora es apta
            paquete["apto"] = any(d["apto"] for d in paquete["datos"])
    
    # Solo devolver paquetes que tienen datos
    return [p for p in paquetes if p["datos"]]

# Mostrar spinner mientras se cargan los datos
with st.spinner("Consultando datos meteorológicos..."):
    # Resultados
    resultados_por_dia = {fecha.isoformat(): [] for fecha in fechas_consulta}
    datos_zonas = {}
    
    # Procesar cada zona
    for nombre, coords in zonas.items():
        try:
            # Usamos la API general de Open-Meteo
            url = (
                f"https://api.open-meteo.com/v1/forecast?"
                f"latitude={coords['lat']}&longitude={coords['lon']}"
                f"&hourly=windspeed_10m&timezone=auto"
            )
            
            response = requests.get(url)
            if response.status_code != 200:
                st.error(f"Error al consultar API para {nombre}: {response.status_code}")
                continue
                
            data = response.json()
            
            if "hourly" in data:
                horas = data["hourly"]["time"]
                viento = data["hourly"]["windspeed_10m"]
                
                # Para la altura de las olas, usamos una fórmula aproximada para aguas costeras
                olas = []
                for v in viento:
                    altura_ola = v * 0.08  # Fórmula ajustada para Mallorca
                    olas.append(altura_ola)
                
                datos_zonas[nombre] = {
                    "region": coords["region"],
                    "datos": []
                }
                
                for fecha in fechas_consulta:
                    fecha_str = fecha.isoformat()
                    zona_apta = False
                    datos_dia = []
                    
                    for i, hora in enumerate(horas):
                        if hora.startswith(fecha_str):
                            hora_obj = datetime.fromisoformat(hora.replace('Z', '+00:00'))
                            hora_formato = hora_obj.strftime("%H:%M")
                            
                            # Verificar si cumple ESTRICTAMENTE las condiciones
                            apto = viento[i] <= viento_max and olas[i] <= olas_max
                            
                            datos_dia.append({
                                "hora": hora_formato,
                                "viento": viento[i],
                                "olas": olas[i],
                                "apto": apto
                            })
                            
                            # Solo si alguna hora cumple las condiciones, la zona es apta
                            if apto:
                                zona_apta = True
                    
                    datos_zonas[nombre]["datos"].append(datos_dia)
                    
                    # Solo agregar a resultados si es realmente apta
                    if zona_apta:
                        resultados_por_dia[fecha_str].append(nombre)
        except Exception as e:
            st.error(f"Error al procesar datos para {nombre}: {str(e)}")
            continue

# Mostrar los resultados en las pestañas
for i, (tab, fecha) in enumerate(zip(tabs, fechas_consulta)):
    fecha_str = fecha.isoformat()
    
    with tab:
        # Verificar si hay zonas recomendadas
        zonas_recomendadas = resultados_por_dia[fecha_str]
        
        # Mensaje general sobre condiciones
        if not zonas_recomendadas:
            st.error("❌ No se recomienda ir a pescar con estas condiciones meteorológicas.")
            st.warning("""
            **AVISO DE SEGURIDAD**: Las condiciones meteorológicas actuales no son favorables para la pesca.
            Se recomienda no salir al mar con vientos superiores a 4 m/s o altura de olas superior a 0.4 m.
            """)
        
        # Mostrar todas las zonas agrupadas por región
        st.subheader("Condiciones por zona")
        
        # Agrupar por región
        regiones = {}
        for nombre, info in datos_zonas.items():
            region = info["region"]
            if region not in regiones:
                regiones[region] = []
            regiones[region].append(nombre)
        
        # Mostrar por región
       # En la parte donde se muestran las regiones, cambio la propiedad "expanded" a False
for region, zonas_region in sorted(regiones.items()):
    with st.expander(f"{region} ({len(zonas_region)} zonas)", expanded=False):  # Cambiado a False
        for nombre in zonas_region:
            # El resto del código permanece igual
                    # Verificar si esta zona está en las recomendadas
                    es_recomendada = nombre in zonas_recomendadas
                    
                    if es_recomendada:
                        st.markdown(f"### ✅ {nombre}")
                    else:
                        st.markdown(f"### ❌ {nombre}")
                    
                    # Datos meteorológicos
                    if nombre in datos_zonas and i < len(datos_zonas[nombre]["datos"]):
                        datos_dia = datos_zonas[nombre]["datos"][i]
                        
                        # Calcular y mostrar valores promedio
                        if datos_dia:
                            promedio_viento = sum(d["viento"] for d in datos_dia) / len(datos_dia)
                            promedio_olas = sum(d["olas"] for d in datos_dia) / len(datos_dia)
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                color_viento = "green" if promedio_viento <= viento_max else "red"
                                st.markdown(f"<span style='color:{color_viento}'>**Viento promedio:** {promedio_viento:.1f} m/s</span>", unsafe_allow_html=True)
                            with col2:
                                color_olas = "green" if promedio_olas <= olas_max else "red"
                                st.markdown(f"<span style='color:{color_olas}'>**Olas promedio:** {promedio_olas:.2f} m</span>", unsafe_allow_html=True)
                            
                            # Agrupar datos en paquetes de 6 horas
                            paquetes = agrupar_por_paquetes(datos_dia)
                            
                            # Mostramos los datos en formato de paquetes
                            st.write("**Previsión por periodos de 6 horas:**")
                            
                            for j, paquete in enumerate(paquetes):
                                if not paquete["datos"]:
                                    continue  # Omitir paquetes sin datos
                                    
                                # Determinar si el paquete es apto
                                color = "green" if paquete["apto"] else "red"
                                estado = "✓ Condiciones aptas" if paquete["apto"] else "✗ No recomendado"
                                
                                st.markdown(f"""
                                <div style="padding:15px;border:1px solid {color};border-radius:5px;margin-bottom:10px">
                                    <h4 style="margin:0;color:{color}">{paquete["nombre"]}</h4>
                                    <p style="font-weight:bold;color:{color};margin:5px 0">{estado}</p>
                                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px">
                                        <div>
                                            <p style="margin:0"><b>Viento:</b></p>
                                            <p style="margin:0">Mín: {paquete["viento_min"]:.1f} m/s</p>
                                            <p style="margin:0">Máx: {paquete["viento_max"]:.1f} m/s</p>
                                            <p style="margin:0">Promedio: {paquete["viento_promedio"]:.1f} m/s</p>
                                        </div>
                                        <div>
                                            <p style="margin:0"><b>Olas:</b></p>
                                            <p style="margin:0">Mín: {paquete["olas_min"]:.2f} m</p>
                                            <p style="margin:0">Máx: {paquete["olas_max"]:.2f} m</p>
                                            <p style="margin:0">Promedio: {paquete["olas_promedio"]:.2f} m</p>
                                        </div>
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)
                    
                    st.divider()

# Aviso importante
st.info("""
**⚠️ Aviso importante**: Esta aplicación usa datos meteorológicos con estimación aproximada para la altura de las olas. 
Para decisiones sobre navegación, siempre consulta fuentes oficiales como AEMET o Puertos del Estado.

Recuerda que la pesca en condiciones de viento superior a 4 m/s o altura de olas superior a 0.4 m puede ser peligrosa 
y poco productiva en las costas de Mallorca.
""")

# Añadir información en la barra lateral
st.sidebar.write("## Información")
st.sidebar.write(f"Última actualización: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
st.sidebar.write("Datos obtenidos de: Open-Meteo API")

# Criterios y recomendaciones
st.sidebar.write("## Criterios de seguridad")
st.sidebar.write("""
**Condiciones recomendadas para pesca:**
- Viento máximo: 4 m/s
- Olas máximas: 0.4 m

**No se recomienda pescar cuando:**
- El viento supera los 4 m/s
- Las olas superan los 0.4 m de altura
""")