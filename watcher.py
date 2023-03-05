import datetime
import dateutil
import math
import sys
import pytz
import time
from dotenv import dotenv_values

import caldav
import webbrowser
import util
from gotify import Gotify

import taskcollection
import subprocess

def main():
    config = dotenv_values(".env")
    ## We'll try to use the local caldav library, not the system-installed
    sys.path.insert(0, '..')
    sys.path.insert(0, '.')

    local_timezone = pytz.timezone('Europe/Berlin')

    #for events
    caldav_url = config["caldav_url"]
    username = config["username"]
    password = config["password"]
    cal=config["cal"]

    #watcher settings
    present_hosts=config["present_hosts"].split(",")
    presence_stop_delay=int(config["presence_stop_delay"])
    presence_start_delay=int(config["presence_start_delay"])
    gotify_url=config["gotify_url"]
    gotify_token=config["gotify_token"]
    
    client = caldav.DAVClient(url=caldav_url, username=username, password=password)
    my_principal = client.principal()

    while True:
        P=util.get_presence(present_hosts)
        col=taskcollection.taskcollection("data")
        calendar = my_principal.calendar(name=cal)
        t=col.check_running()

        if not (t is None):
            print(" a task is running, checking if person is present on one of the present_hosts")
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
                for i in I:
                    col.stop_all_tasks()
            
            #stop task if appointment is currently running
            local_timezone = pytz.timezone('Europe/Berlin')
            now = datetime.datetime.now(local_timezone)
            today=local_timezone.localize(datetime.datetime(now.year, now.month, now.day)) #.replace(tzinfo=local_timezone).astimezone(local_timezone)
            calevents=calendar.date_search(start=today, end=today+dateutil.relativedelta.relativedelta(days=1), expand=True)
            overlap=False
            for t in calevents:
                T=util.parse_ics(t.data,str(t))
                if T["dtstart"]<=now and T["dtend"]>=now:
                    print("overlapping event=",T)
                    overlap=True
            if overlap:
                print("there is an overlapping event, stopping tasks")
                for i in I:
                    col.stop_all_tasks()
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

        time.sleep(60)












if __name__ == "__main__":
    main()
