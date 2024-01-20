import requests 
import time


def authorize(client_id, secret_token, reddit_username, reddit_password):

    auth = requests.auth.HTTPBasicAuth(client_id, secret_token)

    # here we pass our login method (password), username, and password
    data = {'grant_type': 'password',
            'username':  reddit_username,
            'password': reddit_password}

    # setup our header info, which gives reddit a brief description of our app
    headers = {'User-Agent': 'PhilipVDataProjectAPI/0.0.1'}

    # send our request for an OAuth token
    res = requests.post('https://www.reddit.com/api/v1/access_token',
                        auth=auth, data=data, headers=headers)

    # convert response to JSON and pull access_token value

    TOKEN = res.json()['access_token']

    # add authorization to our headers dictionary
    headers = {**headers, **{'Authorization': f"bearer {TOKEN}"}}

    return headers



# while the token is valid (~2 hours) we just add headers=headers to our requests
def get_data_from_subforum(subforum, params, headers):
    # make a request for the trending posts in /r/Python
    res = requests.get(f"https://oauth.reddit.com/r/{subforum}/new",
                    headers=headers,
                    params=params)

    
    comment_lst = []
    kind_lst = []
    comment_id_list = []
    # loop through each post retrieved from GET request
    for post in res.json()['data']['children']:
        # append relevant data to dataframe
        comment_lst.append(post['data']['title'])
        kind_lst.append(post['kind'])
        comment_id_list.append(post['data']['id'])

    return comment_lst, kind_lst, comment_id_list



def subbredit_is_valid(name, headers):
    
    name = name.split('/')
    print(name)

    if len(name) == 1: #If the r isn't included
        return False

    
   
    res = requests.get(f"https://oauth.reddit.com/api/subreddit_autocomplete",
                    headers=headers,
                    params={'query': name[-1]})
    
    
    
   

    data = res.json()['subreddits']
    

    try:
        for row in data:
            print(row['name'])
            if row['name'] == name[-1]:
                return True
            else:
                pass

        return False
    except:
        return 'ERROR'
    

    

import sys

if __name__ == '__main__':
    def main(subforum, times):
        headers = authorize("5Y2eEUbCLA5tU0tQCMFoaQ", "krC4qa1ZYHAcRS-i6__ZO2a7jkjnPQ", 'ChampPhil', '@Philip2010')
        params = {"limit": 100}
        data = []

        for i in range(times):
            comments, kinds, ids = get_data_from_subforum(subforum, params, headers)
            print("---------------\nCurrent Data\n------------------------------\n\n")

            for comment in comments:
                data.append(comment)

            if len(kinds) == 0:
                print("No Comments")
                break 

            fullname = kinds[-1] + '_' + ids[-1]
            params['after'] = fullname

        print(data)

    main('python', 10)
