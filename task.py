import os
import json
import inputs
import util
import timeslot
import taskcollection
import datetime
import pytz
from dateutil import relativedelta
import copy

class task:
    jsonpath=""
    data=""
    read=False
    ID=-1

    def __init__(self):
        self.data={}
        self.data["timeslots"]=[]
        self.data["name"]=None
        self.data["due"]=None
        self.data["eligible"]=None
        self.data["estworktime"]=[]
        self.data["tags"]=[]
        self.data["tasktype"]=None
        self.data["priority"]=None
        self.data["completed"]=None
        self.data["notes"]=[]
   
    def input(self,tasks=None,name=None,due=None,eligible=None,estworktime=None,tags=None,tasktype=None,priority=None,completed=None):
        if name is None:
            name=inputs.input_string("name")
        self.data["name"]=name
        
        if due is None:
            due=inputs.input_date("Due date",emptyallowed=True)
        self.data["due"]=due

        if eligible is None:
            eligible=inputs.input_date("Eligible from",emptyallowed=True,limit=self.data["due"])
        self.data["eligible"]=eligible

        if estworktime is None:
            estworktime=inputs.input_float("Estimated work time in hours")
        t=timeslot.timeslot(duration=estworktime)
        self.data["estworktime"]=[t.data]
        
        if tags is None:
            if not (tasks is None):
                alltags=tasks.get_all_tags()
            else:
                alltags=[]
            alltags.append("no tag")
            tags=inputs.input_tags("Tag",alltags=alltags)
        if "no tag" in tags:
            self.data["tags"]=[]
        else:
            self.data["tags"]=tags

        #if tasktype is None:
        #    tasktype=inputs.select_from_set("Type of task",["todo","wait"])
        self.data["tasktype"]="todo"

        if priority is None:
            priority=inputs.input_int("Priority 0-10",vmin=0,vmax=10)
        self.data["priority"]=priority

        if completed is None:
            completed=inputs.input_int("completed 0-100",vmin=0,vmax=100)
        self.data["completed"]=completed

        self.data["timeslots"]=[]
        self.data["notes"]=[]
        self.data["subtasks"]=[]

    def set_ID(self,ID):
        self.ID=ID
        self.data["ID"]=ID
    
    def set_due(self,due):
        self.data["due"]=due
    
    def set_eligible(self,eligible):
        self.data["eligible"]=eligible
    
    def set_estworktime(self,worktime):
        self.data["estworktime"]=worktime
    
    def set_path(self, jsonpath):
        self.jsonpath=jsonpath

    def read_from_file(self,jsonpath):
        self.jsonpath=jsonpath
        with open(jsonpath, 'r') as f:
            self.data = json.load(f)
        self.ID=self.data["ID"]
        #modify all tasks at once
        #self.data["tags"]=[]
        #with open(self.jsonpath, 'w') as json_file:
        #    json.dump(self.data, json_file,default=util.serialize_datetime)
    
    def write_to_file(self):
        with open(self.jsonpath, 'w') as json_file:
            json.dump(self.data, json_file,default=util.serialize_datetime)
    
    def __str__(self):
        return json.dumps(self.data, indent = 4, sort_keys=True, default=util.serialize_datetime)

    def get_used(self,start=None,end=None):
        tused=0
        for ts in self.data["timeslots"]:
            tend=ts["end"]
            tstart=datetime.datetime.fromisoformat(ts["start"])
            if tend is None:
                tend=datetime.datetime.now()
            else:
                tend=datetime.datetime.fromisoformat(ts["end"])
            if not(start is None):
                tend=max(tend,start)
                tstart=max(tstart,start)
            if not(end is None):
                tend=min(tend,end)
                tstart=min(tstart,end)
            tused=tused+(tend-tstart).total_seconds()/3600.0
        return tused

    def modify_interactive(self,col=None):
        while True:
            actions=[]
            actions.append("name "+self.data["name"])
            actions.append("due "+str(self.data["due"]))
            actions.append("eligible "+str(self.data["eligible"]))
            actions.append("priority "+str(self.data["priority"]))
            actions.append("completed "+str(self.data["completed"]))
            
            p=0
            for s in col.tasks:
                if self.ID in col.tasks[s].data["subtasks"]:
                    p=s
                    break
            actions.append("parent "+col.tasks[p].data["name"])
            #FIXME show list
            ttot=0
            for ts in self.data["estworktime"]:
                ttot=ttot+ts["duration"]
            tused=self.get_used()
            left=ttot-tused
            actions.append("add to estimated work time of "+str(ttot)+" hours, left are "+str(left)+" hours")
            actions.append("tags "+" ".join(self.data["tags"]))
            actions.append("back")
            
            result=inputs.select_from_set("Action",actions)
            
            if result==actions[0]:
                self.data["name"]=inputs.input_string("New task name")
            elif result==actions[1]:
                due=inputs.input_date("Due date",emptyallowed=True)
                if due is None:
                    self.data["due"]=due
                else:
                    self.data["due"]=due.isoformat()
            elif result==actions[2]:
                eligible=inputs.input_date("Eligible from",emptyallowed=True,limit=datetime.datetime.fromisoformat(self.data["due"]))
                self.data["eligible"]=eligible.isoformat()
            elif result==actions[3]:
                priority=inputs.input_int("Priority 0-10",vmin=0,vmax=10)
                self.data["priority"]=priority
            elif result==actions[4]:
                completed=inputs.input_int("completed 0-100",vmin=0,vmax=100)
                self.data["completed"]=completed
                if completed==100:
                    #recursively expand dependencies
                    changed=True
                    for ip in col.tasks:
                        col.tasks[ip].tmp={}
                        col.tasks[ip].tmp["subtasks_implicit"]=[]
                    while changed:
                        changed=False
                        for ip in col.tasks:
                            for i in col.tasks[ip].tmp["subtasks_implicit"]:
                                for j in col.tasks[i].tmp["subtasks_implicit"]:
                                    if j not in col.tasks[ip].tmp["subtasks_implicit"]:
                                        col.tasks[ip].tmp["subtasks_implicit"].append(j)
                                        changed=True
                    #mark all subtasks as completed
                    for i in self.tmp["subtasks_implicit"]:
                        col.tasks[i].data["completed"]=completed
            elif result==actions[5]:
                search=inputs.input_string("Serach",emptyallowed=True)
                t=col.select_task(search)
                if not (self.ID in col.tasks[t].data["subtasks"]):
                    #remove from all 
                    for it in col.tasks:
                        if self.ID in col.tasks[it].data["subtasks"]:
                            col.tasks[it].data["subtasks"].remove(self.ID)
                    #add to new
                    col.tasks[t].data["subtasks"].append(self.ID)
                
            elif result==actions[6]:
                estworktime=inputs.input_float("Add to estimated work time in hours")
                t=timeslot.timeslot(duration=estworktime)
                self.data["estworktime"].append(t.data)
            elif result==actions[7]:
                #tags
                actions=["add tag","remove tag","back"]
                result=inputs.select_from_set("Action",actions)
                if result==actions[0]:
                    #add tag
                    tag=inputs.input_string("additional tag",emptyallowed=False)
                    if not tag in self.data["tags"]:
                        self.data["tags"].append(tag)
                elif result==actions[1]:
                    #remove tag
                    actions=copy.deepcopy(self.data["tags"])
                    actions.append("back")
                    result=inputs.select_from_set("remove tag",actions)
                    if result!="back":
                        self.data["tags"].remove(result)               

            elif result==actions[len(actions)-1]:
                break
        self.write_to_file()


