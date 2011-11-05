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
import RTC

class CongressPerson(db.Model):
    first_name = db.StringProperty()
    last_name = db.StringProperty()
    chamber = db.CategoryProperty()
    state = db.StringProperty()
    title = db.StringProperty()
    party = db.StringProperty()
    district = db.StringProperty()
    govtrack_id = db.StringProperty()

    @staticmethod
    def get_or_create_new_congress_person(rtc_bill):
        if rtc_bill.sponsor:
            q = CongressPerson.all()
            q.filter("govtrack_id =", str(rtc_bill.sponsor.govtrack_id))
            results = q.fetch(1)            
            if len(results) > 0:
                return results[0]
            else:
                #format some fields
                title = ('Senator' if rtc_bill.sponsor.title == 'Sen' else 'Representative')
                party = ''
                if rtc_bill.sponsor.party == 'R':
                    party = 'Republican'
                elif rtc_bill.sponsor.party == 'D':
                    party = 'Democrat'
                elif rtc_bill.sponsor.party == 'I':
                    party = 'Independent'
                
                new_congress_person = CongressPerson(
                                            first_name=rtc_bill.sponsor.first_name,
                                            last_name=rtc_bill.sponsor.last_name,
                                            chamber=db.Category((rtc_bill.sponsor.chamber).capitalize()),
                                            state=rtc_bill.sponsor.state,
                                            title=title,
                                            party=party,
                                            district=rtc_bill.sponsor.district,
                                            govtrack_id=rtc_bill.sponsor.govtrack_id)
                new_congress_person.put()
                return new_congress_person
