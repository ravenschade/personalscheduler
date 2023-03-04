import os
import json
import datetime
import task
import taskcollection
import inputs 
import timeslot

col=taskcollection.taskcollection("data")
if len(col.tasks)==0:
    #root task
    t=task.task()
    t.input(tasks=col,name="root",due=datetime.datetime(year=2070,month=1,day=1),eligible=datetime.datetime(year=2023,month=3,day=4),estworktime=0,tags=[],priority=10,tasktype="root",completed=100)
    col.add_task(t)

    t=task.task()
    t.input(tasks=col,name="task 1",due=datetime.datetime(year=2023,month=3,day=4),eligible=datetime.datetime(year=2023,month=3,day=4),estworktime=1,tags=["Fachberatung"],priority=10,tasktype="todo",completed=0)
    col.add_task(t,parent=0)

    t=task.task()
    t.input(tasks=col,name="task 2",due=datetime.datetime(year=2023,month=3,day=4),eligible=datetime.datetime(year=2023,month=3,day=4),estworktime=1,tags=["Fachberatung"],priority=10,tasktype="todo",completed=0)
    col.add_task(t,parent=1)

    t=task.task()
    t.input(tasks=col,name="task 5",due=datetime.datetime(year=2023,month=3,day=4),eligible=datetime.datetime(year=2023,month=3,day=4),estworktime=1,tags=["Fachberatung"],priority=10,tasktype="todo",completed=0)
    col.add_task(t,parent=2)

    t=task.task()
    t.input(tasks=col,name="task 3",due=datetime.datetime(year=2023,month=3,day=4),eligible=datetime.datetime(year=2023,month=3,day=4),estworktime=1,tags=["Fachberatung"],priority=10,tasktype="todo",completed=0)
    col.add_task(t,parent=0)

    t=task.task()
    t.input(tasks=col,name="aufgabe 4",due=datetime.datetime(year=2023,month=3,day=4),eligible=datetime.datetime(year=2023,month=3,day=4),estworktime=1,tags=["Fachberatung"],priority=10,tasktype="todo",completed=0)
    col.add_task(t,parent=0)

print(col)
col.write()

actions=["create task","start work on task","stop work on task","modify task","schedule","import","exit"]
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
    search=inputs.input_string("Serach",emptyallowed=Tru)
    t=col.select_task(search)

    actions=[""]
    result=inputs.select_from_set("Action",actions)

elif result=="schedule":
    print("Trying to schedule, please wait")
elif result=="import":
    print("Trying to import from webdav, please wait")
    col.import_caldav()
    
elif result=="exit":
    print("bye")



