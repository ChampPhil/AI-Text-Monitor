import sys
import os
from threading import Lock, Event, Thread
import threading
import trace
import time

done = False
def test_function():
    counter = 0
    while not done:
        time.sleep(1)
        counter += 1
        print(counter)

threading.Thread(target=test_function).start()
input("Press Enter to Quit")
done = True