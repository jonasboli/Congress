from google.appengine.ext import webapp

register = webapp.template.create_template_register()

@register.inclusion_tag('tagtemplates/bill_list_item.html')
def show_bill_list_item(bill):
    return {'bill': bill}

@register.inclusion_tag('tagtemplates/bill_list_item_with_votes.html')
def show_bill_list_item_with_votes(user, bill):
    return {'user': user,
            'bill': bill}


@register.inclusion_tag('tagtemplates/vote_buttons.html')
def show_vote_buttons(bill):
    return {'bill': bill}

@register.inclusion_tag('tagtemplates/vote_counts.html')
def show_vote_counts(user, bill):
    return {'bill': bill,
            'vote': user.get_vote_for_bill(bill),
            'aye_count': bill.get_aye_count(),
            'nay_count': bill.get_nay_count(),
            'abstention_count': bill.get_abstention_count(),
            'last_house_vote': bill.get_last_house_vote(),
            'last_senate_vote': bill.get_last_senate_vote()
            }

@register.inclusion_tag('tagtemplates/congressionalvote_counts.html')
def show_congressionalvote_counts(c_v):
    return {'c_v': c_v}
