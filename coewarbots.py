#!/usr/bin/python3
# coding=utf-8

import mysql.connector as mariadb
from configloader import Config
import fiona
from shapely.geometry import shape
from shapely.figures import set_limits, GREEN, BLACK, RED
from shapely.ops import cascaded_union
import matplotlib.pyplot as plt
from descartes import PolygonPatch
import random
import math

class WarBotStateManager:
    """Manages territories and factions from WarBots."""
    
    db = None    
    territorios = {}
    faccions = {}
    formables = {}
    activo = 0
    iteracion_actual = 0
    
    def _conectar(self):
        config = Config()
        if self.db == None:
            self.db = mariadb.connect(user=config.gwb('db_user'),
                        password=config.gwb('db_password'),
                        host=config.gwb('db_location'),
                        database=config.gwb('db_name'))
    
    def load_data(self):
        config = Config()
        self._conectar()
        cursor = self.db.cursor()
        sql_faccion = "SELECT id, cor, nome FROM faccion"
        sql_territorio = "SELECT id, faccion, nome, faccion_orixinal FROM territorio"
        sql_rexion = "SELECT id, territorio, nome FROM parroquia"
        sql_potencial = "SELECT territorio, faccion FROM faccion_potencial"
        sql_estado = "SELECT activo, ronda_actual FROM estado_xogo"
        sql_usuario = "SELECT id, nome, faccion FROM usuario"
        
        cursor.execute(sql_faccion)
        for (id_f, cor, nome) in cursor:
            self.faccions[id_f] = Faccion(id_f, cor, nome)
            
        cursor.execute(sql_territorio)
        for (id_t, id_f, nome, fac_or) in cursor:
            self.territorios[id_t] = Territorio(id_t, self.faccions[id_f], nome, self.faccions[fac_or])
            self.faccions[id_f].territorios.append(self.territorios[id_t])
            self.faccions[fac_or].de_jure.append(self.territorios[id_t])
        
        cursor.execute(sql_rexion)
        for (id_p, id_t, nome) in cursor:
            self.territorios[id_t].rexions.append(nome)
        
        cursor.execute(sql_potencial)
        for (id_t, id_f) in cursor:
            self.formables[id_f] = self.faccions[id_f]
            self.faccions[id_f].de_jure.append(self.territorios[id_t])
            self.faccions[id_f].formable = True
        
        cursor.execute(sql_estado)
        for (activo, ronda_actual) in cursor:
            self.activo = (activo == True)
            self.iteracion_actual = ronda_actual
        
        cursor.execute(sql_usuario)
        for (id, nome, id_f) in cursor:
            self.faccions[id_f].usuarios.append(nome)
        
        cursor.close()
        
        with fiona.open(config.gwb('shp_territories_path'), "r") as territorios_shp:
            for territorio in territorios_shp:
                self.territorios[territorio["properties"]["CCONC"]].xeometria = territorio["geometry"]
        
        with fiona.open(config.gwb('shp_regions_path'), "r") as rexions_shp:
            for rexion in rexions_shp:
                self.territorios[rexion["properties"]["CCONC"]].xeometria_rexions.append(rexion["geometry"])
    
    def close(self):
        if self.db != None:
            self.db.close()
        self.db = None

    def commit(self):
        if self.db != None:
            self.db.commit()

    def inicializar_database(self):
        self._conectar()
        config = Config()
        
        cursor = self.db.cursor()
        cursor.execute("DELETE FROM territorio")
        cursor.execute("DELETE FROM faccion")
        cursor.execute("DELETE FROM ronda")
        cursor.execute("DELETE FROM ronda_usuario")
        cursor.execute("DELETE FROM parroquia")
        cursor.execute("DELETE FROM usuario")
        cursor.execute("DELETE FROM faccion_potencial")
        cursor.execute("UPDATE estado_xogo SET ronda_actual = 0, activo = 0")
        
        sql_faccion = "INSERT INTO faccion (id, cor, nome) VALUES (%s  , %s, %s)"
        sql_territorio = "INSERT INTO territorio (id, faccion, nome, faccion_orixinal) VALUES (%s, %s, %s, %s)"
        sql_potencial = "INSERT INTO faccion_potencial (territorio, faccion) VALUES (%s, %s)"
        sql_rexion = "INSERT INTO parroquia (id, territorio, nome) VALUES (%s, %s, %s)"
        try:
            with fiona.open(config.gwb('shp_territories_path'), "r") as territorios_shp:
                for territorio in territorios_shp:
                    cursor.execute(sql_faccion, (territorio["properties"]["CCONC"],
                                                 self._xerar_cor(int(territorio["properties"]["CCONC"])),
                                                 territorio["properties"]["NOME"]))
                    cursor.execute(sql_territorio, (territorio["properties"]["CCONC"],
                                                    territorio["properties"]["CCONC"],
                                                    territorio["properties"]["NOME"],
                                                    territorio["properties"]["CCONC"]))
                    cursor.execute(sql_potencial, (territorio["properties"]["CCONC"],
                                                   territorio["properties"]["CCOM"]))
            
            with fiona.open(config.gwb('shp_potential_path'), "r") as potencial_shp:
                for potencial in potencial_shp:
                   cursor.execute(sql_faccion, (potencial["properties"]["CCom"],
                                                 self._xerar_cor(int(potencial["properties"]["CCom"])),
                                                 potencial["properties"]["Nome"]))
            
            with fiona.open(config.gwb('shp_regions_path'), "r") as rexions_shp:
                for rexion in rexions_shp:
                    cursor.execute(sql_rexion, (rexion["properties"]["CPARR"],
                                                   rexion["properties"]["CCONC"],
                                                   rexion["properties"]["NOME"]))
            cursor.close()
            self.db.commit()
        except mariadb.Error as err:
            print("Something went wrong: {}".format(err))
        self.close()

    def activar(self):
        self._conectar()
        config = Config()
        cursor = self.db.cursor()
        cursor.execute("UPDATE estado_xogo SET activo = 1")
        cursor.close()
        self.db.commit()
        
    def desactivar(self):
        self._conectar()
        config = Config()
        cursor = self.db.cursor()
        cursor.execute("UPDATE estado_xogo SET activo = 0")
        cursor.close()
        self.db.commit()
    
    def _xerar_cor(self, id):
        numbers = [(id*739)%256, (id*457)%256, (id*593)%256 ]
        return '#' + ''.join('{:02X}'.format(a) for a in numbers)
        return "#" + format((id*739)%256, 'X') + format((id*457)%256, 'X') + format((id*593)%256, 'X')
    
    def escoller_agresor(self):
        #return self.territorios[15056] #TODO: testing
        agresor = random.choice(list(self.territorios.values()))
        return agresor

    def escoller_agredido(self, agresor):
        distancia = -1
        agredido = None
        agresor_shape = shape(agresor.xeometria)
        for key, territorio in self.territorios.items():
            if territorio.faccion != agresor.faccion:
                d = agresor_shape.centroid.distance(shape(territorio.xeometria).centroid)
                if distancia == -1 or d < distancia:
                    distancia = d
                    agredido = territorio
        if distancia == -1:
            print("Non se atopou obxectivo válido para o ataque")
            return None
        print("o concello mais próximo é " + agredido.nome)
        print("distancia de ataque: " + str(distancia))
        
        #xa coñecemos o concello mais próximo; agora toca unha escolla mais selectiva
        marxe = 0.2
        potenciais = []
        
        for key, territorio in self.territorios.items():
            if territorio.faccion != agresor.faccion:
                d = agresor_shape.centroid.distance(shape(territorio.xeometria).centroid)
                if d <= distancia*(1+marxe):
                    potenciais.append(territorio)
        
        formables_agresor = self.obxectivos_formables(agresor.faccion)
        pesos = []
        
        
        for territorio in potenciais:
            if territorio in agresor.faccion.de_jure:
                #CASUS BELLI!
                pesos.append(15)
            elif len([f for f in formables_agresor if territorio in f.de_jure]) > 0:
                #comparten facción formable, ten prioridade sobre outros
                pesos.append(12)
            else:
                pesos.append(10)
        
        return random.choices(potenciais, pesos)[0]
    
    def obxectivos_formables(self, faccion):
        return {f for f in self.formables.values() if len(set(faccion.de_jure).intersection(set(f.de_jure))) > 0 and len(f.de_jure) > len(faccion.de_jure)}

    #deprecated
    def faccions_formables(self, territorio):
        return {f for f in self.formables.values() if territorio in f.de_jure}

    def pode_formar(self, faccion):
        return {f for f in self.formables.values() if len(set(f.de_jure).difference(set(faccion.territorios))) == 0 and len(set(faccion.de_jure).difference(set(f.de_jure))) == 0 and len(f.de_jure) > len(faccion.de_jure) and len(f.territorios) == 0}

    def atacar(self):
        agresor = self.escoller_agresor()
        agredido = self.escoller_agredido(agresor)
        return (agresor, agredido)
    
    def independencia_exitosa(self, territorio):
        chance = 12
        if territorio in territorio.faccion.de_jure:
            chance += 10
        chance += math.floor(self.iteracion_actual/10)
        
        if territorio.faccion != territorio.faccion_orixinal and len(territorio.faccion_orixinal.territorios) == 0:
            print(territorio.nome + " intenta acadar a independencia, probabilidade: 1 entre " + str(chance))
            if random.randrange(0, chance) == 0:
                return True
        return False
    
    def posibel_independencia_comarcal(self, territorio, faccion_defensora):
        formables = self.faccions_formables(territorio)
        for f in list(formables):
            if len(set(f.de_jure).difference(set(faccion_defensora.territorios))) == 0 and len(faccion_defensora.territorios) > len(f.de_jure)*2 and len(f.territorios) == 0:
                return f
        return None
        
    
    def cambio_governo(self, territorio, faccion):
        territorio.faccion.territorios.remove(territorio)
        faccion.territorios.append(territorio)
        territorio.faccion = faccion
        
        self._conectar()
        config = Config()
        sql_cambio_governo = "UPDATE territorio SET faccion = %s WHERE id = %s"
        cursor = self.db.cursor()
        try:
            cursor.execute(sql_cambio_governo, (faccion.id, territorio.id))
            cursor.close()
            self.db.commit()
        except mariadb.Error as err:
            print("Something went wrong: {}".format(err))
        
    def avance_iteracion(self, agresor, agredido, lider_atacante, lider_defensor):
        faccion_agredido_orixinal = agredido.faccion
        
        self.cambio_governo(agredido, agresor.faccion)
        self.iteracion_actual += 1
        
        self._conectar()
        config = Config()
        
        cursor = self.db.cursor()
        sql_iteracion = "UPDATE estado_xogo SET ronda_actual = %s"
        sql_cambio_governo = "UPDATE territorio SET faccion = %s WHERE id = %s"
        sql_ronda = "INSERT INTO ronda (iteracion, agresor, agredido, faccion_agresor, faccion_agredido) VALUES (%s, %s, %s, %s, %s)"
        sql_ronda_usuario = "INSERT INTO ronda_usuario (iteracion, usuario_vencedor, usuario_vencido) VALUES (%s, %s, %s)"
        sql_usuario = "SELECT id FROM usuario WHERE nome = %s"
        try:
            cursor.execute(sql_iteracion, (self.iteracion_actual,))
            
            cursor.execute(sql_cambio_governo, (agresor.faccion.id, agredido.id))
            cursor.execute(sql_ronda, (self.iteracion_actual,
                                       agresor.id,
                                       agredido.id,
                                       agresor.faccion.id,
                                       faccion_agredido_orixinal.id))
            if lider_atacante != None or lider_defensor != None:
                id_atacante = None
                id_defensor = None
                
                cursor2 = self.db.cursor(buffered=True)
                
                if lider_atacante != None:
                    row = cursor2.execute(sql_usuario, (lider_atacante,))
                    if row != None:
                        (id_atacante) = row.fetchone()
                if lider_defensor != None:
                    row = cursor2.execute(sql_usuario, (lider_defensor,))
                    if row != None:
                        (id_defensor) = row.fetchone()
                
                if id_atacante != None or id_defensor != None:
                    cursor2.execute(sql_ronda_usuario, (self.iteracion_actual,
                                                   id_atacante,
                                                   id_defensor))
            cursor.close()
            self.db.commit()
        except mariadb.Error as err:
            print("Something went wrong: {}".format(err))
        
    def alistar_usuario(self, id_usuario, nome, faccion):
        self._conectar()
        config = Config()
        
        cursor = self.db.cursor()
        sql_alistar = "INSERT INTO usuario (id, nome, faccion) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE nome = %s, faccion = %s"
        try:
            cursor.execute(sql_alistar, (id_usuario, nome, faccion.id, nome, faccion.id))
            cursor.close()
            self.db.commit()
        except mariadb.Error as err:
            print("Something went wrong: {}".format(err))
    
    def desalistar_usuario(self, id_usuario):
        self._conectar()
        config = Config()
        
        cursor = self.db.cursor()
        sql_desalistar = "DELETE FROM usuario WHERE id = %s"
        try:
            cursor.execute(sql_desalistar, (id_usuario,))
            cursor.close()
            self.db.commit()
        except mariadb.Error as err:
            print("Something went wrong: {}".format(err))
    
    def faccions_mais_fortes(self, limite):
        self._conectar()
        config = Config()
        cursor = self.db.cursor()
        sql = "select t.faccion, f.nome, count(t.id) tamanho \
                from territorio t \
                inner join faccion f on (f.id = t.faccion) \
                left join faccion_potencial fp on (fp.faccion = t.faccion and fp.territorio = t.id) \
                group by t.faccion \
                order by count(t.id) desc \
                limit %s"
        
        ranking = []
        cursor.execute(sql, (limite,))
        for (id_f, nome, tamanho) in cursor:
            ranking.append({"id" : id_f, "nome": nome, "tamanho": tamanho})
        cursor.close()
        return ranking
    
    def pintar_mapa(self, agresor, agredido, img_path='current.png', img_zoom_path='current_zoom.png', dpi=180):
        fig = plt.figure(1, figsize=(10,10), dpi=dpi)
        ax = fig.add_subplot(111)
        ax.set_aspect("equal")
        for key, territorio in self.territorios.items():
            color_conc = BLACK
            color_parr = BLACK
            zorder_conc = 2
            zorder_parr = 3
            width_conc = 0.5
            hatch_conc = None
            if territorio == agredido:
                color_conc = RED
                color_parr = BLACK
                zorder_conc = 10
                zorder_parr = 11
                width_conc = 1.5
                hatch_conc = r'//'
            patch = PolygonPatch(territorio.xeometria, fc=territorio.faccion.cor, ec=color_conc, alpha=1, linewidth=width_conc, zorder=zorder_conc, hatch=hatch_conc)
            ax.add_patch(patch)
            for x_rexion in territorio.xeometria_rexions:
                patch = PolygonPatch(x_rexion, fc="none", ec=color_parr, alpha=0.5, linewidth=0.1, zorder=zorder_parr)
                ax.add_patch(patch)
                
        for key, faccion in self.faccions.items():
            if len(faccion.territorios) > 0 :
                color_com = BLACK
                zorder_com = 4
                width_com = 1
                if faccion == agresor.faccion:
                    color_com = 'lime'
                    zorder_com = 6
                    width_com = 3
                elif faccion == agredido.faccion:
                    color_com = "mediumblue"
                    zorder_com = 5
                    width_com = 3
                polygon = PolygonPatch(faccion.union_territorios(), fc="none", ec=color_com, alpha=1, linewidth=width_com, zorder=zorder_com)
                ax.add_patch(polygon)
        
        #drawing the map
        ax.set_axis_off()
        ax.set_xlim(450000, 750000)
        ax.set_ylim(4600000, 4850000)
        plt.savefig(fname=img_path, bbox_inches="tight", transparent=True, dpi=dpi)
        
        #zoomed version
        ax.set_xlim(int(shape(agredido.xeometria).centroid.x - 40000), int(shape(agredido.xeometria).centroid.x + 40000))
        ax.set_ylim(int(shape(agredido.xeometria).centroid.y - 40000), int(shape(agredido.xeometria).centroid.y + 40000))
        #plt.show();
        plt.savefig(fname=img_zoom_path, bbox_inches="tight", transparent=True, dpi=dpi)

class Territorio:    
    def __init__(self, id, faccion, nome, faccion_orixinal):
        self.id = id
        self.faccion = faccion
        self.nome = nome
        self.faccion_orixinal = faccion_orixinal
        self.rexions = []
        self.xeometria_rexions = []

class Faccion:
    def __init__(self, id, cor, nome):
        self.id = id
        self.cor = cor
        self.nome = nome
        self.territorios = []
        self.de_jure = []
        self.formable = False
        #self.usuarios = [ None ] * 5
        self.usuarios = []
        
    def union_territorios(self):
        return cascaded_union(list(map(lambda x: shape(x.xeometria), self.territorios)))
