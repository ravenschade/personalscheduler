import datetime
import dateutil
import math
import sys
import pytz
import time
from dotenv import dotenv_values

import caldav
import webbrowser
import util
#from gotify import Gotify

import taskcollection
import subprocess

#from imaplib import IMAP4_SSL
import imap_tools
from imap_tools import MailBox, AND,A

#import signal_wrapper

import task
import taskcollection
import requests
from requests.auth import HTTPBasicAuth
import speech_to_text

import matrix_wrapper

def main():
    config = dotenv_values(".env")
    ## We'll try to use the local caldav library, not the system-installed
    sys.path.insert(0, '..')
    sys.path.insert(0, '.')

    local_timezone = pytz.timezone('Europe/Berlin')

    #for events
    caldav_url = config["caldav_url"]
    username = config["username"]
    password = config["password"]
    cal=config["cal"]

    #watcher settings
    present_hosts=config["present_hosts"].split(",")
    presence_stop_delay=int(config["presence_stop_delay"])
    presence_start_delay=int(config["presence_start_delay"])
    #gotify_url=config["gotify_url"]
    #gotify_token=config["gotify_token"]
    
    matrix_dest=config["matrix_dest"]

    client = caldav.DAVClient(url=caldav_url, username=username, password=password)
    my_principal = client.principal()

    #for imap
    imap_host=config["imap_host"]
    imap_port=config["imap_port"]
    imap_user=config["imap_user"]
    imap_password=config["imap_password"]

    while True:
        P=util.get_presence(present_hosts)
        print(P)
        calendar = my_principal.calendar(name=cal)
            
        #stop task if appointment is currently running
        local_timezone = pytz.timezone('Europe/Berlin')
        now = datetime.datetime.now(local_timezone)
        today=local_timezone.localize(datetime.datetime(now.year, now.month, now.day)) #.replace(tzinfo=local_timezone).astimezone(local_timezone)
        calevents=calendar.date_search(start=today, end=today+dateutil.relativedelta.relativedelta(days=1), expand=True)
        overlap=False
        for t in calevents:
            T=util.parse_ics(t.data,str(t))
            if T["dtstart"]<=now and T["dtend"]>=now and not T["transp"]:
                print("overlapping event=",T)
                overlap=True

        col=taskcollection.taskcollection("data")
        t=col.check_running()
        if not (t is None):
            print(" a task (",t,") is running, checking if person is present on one of the present_hosts")
            present=False
            lastpresent=0
            for p in P:
                if p[0]:
                    present=True
                    lastpresent=max(p[1],lastpresent)
                    break
            #stop task is not present for too long
            if not present and lastpresent+presence_stop_delay*60<time.time():
                print("noone has been present for "+str(presence_stop_delay)+" minutes, stopping tasks (" +str(time.time())+" > "+str(lastpresent+presence_stop_delay*60)+")")
                col.stop_all_tasks()
            if overlap:
                print("there is an overlapping event, stopping tasks")
                col.stop_all_tasks()
            
        else:
            #no task is running
            present=False
            lastpresent=0
            for p in P:
                if p[0]:
                    present=True
                    lastpresent=max(p[1],lastpresent)
                    break
            if present and lastpresent+presence_start_delay*60<=time.time() and not overlap:
                print("someone has been present for at least "+str(presence_start_delay)+" minutes but no task is running, sending notification")
                #gotify = Gotify(base_url=gotify_url,app_token=gotify_token)
                #gotify.create_message("NO TASK IS RUNNING!",title="personalscheduler",priority=10)
                matrix_wrapper.send(matrix_dest,"NO TASK IS RUNNING!")
        with MailBox(imap_host,port=imap_port).login(imap_user,imap_password, initial_folder='INBOX') as mailbox:
            #flags = (imap_tools.MailMessageFlags.SEEN, imap_tools.MailMessageFlags.FLAGGED
            for msg in mailbox.fetch(A(flagged=True),mark_seen=False):
                col=taskcollection.taskcollection("data")
                print(msg.date, msg.subject, msg.from_,msg.flags,msg.uid)
                mailbox.flag(mailbox.uids(A(uid=msg.uid)),imap_tools.MailMessageFlags.FLAGGED,False) #tuple(l),True)
                mailbox.flag(mailbox.uids(A(uid=msg.uid)),imap_tools.MailMessageFlags.SEEN,True) #tuple(l),True)
                #add task in Mails
                t=task.task()
                tomorrow=datetime.datetime.combine(datetime.datetime.now(), datetime.time.min)+datetime.timedelta(days=1)
                t.input(tasks=col,name=msg.from_+" "+msg.subject,due=tomorrow,eligible=datetime.datetime.now(),estworktime=0.5,tags=["Mail"],priority=8,tasktype="todo",completed=0)
                p=0
                for it in col.tasks:
                    if col.tasks[it].data["name"]=="Mails":
                        p=it
                        break

                col.add_task(t,parent=p)
                col.write()              
        #get input from signal
        got=matrix_wrapper.receive(matrix_dest)
        print("got=",got)
        for g in got:
            if g["msg_type"]=="text":
                col=taskcollection.taskcollection("data")
                t=task.task()
                tomorrow=datetime.datetime.combine(datetime.datetime.now(), datetime.time.min)+datetime.timedelta(days=1)
                t.input(tasks=col,name=g["text"],due=tomorrow,eligible=datetime.datetime.now(),estworktime=0.5,tags=["Mail"],priority=8,tasktype="todo",completed=0)
                p=0
                for it in col.tasks:
                    if col.tasks[it].data["name"]=="Staging":
                        p=it
                        break
                col.add_task(t,parent=p)
                col.write()              
            elif g["msg_type"]=="file":
                col=taskcollection.taskcollection("data")
                path=g["path"]
                fn=g["path"].split("/")[-1]
                #copy file to nc
                nc_share=config["nc_share"]
                nc_url=config["nc_url"]
                while True:
                    response = requests.put(nc_url+"/"+fn,  auth = HTTPBasicAuth(nc_share, ''), data=open(path,'rb').read())
                    print(response)
                    if response.status_code==201 or response.status_code==204:
                        break
                    else:
                        time.sleep(1)
                text=""
                #transcribe if aac
                if fn.endswith(".ogg") or fn.endswith(".aac"):
                    text=speech_to_text.speech_to_text_whisper(path)
                    matrix_wrapper.send(matrix_dest,"text recognised: "+text)

                tomorrow=datetime.datetime.combine(datetime.datetime.now(), datetime.time.min)+datetime.timedelta(days=1)
                t=task.task()
                tn=text+" "+config["nc_downurl"]+fn
                t.input(tasks=col,name=tn,due=tomorrow,eligible=datetime.datetime.now(),estworktime=0.5,tags=[],priority=8,tasktype="todo",completed=0)
                p=0
                for it in col.tasks:
                    if col.tasks[it].data["name"]=="Staging":
                        p=it
                        break
                col.add_task(t,parent=p)
                col.write()


        time.sleep(60)

if __name__ == "__main__":
    while True:
        try:
            main()
        except:
            pass

