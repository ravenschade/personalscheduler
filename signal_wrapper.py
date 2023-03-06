import subprocess
from dotenv import dotenv_values
from subprocess import Popen, PIPE, STDOUT

def signal_receive():
    config = dotenv_values(".env")
    signal_self = config["signal_self"]
    signal_remote = config["signal_remote"]

    got=[]
    cmd="./signalwrapper -a "+signal_self+" receive"
    p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
    output = p.stdout.read().decode()
    print(output)
    for l in output.splitlines():
        if l.startswith("Body: "):
            s=l.split("Body: ")[1]
            got.append({"msg_type":"text","text":s})
        if l.startswith("  Stored plaintext in: "):
            p=l.split("  Stored plaintext in: ")[1]
            got.append({"msg_type":"file","path":p})
    #print(got)
    return got

