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

    def select_task(self,search=None):
        opt=[]
        self.buf=[]
        self.buf2=[]
        self.buf_paths=[]
        self.tasks_to_list(element=0,level=0)
        result=0
        if not (search is None):
            #find tasks with search string in name
            res=[]
            for t in self.tasks:
                if self.tasks[t].data["name"].lower().find(search.lower())>=0:
                    res.append(t)
            print(res)
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
            result=inputs.select_from_set("Select Task",buf,buf2)
        else:
            result=inputs.select_from_set("Select Task",self.buf,self.buf2)
        return result

    def tasks_to_list(self,element=0,level=0,path=[0]):
        if len(self.tasks[element].data["subtasks"])==0:
            self.buf_paths.append(path)
        for t in self.tasks[element].data["subtasks"]:
            s=""
            for i in range(level):
                s=s+"  "
            self.buf.append(s+" "+self.tasks[t].data["name"])
            self.buf2.append(t)
            path2=copy.deepcopy(path)
            path2.append(t)
            self.tasks_to_list(element=t,level=level+1,path=path2)

    def stop_all_tasks(self):
        for t in self.tasks:
            for ts in self.tasks[t].data["timeslots"]:
                if ts["end"] is None:
                    print("stopping task",t)
                    ts["end"]=datetime.datetime.now()
                    ts["endtype"]="start_of_other_task"
        self.write()

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
            t.data["due"]=todos[it]["due"]
            t.data["priority"]=todos[it]["priority"]
            t.data["tags"]=todos[it]["categories"]
            t.data["subtasks"]=[]
            for d in todos[it]["depends-on"]:
                t.data["subtasks"].append(d+1)
            if not(todos[it]["duration"] is None):
                esttime=float(todos[it]["duration"])
                ts=timeslot.timeslot(duration=esttime)
                t.data["estworktime"]=[ts.data]
            if len(todos[it]["related-to2"])==0:
                self.tasks[0].data["subtasks"].append(it)
            self.tasks[ID]=t
            self.tasks[ID].jsonpath="data/tasks/"+str(ID)+".json"
        self.write()

         

        

