# 🚌 Dashboard de Tráfico Urbano — Líneas 544 & 525

Dashboard interactivo Streamlit para monitoreo operativo en tiempo real.

## Instalación

```bash
pip install -r requirements.txt
```

## Ejecución

```bash
streamlit run dashboard_transito.py
```

El dashboard se abrirá en http://localhost:8501

---

## Estructura del Dashboard

### 🔧 Filtros (Sidebar)
- **Rango de Fechas** — Compara períodos (semana 1 vs semana 2)
- **Línea / Servicio** — Filtra por 544 o 525
- **Interno** — Rendimiento individual por coche
- **Estado de Obra** — Solo días con desvíos activos
- **Turno** — Mañana / Tarde / Noche

### 📊 KPIs (5 indicadores)
| Indicador | Verde | Amarillo | Rojo |
|---|---|---|---|
| % Puntualidad | ≥80% | 70–79% | <70% |
| Retraso Promedio | ≤5 min | 5–12 min | >12 min |
| Velocidad Comercial | ≥17 km/h | 15–17 km/h | <15 km/h |
| Desvío KM | ≤1 km | 1–3 km | >3 km |

### 📈 Gráficos
1. **Semáforo de Salidas** — Gauge con umbral en 70%
2. **Heatmap Horario** — Retraso promedio por día y hora
3. **Barras por Interno** — Ordena de mejor a peor, con color automático
4. **Comparador KM** — Autorizados vs Recorridos por interno
5. **Evolución Temporal** — Puntualidad diaria + días con obra sombreados
6. **Impacto Obra** — Retraso Con Obra vs Sin Obra

### 🚨 Alertas Automáticas
- **Naranja** si un interno supera **3 vueltas perdidas** en el período
- **Rojo** si la velocidad comercial cae **por debajo de 15 km/h**
- Banner de alerta visible en la parte superior

---

## Conectar con tus datos reales

Reemplazá la función `generar_datos()` con la carga de tus CSV:

```python
@st.cache_data
def cargar_datos():
    df_salidas   = pd.read_csv("salidas.csv", parse_dates=["Fecha"])
    df_novedades = pd.read_csv("novedades.csv", parse_dates=["Fecha"])
    
    # Normalizar nombres de internos
    df_salidas["Interno"] = df_salidas["Interno"].str.strip().str.upper()
    
    # Convertir tiempo de retraso a minutos enteros
    # df_salidas["MinutosRetraso"] = pd.to_timedelta(df_salidas["Retraso"]).dt.total_seconds() / 60
    
    # Marcar días con obra
    fechas_obra = df_novedades["Fecha"].dt.date.unique()
    df_salidas["EstadoObra"] = df_salidas["Fecha"].dt.date.apply(
        lambda d: "Con Obra" if d in fechas_obra else "Sin Obra"
    )
    return df_salidas

df_raw = cargar_datos()
```

## Columnas esperadas en el CSV
| Columna | Tipo | Descripción |
|---|---|---|
| Fecha | datetime | Fecha de la salida |
| Linea | str | "544" o "525" |
| Interno | str | Ej: "500-055" |
| Chofer | str | Nombre del chofer |
| Turno | str | "Mañana" / "Tarde" / "Noche" |
| HoraProgramada | int | Hora de salida (0–23) |
| MinutosRetraso | float | Retraso en minutos |
| KM_Autorizados | float | KM del recorrido oficial |
| KM_Recorridos | float | KM realmente registrados |
| VelocidadComercial | float | km/h promedio del servicio |
