from datetime import datetime
from datetime import timedelta
from dateutil import relativedelta
import plotly.express as px
import pandas as pd
import math
import sys
import pytz
import time
from plotly.subplots import make_subplots
from dotenv import dotenv_values

from PyInquirer import prompt
from examples import custom_style_2
from prompt_toolkit.validation import Validator, ValidationError
import caldav
import webbrowser
import subprocess
import util
from gotify import Gotify

def main():
    config = dotenv_values(".env")
    ## We'll try to use the local caldav library, not the system-installed
    sys.path.insert(0, '..')
    sys.path.insert(0, '.')

    local_timezone = pytz.timezone('Europe/Berlin')

    now = datetime.now(local_timezone)
    today=local_timezone.localize(datetime(now.year, now.month, now.day)) #.replace(tzinfo=local_timezone).astimezone(local_timezone)

    #for events
    caldav_url = config["caldav_url"]
    username = config["username"]
    password = config["password"]
    cal=config["cal"]

    #for todos
    caldav_url2 = config["caldav_url2"]
    tasks_url2 = config["tasks_url2"]
    username2 = config["username2"]
    password2 = config["password2"]
    cal2=config["cal2"]
    
    #watcher settings
    present_hosts=config["present_hosts"].split(",")
    presence_stop_delay=int(config["presence_stop_delay"])
    presence_start_delay=int(config["presence_start_delay"])
    gotify_url=config["gotify_url"]
    gotify_token=config["gotify_token"]

    
    client = caldav.DAVClient(url=caldav_url, username=username, password=password)
    my_principal = client.principal()

    client2 = caldav.DAVClient(url=caldav_url2, username=username2, password=password2)
    my_principal2 = client2.principal()
    

    while True:
        calendar = my_principal.calendar(name=cal)
        calendar2 = my_principal2.calendar(name=cal2)
        print("loading tasks...")
        todos=util.get_tasks(calendar2)
        events,C,I=util.find_running(calendar2)
        print(events)
        print(I)
        
        P=util.get_presence(present_hosts)

        if len(I)>0:
            print("one or more tasks are running, checking if person is present on one of the present_hosts")
            present=False
            lastpresent=0
            for p in P:
                if p[0]:
                    present=True
                    lastpresent=max(p[1],lastpresent)
                    break
            #stop task is not present for too long
            if not present and lastpresent+presence_stop_delay*60<time.time():
                print("noone has been present for "+str(presence_stop_delay)+" minutes, stopping tasks (" +str(time.time())+" > "+str(lastpresent+presence_stop_delay*60)+")")
                for i in range(len(I)):
                    util.stop_task(events,I[i])
            
            #stop task if appointment is currently running
            local_timezone = pytz.timezone('Europe/Berlin')
            now = datetime.now(local_timezone)
            today=local_timezone.localize(datetime(now.year, now.month, now.day)) #.replace(tzinfo=local_timezone).astimezone(local_timezone)
            calevents=calendar.date_search(start=today, end=today+relativedelta.relativedelta(days=1), expand=True)
            overlap=False
            for t in calevents:
                T=util.parse_ics(t.data,str(t))
                if T["dtstart"]<=now and T["dtend"]>=now:
                    overlap=True
            if overlap:
                print("there is an overlapping event, stopping tasks")
                for i in I:
                    util.stop_task(events,I[i])
        else:
            #no task is running
            present=False
            lastpresent=0
            for p in P:
                if p[0]:
                    present=True
                    lastpresent=max(p[1],lastpresent)
                    break
            if lastpresent+presence_start_delay*60<time.time():
                print("someone has been present for at least "+str(presence_start_delay)+" minutes but no task is running, sending notification")
                gotify = Gotify(base_url=gotify_url,app_token=gotify_token)
                gotify.create_message("NO TASK IS RUNNING!",title="personalscheduler",priority=10)


        time.sleep(30)












if __name__ == "__main__":
    main()
