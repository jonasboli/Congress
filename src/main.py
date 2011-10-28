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
from BeautifulSoup import BeautifulSoup
import urllib2
import re
import RTC
from pprint import *

import User
import Bill
import Activity
import Vote
import CongressionalVote
import CongressPerson
import CongressScraper

RTC.API_KEY = 'c448541518f24d79b652ccc57b384815'
RTC.apikey = 'c448541518f24d79b652ccc57b384815'
#http://api.realtimecongress.org/api/v1/bills.json?apikey=c448541518f24d79b652ccc57b384815&bill_id=hr3590-111

class BaseHandler(webapp.RequestHandler):
    user = None
    new_user_id = None

    def initialize(self, request, response):
        """General initialization for every request"""
        super(BaseHandler, self).initialize(request, response)

        try:
            #handle the cookie
            self.handle_cookie()
            self.response.headers[u'P3P'] = u'CP=HONK'  # iframe cookies in IE
            
            #if we've found a user, update the last_visited_at field
            if self.user:
                self.user.last_visit_at = datetime.datetime.now()
                self.user.put()
            
        except Exception, ex:
            raise
    
    #loads up the current user object based on a cookie
    #creates a new uuid if no cookie found
    #doesnt create a new User.User yet because the following
    #request may include one, as retrieved from local storage
    def handle_cookie(self):
        # fetch cookie from os.environ dictionary
        cookie_string = os.environ.get('HTTP_COOKIE')
        no_cookie = False
        if cookie_string: 
           #logging.debug("COOKIE EXISTS")
           cookie = Cookie.SimpleCookie()  
           cookie.load(cookie_string)
           if cookie['uuid']:
               user_id = str(cookie['uuid'].value)
               q = User.User.all()
               q.filter('user_id = ', user_id)  
               results = q.fetch(1)
               
               #if there is a user, retrieve it
               if len(results) > 0:
                   #logging.debug("USER EXISTS")
                   self.user = results[0]
               #if there is no existing user, create one
               else:
                   #logging.debug("CREATING NEW USER")
                   new_user = User.User(user_id=user_id)
                   new_user.put()
                   self.user = new_user
           else:
                no_cookie = True   
        if (not cookie_string) or (no_cookie):
            #logging.debug("NO COOKIE EXISTS")
            #create a new uuid
            self.new_user_id = str(uuid.uuid1())

    def render(self, name, **data):
        """Render a template"""
        if not data:
            data = {}
        data['user'] = self.user
        data['new_user_id'] = self.new_user_id
        self.response.out.write(template.render(
            os.path.join(
                os.path.dirname(__file__), 'templates', name + '.html'),
            data))

class MainPage(BaseHandler):        
    def get(self, year=None, month=None, day=None):        
        date_obj = None
        
        try:
            if year and month and day:
                date_obj = datetime.datetime(int(year), int(month), int(day))            
            else:
                date_obj = get_most_recent_day() 
            
            if date_obj:
                activities = get_activities_by_day(date_obj)
                day_string = date_obj.strftime('%b %d')
                previous_day = get_previous_day(date_obj)
                next_day = get_next_day(date_obj)
                
                self.render('index', 
                                activities=activities,
                                day_string=day_string,
                                previous_day=previous_day,
                                next_day=next_day)
        except:
            logging.error('Error in main page handler')
            

class AjaxUpdateCount(BaseHandler):        
    def post(self):
        update_count = self.user.get_update_count()        
        self.render('ajax_update_count', update_count=update_count)

def get_previous_day(reference_day):
    q = Activity.Activity.all()
    q.order('-day')
    results = q.run()
    for a in results:
        if a.day < reference_day:
            return a.day

def get_next_day(reference_day):
    q = Activity.Activity.all()
    q.order('-day')
    results = q.run()
    prev_a = None    
    for a in results:
        if a.day == reference_day:
            if prev_a:
                return prev_a.day
            else:
                return None
        prev_a = a
    return None

def get_most_recent_day():
    q = Activity.Activity.all()
    q.order('-day')
    results = q.fetch(1)
    if (len(results) > 0):
        most_recent_day = results[0].day
        return most_recent_day
    return None

def get_activities_by_day(date_obj):
    q = Activity.Activity.all()
    q.filter('day = ', date_obj)
    results = q.fetch(50)
    if (len(results) > 0):
        return results
    return None

class RecentVotesPage(BaseHandler):
    def get(self):
        recent_votes = self.user.vote_set.order('-created')
        recent_votes = recent_votes.fetch(15)
        self.render('recentvotes',
                        recent_votes=recent_votes)

class UpdatesPage(BaseHandler):
    def get(self):
        if self.user:
            updated_bills = self.user.get_updated_bills()        
            recent_bills = self.user.get_recent_bills()        
      
            user_votes = self.user.vote_set.order('-created')
            
            #TODO - make the front end render using the bills, not the user votes
            self.render('updates',
                        user_votes=user_votes,
                        updated_bills=updated_bills,
                        recent_bills=recent_bills)
        else:        
            self.render('updates',
                        user_votes=None,
                        updated_bills=None)


class WelcomePage(BaseHandler):
    def get(self):
        if self.user and self.user.zip:
            self.redirect('/main')    
        self.render('welcome')
        
class ZipHandler(BaseHandler):
    def post(self):
        #get and store the zip from the request
        zip = cgi.escape(self.request.get('zip'))
        self.user.zip = zip
        self.user.put()
            
        #redirect to the main page
        self.redirect('/main')

class BillPage(BaseHandler):
    def get(self, chamber=None, number=None):
        #bill = get_bill(chamber, number)
        bill = Bill.Bill.get_by_chamber_and_number(chamber, number)
        
        #calculate vote counts
        q = bill.vote_set
        q.filter('value = ', db.Category('aye'))
        aye_count = q.count()
        q = bill.vote_set
        q.filter('value = ', db.Category('nay'))
        nay_count = q.count()
        q = bill.vote_set
        q.filter('value = ', db.Category('abstain'))
        abstention_count = q.count()
        
        #get the user's vote, if any
        vote = None
        if(self.user):
            q = self.user.vote_set
            q.filter('bill = ', bill)
            results = q.fetch(1)
            if len(results) > 0:
                vote = results[0]
        
        self.render('bill',
                        bill=bill,
                        vote=vote,
                        aye_count=aye_count,
                        nay_count=nay_count,
                        abstention_count=abstention_count)
      
class VoteHandler(BaseHandler):
    def post(self):        
        #look up the bill
        chamber = self.request.get('chamber')
        number = self.request.get('number')
        bill = Bill.Bill.get_by_chamber_and_number(chamber, number)
        
        #get the vote value
        value = db.Category(self.request.get('vote_value'))
        
        vote = Vote(user=self.user,
                    bill=bill,
                    value=value)
        vote.put()
        #self.redirect('/')

class ScrapeWorker(webapp.RequestHandler):
    def get(self):
        scraper = CongressScraper()
        scraper.scrape_day()

class CongressionalVotesWorker(webapp.RequestHandler):
    def get(self):
        worker = CongressionalVotesWorker()
        worker.fetch()

application = webapp.WSGIApplication(
                                     [('/', WelcomePage),
                                        ('/zip', ZipHandler),
                                        ('/vote', VoteHandler),
                                        ('/bill', BillPage),
                                        ('/main', MainPage),
                                        ('/main/(.*)/(.*)/(.*)', MainPage), #/main/year/month/day
                                        ('/ajax_fetch_update_count', AjaxUpdateCount),
                                        #('/recentvotes', RecentVotesPage),
                                        ('/updates', UpdatesPage),
                                        ('/bill/(.*)/(.*)', BillPage), #/[House|Senate]/[1234]
                                        ('/tasks/scrape', ScrapeWorker),
                                        ('/tasks/process_congressional_votes', CongressionalVotesWorker)],
                                     debug=True)

def main():
    logging.getLogger().setLevel(logging.DEBUG)
    run_wsgi_app(application)

if __name__ == "__main__":
    main()

