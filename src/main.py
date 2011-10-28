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

import Foo


RTC.API_KEY = 'c448541518f24d79b652ccc57b384815'
RTC.apikey = 'c448541518f24d79b652ccc57b384815'
#http://api.realtimecongress.org/api/v1/bills.json?apikey=c448541518f24d79b652ccc57b384815&bill_id=hr3590-111


class User(db.Model):
    zip = db.StringProperty()
    user_id = db.StringProperty()
    last_visit_at = db.DateTimeProperty()
    
    def get_update_count(self):
        votes = self.vote_set
        count = 0
        for v in votes:
            #logging.debug("BILL: " + str(v.bill.number))
            #logging.debug("BILL LAST PASSAGE VOTE: " + str(v.bill.last_passage_vote_at))
            #logging.debug("USER LAST VISIT AT: " + str(self.last_visit_at))
            if v.bill.last_passage_vote_at > self.last_visit_at:
                count = count + 1
        logging.debug("UPDATE COUNT: " + str(count))
        return count

    def get_recent_bills(self):
        recent_bills = [] 
        for v in self.vote_set:
            #logging.debug("RECENT")
            #logging.debug("BILL: " + str(v.bill.number))
            #logging.debug("BILL LAST PASSAGE VOTE: " + str(v.bill.last_passage_vote_at))
            #logging.debug("USER LAST VISIT AT: " + str(self.last_visit_at))
      
            #filter to bills updated in the last 10 days
            if v.bill.last_passage_vote_at > (datetime.datetime.now() - datetime.timedelta(days=-10)):
                recent_bills = recent_bills + v.bill
                #TODO: sort the bills by updated date
        return recent_bills
    
    def get_updated_bills(self):
        #TODO: sort the bills by updated date
        #TODO: build the front end to process this format
        updated_bills = []
        for v in self.vote_set:    
            logging.debug("UPDATED")
            logging.debug("BILL: " + str(v.bill.number))
            logging.debug("BILL LAST PASSAGE VOTE: " + str(v.bill.last_passage_vote_at))
            logging.debug("USER LAST VISIT AT: " + str(self.last_visit_at))
            
            #filter to bills updated since last visit
            if (v.bill.last_passage_vote_at > self.last_visit_at) or (v.bill.last_passage_vote_at > (datetime.datetime.now() - datetime.timedelta(days=10))):
                logging.debug("FOUND UPDATED BILL")
            
                last_house_vote = None
                last_senate_vote = None
                
                #find the last house and senate votes
                c_votes = v.bill.congressionalvote_set
                c_votes.order('-voted_at')
                for c_v in c_votes:
                    if (not last_house_vote) and (c_v.chamber == 'house'):
                        last_house_vote = c_v
                    elif (not last_senate_vote) and (c_v.chamber == 'senate'):
                        last_senate_vote = c_v
                    elif last_house_vote and last_senate_vote:
                        break

                bill_data = {}
                bill_data['last_house_vote'] = v.value
                bill_data['last_senate_vote'] = v.value
                bill_data['user_vote'] = v.value
                bill_data['bill'] = v.value
                if v.bill.last_passage_vote_at > self.last_visit_at:
                    bill_data['kind'] = 'updated'
                elif v.bill.last_passage_vote_at > (datetime.datetime.now() - datetime.timedelta(days=10)):
                    bill_data['kind'] = 'recent'
                
                updated_bills = updated_bills + [bill_data]
        return updated_bills
    
    
    
class CongressPerson(db.Model):
    first_name = db.StringProperty()
    last_name = db.StringProperty()
    chamber = db.CategoryProperty()
    state = db.StringProperty()
    title = db.StringProperty()
    party = db.StringProperty()
    district = db.StringProperty()
    govtrack_id = db.StringProperty()

class Bill(db.Model):
    rtc_id = db.StringProperty()
    chamber = db.CategoryProperty()
    number = db.IntegerProperty()
    href = db.StringProperty()
    short_title = db.TextProperty() 
    official_title = db.TextProperty()
    popular_title = db.TextProperty()
    summary = db.TextProperty()
    introduced_at = db.TextProperty()
    house_passage_result = db.StringProperty()
    house_passage_result_at = db.DateTimeProperty()
    senate_passage_result = db.StringProperty()
    senate_passage_result_at = db.DateTimeProperty()
    sponsor = db.ReferenceProperty(CongressPerson)
    last_passage_vote_at = db.DateTimeProperty()
    last_house_vote = db.Key()
    last_senate_vote = db.Key()
    
    @classmethod
    def get_by_chamber_and_number(cls, chamber, number):
        q = Bill.all()
        q.filter('chamber = ', str(chamber))
        q.filter('number = ', int(number))
        result = q.fetch(1)
        if(len(result) > 0):            
            return result[0]
        return None

class Activity(db.Model):
    bill = db.ReferenceProperty(Bill)
    day = db.DateTimeProperty()
    activity_description = db.StringProperty()
    committee_description = db.StringProperty()

class CongressionalVote(db.Model):
    bill = db.ReferenceProperty(Bill)
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

class Vote(db.Model):
    user = db.ReferenceProperty(User)
    activity = db.ReferenceProperty(Activity)
    bill = db.ReferenceProperty(Bill)
    value = db.CategoryProperty()
    created = db.DateTimeProperty(auto_now_add=True)

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
    #doesnt create a new User yet because the following
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
               q = User.all()
               q.filter('user_id = ', user_id)  
               results = q.fetch(1)
               
               #if there is a user, retrieve it
               if len(results) > 0:
                   #logging.debug("USER EXISTS")
                   self.user = results[0]
               #if there is no existing user, create one
               else:
                   #logging.debug("CREATING NEW USER")
                   new_user = User(user_id=user_id)
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
    q = Activity.all()
    q.order('-day')
    results = q.run()
    for a in results:
        if a.day < reference_day:
            return a.day

def get_next_day(reference_day):
    q = Activity.all()
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
    q = Activity.all()
    q.order('-day')
    results = q.fetch(1)
    if (len(results) > 0):
        most_recent_day = results[0].day
        return most_recent_day
    return None

def get_activities_by_day(date_obj):
    q = Activity.all()
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
        bill = Bill.get_by_chamber_and_number(chamber, number)
        
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
        bill = Bill.get_by_chamber_and_number(chamber, number)
        
        #get the vote value
        value = db.Category(self.request.get('vote_value'))
        
        vote = Vote(user=self.user,
                    bill=bill,
                    value=value)
        vote.put()
        #self.redirect('/')

class ScrapeWorker(webapp.RequestHandler):
    def get(self):
        #scrape_week()
        scrape_day()

class BlockType:
    a = 1
    p = 2        
                 
def scrape_day():
    #fetch the page to scrape
    page = urllib2.urlopen("http://majorityleader.gov/floor/daily.html")
    soup = BeautifulSoup(page)
    
    day = None
    b_blocks = soup.findAll('b')
    for b in b_blocks:
        day = extract_day_from_block(b)
        if day:
            break
    #if we couldnt figure out the day, abort
    if not day:
        print "cant find day"
        return
    
    #find all bills stuck in a <p> block
    p_blocks = soup.findAll('p') 
    for p in p_blocks:
        extract_bill_from_block(p, BlockType.p, day)        

    #find all committee activity
    """b_blocks = soup.findAll('b') 
    for b in b_blocks:
        if(is_committee_activity_block(b)):
            committee_description = extract_committee_info_from_block(b.parent.parent)
            a_blocks = b.parent.parent.findAll('a')
            for a in a_blocks:
                extract_committee_link_from_block(a)
    """

    #<p style="text-align: center;">
    #  <u>
    #    <b>MONDAY, OCTOBER 3RD</b>
    #  </u>
    #...
    #</p>
def extract_day_from_block(block):
    days = r'[monday|tuesday|wednesday|thursday|friday|saturday|sunday]'
    day_regex = re.compile(days + r',\s+([a-z]+)\s+(\d+)', re.IGNORECASE)
    block_contents = str(block.contents)
    day_results = day_regex.search(block_contents)
    if day_results :
        #format the date string as a date object
        day_in_month = str(day_results.group(2))
        month_in_year = str(day_results.group(1)) 
        current_year = str(time.localtime()[0])
        time_string = day_in_month + ' ' + month_in_year + ' ' + current_year
        date_obj = datetime.datetime.strptime(time_string, "%d %B %Y") 
         
        return date_obj
    return None    
                    

    #<p style="margin-left: 40px;">
    #  <b>1)    
    #    <a href="http://www.gpo.gov/fdsys/pkg/BILLS-112hr686rh/pdf/BILLS-112hr686rh.pdf">H.R. 686</a>
    #  </b>
    #...
    #</p>
def extract_bill_from_block(block, block_type, day):
    bill_finder_regex = re.compile(r'H\.\s*R\.\s*(\d+)', re.IGNORECASE)
    block_contents = str(block.contents)
    print "block contents = " + block_contents
    bill_finder_results = bill_finder_regex.search(block_contents)
    if bill_finder_results:
        bill_number = bill_finder_results.group(1)
        action_type = None
        #if block_type == BlockType.a:
        #    action_type = find_action_type_in_block(block.parent, block_type)
        if block_type == BlockType.p and block.contents:
            action_type = find_action_type_in_block(block.contents[0], block_type)
        bill = get_or_create_new_bill(bill_number, 'house')
        get_or_create_new_activity(bill, day, action_type)



def find_action_type_in_block(block, block_type):
    if block.contents:
    #build the regex to extract the action congress will take
        begin_consideration_regex = r'begin\s*consideration'
        possible_further_consideration_regex = r'possible\s*further\s*consideration'
        complete_consideration_regex = r'complete\s*consideration'
        one_minute_speeches_regex = r'one\s*minute\s*speeches'
        full_regex = r'.*(' + begin_consideration_regex + r'|' + possible_further_consideration_regex + r'|' + complete_consideration_regex + r'|' + one_minute_speeches_regex + r').*'
        action_regex = re.compile(full_regex, re.IGNORECASE)
        
        #run the regex
        #print "ACTION BLOCK CONTENTS = " + str(block.contents)
        #print "ACTION BLOCK CONTENTS[0] = " + str(block.contents[0])
        action_type_results = action_regex.search(str(block.contents[0]))
        if action_type_results:
            action_type = str(action_type_results.group(1))
            return action_type
    return None
    

def get_or_create_new_activity(bill, day, description):
    logging.debug("FOUND ACTIVITY = " + str(bill) + ", " + str(day) + ', ' + str(description))
    
    #find any existing record of this activity
    q = Activity.all()
    q.filter("bill =", bill)
    q.filter("day =", day)
    results = q.fetch(1)            
    if len(results) == 0:
        new_activity = Activity(bill=bill,
                                day=day,
                                activity_description=description)
        new_activity.put()
    
def get_or_create_new_bill(bill_number, chamber):
    logging.debug("FOUND BILL:  " +  str(bill_number))

    #find any existing record of this bill
    q = Bill.all()
    q.filter("number =", int(bill_number))
    results = q.fetch(1) 
    if len(results) > 0:
        return results[0]
    else:
        rtc_bill = RTC.Bill.get_bill(bill_id='hr'+str(bill_number)+'-112')
        if rtc_bill:
            congress_person = get_or_create_new_congress_person(rtc_bill)
            
            #do a fallback or some formatting on the summary field
            summary = rtc_bill.summary;
            if rtc_bill.summary == None:
                summary = rtc_bill.official_title
            else:
                summary_split_list = str(rtc_bill.summary).split(' - ', 1)
                if len(summary_split_list) > 1:
                    summary = summary_split_list[1]
                else:
                    summary_split_list = str(rtc_bill.summary).split('.', 1)
                    if len(summary_split_list) > 1:
                        summary = summary_split_list[1]
            short_title = rtc_bill.short_title if rtc_bill.short_title else "No Title"
            official_title = rtc_bill.official_title if rtc_bill.short_title else "No Title"
            popular_title = rtc_bill.popular_title if rtc_bill.short_title else "No Title"
            
            #create the new bill
            new_bill = Bill(rtc_id=rtc_bill.bill_id,
                            number=int(bill_number),
                                    chamber=db.Category((rtc_bill.chamber).capitalize()),
                                    summary=summary,
                                    short_title=short_title, 
                                    official_title=official_title,
                                    popular_title=popular_title,
                                    introduced_at=rtc_bill.introduced_at,
                                    #house_passage_result = rtc_bill.house_passage_result,
                                    #house_passage_result_at = rtc_bill.house_passage_result_at,
                                    #senate_passage_result = rtc_bill.senate_passage_result,
                                    #senate_passage_result_at = rtc_bill.senate_passage_result, 
                                    sponsor=congress_person
                            )
            new_bill.put()
            return new_bill

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


    #extract committee activity. structure:
    #<p>
    #  <u>
    #    <b>committee activity of the day</b>
    #  </u>
    #  <br>
    #  committee description
    #  <a>link to topic</a>
    #</p>

def extract_committee_link_from_block(block):
    committee_text = block.contents[0]
    committee_href = block['href']
    #print "committee text = " + str(committee_text)
    #print "committee link = " + str(committee_href)

def extract_committee_info_from_block(block):
    committee_description_regex = re.compile(r'([a-z|\s]*)\s+committee\s+hearing.*', re.IGNORECASE)
    block_contents = str(block.contents)
    #print "description bnlock contents = "+ str(block.contents)
    comittee_description_results = committee_description_regex.search(block_contents)
    if comittee_description_results :
        description = str(comittee_description_results.group(1))
        #print "committee description = " + description
        return description
    return None    

def is_committee_activity_block(block):
    committee_finder_regex = re.compile(r'committee\s*activity', re.IGNORECASE)
    block_contents = str(block.contents)
    comittee_finder_results = committee_finder_regex.search(block_contents)
    if comittee_finder_results :
        return True
    return None


def scrape_week():
    page = urllib2.urlopen("http://majorityleader.gov/floor/weekly.html")
    soup = BeautifulSoup(page)
    #ps = soup.findAll('p')
    
    #find all uppercase tags, which will contain the dates
    for u in soup.html.body.findAll('u'):
        parent = u.parent
        #find the date tag again
        date = u.find('b')
        #print date.contents[0]
        #find the summary for that date
        regex = re.compile(r'<br />(.*)</p>')
        m = regex.search(str(parent))
        #print m.group(1)
        
        #find the next-next sibling, which would contain any bills
        sibling = parent.nextSibling.nextSibling
        #find the links to bills within that sibling
        bill_links = sibling.findAll('a')
        #extract the bill number
        regex = re.compile(r'>.* (\d+)</a>')
        #extract the bill href
        regex2 = re.compile(r'href="(.*)"')
        #extract the bill description
        regex3 = re.compile(r'- (.*)')
        
        for bl in bill_links:
            try:
                number = regex.search(str(bl)).group(1)
                href = regex2.search(str(bl)).group(1)
                #print 'number = ' + number
                #print 'href = ' + href
                billtextnode = bl.parent.nextSibling
                billtext = regex3.search(str(billtextnode)).group(1)
                #print 'bill descr = ' + billtext

                #old_bill = Bill.get_by_key_name(number=int(number))
                
                #find any existing record of this bill
                q = Bill.all()
                q.filter("number =", int(number))
                results = q.fetch(1)
                bill = None
                                    
                if len(results) == 0:
                    #print "new billah"
                    new_bill = Bill(number=int(number),
                                    href=str(href),
                                    title=str(billtext),
                                    house=db.Category('houseofreps')                                
                                    )
                    new_bill.put()
                    bill = new_bill
                else:
                    bill = results[0]
                
                new_activity = Activity(bill=bill)
                new_activity.put()
            except Exception as e:
                print e
                continue
    

class CongressionalVotesWorker(webapp.RequestHandler):
    def get(self):
        q = Activity.all()
        q.order('-day')
        activities = q.fetch(1)
        for a in activities:
            db_bill = a.bill
            #rtc_bill = RTC.Bill.get_bill(bill_id=db_bill.bill_id)
            rtc_votes = RTC.Votes.get_by_bill(db_bill.rtc_id).votes
            last_house_day = 0
            last_senate_day = 0
            logging.debug("FETCHED RTC VOTES:  COUNT = " + str(len(rtc_votes)))
       
            for v in rtc_votes:
                logging.debug("looking for a passage vote")
                if str(v.vote_type) == 'passage':
                    #create the new c vote
                    c_vote = get_or_create_new_c_vote(v, db_bill)                    
                    
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

