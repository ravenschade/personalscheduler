import subprocess
from dotenv import dotenv_values
from subprocess import Popen, PIPE, STDOUT
from os.path import expanduser
import json

def send(dest,msg):
    home = expanduser("~")
    cmd=home+"/.local/bin/matrix-commander --sync OFF -s "+home+"/.config/matrix-commander/store  -m \""+msg+"\" --user '"+dest+"'"
    print(cmd)
    p = Popen(cmd, shell=True,stdout=PIPE, stderr=STDOUT, close_fds=True)
    output = p.stdout.read().decode()
    print(output)

def receive(src):
    config = dotenv_values(".env")
    home = expanduser("~")

    got=[]
    cmd=home+"/.local/bin/matrix-commander -s "+home+"/.config/matrix-commander/store --listen once  --output=json"
    p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
    output = p.stdout.read().decode()
    print(output)
    try:
        for k in output.splitlines():
            j=json.loads(k)
            print(j)
            if j["source"]["sender"]==src:
                if j["source"]["content"]["msgtype"]=="m.text":
                    got.append({"msg_type":"text","text":j["source"]["content"]["body"]})
                elif j["source"]["content"]["msgtype"]=="m.audio":
                    url=j["source"]["content"]["file"]["url"]
                    h=j["source"]["content"]["file"]["hashes"]["sha256"]
                    cmd=home+"/.local/bin/matrix-commander -s "+home+"/.config/matrix-commander/store --download +"+url+" --file-name media/"+h+".ogg"
                    p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
                    output = p.stdout.read().decode()
                    print(output)
                    got.append({"msg_type":"file","path":"media/"+h+".ogg"})
                elif j["source"]["content"]["msgtype"]=="m.image":
                    url=j["source"]["content"]["file"]["url"]
                    h=j["source"]["content"]["file"]["hashes"]["sha256"]
                    cmd=home+"/.local/bin/matrix-commander -s "+home+"/.config/matrix-commander/store --download +"+url+" --file-name media/"+h+".jpg"
                    p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
                    output = p.stdout.read().decode()
                    print(output)
                    got.append({"msg_type":"file","path":"media/"+h+".jpg"})

    except Exception as inst:
        print(inst)
    #for l in output.splitlines():
    #    if l.startswith("Body: "):
    #        s=l.split("Body: ")[1]
    #        got.append({"msg_type":"text","text":s})
    #    if l.startswith("  Stored plaintext in: "):
    #        p=l.split("  Stored plaintext in: ")[1]
    #        got.append({"msg_type":"file","path":p})
    #print(got)
    #cmd="matrix-commander -s /home/robert/.config/matrix-commander/store/ --download mxc://matrix.aphysicist.eu/WrKwsWouWRdziixFPDSvKikc --file-name bla"
    print(got)
    return got

