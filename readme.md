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
The percentages of this analyze (e.g., 10% toxic, 90% non-toxic) are stored in a back-end database 
and can be viewed at will.


----------------------------------------------------------------------------------------------------------

**Rules/Things to Take Note Of**

1. Only have one client (or one tab) of this project open at a time
2. The YouTube API/Reddit API is inconsistent, so, on occassion, the AI Text Monitor cannot analyze a certain channel/forum


----------------------------------------------------------------------------------------------------------------------

Detailed Breakdown of Each Page:



