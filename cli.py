
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

def parse_ics(t):
    local_timezone = pytz.timezone('Europe/Berlin')
    ret=dict()
    T=t.splitlines()
    buf=""
    token=[{"name":"CATEGORIES","type":"commasep"},{"name":"DESCRIPTION","type":"string"},{"name":"PRIORITY","type":"int"},{"name":"SUMMARY","type":"string"},{"name":"DTSTART","type":"date"},{"name":"DTEND","type":"date"},{"name":"DUE","type":"date"},{"name":"STATUS","type":"string"},{"name":"PERCENT-COMPLETE","type":"int",},{"name":"TRANSP","type":"transparency"},{"name":"RELATED-TO","type":"string"},{"name":"UID","type":"string"}]

    for t in token:
        sec=False
        for i in range(len(T)):
            if not sec and (T[i].startswith("BEGIN:VTODO") or T[i].startswith("BEGIN:VEVENT")):
                sec=True
                continue
            if not sec:
                continue
            found=False
            if T[i].startswith(t["name"]):
                #build full string
                s=T[i]
                for j in range(i+1,len(T)):
                    if T[j][0]==" ":
                        s=s+T[j][1:]
                    else:
                        break
                s=s[s.find(":")+1:]
                if t["type"]=="commasep":
                    ret[t["name"].lower()]=s.split(",")
                elif t["type"]=="string":
                    ret[t["name"].lower()]=s
                elif t["type"]=="int":
                    ret[t["name"].lower()]=int(s)
                elif t["type"]=="transparency":
                    if s=="TRANSPARENT":
                        ret[t["name"].lower()]=True
                    else:
                        ret[t["name"].lower()]=False
                elif t["type"]=="date":
                    if s.find("T")>=0 and s.find("Z")<0:
                        ret[t["name"].lower()]=datetime.strptime(s,"%Y%m%dT%H%M%S").replace(tzinfo=pytz.utc).astimezone(local_timezone)
                    elif s.find("T")>=0 and s.find("Z")>0:
                        ret[t["name"].lower()]=datetime.strptime(s,"%Y%m%dT%H%M%SZ").replace(tzinfo=pytz.utc).astimezone(local_timezone)
                    elif len(s)==8:
                        ret[t["name"].lower()]=datetime.strptime(s,"%Y%m%d").replace(tzinfo=pytz.utc).astimezone(local_timezone)
                        if t["name"].lower()=="due":
                            ret["due"]=ret["due"]+relativedelta.relativedelta(hours=23,minutes=59)
                    else:
                        raise RuntimeError("unknown time format "+s)
                found=True 
                break
            if not found:
                if t["type"]=="commasep":
                    ret[t["name"].lower()]=[]
                elif t["type"]=="string":
                    ret[t["name"].lower()]=""
                elif t["type"]=="int":
                    ret[t["name"].lower()]=0
                elif t["type"]=="transparency":
                    ret[t["name"].lower()]=False
                elif t["type"]=="date":
                    ret[t["name"].lower()]=None
    if ret["due"] is not None and ret["dtstart"] is not None:
        if ret["due"]==ret["dtstart"]:
            ret["due"]=ret["dtstart"]+relativedelta.relativedelta(days=1)
    if ret["priority"]==0:
        ret["priority"]=10
    ret["depends-on"]=[]
    ret["related-to2"]=[]
    if len(ret["categories"])==0:
        ret["categories"]=["not defined"]

    #get estimated duration from description field
    if ret["description"].find("DURATION=")==0:
        try:
            ret["duration"]=float(ret["description"].split("\\n")[0].split("=")[1])
        except:
            print(ret)
            raise RuntimeError("Duration not parseable")
        ret["description"]=" ".join(ret["description"].split("\\n")[1:])
    else:
        ret["duration"]=None

    

    return ret

def get_tasks(calendar2):
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
    return todos

def build_todo_list(todos):
    L=[]
    for i in range(len(todos)):
        if len(todos[i]["related-to2"])==0:
            L.append(todos[i]["summary"]+" ["+str(i)+"]")
            for j in todos[i]["depends-on"]:
                L.append("     "+todos[j]["summary"]+" ["+str(j)+"]")
    return L

def find_running(calendar2):
    events=calendar2.date_search(start=datetime.today()-timedelta(days=7),end=datetime.today()+timedelta(days=1),expand=True)
    i=0
    C=[]
    I=[]
    for e in events:
        E=parse_ics(e.data)
        if E["description"].startswith("started"):
            C.append(E["summary"]+": started at "+str(E["dtstart"])+" ["+str(i)+"]")
            I.append(i)
        i=i+1
    return events,C,I

def stop_task(events,I):
    print("stopping: ",events[I].vobject_instance.vevent.summary.value)
    events[I].vobject_instance.vevent.description.value = "\n".join(events[I].vobject_instance.vevent.description.value.split("\n")[1:])
    events[I].vobject_instance.vevent.dtend.value = datetime.now()
    print(events[I].save())

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
        todos=get_tasks(calendar2)
        
        questions = [{'type': 'list','name': 'user_option','message': 'Welcome to the time tracker','choices': ["start task","stop task","update task list"]}]
        answers = prompt(questions, style=custom_style_2)
        if answers.get("user_option") == "start task":
            events,C,I=find_running(calendar2)
            if len(C)>0:
                print("some tasks are running, stopping them")
                for i in I:
                    stop_task(events,i)
            C=build_todo_list(todos)

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
        elif answers.get("user_option") == "stop task":
            #find started but not stopped tasks
            events,C,I=find_running(calendar2)
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
