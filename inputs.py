import os
from InquirerPy import inquirer
from InquirerPy import prompt
from InquirerPy.validator import NumberValidator
from InquirerPy.base.control import Choice
import datetime

def input_string(text,emptyallowed=False):
    s=""
    while len(s)==0:
        s=input(text+": ")
        if emptyallowed:
            break
    return s

def input_int(text,emptyallowed=False,vmin=None,vmax=None):
    s=None
    while s is None:
        try:
            s=int(input(text+": "))
            if not(vmin is None):
                if s<vmin:
                    s=None
                    raise RuntimeError("boundaries")
            if not(vmax is None):
                if s>vmax:
                    s=None
                    raise RuntimeError("boundaries")
            break
        except:
            pass
        if emptyallowed:
            break
    return s

def input_float(text,emptyallowed=False):
    s=""
    while len(s)==0:
        try:
            s=float(input(text+": "))
            break
        except:
            pass
        if emptyallowed:
            break
    return s

def input_date(text,emptyallowed=False,future=True,limit=None):
    s=None 
    while s is None:
        #display next weeks
        dayiter=-1
        if future:
            dayiter=1
        now=datetime.datetime.now()
        options={"enter date directly":None,"None":None}
        for d in range(30):
            D=now+datetime.timedelta(days=d*dayiter)
            if (limit is None) or (future and D<=limit) or (not future and D>=limit):
                options[D.strftime("%Y-%m-%d %A")+" "+str(d)+" days from now"]=None
            
        questions = [{"type": "input","message": text+":","completer": options}] #,"multicolumn_complete": True}]
        result = prompt(questions)
        if result[0] in options:
            if result[0]=="enter date directly":
                while True:
                    d=input_string(text+" as %Y-%m-%d")
                    try:
                        s=datetime.datetime.strptime(d, '%Y-%m-%d')
                        break
                    except:
                        pass
            elif result[0]=="None":
                return None
            else:
                d=result[0].split()[0]
                s=datetime.datetime.strptime(d, '%Y-%m-%d')
        print(s,emptyallowed)
        if emptyallowed:
            break
    return s

def input_tags(text,emptyallowed=False,alltags=None):
    if alltags is None:
        options={}
        questions = [{"type": "input","message": text+":","completer": options}] #,"multicolumn_complete": True}]
        result = prompt(questions)
        return [result[0]]
    else:
        choices=["enter additional "+text]
        for t in alltags:
            choices.append(t)
        result = inquirer.select(message=text+":", choices=choices, multiselect=True).execute()
        if "enter additional "+text in result:
            t2=input_tags(text)
            for g in t2:
                result.append(g)
        try:
            result.remove("enter additional "+text)
        except:
            pass
        return result


def select_from_set(text,options,key=None,multi=False):
    if multi:
        result = inquirer.checkbox(message=text+":", choices=options).execute()
        print(result)
        if not(key is None):
            keys=[]
            for r in result:
                keys.append(key[options.index(r)])
            return keys
        else:
            return result
    else:
        result = inquirer.select(message=text+":", choices=options).execute()
        if not(key is None):
            return key[options.index(result)]
        else:
            return result


