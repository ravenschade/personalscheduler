import datetime
import dateutil
import math
import sys
import pytz
import time
from dotenv import dotenv_values
import os
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
    
    notes_root=config["notes_root"]

    client = caldav.DAVClient(url=caldav_url, username=username, password=password)
    my_principal = client.principal()

    #for imap
    imap_host=config["imap_host"]
    imap_port=config["imap_port"]
    imap_user=config["imap_user"]
    imap_password=config["imap_password"]

    staging_files=config["staging_files"]
    schedule_result_html=config["schedule_result_html"]

    while True:
        P=util.get_presence(present_hosts)
        print(P)
        calendar = my_principal.calendar(name=cal)

        #sync notes
        cmd="bash "+notes_root+"/sync.sh"
        p = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
        output = p.stdout.read().decode()
        print("notes synced:",output)
            
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
                col=taskcollection.taskcollection("data",lock=True)
                print(msg.date, msg.subject, msg.from_,msg.flags,msg.uid)
                mailbox.flag(mailbox.uids(A(uid=msg.uid)),imap_tools.MailMessageFlags.FLAGGED,False) #tuple(l),True)
                mailbox.flag(mailbox.uids(A(uid=msg.uid)),imap_tools.MailMessageFlags.SEEN,True) #tuple(l),True)
                #add task in Mails
                t=task.task()
                tomorrow=datetime.datetime.combine(datetime.datetime.now(), datetime.time.min)+datetime.timedelta(days=1)
                t.input(tasks=col,name=msg.from_+" "+msg.subject,due=tomorrow,eligible=datetime.datetime.now(),estworktime=0.5,tags=[],priority=8,tasktype="todo",completed=0)
                p=0
                for it in col.tasks:
                    if col.tasks[it].data["name"]=="Mails":
                        p=it
                        break

                col.add_task(t,parent=p)
                col.write_and_unlock()              
        #get input from signal
        got=matrix_wrapper.receive(matrix_dest)
        print("got=",got)
        for g in got:
            if g["msg_type"]=="text":
                col=taskcollection.taskcollection("data",lock=True)
                t=task.task()
                tomorrow=datetime.datetime.combine(datetime.datetime.now(), datetime.time.min)+datetime.timedelta(days=1)
                t.input(tasks=col,name=g["text"],due=tomorrow,eligible=datetime.datetime.now(),estworktime=0.5,tags=["Mail"],priority=8,tasktype="todo",completed=0)
                p=0
                for it in col.tasks:
                    if col.tasks[it].data["name"]=="Staging":
                        p=it
                        break
                col.add_task(t,parent=p)
                col.write_and_unlock()              
            elif g["msg_type"]=="file":
                col=taskcollection.taskcollection("data",lock=True)
                path=g["path"]
                fm=path.split("/")[-1].replace(" ","_")
                fn=fm.split(".")[0]+"_"+str(datetime.datetime.now()).replace(" ","_")+"."+fm.split(".")[1]
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
                col.write_and_unlock()

        #get input from Notes Staging directory (staging_files)
        for root, subdirs, files in os.walk(staging_files):
            for f in files:
                if f.endswith(".pdf"):
                    fpath=root+"/"+f
                    hnew=util.hashfile(fpath)
                    hold=""
                    if os.path.isfile(fpath+".sha256sum"):
                        with open(fpath+".sha256sum","r") as f:
                            hold=f.read()
                    if hold.strip()!=hnew.strip():
                        print("processing: "+fpath)
                        col=taskcollection.taskcollection("data",lock=True)
                        fm=fpath.replace(staging_files,"").replace("/"," ")
                        fn=".".join(fm.split(".")[:-1])+"_"+str(datetime.datetime.now()).replace(" ","_")+"."+fm.split(".")[-1]
                        fn=fn.strip()
                        #copy file to nc
                        nc_share=config["nc_share"]
                        nc_url=config["nc_url"]
                        while True:
                            response = requests.put(nc_url+"/"+fn,  auth = HTTPBasicAuth(nc_share, ''), data=open(fpath,'rb').read())
                            print(response)
                            if response.status_code==201 or response.status_code==204:
                                break
                            else:
                                time.sleep(1)
                
                        name=fm+" "+config["nc_downurl"]+fn
                        tomorrow=datetime.datetime.combine(datetime.datetime.now(), datetime.time.min)+datetime.timedelta(days=1)
                        t=task.task()
                        t.input(tasks=col,name=name,due=tomorrow,eligible=datetime.datetime.now(),estworktime=0.5,tags=[],priority=8,tasktype="todo",completed=0)
                        p=0
                        for it in col.tasks:
                            if col.tasks[it].data["name"]=="Staging":
                                p=it
                                break
                        col.add_task(t,parent=p)
                        col.write_and_unlock()
                        with open(fpath+".sha256sum","w") as f:
                            f.write(hnew)
        
        #write schedule
        col=taskcollection.taskcollection("data")
        ret=col.schedule_all(prioritycutoff=-1)
        fi=open(schedule_result_html,"w")
        fi.write("<html lang=\"en\">\n")
        fi.write("<head>\n")
        fi.write("<meta charset=\"utf-8\">\n")
        fi.write("</head>\n")
        fi.write("<body>\n")
        r=col.check_running()
        if r is None:
           fi.write("No Task is running<br>\n")
        else:
           fi.write("Task "+util.hrefurls(util.tohtml(r))+" running<br>\n")
        for l in col.stats(7).splitlines():
            fi.write(l+"<br>\n")
        #staging
        ip=0
        for it in col.tasks:
            if col.tasks[it].data["name"]=="Staging":
                ip=it
                break
        col.recursive_dependencies()
        staging=[]
        for it in col.tasks[ip].tmp["subtasks_implicit"]:
            if col.tasks[it].data["completed"]!=100:
                staging.append(it)

        if len(staging)>0:
            fi.write("<table style=\"width:100%\">\n")
            fi.write("<tr>\n")
            fi.write("<th>Staging</th>\n")
            fi.write("</tr>\n")
            for it in staging:
                fi.write("<tr>\n")
                fi.write("<td>"+util.hrefurls(util.tohtml(col.getfullname(it)))+"</td>\n")
                fi.write("</tr>\n")
            fi.write("</table>\n")

        if len(ret["problems"])>0:
            fi.write("<table style=\"width:100%\">\n")
            fi.write("<tr>\n")
            fi.write("<th>problems ("+str(len(ret["problems"]))+")</th>\n")
            fi.write("<th>task</th>\n")
            fi.write("<th>due</th>\n")
            fi.write("<th>id</th>\n")
            fi.write("</tr>\n")
            for q in sorted(ret["problems"]):
                fi.write("<tr>\n")
                p=util.hrefurls(util.tohtml(q))
                fi.write("<td>"+p.split(":")[0]+"</td>\n")
                if q.split(":")[0]=="Task couldn't be scheduled":
                    fi.write("<td>"+" ".join(":".join(p.split(":")[1:]).split()[1:-1])+"</td>\n")
                    fi.write("<td>"+":".join(p.split(":")[1:]).split()[-1]+"</td>\n")
                    fi.write("<td>"+":".join(p.split(":")[1:]).split()[0]+"</td>\n")
                else:
                    fi.write("<td>"+":".join(p.split(":")[1:])+"</td>\n")

                fi.write("</tr>\n")
            fi.write("</table>\n")
        fi.write("<table style=\"width:100%\">\n")
        fi.write("<tr>\n")
        fi.write("<th>start</th>\n")
        fi.write("<th>end</th>\n")
        fi.write("<th>task</th>\n")
        fi.write("<th>due</th>\n")
        fi.write("<th>eff due</th>\n")
        fi.write("<th>id</th>\n")
        fi.write("</tr>\n")
        for p in sorted(ret["slots_compressed"]):
            fi.write("<tr>\n")
            p=util.hrefurls(util.tohtml(p))
            fi.write("<td>"+" ".join(p.split(" ")[0:2])+"</td>\n")
            fi.write("<td>"+" ".join(p.split(" ")[3:5])+"</td>\n")
            fi.write("<td>"+(" ".join(p.split(" ")[5:]).split(" (due ")[0])+"</td>\n")
            fi.write("<td>"+p.split(" (due ")[1].split()[0]+"</td>\n")
            fi.write("<td>"+p.split(" (due ")[1].split()[3].replace(")","")+"</td>\n")
            fi.write("<td>"+p.split(" (due ")[1].split()[4]+"</td>\n")
            fi.write("</tr>\n")
        fi.write("</table>\n")

        fi.write("</body>\n")
        fi.write("</html>\n")
        fi.close()

        time.sleep(60)

if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as err:
            print(f"Unexpected {err=}, {type(err)=}")
            pass

