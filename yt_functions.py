from googleapiclient.discovery import build
import cleantext
from operator import itemgetter



def get_data_from_display_name(display_name, youtube_api_object):
    try:
        channel_id = channel_id_from_display_name(display_name, youtube_api_object)[display_name] #If there isn't an exact match
    except Exception as e:
        try:
            if e.status_code == 403: #If this fails, it means it nots a HTTP-Error 
                print('api_exceeded')
                return 'API_EXCEEDED', 'API_EXCEEDED'
        except Exception: #Therefore, the channel name is invalid
            return 'FAILED', 'FAILED'
    
    upload_id = get_upload_id_from_channel_id(channel_id, youtube_api_object)
    
    return channel_id, upload_id

"""
def remove_unicode_escape_sequences(input_string):
    # Define a regular expression pattern to match Unicode escape sequences
    escape_sequence_pattern = r'\\u[0-9A-Fa-f]{4}|\\U[0-9A-Fa-f]{8}'

    # Use re.sub to replace escape sequences with an empty string
    result_string = re.sub(escape_sequence_pattern, '', input_string)
    
    return result_string

"""

def clean_str(input_str):
    return cleantext.clean(input_str, fix_unicode=True, to_ascii=True, no_emoji=True)
    


def get_upload_id_from_channel_id(channel_id, youtube_object):
    res = youtube_object.channels().list(id=channel_id, part='contentDetails').execute()
    
    if res['pageInfo']['totalResults'] == 0:
        print("ID INVALID")
        return 'ID INVALID'
    
    playlist_id = res['items'][0]['contentDetails']['relatedPlaylists']['uploads'] #Get the id of all the uploads of this channel
    return playlist_id

def get_comments_from_vid_id(vid_id, nextPageToken, max_size, youtube_object):
    request = youtube_object.commentThreads().list( #Get the first 100 comments of that video
                part="snippet",
                videoId=vid_id,
                pageToken=nextPageToken,
                maxResults=max_size
            )
            
    comment_data = request.execute() #Get the data from those comments
    
    """
    snippets = list(map(itemgetter('snippet'), comment_data['items']))
    topLevelComment = list(map(itemgetter('topLevelComment'), snippets))
    snippets_two = list(map(itemgetter('snippet'), topLevelComment))
    raw_text = list(map(itemgetter('textOriginal'), snippets_two))

    """
    #raw_text = list(map(itemgetter('textOriginal'), list(map(itemgetter('snippet'), list(map(itemgetter('topLevelComment'), list(map(itemgetter('snippet'), comment_data['items']))))))))
      
    return comment_data, comment_data.get('nextPageToken')
    #return list(map(clean_str, raw_text)), comment_data.get('nextPageToken')





def get_vid_id_from_playlist(playlist_id, nextPageToken, youtube_object):
    res = youtube_object.playlistItems().list(playlistId=playlist_id, 
                                            part='snippet', 
                                            maxResults=1,
                                            pageToken=nextPageToken).execute() #Get the first video in playlist
    
    
    vid_id = res['items'][0]['snippet']['resourceId']['videoId'] #Get the video id
    return vid_id, res.get('nextPageToken')

  
    
def channel_id_from_display_name(display_name, youtube_object):
    res = youtube_object.search().list(part='snippet', type='channel', q=display_name).execute()['items'] 
    names_ids = {}

    for data in res: #For every channe data
        names_ids[data['snippet']['channelTitle']] = data['snippet']['channelId']
        #Get name and corresponding id

    print(f"Returned matches: {names_ids}")
    return names_ids










