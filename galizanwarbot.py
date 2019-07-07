#!/usr/bin/python3
# coding=utf-8
from shapely.geometry import shape
from shapely.figures import set_limits, GREEN, BLACK, RED
from shapely.ops import cascaded_union
import fiona
from descartes import PolygonPatch
import matplotlib.pyplot as plt
import random
import sys
import csv
from datetime import datetime, timedelta
import locale
import twitter

def cargar_comarcas (path):
    comarcas = {}
    with fiona.open(path, "r") as comarcas_shp:
        for comarca in comarcas_shp:
            comarcas[comarca["properties"]["CCom"]] = {"nome":comarca["properties"]["Nome"], "color":comarca["properties"]["color"], "concellos":[]}
    return comarcas

def escoller_agresor(concellos_shp):
    poly = random.choice(concellos_shp)
    return poly

def escoller_agredido(concellos_shp, agresor):
    distancia = -1
    agredido = None
    agresor_shape = shape(agresor["geometry"])
    for concello in concellos_shp:
        if governo_actual(concello) != governo_actual(agresor):
            d = agresor_shape.centroid.distance(shape(concello["geometry"]).centroid)
            if distancia == -1 or d < distancia:
                distancia = d
                agredido = concello
    if distancia == -1:
        exit()
    print("distancia de ataque: " + str(distancia))
    return agredido

def governo_actual(concello):
    return current_state[concello["properties"]["CCONC"]]

def formato_data(data):
    return data.strftime("%a, %d %b %Y")


def iteracion(comarcas):
    global current_state
    global current_iteration
    resumo = ""
    assoc_conc_parr = {}
    dpi = 180
    
    with fiona.open("datos_concellos.shp", "r") as concellos_shp:
        agresor = escoller_agresor(concellos_shp)
        agredido = escoller_agredido(concellos_shp, agresor)
        
        print("concello agresor: " + agresor["properties"]["NOME"] + " (" + comarcas[governo_actual(agresor)]["nome"] + ")")
        print("concello agredido: " + agredido["properties"]["NOME"] + " (" + comarcas[governo_actual(agredido)]["nome"] + ")")

        fig = plt.figure(1, figsize=(10,10), dpi=dpi)
        ax = fig.add_subplot(111)
        ax.set_aspect("equal")
        
        for concello in concellos_shp:
            assoc_conc_parr[concello["properties"]["CCONC"]] = []
            color_conc = BLACK
            zorder_conc = 2
            width_conc = 0.5
            hatch_conc = None
            if concello["properties"]["CCONC"] == agredido["properties"]["CCONC"]:
                color_conc = RED
                zorder_conc = 10
                width_conc = 1.5
                hatch_conc = r'//'
            comarcas[governo_actual(concello)]["concellos"].append(shape(concello["geometry"]))
            patch = PolygonPatch(concello["geometry"], fc=comarcas[governo_actual(concello)]["color"], ec=color_conc, alpha=1, linewidth=width_conc, zorder=zorder_conc, hatch=hatch_conc)
            ax.add_patch(patch)
    
        
    with fiona.open("datos_parroquias.shp", "r") as parroquias:
        for parroquia in parroquias:
            assoc_conc_parr[parroquia["properties"]["CCONC"]].append(parroquia["properties"]["NOME"])
            color_parr = BLACK
            zorder_parr = 3
            if parroquia["properties"]["CCONC"] == agredido["properties"]["CCONC"]:
                color_parr = BLACK
                zorder_parr = 11
            patch = PolygonPatch(parroquia["geometry"], fc="none", ec=color_parr, alpha=0.5, linewidth=0.1, zorder=zorder_parr)
            ax.add_patch(patch)
    
    for ccom,comarca in comarcas.items():
        if len(comarca["concellos"]) > 0 :
            color_com = BLACK
            zorder_com = 4
            width_com = 1
            if ccom == governo_actual(agresor):
                color_com = 'lime'
                zorder_com = 6
                width_com = 3
            if ccom == governo_actual(agredido):
                color_com = "mediumblue"
                zorder_com = 5
                width_com = 3
            polygon = PolygonPatch(cascaded_union(comarca["concellos"]), fc="none", ec=color_com, alpha=1, linewidth=width_com, zorder=zorder_com)
            ax.add_patch(polygon)
    
    ax.set_axis_off()
    ax.set_xlim(450000, 750000)
    ax.set_ylim(4600000, 4850000)
    plt.savefig(fname="current.png", bbox_inches="tight", transparent=True, dpi=dpi)
    
    ax.set_xlim(int(shape(agredido["geometry"]).centroid.x - 40000), int(shape(agredido["geometry"]).centroid.x + 40000))
    ax.set_ylim(int(shape(agredido["geometry"]).centroid.y - 40000), int(shape(agredido["geometry"]).centroid.y + 40000))
    #plt.show();
    plt.savefig(fname="current_zoom.png", bbox_inches="tight", transparent=True, dpi=dpi)
    
    #####Escribindo a conquista
    resumo += formato_data(datetime.strptime("2020/01/01", "%Y/%m/%d") + timedelta(days=current_iteration))
    resumo += ", " + comarcas[governo_actual(agresor)]["nome"] + " invade o concello de " + agredido["properties"]["NOME"]
    resumo += ", anteriormente baixo o control de " + comarcas[governo_actual(agredido)]["nome"] + "."
    
    ###Escoller unha parroquia
    l_parr = assoc_conc_parr[agredido["properties"]["CCONC"]]
    if len(l_parr) > 0:
        resumo += "\nA batalla decisiva deuse na parroquia de " + random.choice(l_parr) + "."
    
    print("Concellos na comarca despois do ataque: "+ str(len(comarcas[governo_actual(agredido)]["concellos"])-1))
    if len(comarcas[governo_actual(agredido)]["concellos"]) == 1:
        print("Comarca derrotada")
        resumo += "\n" + comarcas[governo_actual(agredido)]["nome"] + " foi completamente derrotada."
        c_com = -1
        for key,comarca in comarcas.items():
            if len(comarca["concellos"]) > 0:
                c_com += 1
        if c_com <= 1:
            print("Fin do xogo")
            resumo += "\n" + comarcas[governo_actual(agresor)]["nome"] + " fíxose co control de todo o país!"
            rematar_partida()
        else:
            resumo += "\nQuedan " + str(c_com) + " comarcas en pé."
    
    #hashtags
    resumo += "\n" + nome_a_hashtag(comarcas[governo_actual(agresor)]["nome"])
    resumo += " " + nome_a_hashtag(agredido["properties"]["NOME"])
    
    #rexístrase o cambio de governo
    current_state[agredido["properties"]["CCONC"]] = governo_actual(agresor)
    current_iteration += 1
    
    return resumo

def nome_a_hashtag(nome):
    return '#' + "".join(x.capitalize() or ' ' for x in nome.split(' '))

def cargar_datos_iniciais(conc_path, cstate_path, cit_path):
    global current_state
    global current_iteration
    random.seed()
    with fiona.open(conc_path, "r") as concellos_shp:
        for concello in concellos_shp:
            current_state[concello["properties"]["CCONC"]] = concello["properties"]["CCOM"]
    with open(cstate_path, mode='w') as current_state_file:
        writer = csv.writer(current_state_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        for concello,comarca in current_state.items():
            writer.writerow([concello, comarca])
    with open(cit_path, "w") as it_file:
        it_file.write("0")

def cargar_datos(cstate_path, cit_path):
    global current_state
    global current_iteration
    with open(cstate_path, mode='r') as current_state_file:
        csv_reader = csv.reader(current_state_file)
        for row in csv_reader:
            current_state[int(row[0])] = int(row[1])
    
    with open(cit_path, "r") as it_file:
        current_iteration = int(it_file.read())

def gardar_datos(cstate_path, cit_path):
    with open(cstate_path, mode='w') as current_state_file:
        writer = csv.writer(current_state_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        for concello,comarca in current_state.items():
            writer.writerow([concello, comarca])
    with open(cit_path, "w") as it_file:
        it_file.write(str(current_iteration))

def partida_activa():
    with open('activa.txt', "r") as activa_file:
        return int(activa_file.read()) > 0

def rematar_partida():
   with open('activa.txt', "w") as activa_file:
        activa_file.write(str(0))

def tweet_resumo(resumo, img, img_zoom):
    api = twitter.Api(consumer_key='consumer_key',
                      consumer_secret='consumer_secret',
                      access_token_key='access_token_key',
                      access_token_secret='access_token_secret')
    status = api.PostUpdate(resumo, media=[img,img_zoom])

#COMEZO DO SCRIPT
locale.setlocale(locale.LC_TIME, "gl_ES")
current_state = {}
current_iteration = 0
if len(sys.argv) > 1 and sys.argv[1] == 'reinicio':
    cargar_datos_iniciais("datos_concellos.shp", "current_state.csv", "current_iteration.txt")
    print("Reinicio completado")
else:
    if partida_activa():
        cargar_datos("current_state.csv", "current_iteration.txt")

        comarcas = cargar_comarcas("datos_comarcas.shp")
        resumo = iteracion(comarcas)
        gardar_datos("current_state.csv", "current_iteration.txt")
        tweet_resumo(resumo, "current.png", "current_zoom.png")
