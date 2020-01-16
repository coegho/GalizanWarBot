#!/usr/bin/python3
# coding=utf-8
from configloader import Config
import locale
import tweepy
from coewarbots import WarBotStateManager

def publicar_ranking(warbot):
    auth = tweepy.OAuthHandler(config.gwb('twitter_consumer_key'), config.gwb('twitter_consumer_secret'))
    auth.set_access_token(config.gwb('twitter_access_token_key'), config.gwb('twitter_access_token_secret'))
    
    api = tweepy.API(auth)
    
    me = api.me()
    
    ranking = warbot.faccions_mais_fortes(5)
    
    resumo = "RESUMO DO DÍA: Ranking de faccións"
    i = 0
    for r in ranking:
        i += 1
        resumo += "\n" + str(i) + ". " + r["nome"] + ": " + str(r["tamanho"]) + " territorios"
    
    status = api.update_status(status=resumo)
    
    print(status.text)
    return status.id


#COMEZO DO SCRIPT
locale.setlocale(locale.LC_TIME, "gl_ES")

config = Config('config.ini')
warbot = WarBotStateManager()

warbot.load_data()
if warbot.activo:
    publicar_ranking(warbot)
