#Imports 

from flask import Flask, render_template, send_from_directory, request, session, redirect, url_for, flash, copy_current_request_context
from flask_socketio import join_room, leave_room, send, SocketIO, emit
import numpy as np
import signal
import threading
import googleapiclient
from googleapiclient.discovery import build
import reddit_functions
import sys
import time
import atexit  
import yt_functions
import os
import datetime
import inferenceFunctions
import sqlite3
import math
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline




#Intialize The Pretrained Hugging Face Transformer Models
binary_toxic_model_pipeline = pipeline('text-classification', model=f"s-nlp/roberta_toxicity_classifier")
neg_neutral_positive_model_pipeline = pipeline('sentiment-analysis', model=f"cardiffnlp/twitter-roberta-base-sentiment")
emotions_detector_model_pipeline = pipeline('text-classification', model=f"j-hartmann/emotion-english-distilroberta-base")

binary_toxic_model_pipeline_return_all_scores = pipeline('text-classification', model=f"s-nlp/roberta_toxicity_classifier", return_all_scores=True)
neg_neutral_positive_model_pipeline_return_all_scores = pipeline('sentiment-analysis', model=f"cardiffnlp/twitter-roberta-base-sentiment", return_all_scores=True)
emotions_detector_model_pipeline_return_all_scores = pipeline('text-classification', model=f"j-hartmann/emotion-english-distilroberta-base", return_all_scores=True)

#Make an absolute path to directory
dir_name = os.path.dirname(os.path.abspath(__file__))


#Num of seconds app should wait for new clients to connect, after this, if no clients, then shutdown app
grace_period = 5
    
#More Intialization
app = Flask(__name__) #Make an app object
app.config['SECRET_KEY'] = "E9h1WXxAPLPlBOlJM0Fl" #Configure a secret Key
app.config['JSON_DATA_FILES'] = os.path.join(os.path.abspath(dir_name), 'sql_data')

socketio = SocketIO(app)

first_sqliteConnection = sqlite3.connect(f"{app.config['JSON_DATA_FILES']}/auth_database.db")
first_cursor = first_sqliteConnection.cursor()

#Get the user data
first_cursor.execute("SELECT * FROM user_data")
application_user_data = first_cursor.fetchone()

if not application_user_data:
    print('**\n\n\nFILL OUT THE USER CREDENTIAL DATABASE BEFORE RUNNING THIS APP!!\n\n')

    print("Shutting Down due to lack of credentials...")
    sys.exit()

yt_api_key = application_user_data[0]
reddit_client_id = application_user_data[1]
reddit_secret_token = application_user_data[2]
reddit_username = application_user_data[3]
reddit_password = application_user_data[4]
default_redirect_site = application_user_data[5]

#Intialize API Objects
youtube_api_object = youtube = build('youtube', 'v3', developerKey=yt_api_key)

reddit_api_headers = reddit_functions.authorize(reddit_client_id, reddit_secret_token, reddit_username, reddit_password)


#List of Clients/Rooms
client_list = []


                                

#KEEP THIS
model_labels = [["Negative", "Neutral", "Positive"],
           ["Non-Toxic", "Toxic"],
           ["Passion/Anger", "disgust", 'Concern/Fear', 'Joy', 'Neutral', 'Sadness', 'Surprise/Questioning']]
    
#KEEP THIS
model_titles = ['Sentiment Model', 'Toxicity Measurer', 'Emotions Classifier']


#Direct user to home.html
@app.route("/", methods=('GET', 'POST')) #The default website page (only shown the first time ever)
def hello_world():
    session.clear()

    sqliteConnection = sqlite3.connect(f"{app.config['JSON_DATA_FILES']}/database.db")
    cursor = sqliteConnection.cursor()

    cursor.execute("SELECT * FROM yt_channels")
    yt_channels = cursor.fetchall()

    sqliteConnection.close()

    

    return render_template('home.html', yt_channels=yt_channels, default_site=default_redirect_site)

#Direct user the text_classifier subpage
@app.route("/text_classifier", methods=('GET', 'POST')) #The default website page (only shown the first time ever)
def text_classifier():
    session.clear()

    return render_template('text_classifier.html', enum=enumerate, titles=model_titles, metrics=model_labels, default_site=default_redirect_site)

"""
@app.route("/tooManyClientsOpen", methods=('GET', 'POST'))
def too_many_clients_page():
    
    print("\n\n\nMore than 1 Client\n\n\n")
    return render_template('too_many_clients.html')
"""
    
   


@app.route("/reddit_home", methods=('GET', 'POST')) #The default website page (only shown the first time ever)
def reddit_home():
    session.clear()
    
    sqliteConnection = sqlite3.connect(f"{app.config['JSON_DATA_FILES']}/database.db")
    cursor = sqliteConnection.cursor()

    cursor.execute("SELECT * FROM reddit_data")
    data = cursor.fetchall()

    
    sqliteConnection.close()

    return render_template('reddit_home.html', data=data, default_site=default_redirect_site)

@app.route("/view_inference_results/<media_type>/<database_id>", methods=('GET', 'POST')) #The default website page (only shown the first time ever)
def view_inference_results(media_type, database_id):
    
    session.clear()
    
    sqliteConnection = sqlite3.connect(f"{app.config['JSON_DATA_FILES']}/database.db")
    cursor = sqliteConnection.cursor()

    framework = 'reddit_data' if media_type == 'RD' else 'yt_channels'
    database_names = ['sentimentClassifierRes', 'toxicityMeasurerRes', 'emotionsDetectorRes']

    cursor.execute(f"SELECT title FROM {framework} WHERE pos = ?", (database_id))
    title = cursor.fetchone()


    cursor.execute(f"SELECT usedsentimentmodel, usedtoxicitymodel, usedemotionsmodel FROM {framework} WHERE pos = ?", (database_id))
    has_been_processed = cursor.fetchone() 
   
    inference_res = []

    special_labels = [["Negative", "Neutral", "Positive"],
           ["Toxic", "Non-Toxic"], #The label order for the database.db is toxic, neutral - so that's why its like that here
           #Even though the model itself outputs labels in the [non-toxic, toxic]
           ["Passionate", "Disgust", 'Concern', 'Joy', 'Neutral', 'Sadness', 'Questioning']]

    
    comments_analyzed_for_each_model = []

    for index, database_name in enumerate(database_names):

        if has_been_processed[index] != 0:
            
            cursor.execute(f"SELECT * FROM {database_name} WHERE type = ? AND pos = ?", (media_type, int(database_id)))
            results = cursor.fetchone()
            print(results)

         

            inference_res.append(results[2:-1])
            comments_analyzed_for_each_model.append(results[-1])
            
        else:
          
            inference_res.append([])
            comments_analyzed_for_each_model.append(0)
                
   

    sqliteConnection.close()

    prefix = 'YT Channel' if media_type == 'YT' else 'Reddit Forum'

    return render_template('view_processing_results.html', inference_res=inference_res, comments_analyzed_for_each_model=comments_analyzed_for_each_model,  labels=special_labels, prefix=prefix, title=title, default_site=default_redirect_site)



@app.route("/media_analyzer/<raw_media_type>/<database_id>", methods=('GET', 'POST'))
def yt_channel_monitor(raw_media_type, database_id):
   
    media_type = 'youtube' if raw_media_type == 'YT' else 'reddit'

    sqliteConnection = sqlite3.connect(f"{app.config['JSON_DATA_FILES']}/database.db")
    cursor = sqliteConnection.cursor()

    if media_type == 'youtube':
        prefix = 'YT Channel'
        cursor.execute("SELECT title, usedsentimentmodel, usedtoxicitymodel, usedemotionsmodel, uploadsid, channelid FROM yt_channels WHERE pos = ?", (database_id, ))
        row_results = cursor.fetchone()
        row_results = row_results + ("YT", database_id)
       

    else:
        prefix = "Reddit Forum"
        cursor.execute("SELECT title, usedsentimentmodel, usedtoxicitymodel, usedemotionsmodel FROM reddit_data WHERE pos = ?", (database_id))
        row_results = cursor.fetchone()
        row_results = row_results + ('RD', database_id)
    
    prefix = 'YT Channel' if raw_media_type == 'YT' else 'Reddit Subforum'
    return render_template('data_analyzer.html', prefix=prefix, results=list(row_results), default_site=default_redirect_site)



@socketio.on('endServer')
def end_the_app():
    print("Been called")
    global grace_period
    socketio.emit('redirectTab', {'url': 'None'})
    time.sleep(grace_period)
    
    print("\n\n\nShutdown Beginning...\n\n\n")
    os.kill(os.getpid(), signal.SIGINT)

@atexit.register 
def closeAllTabs():
    socketio.emit('redirectTab', {'url': 'None'})


@socketio.on('runOneInference') #Finish this part
def runOneInference(data): 
    def sendOutputDict(raw_results, model_title, labels_of_model):
        output = {'model-type': model_title, 'labels-list': labels_of_model}
        for index in range(len(raw_results)): #The amount of neurons in the output layer of the model
        #Aka the amount of metrics in the model output
           
            output[f'data{index+1}'] = round(raw_results[index]['score'], 3) * 100
        
        socketio.emit('runOneInference-Results', output, to=request.sid)    
       
    if data['model-title'] == model_titles[0]: #If the model is 'Sentiment Model'
        results = neg_neutral_positive_model_pipeline_return_all_scores(data['text'])[0]
        sendOutputDict(results, data['model-title'], model_labels[0])
        
      

    elif data['model-title'] == model_titles[1]: #If its ' Toxicty Measurer
        results = binary_toxic_model_pipeline_return_all_scores(data['text'])[0]
        sendOutputDict(results, data['model-title'], model_labels[1])

    elif data['model-title'] == model_titles[2]:
        results = emotions_detector_model_pipeline_return_all_scores(data['text'])[0]
        sendOutputDict(results, data['model-title'], model_labels[2])

@socketio.on('getBasicInfo')
def getBasicInfo(data):
   
    sqliteConnection = sqlite3.connect(f"{app.config['JSON_DATA_FILES']}/database.db")
    cursor = sqliteConnection.cursor()


    if data['framework'] == 'YT':
      

        cursor.execute("SELECT COUNT(1) FROM yt_channels WHERE title = ?;", (data['name'], ))
        does_exist = cursor.fetchone()

        if does_exist[0] != 0:
          
            socketio.emit('BasicInfoGotten', {'framework': 'YT', 'stored-already': True}, to=request.sid)
            sqliteConnection.close()
            return
        
        channel_id, upload_id = yt_functions.get_data_from_display_name(data['name'], youtube_api_object)
        if channel_id == 'FAILED':
         
            socketio.emit("API_REQUEST_FAILED", {'framework': 'YT', 'transfer_id': data['name']}, to=request.sid)
            sqliteConnection.close()
            return

        if channel_id == 'API_EXCEEDED':
          
            socketio.emit("API_Error", {'status': 'quota_exceeded_in_info_gathering', 'framework': 'YT', 'name': data['name']}, to=request.sid)
            sqliteConnection.close()
            return

       
        socketio.emit('BasicInfoGotten', {'framework': 'YT', 'channel-id': channel_id, 'upload-id': upload_id, 'stored-already': False}, to=request.sid)
        sqliteConnection.close()

        
    
         
    elif data['framework'] == 'RD':
     

        
        cursor.execute("SELECT COUNT(1) FROM reddit_data WHERE title = ?;", (data['name'], ))

        does_exist = cursor.fetchone()
        
        if does_exist[0] == 0: #If it isn't in database
            is_real = reddit_functions.subbredit_is_valid(data['name'], reddit_api_headers)
            if is_real:
                socketio.emit('BasicInfoGotten', {'framework': 'RD', 'stored-already': False}, to=request.sid)
            else:
                socketio.emit("API_REQUEST_FAILED", {'framework': 'RD', 'transfer_id': data['name']}, to=request.sid)  
        else:
            socketio.emit('BasicInfoGotten', {'framework': 'RD', 'stored-already': True}, to=request.sid)
        

@socketio.on('deleteData')
def deleteData(data):
   

    sqliteConnection = sqlite3.connect(f"{app.config['JSON_DATA_FILES']}/database.db")
    cursor = sqliteConnection.cursor()

    database_id = int(data['key'])
    framework = 'reddit_data' if data['framework'] == 'RD' else 'yt_channels'
    
    if data['framework'] == 'YT':
        cursor.execute(f"SELECT usedtoxicitymodel, usedemotionsmodel, usedsentimentmodel FROM yt_channels WHERE pos = ?", (database_id, ))
    
    else:
        cursor.execute(f"SELECT usedtoxicitymodel, usedemotionsmodel, usedsentimentmodel FROM reddit_data WHERE pos = ?", (database_id, ))
    
    has_been_processed = cursor.fetchone()
    database_names = ['toxicityMeasurerRes', 'emotionsDetectorRes', 'sentimentClassifierRes']

    for index, database_name in enumerate(database_names):
        if has_been_processed[index] != 0:
            if data['framework'] == 'YT':
                cursor.execute(f"DELETE FROM {database_name} WHERE pos = ?", (database_id, ))
            else:
                cursor.execute(f"DELETE FROM {database_name} WHERE pos = ?", (database_id, ))
    

    
    
    cursor.execute(f"DELETE FROM {framework} WHERE pos = ?", (database_id, ))
    sqliteConnection.commit()
    sqliteConnection.close()

    

    

continue_with_processing = True

#This is singular background task (run inference)
@socketio.on('runDataInfernece')
def collect_yt_channel_comments(data):
    
    #
    sid_id = request.sid

    if data['model-type'] == "emotions-model":
        results = [0, 0, 0, 0, 0, 0, 0]

    elif data['model-type'] == "toxicity-model":
        results = [0, 0]

    elif data['model-type'] == "sentiment-model":
        results = [0, 0, 0]
    

    if data['framework'] == 'YT':
        
        sqliteConnection = sqlite3.connect(f"{app.config['JSON_DATA_FILES']}/database.db")
        cursor = sqliteConnection.cursor()

        

        #User can end data processing by clicking 'EndDataInference' 
        @socketio.on('endDataInference')
        def endAPI_Processing():
            global continue_with_processing
            continue_with_processing = False
          
            socketio.emit("API_Error", {'text': 'User Ended Processing', 'num-collected': f'{sum(results)} comments analyzed'}, to = sid_id)
            return

        
        
        
        cursor.execute("SELECT uploadsid, title FROM yt_channels WHERE pos = ?", (data['key'],))
        data_row = cursor.fetchone()

      
      
        currentTime = datetime.datetime.now()
        timestamp = currentTime.timestamp()
        date_time = datetime.datetime.fromtimestamp(timestamp)


 

        def yt_comment_collector():
            global continue_with_processing
            continue_with_processing = True

            vid_next_page_token = None
        
            commentThread_next_page_token = None   

            vid_id = None 

            while True: #Loop over each video_id
             
                try:
                    vid_id, vid_next_page_token = yt_functions.get_vid_id_from_playlist(data_row[0], vid_next_page_token, youtube_api_object)
                except googleapiclient.errors.HttpError as e:
                    if int(e.status_code) == 403:
                        
                        socketio.emit("API_Error", {'text': 'API Quota Exceeded', 'num-collected': f'{sum(results)} comments analyzed'}, to=sid_id)

                   
                    break

                if continue_with_processing == False:
                    break

                if vid_next_page_token == None:
                       
                    socketio.emit("API_Error", {'text': 'No More Videos', 'num-collected': f'{sum(results)} comments analyzed'}, to=sid_id)
                    break

                while True: #Loop over each comment_thread
                   
                    try:
                        commentThreads, commentThread_next_page_token = yt_functions.get_comments_from_vid_id(vid_id, commentThread_next_page_token, 100, youtube_api_object) #Make this 100
                       
                    except Exception as e:
                        #This also works if it runs out of comments, because it will go back and use the API to get the vid_id
                        #Then, the API Quota Exceeded error will be caught there!
                        break

                    if data['limit'] != 0 and sum(results) >= data['limit']:
            
                        continue_with_processing = False
                        break
                    
                    
                        
                    if continue_with_processing == False:
                        break


                    
                    for commentThread in commentThreads['items']:  #Loop over each comment 
                        try:
                            if continue_with_processing == False:
                                break

                            if data['model-type'] == 'emotions-model':
                                results[inferenceFunctions.emotions_inference(emotions_detector_model_pipeline, yt_functions.clean_str(commentThread['snippet']['topLevelComment']['snippet']['textOriginal']))] += 1

                                socketio.emit('resultsofInference', {'total-processed': sum(results), 'current-results': results, 
                                     'percentage-processed': round((sum(results)/data['limit']) * 100, 1)}, to=sid_id)
                                
                                
                            
                            elif data['model-type'] == 'toxicity-model':
                              
                                results[inferenceFunctions.toxicity_inference(binary_toxic_model_pipeline, yt_functions.clean_str(commentThread['snippet']['topLevelComment']['snippet']['textOriginal']))] += 1
                                socketio.emit('resultsofInference', {'total-processed': sum(results), 
                                    'current-results': results, 'percentage-processed': round((sum(results)/data['limit']) * 100, 1)}, to=sid_id)
                            else:
                               
                                results[inferenceFunctions.sentiment_classification_inference(neg_neutral_positive_model_pipeline, yt_functions.clean_str(commentThread['snippet']['topLevelComment']['snippet']['textOriginal']))] += 1
                                socketio.emit('resultsofInference', {'total-processed': sum(results), 
                                    'current-results': results, 'percentage-processed': round((sum(results)/data['limit']) * 100, 1)}, to=sid_id)

                            
                            
                            
                        except Exception as e: 
                            pass
                    
                    if commentThread_next_page_token is None:
                      
                        break

                if continue_with_processing == False:
                    break
            
            
                
                #channel_data['data'][database_id]["Stored Comments Date"] = date_time.strftime("%B %d, %Y")
    
        t1 = threading.Thread(target=yt_comment_collector)   
        t1.start()

        t1.join()
       

        cursor.execute(f"SELECT usedemotionsmodel, usedtoxicitymodel, usedsentimentmodel FROM yt_channels WHERE pos = ?", (data['key']))
        has_been_processed = cursor.fetchone()
        if data['model-type'] == "emotions-model":
            cursor.execute("UPDATE yt_channels SET anyProcessed = 1 WHERE pos = ?", (data['key'], ))
            cursor.execute("UPDATE yt_channels SET usedemotionsmodel = 1 WHERE pos = ?", (data['key'], ))
            
            if has_been_processed[0] == 0:
                cursor.execute("INSERT INTO emotionsDetectorRes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", ('YT', data['key'], results[0], results[1], results[2], results[3], results[4], results[5], results[6], sum(results)))
            else:
                cursor.execute("UPDATE emotionsDetectorRes SET anger = ?, fear = ?, disgust = ?, neutral = ?, joy = ?, sadness = ?, surprise = ?, commentnum = ? WHERE pos = ?", (results[0], results[1], results[2], results[3], results[4], results[5], results[6], sum(results), data['key']))
            

        elif data['model-type'] == "toxicity-model":
            cursor.execute("UPDATE yt_channels SET anyProcessed = 1 WHERE pos = ?", (data['key'], ))
            cursor.execute("UPDATE yt_channels SET usedtoxicitymodel = 1 WHERE pos = ?", (data['key'], ))

            if has_been_processed[1] == 0:
               
                cursor.execute("INSERT INTO toxicityMeasurerRes VALUES (?, ?, ?, ?, ?)", ('YT', data['key'], results[0], results[1], sum(results)))
            else:
                
                cursor.execute("UPDATE toxicityMeasurerRes SET toxic = ?, neutral = ?, commentnum = ? WHERE pos = ?", (results[0], results[1], sum(results), data['key']))

        elif data['model-type'] == "sentiment-model":
            cursor.execute("UPDATE yt_channels SET anyProcessed = 1 WHERE pos = ?", (data['key'], ))
            cursor.execute("UPDATE yt_channels SET usedsentimentmodel = 1 WHERE pos = ?", (data['key'], ))

            if has_been_processed[2] == 0:
                
                cursor.execute("INSERT INTO sentimentClassifierRes VALUES (?, ?, ?, ?, ?, ?)", ('YT', data['key'], results[0], results[1], results[2], sum(results) ))

            else:
                
                cursor.execute("UPDATE sentimentClassifierRes SET negative = ?, neutral = ?, positive = ?, commentnum = ? WHERE pos = ?", (results[0], results[1], results[2], sum(results), data['key']))
        
        sqliteConnection.commit()
        sqliteConnection.close()
            

        
        

    elif data['framework'] == 'RD':


       
        

        sqliteConnection = sqlite3.connect(f"{app.config['JSON_DATA_FILES']}/database.db")
        cursor = sqliteConnection.cursor()

        currentTime = datetime.datetime.now()
        timestamp = currentTime.timestamp()
        date_time = datetime.datetime.fromtimestamp(timestamp)

        
        params = {"limit": 100}
        

        cursor.execute("SELECT title FROM reddit_data WHERE pos = ?", (data['key'],))
        data_row = cursor.fetchone()
        broken_name = data_row[0].split('/')

        
        def rd_comment_collector():
            global continue_with_processing
            continue_with_processing = True

            for i in range(math.ceil(data['limit']/100)):
                if continue_with_processing == True:
                    comments_batch, kinds, ids = reddit_functions.get_data_from_subforum(broken_name[-1], params, reddit_api_headers)  

                    for idx, comment in enumerate(comments_batch): #For every comment

                        @socketio.on('endDataInference')
                        def endAPI_Processing():
                           
                            global continue_with_processing
                            continue_with_processing = False
                            socketio.emit("API_Error", {'text': 'User Ended Processing', 'num-collected': f'{sum(results)} comments analyzed'}, to=sid_id)

                        if continue_with_processing == False:
                            break
                        

                        if len(comments_batch) <= 99 and idx == (len(comments_batch) - 1): 
                            #If this is the final comment in the comment batch
                            #and if the comment batch is less than 100 (meaning that there is no next batch)
                         
                            
                            socketio.emit("API_Error", {'text': 'No More Comments', 'num-collected': sum(results)}, to=sid_id)
                            #socketio.emit('requestsInProgress', {'framework': 'RD', 'name': reddit_data['data'][database_id]['title'], 'done': True, 'num-requests-done': len(text)})       
                            
                            continue_with_processing = False
                            break

                        if sum(results) == data['limit']:
                         
                            
                            #socketio.emit('requestsInProgress', {'framework': 'RD', 'name': reddit_data['data'][database_id]['title'], 'done': False, 'num-requests-done': len(text)})       
                            
                            continue_with_processing = False
                            break

                        
                        
                        if data['model-type'] == 'emotions-model':
                            results[inferenceFunctions.emotions_inference(emotions_detector_model_pipeline, yt_functions.clean_str(comment))] += 1

                            socketio.emit('resultsofInference', {'total-processed': sum(results), 
                                 'current-results': results, 'percentage-processed': round((sum(results)/data['limit']) * 100, 1)}, to=sid_id)
                                
                                
                            
                        elif data['model-type'] == 'toxicity-model':
                            results[inferenceFunctions.toxicity_inference(binary_toxic_model_pipeline, yt_functions.clean_str(comment))] += 1
                            socketio.emit('resultsofInference', {'total-processed': sum(results), 
                                 'current-results': results, 'percentage-processed': round((sum(results)/data['limit']) * 100, 1)}, to=sid_id)
                        else:
                            results[inferenceFunctions.sentiment_classification_inference(neg_neutral_positive_model_pipeline, yt_functions.clean_str(comment))] += 1
                            socketio.emit('resultsofInference', {'total-processed': sum(results), 
                                 'current-results': results, 'percentage-processed': round((sum(results)/data['limit']) * 100, 1)}, to=sid_id)
                        #socketio.emit('requestsInProgress', {'framework': 'RD', 'name': reddit_data['data'][database_id]['title'], 'total-requests': data['num'], 'num-requests-done': comment_counter, 'done': False})    

                       
                    if len(kinds) == 0:
                       
                        #socketio.emit('requestsInProgress', {'framework': 'RD', 'name': reddit_data['data'][database_id]['title'], 'done': True, 'num-requests-done': len(text)})
                        break 

                    fullname = kinds[-1] + '_' + ids[-1]
                    params['after'] = fullname
                    params['count'] = sum(results)

                else:
                    
                    break
        
        t1 = threading.Thread(target=rd_comment_collector)   
        t1.start()

        t1.join()
       
        cursor.execute(f"SELECT usedemotionsmodel, usedtoxicitymodel, usedsentimentmodel FROM reddit_data WHERE pos = ?", (data['key']))
        has_been_processed = cursor.fetchone()
      
        if data['model-type'] == "emotions-model":
            cursor.execute("UPDATE reddit_data SET anyProcessed = 1 WHERE pos = ?", (data['key'], ))
            cursor.execute("UPDATE reddit_data SET usedemotionsmodel = 1 WHERE pos = ?", (data['key'], ))
            
            if has_been_processed[0] == 0:
                
                cursor.execute("INSERT INTO emotionsDetectorRes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", ('RD', data['key'], results[0], results[1], results[2], results[3], results[4], results[5], results[6], sum(results)))
            else:
               
                cursor.execute("UPDATE emotionsDetectorRes SET anger = ?, fear = ?, disgust = ?, neutral = ?, joy = ?, sadness = ?, surprise = ?, commentnum = ? WHERE pos = ?", (results[0], results[1], results[2], results[3], results[4], results[5], results[6], sum(results), data['key']))
        
        elif data['model-type'] == "toxicity-model":
            cursor.execute("UPDATE reddit_data SET anyProcessed = 1 WHERE pos = ?", (data['key'], ))
            cursor.execute("UPDATE reddit_data SET usedtoxicitymodel = 1 WHERE pos = ?", (data['key'], ))
            
            if has_been_processed[1] == 0:
                
                cursor.execute("INSERT INTO toxicityMeasurerRes VALUES (?, ?, ?, ?, ?)", ('RD', data['key'], results[0], results[1], sum(results)))
            else:
                
                cursor.execute("UPDATE toxicityMeasurerRes SET toxic = ?, neutral = ?, commentnum = ? WHERE pos = ?", (results[0], results[1], sum(results), data['key']))

        elif data['model-type'] == "sentiment-model":
            cursor.execute("UPDATE reddit_data SET anyProcessed = 1 WHERE pos = ?", (data['key'], ))
            cursor.execute("UPDATE reddit_data SET usedsentimentmodel = 1 WHERE pos = ?", (data['key'], ))
            
            if has_been_processed[2] == 0:
               
                cursor.execute("INSERT INTO sentimentClassifierRes VALUES (?, ?, ?, ?, ?, ?)", ('RD', data['key'], results[0], results[1], results[2], sum(results)))

            else:
                
                cursor.execute("UPDATE sentimentClassifierRes SET negative = ?, neutral = ?, positive = ?, commentnum = ? WHERE pos = ?", (results[0], results[1], results[2], sum(results), data['key']))
        
        
        #cursor.execute("UPDATE reddit_data SET inferencedate = ? WHERE pos = ?", (date_time.strftime('%Y-%m-%d'), data['key']))
        
        
        sqliteConnection.commit()
        sqliteConnection.close()
        
       
        
       


@socketio.on("addToDatabase")
def add_to_database(data): 
   
    sqliteConnection = sqlite3.connect(f"{app.config['JSON_DATA_FILES']}/database.db")
    cursor = sqliteConnection.cursor()

    if data['framework'] == 'YT':
        cursor.execute("SELECT pos FROM yt_channels ORDER BY pos DESC LIMIT 1")
        last_id = cursor.fetchone()

        if not last_id:
            new_id = 1
        else:
            new_id = last_id[0] + 1
        
       
            
    
        cursor.execute("INSERT INTO yt_channels (pos, title, uploadsid, channelid, usedsentimentmodel, usedtoxicitymodel, usedemotionsmodel, anyprocessed) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (new_id, data['title'], data['upload-id'], data['channel-id'], 0, 0, 0, 0))
        sqliteConnection.commit()
        sqliteConnection.close()
             

    elif data['framework'] == 'RD':
        cursor.execute("SELECT pos FROM reddit_data ORDER BY pos DESC LIMIT 1")
        last_id = cursor.fetchone()
      
        
        if not last_id:
            new_id = 1
        else:
            new_id = last_id[0] + 1

        cursor.execute("INSERT INTO reddit_data (pos, title, usedsentimentmodel, usedtoxicitymodel, usedemotionsmodel, anyprocessed) VALUES (?, ?, ?, ?, ?, ?)", (new_id, data['title'], 0, 0, 0, 0))
        sqliteConnection.commit()
        sqliteConnection.close()

      

       
            
   
@socketio.on("connect")
def connect():  
    global client_list
    client_list.append(request.sid)
    print("Connected")
    print(client_list)

    
        
        


@socketio.on('disconnect') #If the socket disconnects
def disconnect():
    print("Removed")
    global client_list
    global continue_with_processing

    continue_with_processing = False
    
    client_list.remove(request.sid)
    
    print(client_list)
   
   

    """
    if len(client_list) == 0: #End server
        print("\n\nNO MORE CLIENTS...ENDING SERVER\n\n")
        os.kill(os.getpid(), signal.SIGINT)
    """

    
    

   
    

#btn btn-outline-primary btn-lg
if __name__ == '__main__':
    print("\n\n----------------------------\nRunning App")
    print("--------------------\n")
    socketio.run(app)