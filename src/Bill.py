import logging

from google.appengine.ext import db

import CongressPerson
import RTC
RTC.API_KEY = 'c448541518f24d79b652ccc57b384815'
RTC.apikey = 'c448541518f24d79b652ccc57b384815'


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
    sponsor = db.ReferenceProperty(CongressPerson.CongressPerson)
    last_passage_vote_at = db.DateTimeProperty()
    last_house_vote = db.Key()
    last_senate_vote = db.Key()
    
    @staticmethod
    def get_by_chamber_and_number(chamber, number):
        q = Bill.all()
        q.filter('chamber = ', str(chamber))
        q.filter('number = ', int(number))
        result = q.fetch(1)
        if(len(result) > 0):            
            return result[0]
        return None
    
    @staticmethod
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
                congress_person = CongressPerson.CongressPerson.get_or_create_new_congress_person(rtc_bill)
                
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
    
