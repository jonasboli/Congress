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


import User
import Activity
import Bill

class Vote(db.Model):
    user = db.ReferenceProperty(User.User)
    activity = db.ReferenceProperty(Activity.Activity)
    bill = db.ReferenceProperty(Bill.Bill)
    value = db.CategoryProperty()
    created = db.DateTimeProperty(auto_now_add=True)
