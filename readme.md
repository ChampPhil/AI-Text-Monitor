**Install the requirements.txt to run this project**

The core idea of this project is an AI Text Monitor.

To explain, this project leverages multiple state of the art, pretained neural networks 
via Hugging Face Transformers, an open source network for deep learning. This project presents
these models with a clean, sleek front-end LOCAL website using Flask (a python library designed to make easy web applications)
HTML and Jinja2 (a web template engine for Python), hundreds of lines of Javascript code, SQL Databases, and Python itself.


The AI Text Monitor allows for the user to process an indivual piece of text and analyze 

1. Whether it's "toxic" or "non-toxic"
2. Whether it's negative, neutral, or positive
3. Whether its Passionate/Angry, Concerned/Fearful, Disgusted, Neutral, Joyful, Sad, or Surprised

On the other hand, the AI Text Monitor also allows the user to store a particular 
YouTube channel or Reddit Forum and then analyze X num of comments from that channel/forum.
The percentages of this analysis (e.g., 10% toxic, 90% non-toxic) are stored in a back-end database 
and can be viewed at will.


----------------------------------------------------------------------------------------------------------

**Rules/Things to Take Note Of**



1. The YouTube API/Reddit API is inconsistent, so, on occassion, the AI Text Monitor cannot analyze a certain channel/forum
2. Whenever a client disconnects from the server, inference of YouTube/Reddit comments is cancelled server-wide.
3. Don't use more than one client at any given time - this can slow down resources and create unexpected errors. 
    - The server has measures in place to prevent multi-client usage
        - If CTRL-C is used to end the program, all tabs of the project will be redirected to either 'https://google.com' or 'https://bing.com'
        - If app.py is terminated using the 'End Data Inference' button, will be redirected to either 'https://google.com' or 'https://bing.com'
        - If there is more than one client, the server will prompt you to close all other clients 
        
4. If (after a client disconnects) there are no more clients, the server will shut down on its own. 
5. After adding/deleting/running inference on a YT Channel or Reddit Forum, you have to reload the page for the changes to be visible.
6. Before running this project, make sure sites are allowed to read/use cookies in your chosen browser. 
----------------------------------------------------------------------------------------------------------------------

**Before Running The Project**



https://www.howtogeek.com/732439/how-to-allow-pop-ups-in-microsoft-edge/







