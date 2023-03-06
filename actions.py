import argparse
import os
import json
import datetime
import task
import taskcollection
import inputs 
import timeslot

parser = argparse.ArgumentParser()
parser.add_argument('-s', '--stop',action='store_true')
parser.add_argument('-c', '--checkrunning',action='store_true')
parser.add_argument('-i', '--init',action='store_true')
parser.add_argument('-p', '--path',default='data')
args = parser.parse_args()


if args.init:
    col=taskcollection.taskcollection(args.path)
    if len(col.tasks)==0:
        #root task
        t=task.task()
        t.input(tasks=col,name="root",due=datetime.datetime(year=2070,month=1,day=1),eligible=datetime.datetime(year=2023,month=3,day=4),estworktime=0,tags=[],priority=10,tasktype="root",completed=100)
        col.add_task(t)
    col.write()

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
        col=taskcollection.taskcollection(args.path)
        actions=["start work on task","modify task","schedule","create task","stop work on task","import","exit"]
        result=inputs.select_from_set("Action",actions)

        if result=="create task":
            print("Select Parent Task")
            search=inputs.input_string("Serach",emptyallowed=True)
            parent=col.select_task(search)

            t=task.task()
            t.input(tasks=col)
            col.add_task(t,parent=parent)
            col.write()

        elif result=="start work on task":
            print("Select Task")
            search=inputs.input_string("Serach",emptyallowed=True)
            t=col.select_task(search)

            #stop all other running tasks
            col.stop_all_tasks()
            #start task
            ts=timeslot.timeslot(start=datetime.datetime.now())
            col.tasks[t].data["timeslots"].append(ts.data)
            col.write()
        elif result=="modify task":
            print("Select Task")
            search=inputs.input_string("Serach",emptyallowed=True)
            t=col.select_task(search)
            print(col.tasks[t].data)
            col.tasks[t].modify_interactive(col=col)
            col.write()

        elif result=="schedule":
            ret=col.schedule(prioritycutoff=0)
            if ret["success"]:
                print("scheduling succesful!")
                result=inputs.select_from_set("Schedule",ret["slots_compressed"])
            else:
                actions=["problems","partial schedule","back"]
                result=inputs.select_from_set("Select",actions)
                if result=="problems":
                    result=inputs.select_from_set("Problems",ret["problems"])
                elif result=="partial schedule":
                    result=inputs.select_from_set("Partial Schedule",ret["slots_compressed"])
        elif result=="import":
            print("Trying to import from webdav, please wait")
            col.import_caldav()
            
        elif result=="exit":
            print("bye")
            break



