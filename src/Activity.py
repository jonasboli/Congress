import logging
import datetime 

from google.appengine.ext import db

import Bill

class Activity(db.Model):
    bill = db.ReferenceProperty(Bill.Bill)
    day = db.DateTimeProperty()
    activity_description = db.StringProperty()
    committee_description = db.StringProperty()

    @staticmethod
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

    @staticmethod
    def get_most_recent_day():
        q = Activity.all()
        q.order('-day')
        results = q.fetch(1)
        if (len(results) > 0):
            most_recent_day = results[0].day
            return most_recent_day
        return None
    
    @staticmethod
    def get_activities_by_day(date_obj):
        q = Activity.all()
        q.filter('day = ', date_obj)
        q.order('-day')
        results = q.fetch(50)
        if (len(results) > 0):
            return results
        return None


    @staticmethod
    def get_recent_N_days_activities(count_days):
        q = Activity.all()
        q.filter('day > ', (datetime.datetime.now() - datetime.timedelta(count_days)))
        q.filter('day < ', Activity.get_most_recent_day())
        q.order('-day')
        results = q.fetch(50)
        if (len(results) > 0):
            return results
        return None

    @staticmethod
    def get_previous_day(reference_day):
        q = Activity.all()
        q.order('-day')
        results = q.run()
        for a in results:
            if a.day < reference_day:
                return a.day

    @staticmethod
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
    
