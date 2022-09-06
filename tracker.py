from datetime import datetime
from dateutil import relativedelta
import plotly.express as px
import pandas as pd
import math
import sys
import pytz
from plotly.subplots import make_subplots
from dotenv import dotenv_values

config = dotenv_values(".env")

## We'll try to use the local caldav library, not the system-installed
sys.path.insert(0, '..')
sys.path.insert(0, '.')

import caldav

local_timezone = pytz.timezone('Europe/Berlin')

now = datetime.now(local_timezone)
today=local_timezone.localize(datetime(now.year, now.month, now.day)) #.replace(tzinfo=local_timezone).astimezone(local_timezone)

#for events
caldav_url = config["caldav_url"]
username = config["username"]
password = config["password"]
cal=config["cal"]

caldav_url2 = config["caldav_url2"]
tasks_url2 = config["tasks_url2"]
username2 = config["username2"]
password2 = config["password2"]
cal2=config["cal2"]

#for s in scheduling_windows:
#    print(s)




client = caldav.DAVClient(url=caldav_url, username=username, password=password)
my_principal = client.principal()
calendars = my_principal.calendars()

client2 = caldav.DAVClient(url=caldav_url2, username=username2, password=password2)
my_principal2 = client2.principal()
calendars2 = my_principal2.calendars()


calendar = my_principal.calendar(name=cal)
calendar2 = my_principal2.calendar(name=cal2)

#try to find task in todos

todos=[]
for t in calendar2.todos():
    T=parse_ics(t.data)
    todos.append(T)

#invert relations from related-to to depends-on
for it in range(len(todos)):
    if "related-to" in todos[it]:
        if todos[it]["related-to"]!=None:
            for it2 in range(len(todos)):
                if todos[it2]["uid"]==todos[it]["related-to"]:
                    todos[it2]["depends-on"].append(it)
        if todos[it]["related-to"]!=None:
            for it2 in range(len(todos)):
                if todos[it2]["uid"]==todos[it]["related-to"]:
                    todos[it]["related-to2"].append(it2)

for it in range(len(todos)):
    if len(todos[it]["related-to2"])==0:
        print(it,todos[it]) #["summary"])
        for r in todos[it]["depends-on"]:
            print("    ",r,todos[r]["summary"])


I=75

my_event = calendar2.save_event(
    dtstart=datetime.now(),
    dtend=datetime.now(),
    summary=todos[I]["summary"],
    location=" "+tasks_url2+"/#/calendars/"+cal2+"/tasks/"+todos[I]["uid"]+".ics",
    description="Notes:"
)
print(my_event.url)

