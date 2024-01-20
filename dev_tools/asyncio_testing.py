import sys
import os

app_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
database_path = os.path.join(app_dir, 'sql_data', 'database.db')
print(database_path)
sys.exit()


from flask import Flask, render_template, send_from_directory, request, session, redirect, url_for, flash, copy_current_request_context
from flask_socketio import join_room, leave_room, send, SocketIO
import numpy as np
import googleapiclient
import reddit_functions




from threading import Lock, Event, Thread
import threading
import trace
import web_app_js.yt_functions as yt_functions
import os
import json
import datetime
import inferenceFunctions
import math
import time
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline

binary_toxic_model_pipeline = pipeline('text-classification', model=f"s-nlp/roberta_toxicity_classifier")
neg_neutral_positive_model_pipeline = pipeline('sentiment-analysis', model=f"cardiffnlp/twitter-roberta-base-sentiment")
emotions_detector_model_pipeline = pipeline('text-classification', model=f"j-hartmann/emotion-english-distilroberta-base")

binary_toxic_model_pipeline_return_all_scores = pipeline('text-classification', model=f"s-nlp/roberta_toxicity_classifier", return_all_scores=True)
neg_neutral_positive_model_pipeline_return_all_scores = pipeline('sentiment-analysis', model=f"cardiffnlp/twitter-roberta-base-sentiment", return_all_scores=True)
emotions_detector_model_pipeline_return_all_scores = pipeline('text-classification', model=f"j-hartmann/emotion-english-distilroberta-base", return_all_scores=True)

class textProcessing(threading.Thread):
  def __init__(self, *args, **keywords):
    threading.Thread.__init__(self, *args, **keywords)
    self.killed = False
 
  def start(self):
    self.__run_backup = self.run
    self.run = self.__run      
    threading.Thread.start(self)
 
  def __run(self):
    sys.settrace(self.globaltrace)
    self.__run_backup()
    self.run = self.__run_backup
 
  def globaltrace(self, frame, event, arg):
    if event == 'call':
      return self.localtrace
    else:
      return None
 
  def localtrace(self, frame, event, arg):
    if self.killed:
      if event == 'line':
        raise SystemExit()
    return self.localtrace
 
  def kill(self):
    self.killed = True
 
def func():
  while True:
    pass

start_loading = time.time()
t1 = textProcessing(target = func)
end_loading = time.time()
print(end_loading - start_loading)
t1.start()
time.sleep(5)
t1.kill()
t1.join()
if not t1.is_alive():
  print('thread killed')