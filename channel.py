## channel.py - a simple message channel
##

from flask import Flask, request, render_template, jsonify
import json
import requests
import datetime
import langid as ln
import random as rn

import re
import html
import urllib.request
import urllib.parse

# Class-based application configuration
class ConfigClass(object):
    """ Flask application config """

    # Flask settings
    SECRET_KEY = 'This is an INSECURE secret!! DO NOT use this in production!!'

def finnish_classify(text):
    """diese Methode gibt True zurück, 
    wenn ein Satz mit einer hohen Wahrscheinlichkeit 
    hauptsächlich aus Finnischen Wörtern besteht"""
    ln.set_languages(["en","fi"])
    result = ln.rank(text)
    if translate(text, to_language="fi") == text:
        return True
    return False

def get_topic():
        topics = [
            "Let's talk about tervehdykset.",  # Greetings
            "Let's talk about numerot.",  # Numbers
            "Let's talk about värit.",  # Colors
            "Let's talk about viikonpäivät.",  # Days of the week
            "Let's talk about kuukaudet.",  # Months
            "Let's talk about vuodenajat.",  # Seasons
            "Let's talk about perhe.",  # Family
            "Let's talk about asuminen.",  # Housing
            "Let's talk about kaupungit ja maat.",  # Cities and countries
            "Let's talk about sää.",  # Weather
            "Let's talk about ruoka ja juoma.",  # Food and drinks
            "Let's talk about kehonosat.",  # Body parts
            "Let's talk about vaatteet.",  # Clothing
            "Let's talk about ostoksilla käynti.",  # Shopping
            "Let's talk about harrastukset.",  # Hobbies
            "Let's talk about matkustaminen.",  # Traveling
            "Let's talk about liikenne.",  # Transportation
            "Let's talk about aikamuodot.",  # Verb tenses
            "Let's talk about kysymyssanat.",  # Question words
            "Let's talk about kohteliaisuusfraasit.",  # Politeness phrases
            "Let's talk about työelämä.",  # Work life
            "Let's talk about koulu ja opiskelu.",  # School and studies
            "Let's talk about suomalainen kulttuuri.",  # Finnish culture
            "Let's talk about juhlapäivät.",  # Holidays
            "Let's talk about terveys ja hyvinvointi.",  # Health and well-being
            "Let's talk about eläimet.",  # Animals
            "Let's talk about adjektiivit.",  # Adjectives
            "Let's talk about verbien taivutus.",  # Verb conjugation
            "Let's talk about suomen kielioppi.",  # Finnish grammar
            "Let's talk about suomen kielen ääntäminen."  # Finnish pronunciation
        ] 
        return topics[int(rn.uniform(1,28))]

# Create Flask app
app = Flask(__name__)
app.config.from_object(__name__ + '.ConfigClass')  # configuration
app.app_context().push()  # create an app context before initializing db

HUB_URL = 'http://vm146.rz.uni-osnabrueck.de/hub'
HUB_AUTHKEY = 'Crr-K24d-2N'
CHANNEL_AUTHKEY = '0987654321'
CHANNEL_NAME = "Finnish learning channel"
CHANNEL_ENDPOINT = "http://vm146.rz.uos.de/u052/task3/channel.wsgi" # don't forget to adjust in the bottom of the file
CHANNEL_FILE = 'messages.json'
CHANNEL_TYPE_OF_SERVICE = 'aiweb24:chat'

@app.cli.command('register')
def register_command():
    global CHANNEL_AUTHKEY, CHANNEL_NAME, CHANNEL_ENDPOINT

    # send a POST request to server /channels
    response = requests.post(HUB_URL + '/channels', headers={'Authorization': 'authkey ' + HUB_AUTHKEY},
                             data=json.dumps({
                                "name": CHANNEL_NAME,
                                "endpoint": CHANNEL_ENDPOINT,
                                "authkey": CHANNEL_AUTHKEY,
                                "type_of_service": CHANNEL_TYPE_OF_SERVICE,
                             }))

    if response.status_code != 200:
        print("Error creating channel: "+str(response.status_code))
        print(response.text)
        return

def check_authorization(request):
    global CHANNEL_AUTHKEY
    # check if Authorization header is present
    if 'Authorization' not in request.headers:
        return False
    # check if authorization header is valid
    if request.headers['Authorization'] != 'authkey ' + CHANNEL_AUTHKEY:
        return False
    return True

@app.route('/health', methods=['GET'])
def health_check():
    global CHANNEL_NAME
    if not check_authorization(request):
        return "Invalid authorization", 400
    return jsonify({'name':CHANNEL_NAME}),  200

# GET: Return list of messages
@app.route('/', methods=['GET'])
def home_page():
    if not check_authorization(request):
        return "Invalid authorization", 400
    # fetch channels from server
    return jsonify(read_messages())

# POST: Send a message
@app.route('/', methods=['POST'])
def send_message():
    # fetch channels from server
    # check authorization header
    if not check_authorization(request):
        return "Invalid authorization", 400
    # check if message is present
    message = request.json
    if not message:
        return "No message", 400
    if not 'content' in message:
        return "No content", 400
    if not 'sender' in message:
        return "No sender", 400
    if not 'timestamp' in message:
        return "No timestamp", 400
    if not 'extra' in message:
        extra = None
    else:
        extra = message['extra']
    # add message to messages
    #error handling einbauen!!!!!!!!!!!
    messages = read_messages()
    message_timestamp = datetime.datetime.now().isoformat()
    if (message['content'].startswith("tr:") or finnish_classify(message['content'])) and message['sender'] != 'Server': #ich habe die Bdg geändert, weil sie vorher falsch war
        if message['content'].startswith("tr:"): #die if conditon habe ich  eingefügt
            message['content']= "USER: "+ message['content'][3:] + " TRANSLATED: " + translate(message['content'][3:], to_language="fi")
        
        messages.append({'content': message['content'],
                        'sender': message['sender'],
                        'timestamp': message_timestamp,
                        'extra': extra,
                        })
    else:
        messages.append({'content': 'Please contribute to the channel according to the rules! Write in Finnish, use "tr:" for translation and do not name yourself "Server"',
                        'sender': 'Server',
                        'timestamp': message_timestamp,
                        'extra': None,
                        })
    save_messages(messages)
    return "OK", 200

def read_messages():
    global CHANNEL_FILE
    try:
        f = open(CHANNEL_FILE, 'r')
    except FileNotFoundError:
        return []
    try:
        messages = json.load(f)
    except json.decoder.JSONDecodeError:
        messages = []
        t_stamp = datetime.datetime.now().isoformat()
        messages.append({'content': "This is a Finish learning center. Feel free to chat with other people in Finnish! You can use the translation service by typing in 'tr: [Your message]'",
                     'sender': "Server",
                     'timestamp': t_stamp,
                     'extra': "",
                     })
        save_messages(messages)
    #Versuch, die erste Nachricht bei mehr als 10 Nachrichten zu löschen
    if len(messages) > 10:
        del(messages[1])
        save_messages(messages)
    #Prüfung, ob der Server ein neues Thema als input geben soll
    timediff =  (datetime.datetime.now() - datetime.datetime.fromisoformat(messages[-1]['timestamp'])).total_seconds()
    if timediff > 600 and not messages[-1]["content"].startswith("Let's talk about"):
        generated = get_topic()
        messages.append({'content': generated,
                    'sender': "Server",
                    'timestamp': datetime.datetime.now().isoformat(),
                    'extra': "",
                    })  

    f.close()
    return messages

def save_messages(messages):
    global CHANNEL_FILE
    with open(CHANNEL_FILE, 'w') as f:
        json.dump(messages, f)


def translate(to_translate, to_language="auto", from_language="auto"):
    """Translates to_translate in language from_language to_langauge
    using Google Translate.

    Adapted code: Copyright (c) 2016 Arnaud Aliès
    https://github.com/mouuff/mtranslate/blob/master/mtranslate/core.py
    """
    agent = {
    'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    }

    base_link = "http://translate.google.com/m?tl=%s&sl=%s&q=%s"
    
    to_translate = urllib.parse.quote(to_translate)
    link = base_link % (to_language, from_language, to_translate)
    request = urllib.request.Request(link, headers=agent)
    raw_data = urllib.request.urlopen(request).read()
    data = raw_data.decode("utf-8")
    expr = r'(?s)class="(?:t0|result-container)">(.*?)<'
    re_result = re.findall(expr, data)
    if (len(re_result) == 0):
        result = ""
    else:
        result = html.unescape(re_result[0])
    return (result)

# Start development web server
# run python -m flask --app channel.py register
# to register channel with hub

if __name__ == '__main__':
    app.run(port=5001, debug=True)
