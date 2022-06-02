from werkzeug.security import generate_password_hash
import uuid
import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv

load_dotenv()
psycopg2.extras.register_uuid()
DATABASE_URL = os.getenv('DATABASE_URL')
con = psycopg2.connect(DATABASE_URL)
# work with json
cur = con.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

cur.execute(
    "CREATE TABLE IF NOT EXISTS users (username TEXT, password TEXT, publicId TEXT, is_playing BOOLEAN,last_time TIMESTAMP,location BOOLEAN)"
)
cur.execute(
    "CREATE TABLE IF NOT EXISTS rules (username TEXT, if_action TEXT, then_action TEXT)")

con.commit()


class User:
    def __init__(self, username, password):
        self.username = username
        self.password = generate_password_hash(password, method='sha256')
        self.publicId = str(uuid.uuid4())
        self.is_playing = False
        self.last_time = None
        self.location = True
        # add user to database
        cur.execute("INSERT INTO users (username, password, publicId, is_playing, last_time,location) VALUES (%s, %s, %s, %s, %s,%s)",
                    (self.username, self.password, self.publicId, self.is_playing, self.last_time, self.location))
        con.commit()

    def toJSON(self):
        return {
            'username': self.username,
            'password': self.password,
            'public_Id': self.publicId,
            'is_playing': self.is_playing,
            'last_time': self.last_time,
            'location': self.location
        }
