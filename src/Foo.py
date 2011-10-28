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




class Foo(db.Model):
    zip = db.StringProperty()
    user_id = db.StringProperty()
    last_visit_at = db.DateTimeProperty()