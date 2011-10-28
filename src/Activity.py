import cgi
import os
import logging
import datetime 
import time
import sys
import string
import Cookie   
import uuid

from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.ext.webapp import template, util
import urllib2
import re
from pprint import *

import Bill

class Activity(db.Model):
    bill = db.ReferenceProperty(Bill.Bill)
    day = db.DateTimeProperty()
    activity_description = db.StringProperty()
    committee_description = db.StringProperty()

    @classmethod
    def get_or_create_new_activity(bill, day, description):
        logging.debug("FOUND ACTIVITY = " + str(bill) + ", " + str(day) + ', ' + str(description))
        
        #find any existing record of this activity
        q = Activity.Activity.all()
        q.filter("bill =", bill)
        q.filter("day =", day)
        results = q.fetch(1)            
        if len(results) == 0:
            new_activity = Activity.Activity(bill=bill,
                                    day=day,
                                    activity_description=description)
            new_activity.put()
