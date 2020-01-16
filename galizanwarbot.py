#!/usr/bin/python3
# coding=utf-8
from configloader import Config
import sys
from datetime import datetime, timedelta
import locale
import tweepy
from coewarbots import WarBotStateManager
import random


def formato_data(data):
    return data.strftime("%m/%d/%Y")
    #return data.strftime("%a, %d %b %Y")


def iteracion(warbot):
    resumo = ""
    
    #Formable nations
    for territorio in warbot.territorios.values():
        formables = warbot.pode_formar(territorio.faccion)
        if len(formables) > 0:
            print("Valorando faccións formables")
            novaf = list(formables)[0]
            faccion_orixinal = territorio.faccion
            print("facción " + territorio.faccion.nome + " transfórmase en " + novaf.nome)
            a_convertir = list(territorio.faccion.territorios)
            for territorio2 in a_convertir:
                print("Cambio de governo en " + territorio2.nome + " a " + novaf.nome)
                warbot.cambio_governo(territorio2, novaf)
            narracion = "Tras conquistar todo o territorio histórico da comarca de {formable}, para {faccion_orixinal} xa non fai sentido seguir considerándose un concello. Unha nova potencia acaba de fundarse no país."
            resumo = narracion.format(formable=nome_a_hashtag(novaf.nome),
                                   faccion_orixinal=faccion_orixinal.nome)
            warbot.pintar_mapa(territorio, territorio)
            return resumo
    
    
    agresor = warbot.escoller_agresor()
    
    print("concello agresor: " + agresor.nome + " (" + agresor.faccion.nome + ")")
    
    comarca_indepe = None
    
    if warbot.independencia_exitosa(agresor):
        #what time is it? Independence time
        agredido = agresor
        faccion_atacante = agresor.faccion_orixinal
        faccion_defensora = agredido.faccion
        
        print("Independencia conquistada. Viva a revolución!")
        
        #sera unha independencia comarcal?
        comarca_indepe = warbot.posibel_independencia_comarcal(agresor, faccion_defensora)
        if (comarca_indepe is not None):
            faccion_atacante = comarca_indepe
            a_convertir = list(comarca_indepe.de_jure)
            for territorio2 in a_convertir:
                print("Cambio de governo en " + territorio2.nome + " a " + comarca_indepe.nome)
                warbot.cambio_governo(territorio2, comarca_indepe)
        
        #####Escribindo a conquista
        #       1       1       1       =>  7
        #   atacante defensor rexion
        narracions = [
                [ '{data}, {atacante} céivase do control de {defensor} e acada a súa independencia plena.' ], #000
                [ '{data}, un grupo de rebeldes da parroquia de {rexion} toman o control de {atacante} e expulsan as tropas de {defensor}. {atacante} é independente agora.' ], #001
                [ '{data}, as tropas de {atacante} reagrúpanse e expulsan ás tropas ocupantes de {defensor}, acabando coa tiranía de {lider_defensor}.' ], #010
                [ '{data}, {atacante} proclama a independencia de {defensor}. Os rebeldes logran capturar a {lider_defensor} na batalla de {rexion}, aínda que finalmente logra fuxir.' ], #011
                [ '{data}, unha guerrilla local, encabezada por {lider_atacante}, toma o control de {atacante} e remata co control efectivo de {defensor}.' ], #100
                [ '{data}, {lider_atacante} proclama a independencia de {atacante}. As tropas de {defensor} son derrotadas na batalla de {rexion}.' ], #101
                [ '{data}, as tropas de {atacante}, lideradas por {lider_atacante}, expulsan aos invasores de {defensor}. A vergoña de {lider_defensor} será coñecida por todo o país.' ], #110
                [ '{data}, {atacante} independízase de {defensor}. A duras penas logra fuxir {lider_defensor} da batalla de {rexion}, onde {lider_atacante} se fai coa vitoria.' ] #111
            ]
    else:
        #un ataque normal
        agredido = warbot.escoller_agredido(agresor)
        faccion_atacante = agresor.faccion
        faccion_defensora = agredido.faccion
        
        if agredido == None:
            exit()

        print("concello agredido: " + agredido.nome + " (" + agredido.faccion.nome + ")")
        

        #####Escribindo a conquista
        #       1       1       1       =>  7
        #   atacante defensor rexion
        narracions = [
                [ '{data}, {atacante} invade {territorio_defensor}, anteriormente baixo o control de {defensor}.' ], #000
                [ '{data}, {atacante} invade {territorio_defensor}, anteriormente baixo {defensor}.\nA batalla decisiva deuse na parroquia de {rexion}.' ], #001
                [ '{data}, as tropas de {atacante} entraron en {territorio_defensor} e desfixeron as defensas. {lider_defensor}, que dirixía as defensas de {defensor}, está en paradeiro descoñecido.',
                  '{data}, {territorio_defensor} cae ante as tropas de {atacante} na batalla de {rexion}. Os esforzos de {lider_defensor} de {defensor} foron insuficientes para deter o ataque.' ], #010
                [ '{data}, {territorio_defensor}, antes baixo o control de {defensor}, cae en mans de {atacante}. A defensa que {lider_defensor} organiza en {rexion} foi insuficiente.' ], #011
                [ '{data}, unha carga gloriosa con {lider_atacante} á cabeza arrasa con {territorio_defensor}, expulsando as tropas de {defensor} da zona. Agora {atacante} controla o lugar.' ], #100
                [ '{data}, as tropas de {atacante} lideradas por {lider_atacante} demostran a súa superioridade na batalla de {rexion}, arrebatando {territorio_defensor} das garras de {defensor}.' ], #101
                [ '{data}, {atacante} conquista {territorio_defensor}. Mentres as tropas saquean a cidade, {lider_atacante} derrota a {lider_defensor} nun duelo épico.' ], #110
                [ '{data}, {territorio_defensor} cae ante a invasión de {atacante}. {lider_defensor} sufre a derrotada en combate singular a mans de {lider_atacante} na batalla de {rexion}, causando a dispersión das tropas de {defensor}.' ] #111
            ]
    
    #parte comun
    tipo_narracion = 0
    
    rexion = None
    if len(agredido.rexions) > 0:
        rexion = random.choice(agredido.rexions)
        tipo_narracion += 1
    
    
    lider_defensor = None
    if len(faccion_defensora.usuarios) > 0:
        lider_defensor = random.choice(faccion_defensora.usuarios)
        if lider_defensor != None:
            lider_defensor = "@" + lider_defensor
            tipo_narracion += 2
    
    lider_atacante = None
    if len(faccion_atacante.usuarios) > 0:
        lider_atacante = random.choice(faccion_atacante.usuarios)
        if lider_atacante != None:
            lider_atacante = "@" + lider_atacante
            tipo_narracion += 4
    
    narracion_escollida = random.choice(narracions[tipo_narracion])
    
    resumo += narracion_escollida.format(data=formato_data(datetime.strptime("2020/01/01", "%Y/%m/%d") + timedelta(days=warbot.iteracion_actual)),
                                               atacante=nome_a_hashtag(faccion_atacante.nome),
                                               defensor=faccion_defensora.nome,
                                               territorio_defensor=nome_a_hashtag(agredido.nome),
                                               rexion=rexion,
                                               lider_atacante=lider_atacante,
                                               lider_defensor=lider_defensor)
    
    warbot.pintar_mapa(agresor, agredido)
    print("Concellos na comarca despois do ataque: "+ str(len(agredido.faccion.territorios)-1))
    if len(agredido.faccion.territorios) == 1:
        print("Comarca derrotada")
        resumo += "\n" + agredido.faccion.nome + " caeu."
        c_com = -1
        for key, faccion in warbot.faccions.items():
            if len(faccion.territorios) > 0:
                c_com += 1
        if c_com <= 1:
            print("Fin do xogo")
            resumo += "\n" + agresor.faccion.nome + " fíxose co control de todo o país!"
            warbot.desactivar()
        else:
            resumo += "\nQuedan " + str(c_com) + " en pé."
    
    #hashtags
    #resumo += "\n" + nome_a_hashtag(agresor.faccion.nome)
    #resumo += " " + nome_a_hashtag(agredido.nome)
    
    #rexístrase o cambio de governo
    warbot.avance_iteracion(agresor, agredido, lider_atacante, lider_defensor)
    
    return resumo

def nome_a_hashtag(nome):
    return ('#' + "".join(x.capitalize() or ' ' for x in nome.split(' '))).replace('-', '')


def tweet_resumo(resumo, img, img_zoom):
    global config
    auth = tweepy.OAuthHandler(config.gwb('twitter_consumer_key'), config.gwb('twitter_consumer_secret'))
    auth.set_access_token(config.gwb('twitter_access_token_key'), config.gwb('twitter_access_token_secret'))

    api = tweepy.API(auth)
    
    img_up = api.media_upload(img)
    img_zoom_up = api.media_upload(img_zoom)
    status = api.update_status(status=resumo, media_ids=[img_up.media_id, img_zoom_up.media_id])

    print(status.text)
    return status.id


#COMEZO DO SCRIPT
locale.setlocale(locale.LC_TIME, "gl_ES")

config = Config('config.ini')
warbot = WarBotStateManager()

if len(sys.argv) > 1:
    if sys.argv[1] == 'reinicio':
        warbot.inicializar_database()
        print("Reinicio completado")
    elif sys.argv[1] == 'activar':
        warbot.activar()
        print("GalizanWarBot activado")
    elif sys.argv[1] == 'desactivar':
        warbot.desactivar()
        print("GalizanWarBot desactivado")
else:
    warbot.load_data()
    
    if warbot.activo:
        resumo = iteracion(warbot)
        tweet_resumo(resumo, "current.png", "current_zoom.png")
        warbot.close()
