import argparse
import os
import json
import datetime
import task
import taskcollection
import inputs 
import timeslot
from dateutil import relativedelta
import html
import re 



parser = argparse.ArgumentParser()
parser.add_argument('-s', '--stop',action='store_true')
parser.add_argument('-c', '--checkrunning',action='store_true')
parser.add_argument('-i', '--init',action='store_true')
parser.add_argument('-p', '--path',default='data')
args = parser.parse_args()

if args.init:
    col=taskcollection.taskcollection(args.path,lock=True)
    if len(col.tasks)==0:
        #root task
        t=task.task()
        t.input(tasks=col,name="root",due=datetime.datetime(year=2070,month=1,day=1),eligible=datetime.datetime(year=2023,month=3,day=4),estworktime=0,tags=[],priority=10,tasktype="root",completed=100)
        col.add_task(t)
    col.write_and_unlock()

if args.stop:
    col=taskcollection.taskcollection(args.path)
    col.stop_all_tasks()
elif args.checkrunning:
    col=taskcollection.taskcollection(args.path)
    r=col.check_running()
    if r is None:
       print("No Task is running")
    else:
       print("Task",r,"running")
else:
    while True:
        os.system("clear")
        col=taskcollection.taskcollection(args.path,lock=False)
        r=col.check_running()
        if r is None:
           print("No Task is running")
        else:
           print("Task",r,"running")

        print(col.stats(7))

        actions=["start work on task","modify task","schedule","create task","stop work on task","import","used time","batch action","exit"] #,"test"]
        result=inputs.select_from_set("Action",actions)

        if result=="create task":
            col=taskcollection.taskcollection(args.path,lock=True)
            print("Select Parent Task")
            search=inputs.input_string("Serach",emptyallowed=True)
            parent=col.select_task(search)

            t=task.task()
            t.input(tasks=col)
            col.add_task(t,parent=parent)
            col.write_and_unlock()

        elif result=="start work on task":
            col=taskcollection.taskcollection(args.path,lock=True)
            print("Select Task")
            search=inputs.input_string("Serach",emptyallowed=True)
            t=col.select_task(search)

            #stop all other running tasks
            col.stop_all_tasks()
            #start task
            ts=timeslot.timeslot(start=datetime.datetime.now())
            col.tasks[t].data["timeslots"].append(ts.data)
            col.write_and_unlock()
        elif result=="modify task":
            col=taskcollection.taskcollection(args.path,lock=True)
            print("Select Task")
            search=inputs.input_string("Serach",emptyallowed=True)
            t=col.select_task(search)
            #print(col.tasks[t].data)
            col.tasks[t].modify_interactive(col=col)
            col.write_and_unlock()

        elif result=="schedule":
            col=taskcollection.taskcollection(args.path,lock=False)
#            sec=col.get_items_at_level()
#            sections=[]
#            for s in sec:
#                sections.append(col.tasks[s].data["name"])
#            result=inputs.select_from_set("Select",sections)
#            ret=col.schedule(prioritycutoff=-1,section=result)
            actions=["all"]
            tags=col.get_all_tags()
            for t in tags:
                actions.append(t)
            result=inputs.select_from_set("Which tag to schedule",actions)

            stag=[]
            if result=="all":            
                ret=col.schedule_all(prioritycutoff=-1)
            else:    
                ret=col.schedule(prioritycutoff=-1,tag=result)
            
            result=None
            resp=None
            if ret["success"]:
                print("scheduling succesful!")
                result=inputs.select_from_set("Schedule",ret["slots_compressed"])
            else:
                for p in ret["problems"]:
                    print(p)
                actions=["partial schedule","problems","back"]
                result=inputs.select_from_set("Select",actions)
                if result=="problems":
                    resp=inputs.select_from_set("Problems",ret["problems"])
                elif result=="partial schedule":
                    resp=inputs.select_from_set("Partial Schedule",ret["slots_compressed"])
            if result=="partial schedule" or ret["success"]:
                sid=None
                try:
                    sid=int(resp.split(" ")[-1])
                except:
                    pass
                if not (sid is None):
                    actions2=["start","modify task"]
                    result2=inputs.select_from_set("Action",actions2)
                    if result2=="start":
                        col=taskcollection.taskcollection(args.path,lock=True)
                        #stop all other running tasks
                        col.stop_all_tasks()
                        #start task
                        ts=timeslot.timeslot(start=datetime.datetime.now())
                        col.tasks[sid].data["timeslots"].append(ts.data)
                        col.write_and_unlock()
                        
                    elif result2=="modify task":
                        col=taskcollection.taskcollection(args.path,lock=True)
                        col.tasks[sid].modify_interactive(col=col)
                        col.write_and_unlock()


        elif result=="stop work on task":
            col=taskcollection.taskcollection(args.path,lock=True)
            #stop all other running tasks
            col.stop_all_tasks()
            col.write_and_unlock()
        elif result=="import":
            col=taskcollection.taskcollection(args.path,lock=True)
            print("Trying to import from webdav, please wait")
            col.import_caldav()
            col.write_and_unlock()
        elif result=="used time":
            col=taskcollection.taskcollection(args.path,lock=False)
            days=inputs.input_int("How many days into the past",emptyallowed=False)
            now=datetime.datetime.now()
            tl=datetime.datetime(now.year, now.month,now.day,0,0)+relativedelta.relativedelta(days=-days)
            print("used time from",tl,"to",now)
            col.used_time(start=tl,end=now)
            parent=col.select_task(search=None,completed=True,fields_tmp=["used_time"])
        elif result=="batch action":
            col=taskcollection.taskcollection(args.path,lock=True)
            bactions=["complete"]
            result=inputs.select_from_set("Batch Action",bactions)
            if result=="complete":
                ta=col.select_task(search=None,multi=True)
                print("ta=",ta)
                for t in ta:
                    col.tasks[t].data["completed"]=100
            col.write_and_unlock()
        elif result=="exit":
            print("bye")
            break
        elif result=="test":
            col=taskcollection.taskcollection(args.path,lock=False)
            col.make_note_structure()
