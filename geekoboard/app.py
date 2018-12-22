import os
import sys
import json
import logging
import datetime
import geckoboard
from googleapiclient.discovery import build
from google.oauth2 import service_account

# disable google api warnings
logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)
# VARS
CLIENT = geckoboard.client(os.getenv('GECKO_API_KEY'))
DATASET_NAME = 'agents.active_groups'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
CREDENTIALS = os.getenv('GOOGLE_SHEETS_SERVICE_CREDENTIALS')
TOKEN = os.getenv('GOOGLE_SHEETS_TOKEN')
SHEET_ID = os.getenv('SCHEDULE_SHEET_ID')
AGENT_SCHEDULES_RANGE = 'AgentSchedules'
SCHEDULE_TIMELINE_RANGE = 'ScheduleTimeline'
SCHEDULE_SCHEMA = {
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
    'online': {
        'type': 'number',
        'name': 'Status',
        'optional': True
    }
}


def current_hour():
    '''gets the current hour out of 24 as an int'''
    return datetime.datetime.now().hour
def to_24hour(hourstring):
    '''converts a time string like 8AM or 5PM to an int representing its 24 hour value'''
    offset = 12 if all(x not in hourstring for x in['12', 'AM']) else 0
    return (int(hourstring[:-2])+offset)%24
def format_dataset(raw_schedule):
    return [{'agent': k.upper(), 'group': v.upper(), 'online': 0} for k, v in raw_schedule.items()]

def get_schedule(schema):
    print(f"Retrieving gecko dataset: {DATASET_NAME}")
    return CLIENT.datasets.find_or_create(DATASET_NAME, schema)
def set_schedule(data, schema):
    print(f"Setting schedule with data:\n{json.dumps(data)}")
    schedule = get_schedule(schema)
    schedule.put(data)
def delete_schedule():
    print(f"Deleting gecko dataset: {DATASET_NAME}")
    CLIENT.datasets.delete(DATASET_NAME)


def get_service():
    creds = service_account.Credentials.from_service_account_file(CREDENTIALS, scopes=SCOPES)
    service = build('sheets', 'v4', credentials=creds)
    return service.spreadsheets()
def get_schedule_timeline(sheets=None):
    if not sheets:
        sheets = get_service()
    timeline_range = sheets.values().get(spreadsheetId=SHEET_ID, range=SCHEDULE_TIMELINE_RANGE).execute()
    values = timeline_range.get('values', [])
    if not values:
        raise ValueError(f"no data found for {SCHEDULE_TIMELINE_RANGE} range")
    else:
        return [to_24hour(x) for x in values[0]]
def get_agent_schedules(sheets=None):
    if not sheets:
        sheets = get_service()
    schedules_range = sheets.values().get(spreadsheetId=SHEET_ID, range=AGENT_SCHEDULES_RANGE).execute()
    values = schedules_range.get('values', [])
    if not values:
        raise ValueError(f"no data found for {AGENT_SCHEDULES_RANGE} range")
    else:
        return values
def current_agent_statuses():
    agent_statuses = {}
    timeblock = get_schedule_timeline().index(current_hour())
    schedules = get_agent_schedules()
    for row in schedules:
        agent = row[0]
        schedule = row[1:]
        try:
            agent_statuses[agent] = schedule[timeblock]
        except IndexError:
            agent_statuses[agent] = ""
    return agent_statuses


def lambda_handler(event, context):
    try:
        CLIENT.ping()
    except:
        raise PermissionError('API key invalid.')
    if len(sys.argv) == 2:
        if sys.argv[1] == 'reset':
            delete_schedule()
            sys.exit()
    print(f"Getting {DATASET_NAME} dataset")
    schedule_dataset = get_schedule(SCHEDULE_SCHEMA)
    print(f"Getting current schedule state")
    current_schedule = format_dataset(current_agent_statuses())
    print(f"Current schedule state:\n{json.dumps(current_schedule)}")
    set_schedule(current_schedule, SCHEDULE_SCHEMA)
    print("Dataset updated!")

if __name__ == '__main__':
    lambda_handler(None, None)
