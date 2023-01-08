
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

def parse_ics(t,url=""):
    local_timezone = pytz.timezone('Europe/Berlin')
    ret=dict()
    T=t.splitlines()
    buf=""
    token=[{"name":"CATEGORIES","type":"commasep"},{"name":"DESCRIPTION","type":"string"},{"name":"PRIORITY","type":"int"},{"name":"SUMMARY","type":"string"},{"name":"DTSTART","type":"date"},{"name":"DTEND","type":"date"},{"name":"DUE","type":"date"},{"name":"STATUS","type":"string"},{"name":"PERCENT-COMPLETE","type":"int",},{"name":"TRANSP","type":"transparency"},{"name":"RELATED-TO","type":"string"},{"name":"UID","type":"string"}]

    ret["url"]=url
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
        T=parse_ics(t.data,str(t).split()[1])
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
    
def get_presence(hosts):
    s=[]
    for h in hosts:
        cmd="ssh "+h+" \"tail -n 1 ~/present\""
        result = subprocess.run(cmd, stdout=subprocess.PIPE,shell=True)
        o=result.stdout.decode()
        if o.find("true")>=0:
            s.append([True,int(o.split()[0])])
        if o.find("false")>=0:
            s.append([False,int(o.split()[0])])
    return s

def stop_task(events,I):
    print("stopping: ",events[I].vobject_instance.vevent.summary.value)
    events[I].vobject_instance.vevent.description.value = "\n".join(events[I].vobject_instance.vevent.description.value.split("\n")[1:])
    events[I].vobject_instance.vevent.dtend.value = datetime.now()
    print(events[I].save())

def taskactions(desc):
    token={"URL":"url","GIT":"url","CONFL":"url","NC":"url","OVERLEAF":"url"}
    urls=[]
    for f in sorted(desc.split()):
        if len(f.split("="))==2:
            if f.split("=")[0] in token:
                if token[f.split("=")[0]]=="url":
                    urls.append(f.split("=")[1])
    print(urls)
    for i in range(len(urls)):
        if i==0:
            webbrowser.get('chromium').open_new(urls[i])
        else:
            webbrowser.get('chromium').open_new_tab(urls[i])

R=[]
def get_related(i,todos,level):
    global R
    if len(todos[i]["depends-on"])==0:
        return
    for j in range(len(todos)):
#        print(i,j,todos[j]["related-to2"])
        if i in todos[j]["related-to2"]:
            s=""
            for l in range(level):
                s=s+"    "
            R.append(s+todos[j]["summary"]+" ["+str(j)+"]")
            get_related(j,todos,level+1)

def build_todo_list(todos):
    global R
    R=[]
    for i in range(len(todos)):
        if len(todos[i]["related-to2"])==0:
            R.append(todos[i]["summary"]+" ["+str(i)+"]")
            get_related(i,todos,1)
    return R

def filter_todo_list(L,filterstr):
    F=[]
    #only filter leafs
    print(L)
    for k in L:
        if k.lower().find(filterstr.lower())>=0:
            F.append(k)
    return F

