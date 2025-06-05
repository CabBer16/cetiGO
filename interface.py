import networkx as nx
import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
from PIL import Image, ImageTk
import io
import folium
from folium import plugins
from folium.plugins import FloatImage
import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import contextily as ctx
import geopandas as gpd
from shapely.geometry import Point, LineString, MultiLineString
import matplotlib
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from math import radians, sin, cos, sqrt, atan2
import osmnx as ox
import networkx as nx
import itertools
import time

from cetiGO import paradas, dijkstra, dijkstra_nx, calcular_tiempo_real, calcular_distancia_real, calcular_tiempo_llegada, grafo

matplotlib.use('Agg')
ox.settings.log_console = True
ox.settings.use_cache = True
geolocator = Nominatim(user_agent="ceti_transport")

class CETIApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CETI GO")
        self.root.geometry("1200x800")
        
        self.style = ttk.Style()
        self.style.configure('TFrame', background='#f0f0f0')
        self.style.configure('TLabel', background='#f0f0f0', font=('Arial', 10))
        self.style.configure('TButton', font=('Arial', 10), padding=5)
        self.style.configure('Header.TLabel', font=('Arial', 14, 'bold'))
        self.style.configure('Title.TLabel', font=('Arial', 16, 'bold'), foreground='darkblue')
        
        self.main_frame = ttk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        self.left_panel = ttk.Frame(self.main_frame, width=300, style='TFrame')
        self.left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        self.left_panel.pack_propagate(False)
        
        self.right_panel = ttk.Frame(self.main_frame)
        self.right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(0,10), pady=10)
        
        ttk.Label(self.left_panel, text="CETI GO", style='Title.TLabel').pack(pady=20)
        
        ttk.Button(self.left_panel, text="Ruta Completa", command=self.mostrar_ruta_completa).pack(fill=tk.X, pady=5, padx=10)
        ttk.Button(self.left_panel, text="Calcular Tiempo de Llegada", command=self.calcular_tiempo_llegada).pack(fill=tk.X, pady=5, padx=10)
        ttk.Button(self.left_panel, text="Paradas del Transporte", command=self.mostrar_todas_paradas).pack(fill=tk.X, pady=5, padx=10)
        ttk.Button(self.left_panel, text="Rutas del Transporte", command=self.elegir_ruta_personalizada).pack(fill=tk.X, pady=5, padx=10)
        ttk.Button(self.left_panel, text="Regreso desde CETI", command=self.elegir_ruta_regreso).pack(fill=tk.X, pady=5, padx=10)
       
        
        self.mapa_frame = ttk.Frame(self.right_panel)
        self.mapa_frame.pack(fill=tk.BOTH, expand=True)
        
        self.fig, self.ax = plt.subplots(figsize=(10, 8))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.mapa_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        self.mostrar_mapa_inicial()

    def obtener_ruta_calle(self, origen_coord, destino_coord):
        try:
            lugar = "Guadalajara, Jalisco, México"
            grafo_calles = ox.graph_from_place(lugar, network_type='drive')
            
            origen_nodo = ox.distance.nearest_nodes(
                grafo_calles, 
                origen_coord[1],  
                origen_coord[0]  
            )
            destino_nodo = ox.distance.nearest_nodes(
                grafo_calles, 
                destino_coord[1], 
                destino_coord[0]
            )
            
            ruta = nx.shortest_path(grafo_calles, origen_nodo, destino_nodo, weight='length')
            
            lineas = []
            for i in range(len(ruta)-1):
                u = ruta[i]
                v = ruta[i+1]
                if grafo_calles.has_edge(u, v):
                    data = grafo_calles.get_edge_data(u, v)
                    if 0 in data: 
                        geom = data[0].get('geometry', LineString([
                            Point(grafo_calles.nodes[u]['x'], grafo_calles.nodes[u]['y']),
                            Point(grafo_calles.nodes[v]['x'], grafo_calles.nodes[v]['y'])
                        ]))
                        lineas.append(geom)
            
            if not lineas:
                return None
                
            if len(lineas) == 1:
                return lineas[0]
            else:
                return MultiLineString(lineas)
                
        except Exception as e:
            print(f"Error al obtener ruta por calles: {e}")
            return None
    
    def mostrar_mapa_inicial(self):
        self.ax.clear()
        
        puntos = []
        for parada, data in paradas.items():
            puntos.append({
                'Parada': parada,
                'geometry': Point(data["coords"][1], data["coords"][0])
            })
        
        gdf = gpd.GeoDataFrame(puntos, crs="EPSG:4326")
        gdf = gdf.to_crs(epsg=3857)  
        
        gdf.plot(ax=self.ax, color='blue', markersize=100, alpha=0.7)
        
        for x, y, label in zip(gdf.geometry.x, gdf.geometry.y, gdf['Parada']):
            self.ax.text(x, y, label, fontsize=8, ha='center', va='bottom')
        
        ctx.add_basemap(self.ax, source=ctx.providers.OpenStreetMap.Mapnik)
        
        self.ax.set_axis_off()
        self.ax.set_title('Paradas de Transporte CETI', fontsize=12)
        
        ceti = gdf[gdf['Parada'] == 'CETI Colomos']
        ceti.plot(ax=self.ax, color='red', markersize=120, alpha=0.7)
        self.ax.text(ceti.geometry.x.iloc[0], ceti.geometry.y.iloc[0], 
                    'CETI Colomos (Destino)', fontsize=9, ha='center', va='bottom', color='red')
        
        self.canvas.draw()
    
    def mostrar_ruta_en_mapa(self, ruta_paradas, titulo="Ruta de Transporte"):
        self.ax.clear()
        
        puntos_ruta = []
        for parada in ruta_paradas:
            coords = paradas[parada]["coords"]
            puntos_ruta.append({
                'Parada': parada,
                'geometry': Point(coords[1], coords[0])
            })
        
        gdf_puntos = gpd.GeoDataFrame(puntos_ruta, crs="EPSG:4326")
        gdf_puntos = gdf_puntos.to_crs(epsg=3857)
        
        lineas_ruta = []
        for i in range(len(ruta_paradas)-1):
            origen = ruta_paradas[i]
            destino = ruta_paradas[i+1]
            
            ruta_calle = self.obtener_ruta_calle(
                paradas[origen]["coords"],
                paradas[destino]["coords"]
            )
            
            if ruta_calle:
                lineas_ruta.append(ruta_calle)
            else:
                lineas_ruta.append(LineString([
                    Point(paradas[origen]["coords"][1], paradas[origen]["coords"][0]),
                    Point(paradas[destino]["coords"][1], paradas[destino]["coords"][0])
                ]))
        
        gdf_lineas = gpd.GeoDataFrame({'geometry': lineas_ruta}, crs="EPSG:4326")
        gdf_lineas = gdf_lineas.to_crs(epsg=3857)
        
        gdf_lineas.plot(ax=self.ax, color='green', linewidth=2, alpha=0.7)
        gdf_puntos.plot(ax=self.ax, color='blue', markersize=100, alpha=0.7)
        
        for x, y, label in zip(gdf_puntos.geometry.x, gdf_puntos.geometry.y, gdf_puntos['Parada']):
            self.ax.text(x, y, label, fontsize=8, ha='center', va='bottom')
        
        ctx.add_basemap(self.ax, source=ctx.providers.OpenStreetMap.Mapnik)
        
        self.ax.set_axis_off()
        self.ax.set_title(titulo, fontsize=12)
        
        inicio = gdf_puntos.iloc[0]
        fin = gdf_puntos.iloc[-1]
        
        self.ax.plot(inicio.geometry.x, inicio.geometry.y, 'o', color='lime', markersize=10)
        self.ax.plot(fin.geometry.x, fin.geometry.y, 'o', color='red', markersize=10)
        
        distancia_total = sum(
            calcular_distancia_real(paradas[ruta_paradas[i]]["coords"], 
            paradas[ruta_paradas[i+1]]["coords"])
            for i in range(len(ruta_paradas)-1)
        )
        
        self.ax.text(
            0.5, 0.02, 
            f"Distancia total: {distancia_total:.2f} km", 
            transform=self.ax.transAxes,
            ha='center', va='bottom',
            bbox=dict(facecolor='white', alpha=0.7)
        )
        
        self.canvas.draw()
        
        return distancia_total
    
    def mostrar_ruta_completa(self):
        self.mostrar_cuadro_carga("Generando mapa de ruta completa...")
        self.root.after(100, self._generar_ruta_completa)
        
    def _generar_ruta_completa(self):
        ruta_completa = [
            "Tonala",
            "Paradero Tlaquepaque",
            "Plaza de la Bandera",
            "Glorieta Minerva",
            "Plaza del Sol",
            "Zapopan Norte",
            "Plaza Patria",
            "CETI Colomos"
        ]
        
        self.mostrar_ruta_en_mapa(ruta_completa, "Ruta Completa del Transporte CETI")
        
        distancia_total = sum(
            calcular_distancia_real(paradas[ruta_completa[i]]["coords"], 
            paradas[ruta_completa[i+1]]["coords"])
            for i in range(len(ruta_completa)-1)
        )
        
        info = f"Ruta completa con {len(ruta_completa)} paradas\n"
        info += f"Distancia total: {distancia_total:.2f} km\n\n"
        info += "Paradas:\n" + "\n".join(f"• {p}" for p in ruta_completa)
        
        self.cerrar_cuadro_carga()
        messagebox.showinfo("Información de Ruta", info)
    
    def calcular_tiempo_llegada(self):
        popup = tk.Toplevel(self.root)
        popup.title("Calcular Tiempo de Llegada")
        popup.geometry("400x450")

        ttk.Label(popup, text="Selecciona tu parada:", style='Header.TLabel').pack(pady=10)

        frame_parada = ttk.Frame(popup)
        frame_parada.pack(pady=5)

        ttk.Label(frame_parada, text="Parada:").pack(side=tk.LEFT)
        self.combo_parada = ttk.Combobox(frame_parada, values=list(grafo.keys()), state="readonly")
        self.combo_parada.pack(side=tk.LEFT, padx=5)
        self.combo_parada.current(0)

        frame_hora = ttk.Frame(popup)
        frame_hora.pack(pady=5)

        ttk.Label(frame_hora, text="Hora de salida:").pack(side=tk.LEFT)
        self.combo_hora = ttk.Combobox(frame_hora, values=["06:00", "13:00"], state="readonly")
        self.combo_hora.pack(side=tk.LEFT, padx=5)
        self.combo_hora.current(0)

        ttk.Button(popup, text="Calcular Tiempo", command=self.calcular_tiempo_opciones).pack(pady=20)

        self.frame_resultados = ttk.Frame(popup)
        self.frame_resultados.pack(fill=tk.X, pady=10)

        self.label_resultado = ttk.Label(self.frame_resultados, text="", wraplength=350)
        self.label_resultado.pack()

    def calcular_tiempo_opciones(self):
        origen = self.combo_parada.get()
        hora_salida = self.combo_hora.get()

        if not origen:
            messagebox.showerror("Error", "Por favor selecciona una parada")
            return

        if not hora_salida:
            messagebox.showerror("Error", "Por favor selecciona una hora de salida")
            return

        self.mostrar_cuadro_carga("Calculando ruta y tiempos...")

        self.root.after(100, lambda: self._calcular_tiempo_opciones(origen, hora_salida))

    def _calcular_tiempo_opciones(self, origen, hora_salida):
        distancia, ruta_paradas = dijkstra(origen, "CETI Colomos")

        if distancia == float('inf'):
            self.cerrar_cuadro_carga()
            messagebox.showerror("Error", "No hay ruta disponible desde esa parada.")
            return

        distancia_total = self.mostrar_ruta_en_mapa(ruta_paradas, f"Ruta desde {origen} a CETI Colomos")

        resultado = f"Ruta desde {origen}:\n\n"
        hora_actual = hora_salida
        tiempo_total = 0

        for i in range(len(ruta_paradas)-1):
            parada_actual = ruta_paradas[i]
            parada_siguiente = ruta_paradas[i+1]
            dist = calcular_distancia_real(paradas[parada_actual]["coords"], paradas[parada_siguiente]["coords"])
            tiempo = calcular_tiempo_real(dist, hora_actual)
            tiempo_total += tiempo

            h, m = map(int, hora_actual.split(":"))
            minutos_totales = h * 60 + m + int(round(tiempo))
            hora_llegada = f"{(minutos_totales // 60) % 24:02d}:{minutos_totales % 60:02d}"

            resultado += f"{parada_actual} → {parada_siguiente}:\n"
            resultado += f"Distancia: {dist:.2f} km\n"
            resultado += f"Tiempo estimado: {tiempo:.0f} min\n"
            resultado += f"Hora estimada de llegada: {hora_llegada}\n\n"

            hora_actual = hora_llegada 

        resultado += f"Distancia total: {distancia_total:.1f} km\n"
        resultado += f"Tiempo estimado total: {tiempo_total:.0f} minutos\n"
        resultado += f"Hora aproximada de llegada a CETI Colomos: {hora_actual}"

        self.label_resultado.config(text=resultado)
        self.cerrar_cuadro_carga()
    
    def mostrar_todas_paradas(self):
        self.mostrar_mapa_inicial()
    
    def elegir_ruta_personalizada(self):
        rutas_disponibles = {
            "1": {
                "nombre": "Ruta 1: Zapopan Norte → Plaza Patria → CETI Colomos",
                "paradas": ["Zapopan Norte", "Plaza Patria", "CETI Colomos"]
            },
            "2": {
                "nombre": "Ruta 2: Tonalá → Tlaquepaque → Plaza de la Bandera → CETI Colomos",
                "paradas": ["Tonala", "Paradero Tlaquepaque", "Plaza de la Bandera", "CETI Colomos"]
            },
            "3": {
                "nombre": "Ruta 3: Plaza del Sol → Glorieta Minerva → CETI Colomos",
                "paradas": ["Plaza del Sol", "Glorieta Minerva", "CETI Colomos"]
            }
        }
        
        popup = tk.Toplevel(self.root)
        popup.title("Rutas Personalizadas")
        popup.geometry("500x300")
        
        ttk.Label(popup, text="Selecciona una ruta:", style='Header.TLabel').pack(pady=10)
        
        frame_rutas = ttk.Frame(popup)
        frame_rutas.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        for i, (clave, datos) in enumerate(rutas_disponibles.items()):
            btn = ttk.Button(
                frame_rutas, 
                text=datos["nombre"], 
                command=lambda d=datos: self.mostrar_ruta_personalizada(d),
                style='TButton'
            )
            btn.pack(fill=tk.X, pady=5)
    
    def mostrar_ruta_personalizada(self, datos_ruta):
        distancia_total = 0
        for i in range(len(datos_ruta["paradas"])-1):
            origen = datos_ruta["paradas"][i]
            destino = datos_ruta["paradas"][i+1]
            distancia_total += calcular_distancia_real(
                paradas[origen]["coords"],
                paradas[destino]["coords"]
            )
        
        self.mostrar_ruta_en_mapa(datos_ruta["paradas"], datos_ruta["nombre"])
        
        # Mostrar información de la ruta
        info = f"{datos_ruta['nombre']}\n\n"
        info += f"📏 Distancia total: {distancia_total:.2f} km\n\n"
        info += "🚏 Paradas:\n" + "\n".join(f"• {p}" for p in datos_ruta["paradas"])
        
        messagebox.showinfo("Información de Ruta", info)
    
    def elegir_ruta_regreso(self):
        rutas_regreso = {
            "1": {
                "nombre": "Regreso Ruta 1: CETI Colomos → Plaza Patria → Zapopan Norte",
                "paradas": ["CETI Colomos", "Plaza Patria", "Zapopan Norte"]
            },
            "2": {
                "nombre": "Regreso Ruta 2: CETI Colomos → Plaza de la Bandera → Paradero Tlaquepaque → Tonala",
                "paradas": ["CETI Colomos", "Plaza de la Bandera", "Paradero Tlaquepaque", "Tonala"]
            },
            "3": {
                "nombre": "Regreso Ruta 3: CETI Colomos → Glorieta Minerva → Plaza del Sol",
                "paradas": ["CETI Colomos", "Glorieta Minerva", "Plaza del Sol"]
            }
        }

        popup = tk.Toplevel(self.root)
        popup.title("Rutas de Regreso")
        popup.geometry("500x350")
        ttk.Label(popup, text="Selecciona una ruta de regreso:", style='Header.TLabel').pack(pady=10)

        frame_rutas = ttk.Frame(popup)
        frame_rutas.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        for i, (clave, datos) in enumerate(rutas_regreso.items()):
            btn = ttk.Button(
                frame_rutas,
                text=datos["nombre"],
                command=lambda d=datos: self.mostrar_ruta_regreso(d)
            )
            btn.pack(fill=tk.X, pady=5)

    def mostrar_ruta_regreso(self, datos_ruta):
        popup = tk.Toplevel(self.root)
        popup.title("Horario de Regreso")
        popup.geometry("350x200")
        ttk.Label(popup, text="Selecciona el horario de salida desde CETI:", style='Header.TLabel').pack(pady=10)

        horarios = ["15:00", "21:30"]
        self.hora_regreso = tk.StringVar(value=horarios[0])
        combo = ttk.Combobox(popup, values=horarios, textvariable=self.hora_regreso, state="readonly")
        combo.pack(pady=10)
        combo.current(0)

        def calcular_y_mostrar():
            popup.destroy()
            distancia_total = 0
            for i in range(len(datos_ruta["paradas"])-1):
                origen = datos_ruta["paradas"][i]
                destino = datos_ruta["paradas"][i+1]
                distancia_total += calcular_distancia_real(
                    paradas[origen]["coords"],
                    paradas[destino]["coords"]
                )
            self.mostrar_ruta_en_mapa(datos_ruta["paradas"], datos_ruta["nombre"])
            tiempo_total = calcular_tiempo_real(distancia_total, self.hora_regreso.get())
            info = f"{datos_ruta['nombre']}\n\n"
            info += f"Distancia total: {distancia_total:.2f} km\n"
            info += f"Tiempo estimado: {tiempo_total:.0f} minutos\n"
            info += f"Hora de salida: {self.hora_regreso.get()}\n\n"
            info += f"Paradas:\n" + "\n".join(f"• {p}" for p in datos_ruta["paradas"])
            messagebox.showinfo("Información de Ruta de Regreso", info)

        ttk.Button(popup, text="Calcular y Mostrar Ruta", command=calcular_y_mostrar).pack(pady=20)
    
    def mostrar_cuadro_carga(self, mensaje="Cargando..."):
        self.cuadro_carga = tk.Toplevel(self.root)
        self.cuadro_carga.title("Por favor espera")
        self.cuadro_carga.geometry("250x120")
        self.cuadro_carga.resizable(False, False)
        self.cuadro_carga.grab_set()
        ttk.Label(self.cuadro_carga, text=mensaje, font=("Arial", 12)).pack(pady=(10, 5))

        self.gif = Image.open("cargando.gif")
        self.frames = []
        try:
            while True:
                frame = ImageTk.PhotoImage(self.gif.copy())
                self.frames.append(frame)
                self.gif.seek(len(self.frames))  
        except EOFError:
            pass 

        self.gif_label = ttk.Label(self.cuadro_carga)
        self.gif_label.pack()
        self._animar_gif(0)

        self.cuadro_carga.update()

   
    def _animar_gif(self, idx):
        if hasattr(self, 'frames') and self.frames:
            frame = self.frames[idx % len(self.frames)]
            self.gif_label.configure(image=frame)
            self.cuadro_carga.after(80, self._animar_gif, idx + 1)

    def cerrar_cuadro_carga(self):
        if hasattr(self, 'cuadro_carga') and self.cuadro_carga.winfo_exists():
            self.cuadro_carga.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = CETIApp(root)
    root.mainloop()
