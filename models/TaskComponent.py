__author__ = 'Aran'


import json
from google.appengine.ext import db


class TaskComponent(db.Model):
    taskId = db.IntegerProperty(required=True)
    userId = db.IntegerProperty(required=True, default = -1)
    type = db.StringProperty(required=True,default=" ")
    label = db.StringProperty(required=True,default=" ")
    isMandatory = db.BooleanProperty(required=True, default=True)
    order = db.IntegerProperty(required=True)

    def to_JSON(self):
        data = {'taskId' : self.taskId,
                'userId' : self.userId,
                'type' : self.type,
                'label' : self.label,
                'isMandatory' : self.isMandatory,
                'order' : self.order
                }
        return json.dumps(data)
