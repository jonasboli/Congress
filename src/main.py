import cgi
import os
import logging
import datetime 
import Cookie   
import uuid

from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.ext.webapp import template, util
import RTC

import User
import Bill
import Activity
import Vote
import CongressScraper
import CongressionalVotesWorker

RTC.API_KEY = 'c448541518f24d79b652ccc57b384815'
RTC.apikey = 'c448541518f24d79b652ccc57b384815'
#http://api.realtimecongress.org/api/v1/bills.json?apikey=c448541518f24d79b652ccc57b384815&bill_id=hr3590-111
MAX_DAYS_FOR_RECENT_ACTIVITY = 30

webapp.template.register_template_library('CustomTemplateTags')

class BaseHandler(webapp.RequestHandler):
    user = None
    new_user_id = None
    update_count = None

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
                self.update_count = self.user.get_update_count_since_last_visit()
            
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
        data['update_count'] = self.update_count
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
                date_obj = Activity.Activity.get_most_recent_day() 
            
            if date_obj:
                todays_activities = Activity.Activity.get_activities_by_day(date_obj)
                day_string = date_obj.strftime('%b %d')
                previous_day = Activity.Activity.get_previous_day(date_obj)
                next_day = Activity.Activity.get_next_day(date_obj)
                
                recent_activities = Activity.Activity.get_recent_N_days_activities(MAX_DAYS_FOR_RECENT_ACTIVITY)
                
                self.render('index', 
                                todays_activities=todays_activities,
                                recent_activities=recent_activities,
                                day_string=day_string,
                                previous_day=previous_day,
                                next_day=next_day)
        except Exception as e:
            logging.error('Error in main page handler: ' + str(e))
            

class AjaxUpdateCount(BaseHandler):        
    def post(self):
        update_count = self.user.get_update_count()        
        self.render('ajax_update_count', update_count=update_count)


class RecentVotesPage(BaseHandler):
    def get(self):
        recent_votes = self.user.vote_set.order('-created')
        recent_votes = recent_votes.fetch(15)
        self.render('recentvotes',
                        recent_votes=recent_votes)

class UpdatesPage(BaseHandler):
    def get(self):
        if self.user:
            updated_bills = self.user.get_updated_bills_since_last_visit()        
            recent_bills = self.user.get_recently_updated_bills(MAX_DAYS_FOR_RECENT_ACTIVITY)        
      
            self.render('updates',
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
        bill = Bill.Bill.get_by_chamber_and_number(chamber, number)
        
        #get the user's vote, if any
        vote = None
        if(self.user):
            vote = self.user.get_vote_for_bill(bill)
        
        self.render('bill',
                        bill=bill,
                        vote=vote)
      
class VoteHandler(BaseHandler):
    def post(self):        
        #look up the bill
        chamber = self.request.get('chamber')
        number = self.request.get('number')
        bill = Bill.Bill.get_by_chamber_and_number(chamber, number)
        
        #get the vote value
        value = db.Category(self.request.get('vote_value'))
        
        vote = Vote.Vote(user=self.user,
                    bill=bill,
                    value=value)
        vote.put()
        #self.redirect('/')

class ScrapeWorker(webapp.RequestHandler):
    def get(self):
        scraper = CongressScraper.CongressScraper()
        scraper.scrape_day()

class CongressionalVotesWorkerHandler(webapp.RequestHandler):
    def get(self):
        worker = CongressionalVotesWorker.CongressionalVotesWorker()
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
                                        ('/tasks/process_congressional_votes', CongressionalVotesWorkerHandler)],
                                     debug=True)



def main():
    logging.getLogger().setLevel(logging.DEBUG)
    run_wsgi_app(application)

if __name__ == "__main__":
    main()

