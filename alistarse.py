#!/usr/bin/python3
# coding=utf-8
from configloader import Config
import locale
import tweepy
from coewarbots import WarBotStateManager

def comprobar_dms(warbot):
    auth = tweepy.OAuthHandler(config.gwb('twitter_consumer_key'), config.gwb('twitter_consumer_secret'))
    auth.set_access_token(config.gwb('twitter_access_token_key'), config.gwb('twitter_access_token_secret'))

    api = tweepy.API(auth)
    
    me = api.me()
    usuarios_ts = {} #timestamps de ultima resposta ao usuario
    
    alistados = {}
    
    msgs = api.list_direct_messages(count=50)
    
    for msg in msgs:
        emisor_id = msg.message_create['sender_id']
        receptor_id = msg.message_create['target']['recipient_id']
        if int(emisor_id) == int(me.id): #resposta
            if receptor_id in usuarios_ts:
                usuarios_ts[receptor_id] = max(usuarios_ts[receptor_id], msg.created_timestamp)
            else:
                usuarios_ts[receptor_id] = msg.created_timestamp
    
    for msg in msgs:
        emisor_id = msg.message_create['sender_id']
        receptor_id = msg.message_create['target']['recipient_id']
        
        if int(emisor_id) != int(me.id): #mensaxe
            if emisor_id not in usuarios_ts or usuarios_ts[emisor_id] < msg.created_timestamp:
                text_dm = msg.message_create['message_data']['text']
                print('Texto recibido de ' + emisor_id + ': ' + text_dm)
                text_dm = text_dm.lower().replace('\"', '').replace('\'', '').replace('+', '').strip()
                if text_dm.startswith('alistarse '):
                    obxectivo = text_dm[10:].strip()
                    if obxectivo.isdigit() and int(obxectivo) in warbot.faccions:
                        usuario = api.get_user(emisor_id)
                        f = warbot.faccions[int(obxectivo)]
                        alistados[emisor_id] = {'faccion': f,
                                                'nome_usuario': usuario.screen_name}
                        print("Alistando a " + usuario.screen_name + " en " + f.nome)
                        api.send_direct_message(emisor_id, "Alistado correctamente en: " + f.nome)
                        usuarios_ts[emisor_id] = msg.created_timestamp
                    else:
                        coincidencias = {k: v for k, v in warbot.faccions.items() if obxectivo in v.nome.lower() }
                        if len(coincidencias) == 1:
                            f_id, f = coincidencias.popitem()
                            usuario = api.get_user(emisor_id)
                            alistados[emisor_id] = {'faccion': f,
                                                    'nome_usuario': usuario.screen_name}
                            print("Alistando a " + usuario.screen_name + " en " + f.nome)
                            api.send_direct_message(emisor_id, "Alistado correctamente en: " + f.nome)
                            usuarios_ts[emisor_id] = msg.created_timestamp
                        elif len(coincidencias) > 0:
                            resposta = "Atopáronse varios resultados, responde con \"alistarse\" e o identificador da facción que desexes:"
                            for f_id, f in coincidencias.items():
                                resposta += "\nalistarse " + str(f.id) + " -> " + f.nome
                                if f.formable:
                                    resposta += " (comarca)"
                                else:
                                    resposta += " (concello)"
                            api.send_direct_message(emisor_id, resposta)
                            usuarios_ts[emisor_id] = msg.created_timestamp
                        else:
                            api.send_direct_message(emisor_id, "Non se atoparon resultados, proba a introducir unha parte do nome")
                            usuarios_ts[emisor_id] = msg.created_timestamp
                elif text_dm.lower().startswith('desalistarse'):
                    usuario = api.get_user(emisor_id)
                    alistados[emisor_id] = {'faccion': None,
                                            'nome_usuario': usuario.screen_name}
                    print("Desalistando a " + usuario.screen_name)
                    api.send_direct_message(emisor_id, "Desalistado correctamente")
                    usuarios_ts[emisor_id] = msg.created_timestamp
                     
    for (usuario_id, datos_alistar) in alistados.items():
        if datos_alistar['faccion'] != None:
            warbot.alistar_usuario(usuario_id, datos_alistar['nome_usuario'], datos_alistar['faccion'])
        else:
            warbot.desalistar_usuario(usuario_id)


#COMEZO DO SCRIPT
locale.setlocale(locale.LC_TIME, "gl_ES")

config = Config('config.ini')
warbot = WarBotStateManager()
warbot.load_data()
if warbot.activo:
    comprobar_dms(warbot)
