import sqlite3
import os
import shutil

database = 'database.db'

sqliteConnection = sqlite3.connect(database)
cursor = sqliteConnection.cursor()


cursor.execute("""
                CREATE TABLE yt_channels (
                    pos INTEGER,
                    title TEXT,
                    UploadsId TEXT,
                    ChannelId TEXT,
                    usedSentimentModel INTEGER,
                    usedToxicityModel INTEGER,
                    usedEmotionsModel INTEGER,
                    anyProcessed INTEGER


                       
                );           
                """)

cursor.execute("""
               CREATE TABLE reddit_data (
                    pos INTEGER,
                    title TEXT,
                    usedSentimentModel INTEGER,
                    usedToxicityModel INTEGER,
                    usedEmotionsModel INTEGER,
                    anyProcessed INTEGER
                );
               
                """)

cursor.execute(""" 
               CREATE TABLE toxicityMeasurerRes  (
                   type TEXT,
                   pos INTEGER,
                   toxic INTEGER,
                   neutral INTEGER,
                   commentNum INTEGER        
                );
                             
               """
                        
               )

cursor.execute(""" CREATE TABLE emotionsDetectorRes  (
                    type TEXT,
                    pos INTEGER,
                    anger INTEGER,
                    fear INTEGER,
                    disgust INTEGER,
                    neutral INTEGER,
                    joy INTEGER,
                    sadness INTEGER,
                    surprise INTEGER,
                    commentNum INTEGER     
                );
                              
            """                          
               )


cursor.execute("""CREATE TABLE sentimentClassifierRes  (
                    type TEXT,
                    pos INTEGER,
                    negative INTEGER,
                    neutral INTEGER,
                    positive INTEGER,   
                    commentNum INTEGER           
                );""")

sqliteConnection.commit()
sqliteConnection.close()

app_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

if os.path.exists(os.path.join(app_dir, 'sql_data', 'database.db')):
    os.remove(os.path.join(app_dir, 'sql_data', 'database.db'))
    shutil.move(os.path.join(app_dir, 'dev_tools', 'database.db'), os.path.join(app_dir, 'sql_data', 'database.db'))
else:
    shutil.move(os.path.join(app_dir, 'dev_tools', 'database.db'), os.path.join(app_dir, 'sql_data', 'database.db'))