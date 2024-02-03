import sqlite3
import os
import sys
from googleapiclient.discovery import build
import requests 

app_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

print("You are editing the AUTH_DATABASE.")
print("----------------------------------------------------------------------------")

#Edit these values 
youtube_api_key = "AIzaSyAJy2ux4lZ2uAgGqpbDF8ewocSSMNum6Uk"
reddit_client_id = "uEmlQgPzkxv7l7gESuDUag"
reddit_secret_token = "xMuH8KjqLcg0Y2C39VYqCfW6LZ8ihw"
reddit_username = "ChampPhil"
reddit_password = "@Philip2010"
default_site = "https://bing.com" 



youtube = build('youtube', 'v3', developerKey=youtube_api_key)
reddit_auth = requests.auth.HTTPBasicAuth(reddit_client_id, reddit_secret_token)

try:
    res = youtube.search().list(part='snippet', type='channel', q='SSSniperWolf').execute()['items'] 
except Exception as e:
    print(e)
    print("\n\nTHE YOUTUBE API KEY YOU PASSED WAS INVALID\n...\n\nEnding Python Script")
    sys.exit()

try:
    test_data = {'grant_type': 'password',
            'username':  reddit_username,
            'password': reddit_password}

    # setup our header info, which gives reddit a brief description of our app
    test_headers = {'User-Agent': 'PhilipVDataProjectAPI/0.0.1'}

    # send our request for an OAuth token
    test_res = requests.post('https://www.reddit.com/api/v1/access_token',
                        auth=reddit_auth, data=test_data, headers=test_headers)
    
    test_res.json()['access_token'] #If the auth_data is wrong, this will trigger an error
except Exception as e:
    print(e)
    print("\n\nTHE REDDIT AUTH DATA YOU PASSED WAS INVALID\n...\n\nEnding Python Script")
    sys.exit()

database = os.path.join(app_dir, 'sql_data', 'auth_database.db')

sqliteConnection = sqlite3.connect(database)
cursor = sqliteConnection.cursor()

cursor.execute("DELETE FROM user_data")



cursor.execute("INSERT INTO user_data (ytkey, clientid, secrettoken, redditusername, redditpassword, defaultsite) VALUES (?, ?, ?, ?, ?, ?)", (youtube_api_key, reddit_client_id, reddit_secret_token, reddit_username, reddit_password, default_site))

sqliteConnection.commit()

sqliteConnection.close()