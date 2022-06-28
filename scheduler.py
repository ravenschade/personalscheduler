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
username2 = config["username2"]
password2 = config["password2"]
cal2=config["cal2"]

timeslices=int(config["timeslice"])
startofwork=int(config["startofwork"])
endofwork=int(config["endofwork"])
scheduledays=int(config["scheduledays"])

workdays=[0,1,2,3,4]

start=math.floor((now.hour*60 + now.minute)/timeslices)*timeslices

scheduling_windows=[] #{"tstart":start,"tend":17*60,"days":[1,2,3,4,5]}]

if now>=today+relativedelta.relativedelta(hours=endofwork,minutes=00):
    today=today+relativedelta.relativedelta(days=1)
#print(today,round(now.minute/timeslices)*timeslices)    

for i in range(scheduledays):
    start=max(today+relativedelta.relativedelta(days=i)+relativedelta.relativedelta(hours=startofwork,minutes=00),local_timezone.localize(datetime(now.year, now.month, now.day,now.hour)+relativedelta.relativedelta(minutes=round(now.minute/timeslices)*timeslices)))
    end=today+relativedelta.relativedelta(days=i)+relativedelta.relativedelta(hours=endofwork,minutes=00)
    if start.weekday() in workdays:
        scheduling_windows.append({"tstart":start,"tend":end})

#for s in scheduling_windows:
#    print(s)

def parse_ics(t):
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



client = caldav.DAVClient(url=caldav_url, username=username, password=password)
my_principal = client.principal()
calendars = my_principal.calendars()

client2 = caldav.DAVClient(url=caldav_url2, username=username2, password=password2)
my_principal2 = client2.principal()
calendars2 = my_principal2.calendars()


calendar = my_principal.calendar(name=cal)
#print(calendar.get_supported_components())
calendar2 = my_principal2.calendar(name=cal2)
#print(calendar2.get_supported_components())

allocated_slices=[]
blocked=[]
for d in range(scheduledays):
    events=calendar.date_search(start=today+relativedelta.relativedelta(days=d), end=today+relativedelta.relativedelta(days=d+1), expand=True)
    for t in events:
        T=parse_ics(t.data)
        #print("event")
        #print(t.data)
        #print(T)

        #if T["dtend"]>now:
        #print(T["dtstart"],T["dtend"],T["summary"],T["transp"])
        if not T["transp"]:
            blocked.append({"dtstart":T["dtstart"],"dtend":T["dtend"],"summary":T["summary"]})
            allocated_slices.append(dict(Task=T["summary"],Start=T["dtstart"],Finish=T["dtend"],Resource="Blocked",dummy=0.1))
#print("blocked=",blocked)

todos=[]
stop=False
for t in calendar2.todos():
    T=parse_ics(t.data)
    #print(t.data)
    #for l in t.data.splitlines():
    #    if l.startswith("RELATED-TO:"):
    #        T["related-to"]=l.split(":")[1]
    #    if l.startswith("UID:"):
    #        T["uid"]=l.split(":")[1]

    if T["due"] is not None:
        if T["duration"] is None:
            print("WARNING: task "+T["summary"]+" with due date but no duration")
            stop=True
    if T["duration"] is not None:
        todos.append(T)
if stop:
    raise RuntimeError("see previous warnings")

#invert relations from related-to to depends-on
for it in range(len(todos)):
    try:
        todos[it]["related-to"]
    except:
        continue
    if todos[it]["related-to"]!=None:
        for it2 in range(len(todos)):
            if todos[it2]["uid"]==todos[it]["related-to"]:
                todos[it2]["depends-on"].append(it)

#recursively resolve dependencies
while True:
    found=False
    for it in range(len(todos)):
        for i in todos[it]["depends-on"]:
            for j in todos[i]["depends-on"]:
                if j not in todos[it]["depends-on"]:
                    todos[it]["depends-on"].append(j)
                    #print(it,"depends on",j)
                    found=True   
                    break
            if found:
                break
        if found:
            break
    if not found:
        break

#prepone due dates of dependencies to due date of job
while True:
    found=False
    for it in range(len(todos)):
        if todos[it]["due"] is None:
            continue
        for i in todos[it]["depends-on"]:
            if todos[i]["due"] is None:
                todos[i]["due"]=todos[it]["due"]
                print("setting due of",i,"to due of",it)
                found=True
                break
            if todos[i]["due"]>todos[it]["due"]:
                todos[i]["due"]=todos[it]["due"]
                print("setting due of",i,"to due of",it)
                found=True
                break
        if found:
            break
    if not found:
        break

for it in range(len(todos)):
    print(it,todos[it])



#schedule tasks
#generate available time slices
all_slices=[]
for w in scheduling_windows:
    t0=w["tstart"]
    t1=t0+relativedelta.relativedelta(minutes=timeslices)

    while t1<=w["tend"]-relativedelta.relativedelta(minutes=timeslices): 
        t1=t0+relativedelta.relativedelta(minutes=timeslices)
        all_slices.append({"start":t0,"end":t1,"used":False})
        t0=t1


#print("number of all_slices=",len(all_slices))


#exclude slices that are blocked by events
slices=[]
for s in all_slices:
    ov=False
    ovb=None
    for b in blocked:
        if s["start"]==b["dtstart"]:
            ov=True
            ovb=b
        if s["end"]==b["dtend"]:
            ov=True
            ovb=b

        if s["start"]<b["dtstart"] and s["end"]>b["dtstart"]:
            ov=True
            ovb=b
        if s["start"]>b["dtstart"] and s["end"]<b["dtend"]:
            ov=True
            ovb=b
        if s["start"]<b["dtend"] and s["end"]>b["dtend"]:
            ov=True
            ovb=b

    if not ov:
        slices.append(s)
#    else:
#        print("Overlap ",s,ovb)


#print("number of slices=",len(slices))
#for s in slices:
#    print(s)


#test feasibility of schedule by assigning slices to todos just before their due date
#find possible slices for each todo
for it in range(len(todos)):
    todos[it]["slices"]=set()
    todos[it]["to_be_scheduled"]=True
    todos[it]["is_scheduled"]=False
    todos[it]["scheduled_slices"]=0
    #go trough slices
    for i in range(len(slices)):
        possible=True
        if todos[it]["dtstart"] is not None:
            if todos[it]["dtstart"]>slices[i]["start"]:
                possible=False
        if todos[it]["due"] is not None:
            if todos[it]["due"]<slices[i]["end"]:
                possible=False
        if possible:
            todos[it]["slices"].add(i)
    #compute number of needed slices for todo
    todos[it]["needed_slices"]=math.ceil(todos[it]["duration"]/100.0*(100.0-todos[it]["percent-complete"])*60.0/timeslices)
    if todos[it]["needed_slices"]==0:
        todos[it]["needed_slices"]=1
    todos[it]["etodos"]=[] #expanded todos, i.e. single sloted-todos

#    print("summary=",todos[it]["summary"],"(",it,")")
#    print("needed slices=",todos[it]["needed_slices"])
#    print("slices=",todos[it]["slices"])

#exclude tasks with due dates beyond the scheduling window
for it in range(len(todos)):
    if todos[it]["due"] is not None and todos[it]["due"]>slices[len(slices)-1]["end"]:
        todos[it]["to_be_scheduled"]=False
        #print("not scheduling",todos[it]["summary"],"(",it,") because due (",str(todos[it]["due"]),") after end of scheduling window.")

#check basic necessary conditions
#check for solution for individual tasks
for it in range(len(todos)):
    if todos[it]["to_be_scheduled"]:
        if todos[it]["needed_slices"]>len(todos[it]["slices"]):
            raise RuntimeError("there are not enough slices available for "+todos[it]["summary"])

#priority-based scheduling

#schedule all events that only have one possible set of slices
for it in range(len(todos)):
    if todos[it]["to_be_scheduled"]:
        if todos[it]["needed_slices"]==len(todos[it]["slices"]):
            todos[it]["scheduled_slices"]=todos[it]["slices"]
            todos[it]["is_scheduled"]=True
            for s in todos[it]["slices"]:
                slices[s]["used"]=True
                slices[s]["task"]=it
            print("schedule",todos[it]["summary"],"(",it,") in slices", " ".join(todos[it]["slices"]))



#schedule: earliest deadline first

for si in range(len(slices)):
    if not slices[si]["used"]:
        #print("scheduling for slice",si,slices[si])
        #find list of viable tasks
        viable_jobs=[]
        for it in range(len(todos)):
            viable=todos[it]["to_be_scheduled"] and not todos[it]["is_scheduled"]
            if si not in todos[it]["slices"]:
                viable=False
#                print(it,"can't be scheduled because start time not reached yet")

            for i in todos[it]["depends-on"]:
                if todos[i]["to_be_scheduled"] and not todos[i]["is_scheduled"]:
                    viable=False
#                    print(it,"can't be scheduled because dependency",i,"is not yet scheduled")
                    break
            if viable:
                    viable_jobs.append(it)

#        print("viable jobs=",viable_jobs)
        if len(viable_jobs)>0:
            #find job with closest deadline
            d=0
            dj=-1
            dp=-1
            #find job with a due date
            for it in viable_jobs:
                if todos[it]["due"] is not None:
                    d=todos[it]["due"]
                    dj=it
                    break
            #compare with other jobs with deadline
            for it in viable_jobs:
                #print(it,todos[it])
                if todos[it]["due"] is not None:
                    if todos[it]["due"]<d:
                        dj=it
                        d=todos[it]["due"]
                        dp=int(todos[it]["priority"])
                    if todos[it]["due"]==d and int(todos[it]["priority"])>dp:
                        dj=it
                        d=todos[it]["due"]
                        dp=int(todos[it]["priority"])
            #what if no job with a deadline was found
            if dj==-1:
                #find job with highest priority
                d=int(todos[viable_jobs[0]]["priority"])
                dj=viable_jobs[0]
                for it in viable_jobs:
                    if int(todos[it]["priority"])>d:
                        dj=it
                        d=int(todos[it]["priority"])
                #print("highest priority:",dj,todos[dj]["priority"])
#            else:
#                print("closest deadline:",dj,todos[dj]["due"])
            #print("scheduling task",dj,todos[dj]["summary"],"in slot",si,slices[si])
            todos[dj]["scheduled_slices"]=todos[dj]["scheduled_slices"]+1
            if todos[dj]["scheduled_slices"]==todos[dj]["needed_slices"]:
                todos[dj]["is_scheduled"]=True
            slices[si]["used"]=True
            slices[si]["task"]=dj
            allocated_slices.append(dict(Task=todos[dj]["summary"],Start=slices[si]["start"],Finish=slices[si]["end"],Resource=" ".join(todos[dj]["categories"]),dummy=0))
        else:
            print("no viable jobs in this slot")
            allocated_slices.append(dict(Task="idle",Start=slices[si]["start"],Finish=slices[si]["end"],Resource="idle",dummy=0))

#check schedule: check if all deadlines could be accomodated
for it in range(len(todos)):
    if todos[it]["due"] is not None:
        if todos[it]["due"]<=today+relativedelta.relativedelta(days=scheduledays+1):
            if not  todos[it]["is_scheduled"]:
                print("Plan BISHER:")
                for si in range(20):
                    print(slices[si]["start"],"-",slices[si]["end"],":",todos[slices[si]["task"]]["summary"])
                raise RuntimeError("Error: Task "+str(it)+" "+todos[it]["summary"]+" couldn't be scheduled before deadline "+str(todos[it]["due"]))


print("Plan:")
for si in range(30):
    print(slices[si]["start"],"-",slices[si]["end"],":",todos[slices[si]["task"]]["summary"])

start=today
end=today+relativedelta.relativedelta(days=14) #scheduledays)

asl=[]
for a in allocated_slices:
    if a["Start"]>=start and a["Finish"]<=end:
        a["Task"]=a["Task"]+" "+str(local_timezone.localize(datetime(a["Start"].year, a["Start"].month, a["Start"].day)))
        a["dummy"]=a["dummy"]+(local_timezone.localize(datetime(a["Start"].year, a["Start"].month, a["Start"].day))-today).days
        a["Start"]=local_timezone.localize(datetime(today.year, today.month, today.day,a["Start"].hour,a["Start"].minute))
        a["Finish"]=local_timezone.localize(datetime(today.year, today.month, today.day,a["Finish"].hour,a["Finish"].minute))
        asl.append(a)
df = pd.DataFrame(asl)
fig = px.timeline(df, x_start="Start", x_end="Finish",y="dummy", color="Task",template='plotly_white')

fig.add_vline(x=now)
fig.update_yaxes(autorange="reversed")
#fig.show()
fig.write_html("plan.html")


