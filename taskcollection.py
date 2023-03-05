import os
import json
import copy
import task
import util
import inputs
import datetime
import timeslot
from dotenv import dotenv_values
import caldav
import math
import pytz
from dateutil import relativedelta

class taskcollection:
    path=""
    tasks={}
    tree={}
    def __init__(self,path):
        self.path=path
        self.read()

    def read(self):
        if os.path.exists(self.path):
            print("reading task collection from",self.path)
            for p in os.listdir(self.path+"/tasks/"):
                t=task.task()
                t.read_from_file(self.path+"/tasks/"+p)
                self.tasks[t.ID]=t
        else:
            print("task collection is not existing at ",self.path,"creating new")
            os.mkdir(self.path)
            os.mkdir(self.path+"/tasks")
            self.tasks={}
    
    def write(self):
        for p in self.tasks:
            #print("writing element "+str(p)+" to "+self.tasks[p].jsonpath)
            self.tasks[p].write_to_file()
    
    def add_task(self,t,parent=None):
        if parent is None:
            #trying to add root element
            if len(self.tasks)>0:
                raise RuntimeError("trying to add a second root element")
            print("adding root element")
            ID=0
            q=copy.deepcopy(t)
            q.ID=ID
            q.set_ID(ID)
            q.set_path(self.path+"/tasks/"+str(ID)+".json")
            self.tasks[ID]=q
        else:
            #find new ID
            ID=1
            for p in os.listdir(self.path+"/tasks/"):
                v=int(p.split(".")[0])
                if v>=ID:
                    ID=v+1
            for p in self.tasks:
                if p>=ID:
                    ID=p+1

            self.tasks[parent].data["subtasks"].append(ID)
            q=copy.deepcopy(t)
            q.ID=ID
            q.set_path(self.path+"/tasks/"+str(ID)+".json")
            q.set_ID(ID)
            self.tasks[ID]=q


    def get_all_tags(self):
        tags=set()
        for t in self.tasks:
            if "tags" in self.tasks[t].data:
                for e in self.tasks[t].data["tags"]:
                    tags.add(e)
        return list(tags)
        
    def __str__(self):
        #s=""
        #for i in self.tasks:
        #    s=s+str(self.tasks[i])+"\n"
        #return s
        self.buf=[]
        self.buf2=[]
        self.buf_paths=[]
        self.tasks_to_list(0,0)
        return "\n".join(self.buf)

    def select_task(self,search=None,fields=None,fields_tmp=None,completed=False):
        opt=[]
        self.buf=[]
        self.buf2=[]
        self.buf_paths=[]
        self.tasks_to_list(element=0,level=0,fields=fields,fields_tmp=fields_tmp,completed=completed)
        result=0
        if not (search is None):
            #find tasks with search string in name
            res=[]
            for t in self.tasks:
                if self.tasks[t].data["name"].lower().find(search.lower())>=0:
                    res.append(t)
            #remove paths from buf and buf 2 that don't include one of the found tasks
            P=[]
            for p in self.buf_paths:
                found=False
                for q in p:
                    if q in res:
                        found=True
                        break
                if found:
                    P.extend(p)
            buf=[]
            buf2=[]
            for i in range(len(self.buf)):
                if self.buf2[i] in P:
                    buf.append(self.buf[i])
                    buf2.append(self.buf2[i])
            if len(buf)>0:
                result=inputs.select_from_set("Select Task",buf,buf2)
            else:
                print("filter search resulted in zero hits, showing full list")
                result=inputs.select_from_set("Select Task",self.buf,self.buf2)
        else:
            result=inputs.select_from_set("Select Task",self.buf,self.buf2)
        return result

    def tasks_to_list(self,element=0,level=0,path=[0],fields=None,fields_tmp=None,completed=False):
        if len(self.tasks[element].data["subtasks"])==0:
            self.buf_paths.append(path)
        for t in self.tasks[element].data["subtasks"]:
            if self.tasks[t].data["completed"]==100 and not completed:
                continue
            s=""
            for i in range(level):
                s=s+"    "
            S=s+" "+self.tasks[t].data["name"]
            if not(fields is None):
                for f in fields:
                    S=S+" "+str(self.tasks[t].data[f])
            if not(fields_tmp is None):
                for f in fields_tmp:
                    S=S+" "+str(self.tasks[t].tmp[f])
            self.buf.append(S)
            self.buf2.append(t)
            path2=copy.deepcopy(path)
            path2.append(t)
            self.tasks_to_list(element=t,level=level+1,path=path2,fields=fields,fields_tmp=fields_tmp,completed=completed)

    def stop_all_tasks(self):
        for t in self.tasks:
            for ts in self.tasks[t].data["timeslots"]:
                if ts["end"] is None:
                    print("stopping task",t)
                    ts["end"]=datetime.datetime.now()
                    ts["endtype"]="start_of_other_task"
        self.write()
    
    def check_running(self):
        #check if a task is running
        for t in self.tasks:
            if self.tasks[t].data["completed"]==100:
                continue
            for ts in self.tasks[t].data["timeslots"]:
                if ts["end"] is None:
                    return self.tasks[t].data["name"]
        return None

    def import_caldav(self):
        self.tasks={}
        print("adding root element")
        ID=0
        t=task.task()
        q=copy.deepcopy(t)
        q.ID=ID
        q.set_ID(ID)
        q.data["name"]="root"
        q.set_path(self.path+"/tasks/"+str(ID)+".json")
        self.tasks[ID]=q
        self.tasks[ID].data["subtasks"]=[]
    
        config = dotenv_values(".env")
        
        caldav_url2 = config["caldav_url2"]
        tasks_url2 = config["tasks_url2"]
        username2 = config["username2"]
        password2 = config["password2"]
        cal2=config["cal2"]

        client2 = caldav.DAVClient(url=caldav_url2, username=username2, password=password2)
        my_principal2 = client2.principal()

        calendar2 = my_principal2.calendar(name=cal2)

        todos=util.get_tasks(calendar2)
#        {'url': 'https://nc.pc2.uni-paderborn.de/remote.php/dav/calendars/rschade/robert2/f3dbc347-5571-4304-bbce-8466d42936ac.ics', 'categories': ['not defined'], 'description': '', 'priority': 9, 'summary': 'Mathematik/Numerik', 'dtstart': None, 'dtend': None, 'due': None, 'status': '', 'percent-complete': 0, 'transp': False, 'related-to': '5ec03e5c-9973-48f6-b827-e2f64d62e3cc', 'uid': 'f3dbc347-5571-4304-bbce-8466d42936ac', 'depends-on': [154, 157, 173], 'related-to2': [167], 'duration': None}, {'url': 'https://nc.pc2.uni-paderborn.de/remote.php/dav/calendars/rschade/robert2/fc61b40f-9279-48db-9866-8558b81bed2a.ics', 'categories': ['Fachberatung'], 'description': '', 'priority': 9, 'summary': 'FPGA', 'dtstart': None, 'dtend': None, 'due': None, 'status': '', 'percent-complete': 0, 'transp': False, 'related-to': '5ec03e5c-9973-48f6-b827-e2f64d62e3cc', 'uid': 'fc61b40f-9279-48db-9866-8558b81bed2a', 'depends-on': [153, 164, 166], 'related-to2': [167], 'duration': None}
        for it in range(len(todos)):
            print("processing task "+str(it))
            print(todos[it])
            t=task.task()
            ID=it+1
            t.ID=ID
            t.data["ID"]=ID
            t.data["name"]=todos[it]["summary"]
            #t.data["due"]=util.caldav_to_datetime(todos[it]["due"]).date()
            if not (todos[it]["due"] is None):
                t.data["due"]=datetime.datetime.combine(todos[it]["due"].date(),datetime.datetime.min.time())
            #t.data["eligible"]=util.caldav_to_datetime(todos[it]["dtstart"]).date()
            if not (todos[it]["dtstart"] is None):
                t.data["eligible"]=datetime.datetime.combine(todos[it]["dtstart"].date(),datetime.datetime.min.time())
            t.data["priority"]=todos[it]["priority"]
            t.data["tags"]=todos[it]["categories"]
            t.data["subtasks"]=[]
            for d in todos[it]["depends-on"]:
                t.data["subtasks"].append(d+1)
            if not(todos[it]["duration"] is None):
                esttime=float(todos[it]["duration"])
                print(t.data["name"],todos[it]["duration"],esttime)
                ts=timeslot.timeslot(duration=esttime)
                t.data["estworktime"]=[ts.data]
#                if t.data["name"].find("Backup")>=0:
#                    print(t.data)
#                    raise RuntimeError("bla")
            if len(todos[it]["related-to2"])==0:
                self.tasks[0].data["subtasks"].append(ID)
            self.tasks[ID]=copy.deepcopy(t)
            self.tasks[ID].jsonpath="data/tasks/"+str(ID)+".json"
        self.write()
    
    def exclude_caldav_event(self,slots,days=30):
        config = dotenv_values(".env")
        caldav_url = config["caldav_url"]
        username = config["username"]
        password = config["password"]
        cal=config["cal"]
        client = caldav.DAVClient(url=caldav_url, username=username, password=password)
        my_principal = client.principal()
        calendars = my_principal.calendars()
        calendar = my_principal.calendar(name=cal)
        blocked=[]
        local_timezone = pytz.timezone('Europe/Berlin')
        now = datetime.datetime.now(local_timezone)
        today=local_timezone.localize(datetime.datetime(now.year, now.month, now.day)) #.replace(tzinfo=local_timezone).astimezone(local_timezone)
        for d in range(days):
            events=calendar.date_search(start=today+relativedelta.relativedelta(days=d), end=today+relativedelta.relativedelta(days=d+1), expand=True)
            for t in events:
                T=util.parse_ics(t.data,str(t))
                if not T["transp"]:
                    blocked.append({"dtstart":T["dtstart"].replace(tzinfo=None),"dtend":T["dtend"].replace(tzinfo=None),"summary":T["summary"]})
        slots2=[]
        for i in range(len(slots)):
            excl=False
            for b in blocked:
                #start of event in slot
                if b["dtstart"]>slots[i]["start"] and b["dtstart"]<slots[i]["end"]:
                    excl=True
                #end of event in slot
                if b["dtend"]>slots[i]["start"] and b["dtend"]<slots[i]["end"]:
                    excl=True
                #slot in event
                if b["dtstart"]<slots[i]["start"] and b["dtend"]>slots[i]["end"]:
                    excl=True
                if b["dtstart"]==slots[i]["start"]:
                    excl=True
                if b["dtend"]==slots[i]["end"]:
                    excl=True
            if not excl:
                slots2.append(slots[i])
        return slots2


    def schedule(self,prioritycutoff=0,returnpartial=False,slotduration=15,futuredays=30):
        #extend due dates from parents to children without due dates
        #introduce indirect due date
        for ip in self.tasks:
            self.tasks[ip].tmp={}
            self.tasks[ip].tmp["due_implicit"]=self.tasks[ip].data["due"]
            self.tasks[ip].tmp["subtasks_implicit"]=copy.deepcopy(self.tasks[ip].data["subtasks"])
            self.tasks[ip].tmp["slots"]=[]

        changed=True
        while changed:
            changed=False
            for ip in self.tasks:
                if not( self.tasks[ip].tmp["due_implicit"] is None):
                    for ic in self.tasks[ip].data["subtasks"]:
                        if self.tasks[ic].tmp["due_implicit"] is None:
                            self.tasks[ic].tmp["due_implicit"]=self.tasks[ip].tmp["due_implicit"]
                            changed=True
        #recursively expand dependencies
        changed=True
        while changed:
            changed=False
            for ip in self.tasks:
                for i in self.tasks[ip].tmp["subtasks_implicit"]:
                    for j in self.tasks[i].tmp["subtasks_implicit"]:
                        if j not in self.tasks[ip].tmp["subtasks_implicit"]:
                            self.tasks[ip].tmp["subtasks_implicit"].append(j)
                            changed=True
        #check for leaf tasks with due but no duration
        incompletetasks=[]
        for ip in self.tasks:
            if not(self.tasks[ip].tmp["due_implicit"] is None) and (len(self.tasks[ip].data["estworktime"])==0) and (len(self.tasks[ip].data["subtasks"])==0):
                incompletetasks.append(ip)

        if len(incompletetasks)>0:
            print("Tasks with explicit or implicit due date and no subtasks but no work time estimation:")
            for ip in incompletetasks:
                print(self.tasks[ip].data)
                self.tasks[ip].modify_interactive()
                self.write()
        else:
            #prepone due dates of dependencies to due date of job
            changed=True
            while changed:
                changed=False
                for ip in self.tasks:
                    if not (self.tasks[ip].tmp["due_implicit"] is None):
                        for i in self.tasks[ip].tmp["subtasks_implicit"]:
                            if self.tasks[i].tmp["due_implicit"] > self.tasks[ip].tmp["due_implicit"]:
                                self.tasks[i].tmp["due_implicit"]=self.tasks[ip].tmp["due_implicit"]
                                changed=True

            overdue=[]
            #find all task that are due tomorrow or overdue
            for ip in self.tasks:
                if not (self.tasks[ip].tmp["due_implicit"] is None):
                    if datetime.datetime.fromisoformat(self.tasks[ip].tmp["due_implicit"]).date()<=datetime.datetime.now().date():
                        overdue.append(ip)

            #settings
            
            td=datetime.timedelta(minutes=slotduration)
            allslots=[]
            t0=datetime.datetime.min + math.ceil((datetime.datetime.now() - datetime.datetime.min) / td) * td
            t1=t0
            tend=t0+datetime.timedelta(days=futuredays)
            while t1<tend:
                allslots.append({"start":t1,"end":t1+td,"used":False,"task":None})
                t1=t1+td

            slots=copy.deepcopy(allslots)
            #exclude slots that are out of work times
            slots2=[]
            #not on weekends
            for i in range(len(slots)):
                excl=False
                if slots[i]["start"].weekday()>=5:
                    excl=True
                if slots[i]["start"].hour<8:
                    excl=True
                if slots[i]["start"].hour>=17:
                    excl=True
                if not excl:
                    slots2.append(slots[i])
    
            #exclude slots that are blocked by events
            slots=self.exclude_caldav_event(slots2)

            for i in range(len(slots)):
                if not slots[i]["used"]: 
                    print("available slot",i,slots[i]) 

            checkok=True
            #set up possible slices for each task
            for it in self.tasks:
                self.tasks[it].tmp["possible_slots"]=set()
                self.tasks[it].tmp["to_be_scheduled"]=True
                self.tasks[it].tmp["scheduled_slots"]=0
                self.tasks[it].tmp["needed_slots"]=0
                if not(self.tasks[it].data["priority"] is None):
                    if self.tasks[it].data["priority"]<prioritycutoff:
                        self.tasks[it].tmp["to_be_scheduled"]=False
                        continue
                if self.tasks[it].data["completed"]==100:
                    self.tasks[it].tmp["to_be_scheduled"]=False

                if ( self.tasks[it].tmp["due_implicit"] is None):
                    self.tasks[it].tmp["to_be_scheduled"]=False
                    self.tasks[it].tmp["needed_slots"]=0
                    continue
                if datetime.datetime.fromisoformat(self.tasks[it].tmp["due_implicit"])>tend:
                    self.tasks[it].tmp["to_be_scheduled"]=False
                    self.tasks[it].tmp["needed_slots"]=0
                else:
                    #go trough slices
                    for i in range(len(slots)):
                        possible=True
                        if not(self.tasks[it].data["eligible"] is None):
                            if datetime.datetime.fromisoformat(self.tasks[it].data["eligible"])>slots[i]["start"]:
                                possible=False
                        if not( self.tasks[it].tmp["due_implicit"] is None):
                            if datetime.datetime.fromisoformat(self.tasks[it].tmp["due_implicit"])<slots[i]["end"]:
                                possible=False
                        if possible:
                            self.tasks[it].tmp["possible_slots"].add(i)
                    #compute number of slices
                    ttot=0
                    for ts in self.tasks[it].data["estworktime"]:
                        ttot=ttot+ts["duration"]
                    nslots=math.ceil(ttot/(slotduration/60.0))
                    if nslots==0:
                        self.tasks[it].tmp["to_be_scheduled"]=False
                        self.tasks[it].tmp["needed_slots"]=0
                    else:
                        self.tasks[it].tmp["needed_slots"]=nslots
            
            #schedule tasks with exactly one slot choice first
            for it in self.tasks:
                if self.tasks[it].tmp["needed_slots"]==len(self.tasks[it].tmp["possible_slots"]):
                    for s in self.tasks[it].tmp["possible_slots"]:
                        if not slots[s]["used"]:
                            slots[s]["used"]=True
                            slots[s]["task"]=it
                            self.tasks[it].tmp["slots"].append(s)
                        else:
                            print("slot",slots[s],"is already in use but task",it,self.tasks[it].data["name"],"requires this slot")
                            raise RuntimeError("Schedule impossible")

            #schedule overdue tasks first
            #FIXME: maybe sort according to priority
            for it in overdue:
                if not self.tasks[it].tmp["to_be_scheduled"]:
                    continue
                print("First scheduling overdue task",it,self.tasks[it].data["name"])
                sc=0
                for i in range(len(slots)):
                    if not slots[i]["used"]:
                        slots[i]["used"]=True
                        slots[i]["task"]=it
                        self.tasks[it].tmp["slots"].append(i)
                        sc=sc+1
                        if sc==self.tasks[it].tmp["needed_slots"]:
                            break
                if sc!=self.tasks[it].tmp["needed_slots"]:
                    print("Couldn't schedule all overdue tasks first")
                    checkok=False
                else:
                    self.tasks[it].tmp["to_be_scheduled"]=False
            
            #check basic necessary conditions
            #check for solution for individual tasks
            for it in self.tasks:
                if self.tasks[it].tmp["needed_slots"]> len(self.tasks[it].tmp["possible_slots"]) and self.tasks[it].tmp["to_be_scheduled"]:
                    print("There are not enough slots to schedule task",it,self.tasks[it].data["name"],"even individually: needed slots",self.tasks[it].tmp["needed_slots"],"possible slots",len(self.tasks[it].tmp["possible_slots"]))
                    checkok=False

            #schedule: earliest deadline first
            for si in range(len(slots)):
                if slots[si]["used"]:
                    continue
                viable_tasks=[]
                for it in self.tasks:
                    viable=self.tasks[it].tmp["to_be_scheduled"]
                    if not (si in self.tasks[it].tmp["possible_slots"]):
                        viable=False
                    for i in self.tasks[it].tmp["subtasks_implicit"]:
                        if self.tasks[i].tmp["to_be_scheduled"]:
                            viable=False
                    if viable:
                        viable_tasks.append(it)
                if len(viable_tasks)>0:
                    #find job with closest deadline
                    closest=-1
                    mindist=None
                    for it in viable_tasks:
                        m=(slots[si]["start"]-datetime.datetime.fromisoformat(self.tasks[it].tmp["due_implicit"])).total_seconds()
                        if mindist is None:
                            mindist=m
                            closest=it
                        else:
                            if m<mindist:
                                closest=it
                                mindist=m
                    slots[si]["used"]=True
                    slots[si]["task"]=closest
                    self.tasks[closest].tmp["slots"].append(si)
                    if self.tasks[closest].tmp["needed_slots"]==len(self.tasks[closest].tmp["slots"]):
                        self.tasks[closest].tmp["to_be_scheduled"]=False
                    

            #check schedule: check if all deadlines could be fulfilled
            for it in self.tasks:
                if self.tasks[it].tmp["to_be_scheduled"]:
                    print("Task couldn't be scheduled:",it,self.tasks[it].data["name"],self.tasks[it].tmp["due_implicit"])
                    checkok=False
            if checkok:
                return slots
            else:
                if returnpartial:
                    return slots
                else:
                    return None
