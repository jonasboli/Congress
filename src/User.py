import logging
import datetime 

from google.appengine.ext import db

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

    def get_recent_bills(self, count):
        recent_bills = [] 
        for v in self.vote_set:
            #logging.debug("RECENT")
            #logging.debug("BILL: " + str(v.bill.number))
            #logging.debug("BILL LAST PASSAGE VOTE: " + str(v.bill.last_passage_vote_at))
            #logging.debug("USER LAST VISIT AT: " + str(self.last_visit_at))
 
            if v.bill.last_passage_vote_at == None:
                continue
           
            #filter to bills updated in the last N days
            if v.bill.last_passage_vote_at > (datetime.datetime.now() - datetime.timedelta(days=-count)):
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
            
            if v.bill.last_passage_vote_at == None:
                continue
            
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
