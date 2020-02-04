import os
from flask import Flask, redirect, session, render_template, request, url_for, jsonify, make_response, flash
import oauth2 as oauth
import urllib.request
import urllib.parse
import urllib.error
import json
import urllib.parse
import urllib
from flask_restful import Resource, Api
import base64 
from wtforms import Form, BooleanField, TextField, StringField, IntegerField, validators
from wtforms.validators import DataRequired, NumberRange
from flask_cors import CORS
from flask_dance.contrib.twitter import make_twitter_blueprint, twitter
from flask_dance.consumer import oauth_authorized
from werkzeug.contrib.fixers import ProxyFix
from werkzeug.datastructures import MultiDict
app = Flask(__name__, static_url_path="", static_folder="static")
app.wsgi_app = ProxyFix(app.wsgi_app)

random_bytes = os.urandom(64)
secret = base64.b64encode(random_bytes).decode('utf-8')
app.secret_key = secret #os.getenv('TWAUTH_APP_SESSION_SECRET', secret)

CORS(app)
#app.debug = True

# get_current_user() is a function that returns the current logged in user

request_token_url = 'https://api.twitter.com/oauth/request_token'
access_token_url = 'https://api.twitter.com/oauth/access_token'
authorize_url = 'https://api.twitter.com/oauth/authorize'
show_user_url = 'https://api.twitter.com/1.1/users/show.json'
search_tweets_url = "https://api.twitter.com/1.1/search/tweets.json"

# Support keys from environment vars (Heroku).
app.config['APP_CONSUMER_KEY'] = os.getenv(
    'TWAUTH_APP_CONSUMER_KEY', 'API_Key_from_Twitter')
app.config['APP_CONSUMER_SECRET'] = os.getenv(
    'TWAUTH_APP_CONSUMER_SECRET', 'API_Secret_from_Twitter')

# alternatively, add your key and secret to config.cfg
# config.cfg should look like:
# APP_CONSUMER_KEY = 'API_Key_from_Twitter'
# APP_CONSUMER_SECRET = 'API_Secret_from_Twitter'
app.config.from_pyfile('config.cfg', silent=True)

twitter_bp =  make_twitter_blueprint(
    api_key=app.config['APP_CONSUMER_KEY'],
    api_secret=app.config['APP_CONSUMER_SECRET'],
    redirect_url="/twitter_api"
)
app.register_blueprint(twitter_bp, url_prefix="/login")



oauth_store = {}

class TweetForm(Form):
    hashtag  = TextField(u'Hashtag(s)', validators=[DataRequired()])
    count = IntegerField(u'How Many?', validators=[DataRequired(), NumberRange(min=1, max=20, message='Must be between 1 and 20')])
   

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/start")
def start():
    if not twitter.authorized:
        return redirect(url_for("twitter.login"))
    resp = twitter.get("account/verify_credentials.json")
    screen_name = resp.json()["screen_name"]
    name = resp.json()["name"]
    assert resp.ok
    return redirect(url_for('twitter_api'))


@app.route('/twitter_api', methods=['GET', 'POST'])
def twitter_api():
    form = TweetForm(request.form)
    formSubmitted = False
    if request.method == 'POST' and form.validate():
        q = form.hashtag.data
        count = form.count.data
        
        response = search_tweets(q, count)

        media = get_hashtag_media(response.content)

        nFound = len(media)
        formSubmitted = True
        message = "Found " + str(len(media)) + "/" + str(count) + " image(s) with search '" + q + "'"
        form = TweetForm()
        return render_template('twitter_api.html', images=media, form=form, formSubmitted=formSubmitted, q=q, count=count, nFound=nFound)
    
    else:
        return render_template('twitter_api.html', form=form)
   
   

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('error.html', error_message='uncaught exception'), 500


def get_hashtag_media(response):
    tweets = json.loads(response)
    media_files = set()
    for status in tweets["statuses"]:
        # print("Status: %s" % status)
        if("media" in status["entities"]):
            media = status["entities"].get('media', [])
            if(len(media) > 0):
                media_files.add(media[0]['media_url'])
                print("Media: %s" % media[0]['media_url'])

    return media_files


def search_tweets(q, count):
    params = {'q': q, 'count': count}
    encoded = urllib.parse.urlencode(params)
    print(encoded)
    url = search_tweets_url + '?' + encoded
    print(url)
    return twitter.get(url)

def get_user(user_id):
    url = show_user_url + '?user_id=' + user_id
    return twitter.get(url)

def to_json(content):
    response = content
    try:
        response = content.decode('utf-8')
    except:
        print("Exception")
    finally:
        return json.loads(response)
  

 
if __name__ == '__main__':
    app.run()
