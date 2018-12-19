import os
import geckoboard

CLIENT = geckoboard.client(os.getenv('GECKO_API_KEY'))

def ping():
    try:
        CLIENT.ping()
        print('Authentication successful')
    except:
        print('Incorrect API key')
