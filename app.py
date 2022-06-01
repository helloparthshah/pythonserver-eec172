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
from user import con, cur

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

''' users = [
    User('test', 'test'),
    User('test1', 'test1'),
] '''


# header = ['eec172', 'testwifi', 'ucdguest', 'eduroam']
# with open('json_data.json', 'a') as f:
#     # if empty, write [
#     if f.tell() == 0:
#         f.write('[\n')
#     f.close()


def token_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        # print the body
        token = None
        auth = request.get_json()
        if 'Authorization' in request.get_json():
            # if 'token' in request.headers or 'Authorization' in request.headers:
            if auth['Authorization'].split()[0] == 'Bearer':
                token = auth['Authorization'].split()[1]

        if not token:
            return jsonify({'message': 'a valid token is missing'})

        try:
            data = jwt.decode(
                token, app.config['SECRET_KEY'], algorithms="HS256")
            cur.execute("SELECT * FROM users WHERE publicId = %s",
                        (data['public_id'],))
            user = cur.fetchone()
            user = dict(user)
            if user:
                current_user = user
            # current_user = next(
            #     (x for x in users if x.publicId == data['public_id']))

        except Exception as e:
            print(e)
            return jsonify({'message': 'token is invalid'})

        return f(*args, **kwargs, current_user=current_user)
    return decorator


@app.route('/')
def getUsers():
    cur.execute("SELECT * FROM users")
    users = cur.fetchall()
    # convert to json
    return jsonify(users)


@app.route('/register', methods=['GET', 'POST'])
def signup_user():
    data = request.get_json()

    if data is None:
        return make_response('Username or password not provided', 400)

    print(data)

    if 'username' in data or 'password' in data:
        cur.execute("SELECT * FROM users WHERE username = %s",
                    (data['username'],))
        user = cur.fetchone()
        if user:
            return make_response('Username already exists', 400)

        usr = User(data['username'], data['password'])
        ''' return make_response('User created', 201)
        users.append(User(
            data['username'],
            data['password'])
        ) '''

        return jsonify({'message': 'registered successfully'})
    return make_response('Username or password not provided', 400)


@app.route('/login', methods=['GET', 'POST'])
def login_user():

    auth = request.authorization

    if not auth or not auth.username or not auth.password:
        return make_response('could not verify', 401, {'WWW.Authentication': 'Basic realm: "login required"'})
    try:
        cur.execute("SELECT * FROM users WHERE username = %s",
                    (auth.username,))
        user = cur.fetchone()
        # convert realdictrow to json
        user = dict(user)
        # user = next((x for x in users if x.username == auth.username), None)
        print(user)
        if user != None and check_password_hash(user['password'], auth.password):
            token = jwt.encode({'public_id': user['publicid'], 'exp': datetime.datetime.utcnow(
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
    return jsonify({'user': current_user})


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
    # save the token to a file
    with open('token.txt', 'w') as f:
        f.write("Bearer " + r.json()['access_token'])
        f.close()
    # return the token
    return jsonify({'success': True})


def play_spotify():
    auth = ""
    # get the token
    with open('token.txt', 'r') as f:
        auth = f.read()
        f.close()
    # play spotify
    res = requests.put('https://api.spotify.com/v1/me/player/play', headers={
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": auth
    },
        data=json.dumps({}))
    print(res.text)


def pause_spotify():
    auth = ""
    # get the token
    with open('token.txt', 'r') as f:
        auth = f.read()
        f.close()
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
    go_outside = 0
    if(prediction_classes[0] == 1):
        # get last_time
        cur.execute("SELECT last_time FROM users WHERE publicid = %s",
                    (current_user['publicid'],))
        last_time = cur.fetchone()
        # convert to json
        last_time = dict(last_time)
        # convert to datetime
        last_time = last_time['last_time']
        # get current time
        current_time = datetime.datetime.now()
        # get difference
        diff = current_time - last_time
        # if difference is greater than 5 minutes
        print(diff.seconds)
        if(diff.seconds > 300):
            go_outside = 1
            print("Go outside!")
    elif (prediction_classes[0] == 0):
        cur.execute("UPDATE users SET last_time = %s WHERE publicid = %s",
                    (datetime.datetime.now(), current_user['publicid']))
    if(prediction_classes[0] == 1 and current_user['is_playing'] == False):
        cur.execute("UPDATE users SET is_playing = %s WHERE publicid = %s",
                    (True, current_user['publicid']))
        play_spotify()
    elif(prediction_classes[0] == 0 and current_user['is_playing'] == True):
        # set last_time to current time
        cur.execute("UPDATE users SET is_playing = %s WHERE publicid = %s",
                    (False, current_user['publicid']))
        pause_spotify()
    con.commit()
    print(prediction_classes)
    # return same json back
    return json.dumps({"prediction": prediction_classes[0], "go_outside": go_outside})


if __name__ == "__main__":
    # app.run(debug=True, host='0.0.0.0', port=443,
    #         ssl_context=('client.crt', 'private.key'))
    print("Running on port 5000")
    app.run(threaded=True, port=5000)
