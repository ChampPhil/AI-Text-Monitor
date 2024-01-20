#Imports 

from flask import Flask, render_template, send_from_directory, request, session, redirect, url_for, flash, copy_current_request_context
from flask_socketio import join_room, leave_room, send, SocketIO, emit
from colorama import Fore, Back, Style
import numpy as np
import signal
import threading
import googleapiclient
from googleapiclient.discovery import build
import reddit_functions
import sys
import time
import random
from string import ascii_uppercase
from threading import Lock, Event, Thread
import yt_functions
import os
import json
import datetime
import inferenceFunctions
import sqlite3
import math
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline

#Intialize The Pretrained Hugging Face Transformer Model
binary_toxic_model_pipeline = pipeline('text-classification', model=f"s-nlp/roberta_toxicity_classifier")
neg_neutral_positive_model_pipeline = pipeline('sentiment-analysis', model=f"cardiffnlp/twitter-roberta-base-sentiment")
emotions_detector_model_pipeline = pipeline('text-classification', model=f"j-hartmann/emotion-english-distilroberta-base")

binary_toxic_model_pipeline_return_all_scores = pipeline('text-classification', model=f"s-nlp/roberta_toxicity_classifier", return_all_scores=True)
neg_neutral_positive_model_pipeline_return_all_scores = pipeline('sentiment-analysis', model=f"cardiffnlp/twitter-roberta-base-sentiment", return_all_scores=True)
emotions_detector_model_pipeline_return_all_scores = pipeline('text-classification', model=f"j-hartmann/emotion-english-distilroberta-base", return_all_scores=True)

#Make an absolute path to directory
dir_name = os.path.dirname(os.path.abspath(__file__))


#Data Thread (Sets Up Article)
data_thread = None
thread_lock = Lock()

    
#More Intialization
app = Flask(__name__) #Make an app object
app.config['SECRET_KEY'] = "E9h1WXxAPLPlBOlJM0Fl" #Configure a secret Key
app.config['JSON_DATA_FILES'] = os.path.join(os.path.abspath(dir_name), 'sql_data')

socketio = SocketIO(app)

sqliteConnection = sqlite3.connect(f"{app.config['JSON_DATA_FILES']}/auth_database.db")
cursor = sqliteConnection.cursor()

#Get the user data
cursor.execute("SELECT * FROM user_data")
application_user_data = cursor.fetchone()

yt_api_key = application_user_data[0]
reddit_client_id = application_user_data[1]
reddit_secret_token = application_user_data[2]
reddit_username = application_user_data[3]
reddit_password = application_user_data[4]


#Intialize API Objects
youtube_api_object = youtube = build('youtube', 'v3', developerKey=yt_api_key)

reddit_api_headers = reddit_functions.authorize(reddit_client_id, reddit_secret_token, reddit_username, reddit_password)

                                                                               

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

    print(yt_channels)

    return render_template('home.html', yt_channels=yt_channels)

#Direct user the text_classifier subpage
@app.route("/text_classifier", methods=('GET', 'POST')) #The default website page (only shown the first time ever)
def text_classifier():
    session.clear()

    return render_template('text_classifier.html', enum=enumerate, titles=model_titles, metrics=model_labels)



@app.route("/reddit_home", methods=('GET', 'POST')) #The default website page (only shown the first time ever)
def reddit_home():
    session.clear()
    
    sqliteConnection = sqlite3.connect(f"{app.config['JSON_DATA_FILES']}/database.db")
    cursor = sqliteConnection.cursor()

    cursor.execute("SELECT * FROM reddit_data")
    data = cursor.fetchall()

    print(data)
    sqliteConnection.close()

    return render_template('reddit_home.html', data=data)

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
    print(has_been_processed)
    inference_res = []

    special_labels = [["Negative", "Neutral", "Positive"],
           ["Toxic", "Non-Toxic"], #The label for the database is toxic, neutral - so that's why its like that here
           ["Passion/Anger", "disgust", 'Concern/Fear', 'Joy', 'Neutral', 'Sadness', 'Surprise/Questioning']]
    
    comments_analyzed_for_each_model = []

    for index, database_name in enumerate(database_names):

        if has_been_processed[index] != 0:
            print(database_name)
            cursor.execute(f"SELECT * FROM {database_name} WHERE type = ? AND pos = ?", (media_type, int(database_id)))
            results = cursor.fetchone()
            print(results)
            print(results[2:-1])
            print(results[-1])

            percentages = [round((result/sum(results[2:-1])) * 100) for result in results[2:-1]] #Change This to 2:-1

            inference_res.append(percentages)
            comments_analyzed_for_each_model.append(results[-1])
            
        else:
            print("In here")
            inference_res.append([])
            comments_analyzed_for_each_model.append(0)
                
   

    sqliteConnection.close()

    prefix = 'YT Channel' if media_type == 'YT' else 'Reddit Forum'

    return render_template('view_processing_results.html', inference_res=inference_res, comments_analyzed_for_each_model=comments_analyzed_for_each_model,  labels=special_labels, prefix=prefix, title=title)



@app.route("/media_analyzer/<raw_media_type>/<database_id>", methods=('GET', 'POST'))
def yt_channel_monitor(raw_media_type, database_id):
    print("\n\n---------------------------\nTurns out you do have a usage after all....\n\n-----------------------------------\n")
    print(raw_media_type)
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
    return render_template('data_analyzer.html', prefix=prefix, results=list(row_results))


@app.route("/begin_shutdown", methods=('GET', 'POST'))
def end_the_app():
    print("\n\n\nShutdown Beginning...\n\n\n")
    os.kill(os.getpid(), signal.SIGINT)




@socketio.on('runOneInference') #Finish this part
def runOneInference(data): 
    def sendOutputDict(raw_results, model_title, labels_of_model):
        output = {'model-type': model_title, 'labels-list': labels_of_model}
        for index in range(len(raw_results)): #The amount of neurons in the output layer of the model
        #Aka the amount of metrics in the model output
            print(f"Raw scores: {raw_results[index]['score']}")
            output[f'data{index+1}'] = round(raw_results[index]['score'], 3) * 100
        
        socketio.emit('runOneInference-Results', output)    
        print(output)  
     
    print(f"\n\nI am in the data: {data}")
    if data['model-title'] == model_titles[0]: #If the model is 'Sentiment Model'
        results = neg_neutral_positive_model_pipeline_return_all_scores(data['text'])[0]
        sendOutputDict(results, data['model-title'], model_labels[0])
        
        print("Sent the results back!")

    elif data['model-title'] == model_titles[1]: #If its ' Toxicty Measurer
        results = binary_toxic_model_pipeline_return_all_scores(data['text'])[0]
        sendOutputDict(results, data['model-title'], model_labels[1])

    elif data['model-title'] == model_titles[2]:
        results = emotions_detector_model_pipeline_return_all_scores(data['text'])[0]
        sendOutputDict(results, data['model-title'], model_labels[2])

@socketio.on('getBasicInfo')
def getBasicInfo(data):
    print("Called")
    sqliteConnection = sqlite3.connect(f"{app.config['JSON_DATA_FILES']}/database.db")
    cursor = sqliteConnection.cursor()


    if data['framework'] == 'YT':
        print("YT called")

        cursor.execute("SELECT COUNT(1) FROM yt_channels WHERE title = ?;", (data['name'], ))
        does_exist = cursor.fetchone()

        if does_exist[0] != 0:
            print("Does Exist")
            socketio.emit('BasicInfoGotten', {'framework': 'YT', 'stored-already': True})
            sqliteConnection.close()
            return
        
        channel_id, upload_id = yt_functions.get_data_from_display_name(data['name'], youtube_api_object)
        if channel_id == 'FAILED':
            print("Invalid Name")
            socketio.emit("API_REQUEST_FAILED", {'framework': 'YT', 'transfer_id': data['name']})
            sqliteConnection.close()
            return

        if channel_id == 'API_EXCEEDED':
            print("Quota Exceeded")
            socketio.emit("API_Error", {'status': 'quota_exceeded_in_info_gathering', 'framework': 'YT', 'name': data['name']})
            sqliteConnection.close()
            return

        print("Is Not Stored")
        socketio.emit('BasicInfoGotten', {'framework': 'YT', 'channel-id': channel_id, 'upload-id': upload_id, 'stored-already': False})
        sqliteConnection.close()

        
        """
        except Exception as e:
            print("Exce")
            print(f"Here's the exception: {e}")
            try:
                if e.status_code == 403:
                    print(f"YouTube API done")
                    socketio.emit("API_Error", {'status': 'quota_exceeded_in_info_gathering', 'framework': 'YT', 'name': data['name']})
                    sqliteConnection.close()
                    return
                else:
                    print("Not A Name...")
                    socketio.emit("API_REQUEST_FAILED", {'framework': 'YT', 'transfer_id': data['name']})
                    sqliteConnection.close()
                    return 
            except Exception as e:
            
                print("yo why'd u fail")
                socketio.emit("API_REQUEST_FAILED", {'framework': 'YT', 'transfer_id': data['name']})
                sqliteConnection.close()
                return
        """
         
    elif data['framework'] == 'RD':
        print("\n\n-----------------------------------We're checking if its in there...")
        print(f"Here's the data sent to the function: {data}\n\n")

        
        cursor.execute("SELECT COUNT(1) FROM reddit_data WHERE title = ?;", (data['name'], ))

        does_exist = cursor.fetchone()
        
        if does_exist[0] == 0: #If it isn't in database
            is_real = reddit_functions.subbredit_is_valid(data['name'], reddit_api_headers)
            if is_real:
                socketio.emit('BasicInfoGotten', {'framework': 'RD', 'stored-already': False})
            else:
                socketio.emit("API_REQUEST_FAILED", {'framework': 'RD', 'transfer_id': data['name']})  
        else:
            socketio.emit('BasicInfoGotten', {'framework': 'RD', 'stored-already': True})
        

@socketio.on('deleteData')
def deleteData(data):
    print(f"Here is the data: {data}")
    print("In Data Deletion")

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
            print("\n\n\n\n\n\n\nUser Said End Processing\n\n\n\n\n")
            socketio.emit("API_Error", {'text': 'User Ended Processing', 'num-collected': f'{sum(results)} comments analyzed'})
            return

        print("In function")
        
        
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
                print("Benchmark One")
                try:
                    vid_id, vid_next_page_token = yt_functions.get_vid_id_from_playlist(data_row[0], vid_next_page_token, youtube_api_object)
                except googleapiclient.errors.HttpError as e:
                    if int(e.status_code) == 403:
                        print("Exceed Quota")

                        socketio.emit("API_Error", {'text': 'API Quota Exceeded', 'num-collected': f'{sum(results)} comments analyzed'})

                    print(e) 
                    break

                if continue_with_processing == False:
                    break

                if vid_next_page_token == None:
                    print(vid_id)
                    print("Stopping YT process")   
                    socketio.emit("API_Error", {'text': 'No More Videos', 'num-collected': f'{sum(results)} comments analyzed'})
                    break

                while True: #Loop over each comment_thread
                    print("Benchmark 2")
                    try:
                        commentThreads, commentThread_next_page_token = yt_functions.get_comments_from_vid_id(vid_id, commentThread_next_page_token, 100, youtube_api_object) #Make this 100
                        print("Benchmark 2.5 (Collected CommentThreads)")
                    except Exception as e:
                        #This also works if it runs out of comments, because it will go back and use the API to get the vid_id
                        #Then, the API Quota Exceeded error will be caught there!
                        print(e)
                        print("Video Has Disabled Comments")
                        break

                    if data['limit'] != 0 and sum(results) >= data['limit']:
                        print("Reached Limit")
                        continue_with_processing = False
                        break
                    
                    
                        
                    if continue_with_processing == False:
                        print("Stop Signal Reached")
                        break


                    
                    for commentThread in commentThreads['items']:  #Loop over each comment
                        print("Benchmark Three")  
                        try:
                            if continue_with_processing == False:
                                print("Stop Signal Reached")
                                break

                            if data['model-type'] == 'emotions-model':
                                results[inferenceFunctions.emotions_inference(emotions_detector_model_pipeline, yt_functions.clean_str(commentThread['snippet']['topLevelComment']['snippet']['textOriginal']))] += 1

                                socketio.emit('resultsofInference', {'total-processed': sum(results), 
                                    'data1': int(results[0]), 'data2': int(results[1]), 
                                    'data3': int(results[2]), 'data4': int(results[3]),
                                    'data5': int(results[4]), 'data6': int(results[5]),
                                    'data7': int(results[6]), 'num-plots': 7, 'percentage-processed': round((sum(results)/data['limit']) * 100, 1)})
                                
                                
                            
                            elif data['model-type'] == 'toxicity-model':
                                print(results)
                                results[inferenceFunctions.toxicity_inference(binary_toxic_model_pipeline, yt_functions.clean_str(commentThread['snippet']['topLevelComment']['snippet']['textOriginal']))] += 1
                                socketio.emit('resultsofInference', {'total-processed': sum(results), 
                                    'data1': int(results[0]), 'data2': int(results[1]), 
                                        'num-plots': 2, 'percentage-processed': round((sum(results)/data['limit']) * 100, 1)})
                            else:
                                print(results)
                                results[inferenceFunctions.sentiment_classification_inference(neg_neutral_positive_model_pipeline, yt_functions.clean_str(commentThread['snippet']['topLevelComment']['snippet']['textOriginal']))] += 1
                                socketio.emit('resultsofInference', {'total-processed': sum(results), 
                                    'data1': int(results[0]), 'data2': int(results[1]), 'data3': int(results[2]),  
                                        'num-plots': 3, 'percentage-processed': round((sum(results)/data['limit']) * 100, 1)})

                            
                            
                            
                        except Exception as e:
                            print(e)
                            print("Couldn't get comment")
                            pass
                    
                    if commentThread_next_page_token is None:
                        print("Go on to next video")
                        break

                if continue_with_processing == False:
                    break
            
            
                
                #channel_data['data'][database_id]["Stored Comments Date"] = date_time.strftime("%B %d, %Y")
    
        t1 = threading.Thread(target=yt_comment_collector)   
        t1.start()

        t1.join()
        print("Updated Channel Data")

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
                print("Hasn't been processed")
                cursor.execute("INSERT INTO toxicityMeasurerRes VALUES (?, ?, ?, ?, ?)", ('YT', data['key'], results[0], results[1], sum(results)))
            else:
                print(results)
                cursor.execute("UPDATE toxicityMeasurerRes SET toxic = ?, neutral = ?, commentnum = ? WHERE pos = ?", (results[0], results[1], sum(results), data['key']))

        elif data['model-type'] == "sentiment-model":
            cursor.execute("UPDATE yt_channels SET anyProcessed = 1 WHERE pos = ?", (data['key'], ))
            cursor.execute("UPDATE yt_channels SET usedsentimentmodel = 1 WHERE pos = ?", (data['key'], ))

            if has_been_processed[2] == 0:
                print("Hasn't been processed")
                cursor.execute("INSERT INTO sentimentClassifierRes VALUES (?, ?, ?, ?, ?, ?)", ('YT', data['key'], results[0], results[1], results[2], sum(results) ))

            else:
                print(results)
                cursor.execute("UPDATE sentimentClassifierRes SET negative = ?, neutral = ?, positive = ?, commentnum = ? WHERE pos = ?", (results[0], results[1], results[2], sum(results), data['key']))
        
        sqliteConnection.commit()
        sqliteConnection.close()
            

        
        

    elif data['framework'] == 'RD':


        print("Reddit Is being Utilized")

        print(f"This is the data that daddy recieved: {data}")
        

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
                            print("\n\n\n-----------------------------------------\nUser's ended it\n-----------------------------------------\n\n\n")
                            global continue_with_processing
                            continue_with_processing = False
                            socketio.emit("API_Error", {'text': 'User Ended Processing', 'num-collected': f'{sum(results)} comments analyzed'})

                        if continue_with_processing == False:
                            break
                        

                        if len(comments_batch) <= 99 and idx == (len(comments_batch) - 1): 
                            #If this is the final comment in the comment batch
                            #and if the comment batch is less than 100 (meaning that there is no next batch)
                            print("Ending Process")
                            
                            socketio.emit("API_Error", {'text': 'No More Comments', 'num-collected': sum(results)})
                            #socketio.emit('requestsInProgress', {'framework': 'RD', 'name': reddit_data['data'][database_id]['title'], 'done': True, 'num-requests-done': len(text)})       
                            
                            continue_with_processing = False
                            break

                        if sum(results) == data['limit']:
                            print("Limit Has Been Reached")
                            
                            #socketio.emit('requestsInProgress', {'framework': 'RD', 'name': reddit_data['data'][database_id]['title'], 'done': False, 'num-requests-done': len(text)})       
                            
                            continue_with_processing = False
                            break

                        
                        
                        if data['model-type'] == 'emotions-model':
                            results[inferenceFunctions.emotions_inference(emotions_detector_model_pipeline, yt_functions.clean_str(comment))] += 1

                            socketio.emit('resultsofInference', {'total-processed': sum(results), 
                                'data1': int(results[0]), 'data2': int(results[1]), 
                                'data3': int(results[2]), 'data4': int(results[3]),
                                'data5': int(results[4]), 'data6': int(results[5]),
                                'data7': int(results[6]), 'num-plots': 7, 'percentage-processed': round((sum(results)/data['limit']) * 100, 1)})
                                
                                
                            
                        elif data['model-type'] == 'toxicity-model':
                            results[inferenceFunctions.toxicity_inference(binary_toxic_model_pipeline, yt_functions.clean_str(comment))] += 1
                            socketio.emit('resultsofInference', {'total-processed': sum(results), 
                                'data1': int(results[0]), 'data2': int(results[1]), 
                                    'num-plots': 2, 'percentage-processed': round((sum(results)/data['limit']) * 100, 1)})
                        else:
                            results[inferenceFunctions.sentiment_classification_inference(neg_neutral_positive_model_pipeline, yt_functions.clean_str(comment))] += 1
                            socketio.emit('resultsofInference', {'total-processed': sum(results), 
                                'data1': int(results[0]), 'data2': int(results[1]), 'data3': int(results[2]),  
                                    'num-plots': 3, 'percentage-processed': round((sum(results)/data['limit']) * 100, 1)})
                        #socketio.emit('requestsInProgress', {'framework': 'RD', 'name': reddit_data['data'][database_id]['title'], 'total-requests': data['num'], 'num-requests-done': comment_counter, 'done': False})    

                        print(results)

                    if len(kinds) == 0:
                        print("No Comments")
                        #socketio.emit('requestsInProgress', {'framework': 'RD', 'name': reddit_data['data'][database_id]['title'], 'done': True, 'num-requests-done': len(text)})
                        break 

                    fullname = kinds[-1] + '_' + ids[-1]
                    params['after'] = fullname
                    params['count'] = sum(results)

                else:
                    print("\n\nThe processing has been cut off...\n\n")
                    break
        
        t1 = threading.Thread(target=rd_comment_collector)   
        t1.start()

        t1.join()
        print("Updated Forum Data")
        cursor.execute(f"SELECT usedemotionsmodel, usedtoxicitymodel, usedsentimentmodel FROM reddit_data WHERE pos = ?", (data['key']))
        has_been_processed = cursor.fetchone()
        print(has_been_processed)
        
        if data['model-type'] == "emotions-model":
            cursor.execute("UPDATE reddit_data SET anyProcessed = 1 WHERE pos = ?", (data['key'], ))
            cursor.execute("UPDATE reddit_data SET usedemotionsmodel = 1 WHERE pos = ?", (data['key'], ))
            
            if has_been_processed[0] == 0:
                print("Hasn't been processed")
                cursor.execute("INSERT INTO emotionsDetectorRes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", ('RD', data['key'], results[0], results[1], results[2], results[3], results[4], results[5], results[6], sum(results)))
            else:
                print(results)
                cursor.execute("UPDATE emotionsDetectorRes SET anger = ?, fear = ?, disgust = ?, neutral = ?, joy = ?, sadness = ?, surprise = ?, commentnum = ? WHERE pos = ?", (results[0], results[1], results[2], results[3], results[4], results[5], results[6], sum(results), data['key']))
        
        elif data['model-type'] == "toxicity-model":
            cursor.execute("UPDATE reddit_data SET anyProcessed = 1 WHERE pos = ?", (data['key'], ))
            cursor.execute("UPDATE reddit_data SET usedtoxicitymodel = 1 WHERE pos = ?", (data['key'], ))
            
            if has_been_processed[1] == 0:
                print("Hasn't been processed")
                cursor.execute("INSERT INTO toxicityMeasurerRes VALUES (?, ?, ?, ?, ?)", ('RD', data['key'], results[0], results[1], sum(results)))
            else:
                print(results)
                cursor.execute("UPDATE toxicityMeasurerRes SET toxic = ?, neutral = ?, commentnum = ? WHERE pos = ?", (results[0], results[1], sum(results), data['key']))

        elif data['model-type'] == "sentiment-model":
            cursor.execute("UPDATE reddit_data SET anyProcessed = 1 WHERE pos = ?", (data['key'], ))
            cursor.execute("UPDATE reddit_data SET usedsentimentmodel = 1 WHERE pos = ?", (data['key'], ))
            
            if has_been_processed[2] == 0:
                print("Hasn't been processed")
                cursor.execute("INSERT INTO sentimentClassifierRes VALUES (?, ?, ?, ?, ?, ?)", ('RD', data['key'], results[0], results[1], results[2], sum(results)))

            else:
                print(results)
                cursor.execute("UPDATE sentimentClassifierRes SET negative = ?, neutral = ?, positive = ?, commentnum = ? WHERE pos = ?", (results[0], results[1], results[2], sum(results), data['key']))
        
        
        #cursor.execute("UPDATE reddit_data SET inferencedate = ? WHERE pos = ?", (date_time.strftime('%Y-%m-%d'), data['key']))
        
        
        sqliteConnection.commit()
        sqliteConnection.close()
        
       
        
       


@socketio.on("addToDatabase")
def add_to_database(data): 
    print("In Function")
    sqliteConnection = sqlite3.connect(f"{app.config['JSON_DATA_FILES']}/database.db")
    cursor = sqliteConnection.cursor()

    if data['framework'] == 'YT':
        cursor.execute("SELECT pos FROM yt_channels ORDER BY pos DESC LIMIT 1")
        last_id = cursor.fetchone()

        if not last_id:
            new_id = 1
        else:
            new_id = last_id[0] + 1
        
        print("Uploading New Data....\n--------------\n\n")
            
    
        cursor.execute("INSERT INTO yt_channels (pos, title, uploadsid, channelid, usedsentimentmodel, usedtoxicitymodel, usedemotionsmodel, anyprocessed) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (new_id, data['title'], data['upload-id'], data['channel-id'], 0, 0, 0, 0))
        sqliteConnection.commit()
        sqliteConnection.close()
             

    elif data['framework'] == 'RD':
        cursor.execute("SELECT pos FROM reddit_data ORDER BY pos DESC LIMIT 1")
        last_id = cursor.fetchone()
        print("Here's the last row")
        print(last_id)
        
        if not last_id:
            new_id = 1
        else:
            new_id = last_id[0] + 1

        cursor.execute("INSERT INTO reddit_data (pos, title, usedsentimentmodel, usedtoxicitymodel, usedemotionsmodel, anyprocessed) VALUES (?, ?, ?, ?, ?, ?)", (new_id, data['title'], 0, 0, 0, 0))
        sqliteConnection.commit()
        sqliteConnection.close()

      

       
            
   
@socketio.on("connect")
def connect(auth):
    pass


@socketio.on('disconnect') #If the socket disconnects
def disconnect():
    global continue_with_processing
    continue_with_processing = False
    print("\n\n\n\nCLIENT DISCONNECTED\n\n\n")
    

#btn btn-outline-primary btn-lg
if __name__ == '__main__':
    print("\n\n----------------------------\nRunning App")
    print("--------------------\n")
    socketio.run(app, debug=True)