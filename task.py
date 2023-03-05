import os
import json
import inputs
import util
import timeslot
import taskcollection
import datetime

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
            due=inputs.input_date("Due date")
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
            tags=inputs.input_tags("Tag",alltags=alltags)
        self.data["tags"]=tags

        if tasktype is None:
            tasktype=inputs.select_from_set("Type of task",["todo","wait"])
        self.data["tasktype"]=tasktype

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
    
    def write_to_file(self):
        with open(self.jsonpath, 'w') as json_file:
            json.dump(self.data, json_file,default=util.serialize_datetime)
    
    def __str__(self):
        return json.dumps(self.data, indent = 4, sort_keys=True, default=util.serialize_datetime)

    def modify_interactive(self,col=None):
        actions=["change name","change priority","change completed","change parent","add work time estimation"]
        result=inputs.select_from_set("Action",actions)

        if result=="change name":
            self.data["name"]=inputs.input_string("New task name")
        if result=="change priority":
            priority=inputs.input_int("Priority 0-10",vmin=0,vmax=10)
            self.data["priority"]=priority
        if result=="change completed":
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

        if result=="change parent":
            search=inputs.input_string("Serach",emptyallowed=True)
            t=col.select_task(search)
            if not (self.ID in col.tasks[t].data["subtasks"]):
                #remove from all 
                for it in col.tasks:
                    if self.ID in col.tasks[it].data["subtasks"]:
                        col.tasks[it].data["subtasks"].remove(self.ID)
                #add to new
                col.tasks[t].data["subtasks"].append(self.ID)

            
        elif result=="add work time estimation":
            estworktime=inputs.input_float("Estimated work time in hours")
            t=timeslot.timeslot(duration=estworktime)
            self.data["estworktime"].append(t.data)


