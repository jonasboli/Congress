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

from BeautifulSoup import BeautifulSoup
import RTC
RTC.API_KEY = 'c448541518f24d79b652ccc57b384815'
RTC.apikey = 'c448541518f24d79b652ccc57b384815'
MAX_ACTIVITIES_TO_PROCESS = 10


import User
import Bill
import Activity
import Vote
import CongressionalVote
import CongressPerson



class CongressionalVotesWorker(object):
                 
    def __init__(self):
        pass
    
    def fetch(self):
        q = Activity.Activity.all()
        q.order('-day')
        activities = q.fetch(MAX_ACTIVITIES_TO_PROCESS)
        for a in activities:
            db_bill = a.bill
            rtc_votes = RTC.Votes.get_by_bill(db_bill.rtc_id).votes
            last_house_day = datetime.datetime.min
            last_senate_day = datetime.datetime.min
            logging.debug("FETCHED RTC VOTES:  COUNT = " + str(len(rtc_votes)))
       
            for v in rtc_votes:
                logging.debug("looking for a passage vote")
                if str(v.vote_type) == 'passage':
                    #create the new c vote
                    c_vote = CongressionalVote.CongressionalVote.get_or_create_new_c_vote(v, db_bill)                    
                    
                    #update the Bill 
                    if (c_vote.chamber.lower() == 'house') and (c_vote.voted_at > last_house_day):
                        db_bill.last_passage_vote_at = c_vote.voted_at
                        db_bill.last_house_vote = c_vote
                        logging.debug("NEW CONGRESSIONAL VOTE CREATED FOR: " + str(db_bill.number))
                        db_bill.put()
                    elif (c_vote.chamber.lower() == 'senate') and (c_vote.voted_at > last_senate_day):
                        db_bill.last_passage_vote_at = c_vote.voted_at
                        db_bill.last_senate_vote = c_vote
                        logging.debug("NEW CONGRESSIONAL VOTE CREATED FOR: " + str(db_bill.number))
                        db_bill.put()
    
    