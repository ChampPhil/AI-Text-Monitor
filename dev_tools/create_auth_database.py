import sqlite3
import os
import shutil

database = 'auth_database.db'

sqliteConnection = sqlite3.connect(database)
cursor = sqliteConnection.cursor()


cursor.execute("""
                CREATE TABLE user_data (
                    ytkey TEXT,
                    clientid TEXT,
                    secrettoken TEXT,
                    redditusername TEXT,
                    redditpassword TEXT,
                    defaultsite TEXT              
                );           
                """)

sqliteConnection.commit()
sqliteConnection.close()

app_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

if os.path.exists(os.path.join(app_dir, 'sql_data', 'auth_database.db')):
    os.remove(os.path.join(app_dir, 'sql_data', 'auth_database.db'))
    shutil.move(os.path.join(app_dir, 'dev_tools', 'auth_database.db'), os.path.join(app_dir, 'sql_data', 'auth_database.db'))
else:
    shutil.move(os.path.join(app_dir, 'dev_tools', 'auth_database.db'), os.path.join(app_dir, 'sql_data', 'auth_database.db'))