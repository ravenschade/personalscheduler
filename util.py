import datetime
import dateutil
import json
import caldav
import pytz
import time

def serialize_datetime(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    raise TypeError("Type not serializable")

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
                        ret[t["name"].lower()]=datetime.datetime.strptime(s,"%Y%m%dT%H%M%S").replace(tzinfo=pytz.utc).astimezone(local_timezone)
                    elif s.find("T")>=0 and s.find("Z")>0:
                        ret[t["name"].lower()]=datetime.datetime.strptime(s,"%Y%m%dT%H%M%SZ").replace(tzinfo=pytz.utc).astimezone(local_timezone)
                    elif len(s)==8:
                        ret[t["name"].lower()]=datetime.datetime.strptime(s,"%Y%m%d").replace(tzinfo=pytz.utc).astimezone(local_timezone)
                        if t["name"].lower()=="due":
                            ret["due"]=ret["due"]+dateutil.relativedelta.relativedelta(hours=23,minutes=59)
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
            ret["due"]=ret["dtstart"]+dateutil.relativedelta.relativedelta(days=1)
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

def caldav_to_datetime(s):
    #2023-03-04T00:59:00+01:00
    return datetime.datetime.strptime(s, '%Y-%m-%dT%h:%m:%s%z')
