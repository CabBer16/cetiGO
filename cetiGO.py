import heapq
import folium
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from math import radians, sin, cos, sqrt, atan2
import osmnx as ox
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

matplotlib.use('Agg')
ox.settings.log_console = True
ox.settings.use_cache = True
geolocator = Nominatim(user_agent="ceti_transport")

paradas = {
    "Plaza Patria": {"coords": (20.71218, -103.37844)},
    "Glorieta Minerva": {"coords": (20.67453, -103.38741)},
    "Tonala": {"coords": (20.6236, -103.2345)},
    "Paradero Tlaquepaque": {"coords": (20.6402, -103.3118)},
    "Plaza del Sol": {"coords": (20.64941, -103.40260)},
    "Zapopan Norte": {"coords": (20.74178, -103.40731)},
    "CETI Colomos": {"coords": (20.70312, -103.38929)},
    "Plaza de la Bandera": {"coords": (20.66524, -103.33268)}
}



def calcular_distancia_real(coord1, coord2):
    return geodesic(coord1, coord2).km

ruta1 = {
    "Zapopan Norte": {"Plaza Patria": calcular_distancia_real(paradas["Zapopan Norte"]["coords"], paradas["Plaza Patria"]["coords"])},
    "Plaza Patria": {
        "Zapopan Norte": calcular_distancia_real(paradas["Zapopan Norte"]["coords"], paradas["Plaza Patria"]["coords"]),
        "CETI Colomos": calcular_distancia_real(paradas["Plaza Patria"]["coords"], paradas["CETI Colomos"]["coords"])
    },
    "CETI Colomos": {"Plaza Patria": calcular_distancia_real(paradas["Plaza Patria"]["coords"], paradas["CETI Colomos"]["coords"])}
}

ruta2 = {
    "Tonala": {"Paradero Tlaquepaque": calcular_distancia_real(paradas["Tonala"]["coords"], paradas["Paradero Tlaquepaque"]["coords"])},
    "Paradero Tlaquepaque": {
        "Tonala": calcular_distancia_real(paradas["Tonala"]["coords"], paradas["Paradero Tlaquepaque"]["coords"]),
        "Plaza de la Bandera": calcular_distancia_real(paradas["Paradero Tlaquepaque"]["coords"], paradas["Plaza de la Bandera"]["coords"])
    },
    "Plaza de la Bandera": {
        "Paradero Tlaquepaque": calcular_distancia_real(paradas["Paradero Tlaquepaque"]["coords"], paradas["Plaza de la Bandera"]["coords"]),
        "CETI Colomos": calcular_distancia_real(paradas["Plaza de la Bandera"]["coords"], paradas["CETI Colomos"]["coords"])
    },
    "CETI Colomos": {"Plaza de la Bandera": calcular_distancia_real(paradas["Plaza de la Bandera"]["coords"], paradas["CETI Colomos"]["coords"])}
}

ruta3 = {
    "Plaza del Sol": {"Glorieta Minerva": calcular_distancia_real(paradas["Plaza del Sol"]["coords"], paradas["Glorieta Minerva"]["coords"])},
    "Glorieta Minerva": {
        "Plaza del Sol": calcular_distancia_real(paradas["Plaza del Sol"]["coords"], paradas["Glorieta Minerva"]["coords"]),
        "CETI Colomos": calcular_distancia_real(paradas["Glorieta Minerva"]["coords"], paradas["CETI Colomos"]["coords"])
    },
    "CETI Colomos": {"Glorieta Minerva": calcular_distancia_real(paradas["Glorieta Minerva"]["coords"], paradas["CETI Colomos"]["coords"])}
}

grafo = {
    **ruta1,
    **ruta2,
    **ruta3
}

def obtener_ruta_calle(origen_coord, destino_coord):
    lugar = "Guadalajara, Jalisco, México"
    grafo_calles = ox.graph_from_place(lugar, network_type='drive')
    
    origen_nodo = ox.distance.nearest_nodes(grafo_calles, origen_coord[1], origen_coord[0])
    destino_nodo = ox.distance.nearest_nodes(grafo_calles, destino_coord[1], destino_coord[0])
    
    ruta = nx.shortest_path(grafo_calles, origen_nodo, destino_nodo, weight='length')
    
    return ruta, grafo_calles

def mostrar_mapa_ruta_calle(origen, destino):

    origen_coord = paradas[origen]["coords"]
    destino_coord = paradas[destino]["coords"]
    
    ruta, grafo_calles = obtener_ruta_calle(origen_coord, destino_coord)
    
    mapa = ox.plot_route_folium(grafo_calles, ruta)
    
    folium.Marker(
        location=origen_coord,
        popup=origen,
        icon=folium.Icon(color="green")
    ).add_to(mapa)
    
    folium.Marker(
        location=destino_coord,
        popup=destino,
        icon=folium.Icon(color="red")
    ).add_to(mapa)
    
    mapa.save("ruta_calles.html")
    print("Mapa con ruta por calles guardado como 'ruta_calles.html'")


def construir_grafo_nx(grafo_dict):
    G = nx.Graph()
    for origen, vecinos in grafo_dict.items():
        for destino, peso in vecinos.items():
            G.add_edge(origen, destino, weight=peso)
    return G

grafo_nx = construir_grafo_nx(grafo)

def dijkstra_nx(inicio, destino):
    try:
        ruta = nx.dijkstra_path(grafo_nx, inicio, destino, weight='weight')
        distancia = nx.dijkstra_path_length(grafo_nx, inicio, destino, weight='weight')
        return distancia, ruta
    except nx.NetworkXNoPath:
        return float('inf'), []
    except nx.NodeNotFound:
        return float('inf'), []

dijkstra = dijkstra_nx

def dijkstra(inicio, destino):
    distancias = {nodo: float('inf') for nodo in grafo}
    distancias[inicio] = 0
    cola = [(0, inicio)]
    rutas = {inicio: [inicio]}
    
    while cola:
        (dist_actual, actual) = heapq.heappop(cola)
        
        if actual == destino:
            break
            
        for vecino, peso in grafo.get(actual, {}).items():
            nueva_dist = dist_actual + peso
            if nueva_dist < distancias.get(vecino, float('inf')):
                distancias[vecino] = nueva_dist
                heapq.heappush(cola, (nueva_dist, vecino))
                rutas[vecino] = rutas[actual] + [vecino]
    
    return distancias.get(destino, float('inf')), rutas.get(destino, [])


def mostrar_ruta():
    print("\nRuta fija del camión:")
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
    
    for i, parada in enumerate(ruta_completa, 1):
        print(f"{i}. {parada}")
    
    mapa = folium.Map(location=[20.7069, -103.3996], zoom_start=13)
    
    for parada in ruta_completa:
        folium.Marker(
            location=paradas[parada]["coords"],
            popup=parada,
            icon=folium.Icon(color="blue", icon="bus", prefix="fa")
        ).add_to(mapa)
    
    for i in range(len(ruta_completa)-1):
        origen = ruta_completa[i]
        destino = ruta_completa[i+1]
        
        try:
            ruta_calle, grafo_calles = obtener_ruta_calle(
                paradas[origen]["coords"],
                paradas[destino]["coords"]
            )
            
            if ruta_calle and grafo_calles:
                route_coords = []
                for node in ruta_calle:
                    point = grafo_calles.nodes[node]
                    route_coords.append((point['y'], point['x']))
                
                folium.PolyLine(
                    route_coords,
                    color=f"#{i*20000:06x}", 
                    weight=5,
                    opacity=0.7,
                    popup=f"Segmento {i+1}: {origen} a {destino}"
                ).add_to(mapa)
            else:
                folium.PolyLine(
                    [paradas[origen]["coords"], paradas[destino]["coords"]],
                    color="gray",
                    weight=3,
                    opacity=0.5
                ).add_to(mapa)
        except Exception as e:
            print(f"Error al procesar segmento {origen}-{destino}: {str(e)}")

            folium.PolyLine(
                [paradas[origen]["coords"], paradas[destino]["coords"]],
                color="gray",
                weight=3,
                opacity=0.5
            ).add_to(mapa)
    
    folium.Marker(
        location=paradas["CETI Colomos"]["coords"],
        popup="CETI Colomos (Destino)",
        icon=folium.Icon(color="red", icon="graduation-cap", prefix="fa")
    ).add_to(mapa)
    
    mapa.save("ruta_completa_calles.html")
    print("\nMapa con ruta completa por calles generado como 'ruta_completa_calles.html'")


def elegir_ruta_personalizada():
    rutas_disponibles = {
        "1": {
            "nombre": "Ruta 1: Zapopan Norte → Plaza Patria → CETI Colomos",
            "paradas": ["Zapopan Norte", "Plaza Patria", "CETI Colomos"],
            "grafo": ruta1
        },
        "2": {
            "nombre": "Ruta 2: Tonalá → Tlaquepaque → Plaza de la Bandera → CETI Colomos",
            "paradas": ["Tonala", "Paradero Tlaquepaque", "Plaza de la Bandera", "CETI Colomos"],
            "grafo": ruta2
        },
        "3": {
            "nombre": "Ruta 3: Plaza del Sol → Glorieta Minerva → CETI Colomos",
            "paradas": ["Plaza del Sol", "Glorieta Minerva", "CETI Colomos"],
            "grafo": ruta3
        }
    }

    print("\nSelecciona una ruta personalizada:")
    for clave, datos in rutas_disponibles.items():
        print(f"{clave}. {datos['nombre']}")
    
    opcion = input("Opción: ")
    if opcion in rutas_disponibles:
        datos_ruta = rutas_disponibles[opcion]
        print(f"\n{datos_ruta['nombre']}:\n")

        for i, parada in enumerate(datos_ruta["paradas"], 1):
            print(f"{i}. {parada}")
        
        distancia_total = 0
        for i in range(len(datos_ruta["paradas"])-1):
            origen = datos_ruta["paradas"][i]
            destino = datos_ruta["paradas"][i+1]
            distancia_total += calcular_distancia_real(
                paradas[origen]["coords"],
                paradas[destino]["coords"]
            )
        
        print(f"\nDistancia total: {distancia_total:.2f} km")
        
        mapa = folium.Map(
            location=[20.7069, -103.3996], 
            zoom_start=13,
            tiles='OpenStreetMap'
        )
        
        for parada in datos_ruta["paradas"]:
            folium.Marker(
                location=paradas[parada]["coords"],
                popup=parada,
                icon=folium.Icon(color="blue", icon="bus", prefix="fa")
            ).add_to(mapa)
        
        for i in range(len(datos_ruta["paradas"])-1):
            origen = datos_ruta["paradas"][i]
            destino = datos_ruta["paradas"][i+1]
            
            try:
                ruta_calle, grafo_calles = obtener_ruta_calle(
                    paradas[origen]["coords"],
                    paradas[destino]["coords"]
                )
                
                if ruta_calle and grafo_calles:
                    route_coords = []
                    for node in ruta_calle:
                        point = grafo_calles.nodes[node]
                        route_coords.append((point['y'], point['x']))
                    
                    folium.PolyLine(
                        route_coords,
                        color=f"#{i*20000:06x}",
                        weight=5,
                        opacity=0.7,
                        popup=f"Segmento {i+1}: {origen} a {destino}"
                    ).add_to(mapa)
                else:
                    folium.PolyLine(
                        [paradas[origen]["coords"], paradas[destino]["coords"]],
                        color="gray",
                        weight=3,
                        opacity=0.5
                    ).add_to(mapa)
            except Exception as e:
                print(f"Error al procesar segmento {origen}-{destino}: {str(e)}")
                folium.PolyLine(
                    [paradas[origen]["coords"], paradas[destino]["coords"]],
                    color="gray",
                    weight=3,
                    opacity=0.5
                ).add_to(mapa)
        
        folium.Marker(
            location=paradas["CETI Colomos"]["coords"],
            popup="CETI Colomos (Destino)",
            icon=folium.Icon(color="red", icon="graduation-cap", prefix="fa")
        ).add_to(mapa)
        
        nombre_archivo = f"ruta_personalizada_{opcion}.html"
        mapa.save(nombre_archivo)
        print(f"\nMapa generado como '{nombre_archivo}'. Ábrelo en tu navegador.")
    else:
        print("Opción inválida.")

def menu():
    while True:
        print("\n ¡Bienvenido a CETI GO !")                                                                                                                                                                                             
        print("1. Ver ruta del camión")
        print("2. Calcular mi tiempo de llegada al CETI")
        print("3. Ver mapa de todas las paradas")
        print("4. Ver rutas personalizadas al CETI")
        print("5. Salir")

        opcion = input("Selecciona una opción: ")

        if opcion == "1":
            mostrar_ruta()
        elif opcion == "2":
            calcular_tiempo_llegada()
        elif opcion == "3":
            mostrar_mapa()
        elif opcion == "4":
            elegir_ruta_personalizada()
        elif opcion == "5":
            print("¡Gracias por usar CETI GO!")
            break
        else:
            print("Opción no válida, intenta de nuevo.")

