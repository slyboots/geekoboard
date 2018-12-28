import os
import sys
import json
import logging
import datetime
import geckoboard
import requests
from googleapiclient.discovery import build
from google.oauth2 import service_account

# disable google api warnings
logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)

# VARS
DEBUG = os.getenv('DEBUG') == 'True'
GOOGLE_API_SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
GOOGLE_SHEETS_SERVICE_CREDENTIALS = os.getenv('GOOGLE_SHEETS_SERVICE_CREDENTIALS')
SCHEDULE_SHEET_ID = os.getenv('SCHEDULE_SHEET_ID')
AGENT_SCHEDULES_RANGE = 'AgentSchedules'
SCHEDULE_TIMELINE_RANGE = 'ScheduleTimeline'
ZD_API_URL = os.getenv('ZD_API_URL')
ZD_API_USER = os.getenv('ZD_API_USER')
ZD_API_KEY = os.getenv('ZD_API_KEY')
ZD_GROUP_ID = os.getenv('ZD_GROUP_ID')
ZD_API_TALK_ENDPOINT = os.getenv('ZD_API_TALK_ENDPOINT')
GECKO_CLIENT = geckoboard.client(os.getenv('GECKO_API_KEY'))
GECKO_DATASET_NAME = 'agents.active_groups'
GECKO_DATA_SCHEMA = {
    'agent': {
        'type': 'string',
        'name': 'Agent',
        'optional': False
    },
    'group': {
        'type': 'string',
        'name': "Group",
        'optional': False
    },
    'status': {
        'type': 'string',
        'name': 'Status',
        'optional': False
    }
}


def get_service():
    creds = service_account.Credentials.from_service_account_file(GOOGLE_SHEETS_SERVICE_CREDENTIALS, scopes=GOOGLE_API_SCOPES)
    service = build('sheets', 'v4', credentials=creds)
    return service.spreadsheets()


GS_SERVICE = get_service()

# GENERAL STUFF
def current_hour():
    '''gets the current hour out of 24 as an int'''
    return datetime.datetime.now(datetime.timezone(-datetime.timedelta(hours=6))).hour
def to_24hour(hourstring):
    '''converts a time string like 8AM or 5PM to an int representing its 24 hour value'''
    offset = 12 if all(x not in hourstring for x in['12', 'AM']) else 0
    return (int(hourstring[:-2])+offset)%24
def format_dataset(raw_schedule):
    print("Converting Google Sheets data to Geckoboard schema.")
    return [{'agent': k.upper(), 'group': v.upper() or 'OTHER', 'status': ''} for k, v in raw_schedule.items()]
# END GENERAL STUFF

# GECKBOARD STUFF
def get_gecko_dataset():
    return GECKO_CLIENT.datasets.find_or_create(GECKO_DATASET_NAME, GECKO_DATA_SCHEMA)
def set_gecko_dataset(data):
    print(f"Pushing new data to Geckoboard '{GECKO_DATASET_NAME}' dataset.")
    DEBUG and print(f"New data:\n{json.dumps(data)}")
    schedule = get_gecko_dataset()
    schedule.put(data)
    print(f"Geckoboard '{GECKO_DATASET_NAME}' dataset updated!")
def del_gecko_dataset():
    print(f"Deleting gecko dataset: {GECKO_DATASET_NAME}")
    GECKO_CLIENT.datasets.delete(GECKO_DATASET_NAME)
# END GECKOBOARD STUFF

# GOOGLE SHEETS STUFF
def get_schedule_timeline():
    timeline_range = GS_SERVICE.values().get(spreadsheetId=SCHEDULE_SHEET_ID, range=SCHEDULE_TIMELINE_RANGE).execute()
    values = timeline_range.get('values', [])
    if not values:
        raise ValueError(f"no data found for {SCHEDULE_TIMELINE_RANGE} range")
    timeline_formatted = [to_24hour(x) for x in values[0]]
    DEBUG and print(f"get_schedule_timeline: {json.dumps(timeline_formatted)}")
    return timeline_formatted
def get_agent_schedules():
    schedules_range = GS_SERVICE.values().get(spreadsheetId=SCHEDULE_SHEET_ID, range=AGENT_SCHEDULES_RANGE).execute()
    values = schedules_range.get('values', [])
    DEBUG and print(f"get_agent_schedules: {json.dumps(values)}")
    if not values: raise ValueError(f"{AGENT_SCHEDULES_RANGE} range empty")
    return values
def current_agent_statuses():
    print("Getting current schedule state from Google Sheets.")
    agent_statuses = {}
    timeblock = get_schedule_timeline().index(current_hour())
    schedules = get_agent_schedules()
    for row in schedules:
        agent, schedule = row[0], row[1:]
        try:
            agent_statuses[agent] = schedule[timeblock]
        except IndexError:
            agent_statuses[agent] = ""
    DEBUG and print(f"Agent statuses: {json.dumps(agent_statuses)}")
    return agent_statuses
# END GOOGLE SHEETS STUFF

# ZENDESK STUFF
def format_call_status(status):
    status_map = {
        'on_call': 'BUSY',
        'not_available': 'OFFLINE',
        'available': 'AVAILABLE',
        'wrap_up': 'WRAPUP'
    }
    return status_map.get(status)
def get_zendesk_talk_status(agent_id):
    talk_api = f"{ZD_API_URL}channels/voice/availabilities/{agent_id}.json"
    auth = requests.auth.HTTPBasicAuth(ZD_API_USER, ZD_API_KEY)
    zd_request = requests.get(talk_api, auth=auth)
    return format_call_status(zd_request.json()["availability"]["status"])
def get_zendesk_support_agents():
    support_agents = {}
    support_api = f"{ZD_API_URL}/users.json?role[]=agent&role[]=admin"
    auth = requests.auth.HTTPBasicAuth(ZD_API_USER, ZD_API_KEY)
    zd_request = requests.get(support_api, auth=auth)
    users = zd_request.json()
    for user in users['users']:
        default_name = user['name'].split(" ")[0]
        display_name = user['user_fields']['geckoboard_display_name']
        agent_name = (display_name or default_name).upper()
        support_agents[agent_name] = {
            'status': get_zendesk_talk_status(user['id'])
        }
    if DEBUG: print(f"agents: {support_agents}")
    return support_agents
def update_schedule_with_availability(schedule):
    print("Getting Zendesk Talk status for agents")
    agents = get_zendesk_support_agents()
    for i in schedule:
        i.update(agents[i['agent']])
    DEBUG and print(f"schedule with online status: {schedule}")
    # sorting the schedule for better display on geckoboard
    schedule.sort(key=lambda k: k['status'], reverse=True)
# END ZENDESK STUFF

# main function
def updateGeckoBoard():
    try:
        GECKO_CLIENT.ping()
    except:
        raise PermissionError('API key invalid.')
    if len(sys.argv) == 2:
        if sys.argv[1] == 'reset':
            del_gecko_dataset()
            sys.exit()
    current_schedule_status = current_agent_statuses()
    formatted_schedule = format_dataset(current_schedule_status)
    update_schedule_with_availability(formatted_schedule)
    set_gecko_dataset(formatted_schedule)

def lambda_handler(event, context):
    DEBUG and print(f"execution event: {event}")
    DEBUG and print(f"execution context: {context}")
    updateGeckoBoard()


if __name__ == '__main__':
    updateGeckoBoard()
