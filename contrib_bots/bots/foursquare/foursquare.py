from __future__ import print_function
from __future__ import absolute_import

import datetime as dt
import re
import requests
from os.path import expanduser
from six.moves import configparser as cp
from six.moves import range

home = expanduser('~')
CONFIG_PATH = home + '/zulip/contrib_bots/bots/foursquare/FourSquareBot/settings.ini'

def get_api_key():
    # settings.ini must have been moved from
    # ~/zulip/contrib_bots/bots/foursquare/FourSquareBot/settings.ini into
    # ~/settings.ini for program to work
    # see doc.md for more information
    with open(CONFIG_PATH) as settings:
        config = cp.ConfigParser()
        config.readfp(settings)
        return config.get('Foursquare', 'api_key')

class FoursquareHandler(object):
    def __init__(self):
        self.api_key = get_api_key()

    def usage(self):
        return '''
            This plugin allows users to search for restaurants nearby an inputted
            location to a limit of 3 venues for every location. The name, address
            and description of the restaurant will be outputted.
            It looks for messages starting with '@foursquare'.
            If you need help, simply type:
            @foursquare /help into the Compose Message box

            Sample input:
            @foursquare Chicago, IL
            @foursquare help
            '''

    help_info = '''
The Foursquare bot can receive keyword limiters that specify the location, distance (meters) and
cusine of a restaurant in that exact order.
Please note the required use of quotes in the search location.

Example Inputs:
@foursquare 'Millenium Park' 8000 donuts
@foursquare 'Melbourne, Australia' 40000 seafood
                '''

    def triage_message(self, message, client):
        callers = ['@FourSquare', '@Foursquare', '@foursquare', '@4square', '@4sq']
        for call in callers:
            if call in message['content']:
                return True
                break
        return False

    def format_json(self, venues):
        def format_venue(venue):
            name = venue['name']
            address = ', '.join(venue['location']['formattedAddress'])
            keyword = venue['categories'][0]['pluralName']
            blurb = '\n'.join([name, address, keyword])
            return blurb

        return '\n'.join(format_venue(venue) for venue in venues)

    def send_info(self, message, letter, client):
        if message['type'] == 'private':
            client.send_message(dict(
                type='private',
                to=message['sender_email'],
                content=letter,
            ))
        else:
            client.send_message(dict(
                type='stream',
                subject=message['subject'],
                to=message['display_recipient'],
                content=letter,
            ))

    def handle_message(self, message, client, state_handler):
        words = message['content'].split()
        if "/help" in words:
            self.send_info(message, self.help_info, client)
            return

        # These are required inputs for the HTTP request.
        try:
            params = {'limit': '3'}
            params['near']  = re.search('\'[A-Za-z]\w+[,]?[\s\w+]+?\'', message['content']).group(0)
            params['v'] = 20170108
            params['oauth_token'] = self.api_key
        except AttributeError:
            pass

        # Optional params for HTTP request.
        if len(words) >= 2:
            try:
                params['radius'] = re.search('([0-9]){3,}', message['content']).group(0)
            except AttributeError:
                pass
            try:
                params['query'] = re.search('\s([A-Za-z]+)$', message['content']).group(0)[1:]
            except AttributeError:
                params['query'] = 'food'

        response = requests.get('https://api.foursquare.com/v2/venues/search?',
                                params=params)
        print(response.url)
        if response.status_code == 200:
            received_json = response.json()
        else:
            self.send_info(message,
                           "Invalid Request\nIf stuck, try '@foursquare help'.",
                           client)
            return

        if received_json['meta']['code'] == 200:
            response_msg = ('Food nearby ' + params['near'] +
                            ' coming right up:\n' +
                            self.format_json(received_json['response']['venues']))
            self.send_info(message, response_msg, client)
            return

        self.send_info(message,
                       "Invalid Request\nIf stuck, try '@foursquare help'.",
                       client)
        return

handler_class = FoursquareHandler

def test_get_api_key():
    # must change to your own api key for test to work
    result = get_api_key()
    assert result == 'abcdefghijksm'

if __name__ == '__main__':
    test_get_api_key()
    print('Success')
