import os
import datetime


class timeslot:
    data={"start":None,"end":None,"duration":None,"starttype":None,"endtype":None,"slottype":None,"added":None}
    def __init__(self,duration=None,start=None,end=None,starttype="manual",endtype="manual"):
        if not (duration is None):
            self.data["slottype"]="duration"
            self.data["duration"]=duration
        if not (start is None):
            self.data["slottype"]="startend"
            self.data["start"]=start
            self.data["starttype"]=starttype
            if not (end is None):
                self.data["end"]=end
                self.data["endtype"]=endtype
        self.data["added"]=datetime.datetime.now()
            
        

