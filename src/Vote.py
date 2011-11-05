from google.appengine.ext import db

import User
import Activity
import Bill

class Vote(db.Model):
    user = db.ReferenceProperty(User.User)
    activity = db.ReferenceProperty(Activity.Activity)
    bill = db.ReferenceProperty(Bill.Bill)
    value = db.CategoryProperty()
    created = db.DateTimeProperty(auto_now_add=True)
