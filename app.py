# flask server
from flask import Flask, jsonify, request, make_response, redirect
import json
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import tensorflow as tf
from werkzeug.security import check_password_hash
import requests
import os
from dotenv import load_dotenv
import jwt
from user import User
from functools import wraps
import datetime
import urllib

load_dotenv()


df = pd.read_csv('data_file1.csv')
df.fillna(0, inplace=True)

df['is_inside'] = [
    1 if typ == 'inside' else 0 for typ in df['location']
]
df.drop('location', axis=1, inplace=True)

X = df.drop('is_inside', axis=1)
y = df['is_inside']

X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2, random_state=42
)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
# X_test_scaled = scaler.transform(X_test)

# convert into dataframe with headers = eduroam  ucd-guest  testwifi  home1 location  DDC-ESDC  Lance2152
headers = ["eduroam",  "ucd-guest",  "testwifi",
           "home1", "location", "DDC-ESDC",  "Lance2152"]

model = tf.keras.models.load_model('model1.h5')

app = Flask(__name__)

app.config['SECRET_KEY'] = os.getenv('secretKey')

users = [
    User('test', 'test'),
    User('test1', 'test1'),
]


# header = ['eec172', 'testwifi', 'ucdguest', 'eduroam']
# with open('json_data.json', 'a') as f:
#     # if empty, write [
#     if f.tell() == 0:
#         f.write('[\n')
#     f.close()


def token_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            # if 'token' in request.headers or 'Authorization' in request.headers:
            if request.headers['Authorization'].split()[0] == 'Bearer':
                token = request.headers['Authorization'].split()[1]

        if not token:
            return jsonify({'message': 'a valid token is missing'})

        try:
            data = jwt.decode(
                token, app.config['SECRET_KEY'], algorithms="HS256")
            current_user = next(
                (x for x in users if x.publicId == data['public_id']))

        except Exception as e:
            print(e)
            return jsonify({'message': 'token is invalid'})

        return f(*args, **kwargs, current_user=current_user)
    return decorator


@app.route('/')
def getUsers():
    return jsonify({'users': [x.toJSON() for x in users]})


@app.route('/register', methods=['GET', 'POST'])
def signup_user():
    data = request.get_json()

    if data is None:
        return make_response('Username or password not provided', 400)

    print(data)

    if 'username' in data or 'password' in data:

        for user in users:
            if user.username == data['username']:
                return make_response('user already exists', 400)

        users.append(User(
            data['username'],
            data['password'])
        )

        return jsonify({'message': 'registered successfully'})
    return make_response('Username or password not provided', 400)


@app.route('/login', methods=['GET', 'POST'])
def login_user():

    auth = request.authorization

    if not auth or not auth.username or not auth.password:
        return make_response('could not verify', 401, {'WWW.Authentication': 'Basic realm: "login required"'})
    try:
        user = next((x for x in users if x.username == auth.username), None)

        if user != None and check_password_hash(user.password, auth.password):
            token = jwt.encode({'public_id': user.publicId, 'exp': datetime.datetime.utcnow(
            ) + datetime.timedelta(minutes=30)}, app.config['SECRET_KEY'], algorithm="HS256")

            return jsonify({'token': token})
    except Exception as e:
        print('err')
        print(e)
        pass

    return make_response('could not verify',  401, {'WWW.Authentication': 'Basic realm: "login required"'})


@app.route('/user', methods=['GET'])
@token_required
def getUser(current_user):
    return jsonify({'user': current_user.toJSON()})


@app.route("/post", methods=['POST'])
@token_required
def post():
    # print the body of the request
    print(request.get_json())
    # write to csv
    with open('json_data.json', 'a') as f:
        data = request.get_json()
        # set location of data to "inside"
        data['location'] = "outside"
        json.dump(data, f)
        f.write(',\n')
        f.close()
    # return same json back
    return request.get_json()


auth = ""


@app.route("/settoken", methods=["GET"])
def set_spotify_token():
    client_id = os.getenv('client_id')
    redirect_uri = request.base_url.replace('/settoken', '/callback')
    url = "https://accounts.spotify.com/authorize"
    data = {
        "response_type": "code",
        "client_id": client_id,
        "scope": "user-modify-playback-state",
        "redirect_uri": redirect_uri,
        "state": "12345"
    }
    # redirect to spotify
    return redirect(url + "?" + urllib.parse.urlencode(data))


@app.route("/callback", methods=["GET"])
def callback():
    global auth
    # get the code from the url
    code = request.args.get('code')
    state = request.args.get('state')
    # get the client id and secret
    client_id = os.getenv('client_id')
    client_secret = os.getenv('client_secret')
    # get the redirect uri
    redirect_uri = request.base_url.replace('/settoken', '/callback')
    # get the token
    token_url = "https://accounts.spotify.com/api/token"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "client_secret": client_secret
    }
    # make the request
    r = requests.post(token_url, data=data)
    # get the token
    auth = "Bearer " + r.json()['access_token']
    # return the token
    return jsonify(auth)


def play_spotify():
    # play spotify
    res = requests.put('https://api.spotify.com/v1/me/player/play', headers={
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": auth
    },
        data=json.dumps({}))
    print(res.text)


def pause_spotify():
    # pause spotify
    res = requests.put('https://api.spotify.com/v1/me/player/pause', headers={
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": auth
    },
        data=json.dumps({}))
    print(res.text)


@app.route("/predict", methods=["POST"])
@token_required
def predict(current_user):
    # print the body of the request
    data = request.get_json()
    df = pd.DataFrame(data, index=[0], columns=headers)
    df.fillna(0, inplace=True)
    df.drop('location', axis=1, inplace=True)
    x_scaled = scaler.transform(df)
    predictions = model.predict(np.array([x_scaled[0], ]))

    prediction_classes = [
        1 if prob > 0.5 else 0 for prob in np.ravel(predictions)
    ]
    if(prediction_classes[0] == 1 and current_user.is_playing == False):
        current_user.is_playing = True
        play_spotify()
    elif(prediction_classes[0] == 0 and current_user.is_playing == True):
        current_user.is_playing = False
        pause_spotify()
    print(prediction_classes)
    # return same json back
    return json.dumps({"prediction": prediction_classes[0]})


if __name__ == "__main__":
    # app.run(debug=True, host='0.0.0.0', port=443,
    #         ssl_context=('client.crt', 'private.key'))
    print("Running on port 5000")
    app.run(threaded=True, port=5000)
