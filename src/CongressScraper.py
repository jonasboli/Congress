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

import User
import Bill
import Activity
import Vote
import CongressionalVote
import CongressPerson



class CongressScraper(object):
    
    def __init__(self):
        pass
    
    class BlockType:
        a = 1
        p = 2        
                 
    def scrape_day(self):
        #fetch the page to scrape
        page = urllib2.urlopen("http://majorityleader.gov/floor/daily.html")
        soup = BeautifulSoup(page)
        
        day = None
        b_blocks = soup.findAll('b')
        for b in b_blocks:
            day = self.extract_day_from_block(b)
            if day:
                break
        #if we couldnt figure out the day, abort
        if not day:
            print "cant find day"
            return
        
        #find all bills stuck in a <p> block
        p_blocks = soup.findAll('p') 
        for p in p_blocks:
            self.extract_bill_from_block(p, self.BlockType.p, day)        
    
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
    def extract_day_from_block(self, block):
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
    def extract_bill_from_block(self, block, block_type, day):
        bill_finder_regex = re.compile(r'H\.\s*R\.\s*(\d+)', re.IGNORECASE)
        block_contents = str(block.contents)
        print "block contents = " + block_contents
        bill_finder_results = bill_finder_regex.search(block_contents)
        if bill_finder_results:
            bill_number = bill_finder_results.group(1)
            action_type = None
            #if block_type == BlockType.a:
            #    action_type = find_action_type_in_block(block.parent, block_type)
            if block_type == self.BlockType.p and block.contents:
                action_type = self.find_action_type_in_block(block.contents[0], block_type)
            bill = Bill.Bill.get_or_create_new_bill(bill_number, 'house')
            Activity.Activity.get_or_create_new_activity(bill, day, action_type)
    
    
    
    def find_action_type_in_block(self, block, block_type):
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
        
    
        #extract committee activity. structure:
        #<p>
        #  <u>
        #    <b>committee activity of the day</b>
        #  </u>
        #  <br>
        #  committee description
        #  <a>link to topic</a>
        #</p>
    
    def extract_committee_link_from_block(self, block):
        committee_text = block.contents[0]
        committee_href = block['href']
        #print "committee text = " + str(committee_text)
        #print "committee link = " + str(committee_href)
    
    def extract_committee_info_from_block(self, block):
        committee_description_regex = re.compile(r'([a-z|\s]*)\s+committee\s+hearing.*', re.IGNORECASE)
        block_contents = str(block.contents)
        #print "description bnlock contents = "+ str(block.contents)
        comittee_description_results = committee_description_regex.search(block_contents)
        if comittee_description_results :
            description = str(comittee_description_results.group(1))
            #print "committee description = " + description
            return description
        return None    
    
    def is_committee_activity_block(self, block):
        committee_finder_regex = re.compile(r'committee\s*activity', re.IGNORECASE)
        block_contents = str(block.contents)
        comittee_finder_results = committee_finder_regex.search(block_contents)
        if comittee_finder_results :
            return True
        return None
    
    
    def scrape_week(self):
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
    
                    #old_bill = Bill.Bill.get_by_keyBill.Bille(number=int(number))
                    
                    #find any existing record of this bill
                    q = Bill.Bill.all()
                    q.filter("number =", int(number))
                    results = q.fetch(1)
                    bill = None
                                        
                    if len(results) == 0:
                        #print "new billah"
                        new_bill = Bill.Bill(number=int(number),
                                        href=str(href),
                                        title=str(billtext),
                                        house=db.Category('houseofreps')                                
                                        )
                        new_bill.put()
                        bill = new_bill
                    else:
                        bill = results[0]
                    
                    new_activity = Activity.Activity(bill=bill)
                    new_activity.put()
                except Exception as e:
                    print e
                    continue
