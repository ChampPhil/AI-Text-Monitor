from configparser import ConfigParser
import os 
import sys
from googleapiclient.discovery import build
import requests 


config = ConfigParser()

#Create a section in the config_file
config["USER-KEYS"]  = {   
    "ytkey": "PUT THE YOUTUBE API KEY RIGHT HERE",
    "client-id":"PUT THE CLIENT ID FOR THE REDDIT APP HERE",
    "secret-token":"PUT THE SECRET TOKEN FOR THE REDDIT APP HERE",
    "reddit-username": "PUT THE USERNAME OF YOUR REDDIT ACCOUNT HERE",
    "reddit-password" :"PUT THE PASSOWRD OF YOUR REDDIT ACCOUNT HERE",
    "default-site": "PUT THE PASSOWRD OF YOUR REDDIT ACCOUNT HERE THAT TABS OF THE PROJECT SHOULD REDIRECT TO ON APP.PY TERMINATION"

}



youtube = build('youtube', 'v3', developerKey=config['USER-KEYS']['ytkey'])
reddit_auth = requests.auth.HTTPBasicAuth(config['USER-KEYS']['client-id'], config['USER-KEYS']['secret-token'])

try:
    res = youtube.search().list(part='snippet', type='channel', q='SSSniperWolf').execute()['items'] 
except Exception as e:
    print(e)
    print("\n\nTHE YOUTUBE API KEY YOU PASSED WAS INVALID\n...\n\nEnding Python Script")
    sys.exit()

try:
    test_data = {'grant_type': 'password',
            'username':  config['USER-KEYS']['reddit-username'],
            'password': config['USER-KEYS']['reddit-password']}

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


response = requests.get(config["USER-KEYS"]['default-site'])
if response.status_code == 200:
    pass
else:
    print('The default-site you inputted does not exist.')
    sys.exit()


app_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
file_path = os.path.join(app_dir, 'sql_data', 'user_data.ini')

with open(file_path, "w") as f:
    config.write(f)
    print("Done")