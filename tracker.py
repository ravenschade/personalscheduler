
from datetime import datetime
from datetime import timedelta
from dateutil import relativedelta
import plotly.express as px
import pandas as pd
import math
import sys
import pytz
from plotly.subplots import make_subplots
from dotenv import dotenv_values

from PyInquirer import prompt
from examples import custom_style_2
from prompt_toolkit.validation import Validator, ValidationError
import caldav
import webbrowser
import util

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

    caldav_url2 = config["caldav_url2"]
    tasks_url2 = config["tasks_url2"]
    username2 = config["username2"]
    password2 = config["password2"]
    cal2=config["cal2"]

    print("loading tasks...")
#    client = caldav.DAVClient(url=caldav_url, username=username, password=password)
#    my_principal = client.principal()
    #calendars = my_principal.calendars()

    client2 = caldav.DAVClient(url=caldav_url2, username=username2, password=password2)
    my_principal2 = client2.principal()
    #calendars2 = my_principal2.calendars()

#    calendar = my_principal.calendar(name=cal)
    calendar2 = my_principal2.calendar(name=cal2)

    while True:
        todos=util.get_tasks(calendar2)
        
        questions = [{'type': 'list','name': 'user_option','message': 'Welcome to the time tracker','choices': ["start task","stop task","update task list"]}]
        answers = prompt(questions, style=custom_style_2)
        if answers.get("user_option") == "start task":
            events,C,I=util.find_running(calendar2)
            if len(C)>0:
                print("some tasks are running, stopping them")
                for i in I:
                    utilstop_task(events,i)
            C=util.build_todo_list(todos)

            #search for string
            filterstr=input("search string:\n")
            if filterstr!="":
                C=util.filter_todo_list(C,filterstr)

            questions = [{'type': 'list','name': 'user_option','message': 'Choose which task to start','choices': C}]
            answers = prompt(questions, style=custom_style_2)
            si=answers.get("user_option").split("[")
            I=int(si[len(si)-1].split("]")[0])
            
            my_event = calendar2.save_event(
                dtstart=datetime.now(),
                dtend=datetime.now(),
                summary=todos[I]["summary"],
                location=tasks_url2+"/#/calendars/"+cal2+"/tasks/"+todos[I]["uid"]+".ics",
                description="started\nNotes:"
            )
            print(my_event.url)
            #get descriptions of parent tasks
            desc=todos[I]["description"]
            print(todos[I])
            parents=[]
            J=I
            for i in range(10):
                if len(todos[J]["related-to2"])!=0:
                    J=todos[J]["related-to2"][0]
                    parents.append(J)
            print(parents)
            desc=todos[I]["description"]
            for p in parents:
                desc=desc+" "+todos[p]["description"]

            util.taskactions(desc)
        elif answers.get("user_option") == "stop task":
            #find started but not stopped tasks
            events,C,I=util.find_running(calendar2)
            if len(C)>0:
                questions = [{'type': 'list','name': 'user_option','message': 'Welcome to the time tracker','choices': C}]
                answers = prompt(questions, style=custom_style_2)
                si=answers.get("user_option").split("[")
                I=int(si[len(si)-1].split("]")[0])
                stop_task(events,I)
        elif answers.get("user_option") == "update task list":
            questions = [{'type': 'list','name': 'user_option','message': 'Welcome to the time tracker','choices': ["start task","stop task","update task list"]}]
            answers = prompt(questions, style=custom_style_2)
if __name__ == "__main__":
    main()
