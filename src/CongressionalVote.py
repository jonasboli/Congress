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

class CongressionalVote(db.Model):
    bill = db.ReferenceProperty(Bill.Bill)
    voted_at = db.DateTimeProperty()
    number = db.IntegerProperty()
    result = db.StringProperty()
    question = db.StringProperty()
    chamber = db.StringProperty()
    yeas = db.IntegerProperty()
    nays = db.IntegerProperty()
    abstentions = db.IntegerProperty()
    dem_yeas = db.IntegerProperty()
    dem_nays = db.IntegerProperty()
    dem_abstentions = db.IntegerProperty()
    rep_yeas = db.IntegerProperty()
    rep_nays = db.IntegerProperty()
    rep_abstentions = db.IntegerProperty()

    @staticmethod        
    def get_or_create_new_c_vote(v, db_bill):
        q = CongressionalVote.all()
        q.filter('number = ', v.number)
        result = q.fetch(1)
        if len(result) > 0:
            return result[0]
        else:
            voted_at = datetime.datetime.strptime(v.voted_at, "%Y-%m-%dT%H:%M:%SZ")
            
            #create the CongressionalVote
            new_c_vote = CongressionalVote(
                            voted_at = voted_at,
                            bill = db_bill,
                            number = v.number,
                            result = v.result,
                            #question = v.question,
                            chamber = v.chamber,
                            yeas = int(v.vote_breakdown.total.yea),
                            nays = int(v.vote_breakdown.total.nay),
                            abstentions = int(v.vote_breakdown.total.not_voting),
                            dem_yeas = int(v.vote_breakdown.party.d.yea),
                            dem_nays = int(v.vote_breakdown.party.d.nay),
                            dem_abstentions = int(v.vote_breakdown.party.d.not_voting),
                            rep_yeas = int(v.vote_breakdown.party.r.yea),
                            rep_nays = int(v.vote_breakdown.party.r.nay),
                            rep_abstentions = int(v.vote_breakdown.party.r.not_voting)
                            )
            new_c_vote.put()
            return new_c_vote
