import logging
import datetime 

from google.appengine.ext import db

class User(db.Model):
    zip = db.StringProperty()
    user_id = db.StringProperty()
    last_visit_at = db.DateTimeProperty(default=datetime.datetime.now())
    
    def get_vote_for_bill(self, bill):
        q = self.vote_set
        q.filter('bill = ', bill)
        results = q.fetch(1)
        if len(results) > 0:
            return results[0]
        return None
    
    def get_recent_bills(self, count):
        recent_bills = [] 
        for v in self.vote_set:
            if v.bill.last_passage_vote_at == None:
                continue
           
            #filter to bills updated in the last N days
            if v.bill.last_passage_vote_at > (datetime.datetime.now() - datetime.timedelta(days=-count)):
                recent_bills = recent_bills + v.bill
                #TODO: sort the bills by updated date
        return recent_bills
    
    def get_update_count_since_last_visit(self):
        updated_bills = self.get_updated_bills_since_last_visit()
        if updated_bills:
            return len(updated_bills)
        return 0
    
    def get_updated_bills_since_last_visit(self):
        return self.__get_updated_bills(self.last_visit_at)
    
    def get_recently_updated_bills(self, max_days):
        return self.__get_updated_bills(datetime.datetime.now() - datetime.timedelta(days=max_days))
    
    def __get_updated_bills(self, updated_since_date):
        #TODO: sort the bills by updated date
        updated_bills = []
        votes = self.vote_set
        for v in votes:
            if not v.bill.last_passage_vote_at:
                continue
            if not (v.bill.last_passage_vote_at > updated_since_date):
                continue    
            logging.debug("UPDATED")
            logging.debug("BILL: " + str(v.bill.number))
            updated_bills = updated_bills + [v.bill]

        return updated_bills