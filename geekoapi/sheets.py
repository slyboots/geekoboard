import os
import datetime
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools

# If modifying these scopes, delete the file token.json.
SCOPES = 'https://www.googleapis.com/auth/spreadsheets.readonly'
CREDENTIALS = os.getenv('GOOGLE_SHEETS_CLIENT_CREDENTIALS')
TOKEN = os.getenv('GOOGLE_SHEETS_TOKEN')

# spreadsheet / range info
SHEET_ID = os.getenv('SCHEDULE_SHEET_ID')
AGENT_SCHEDULES_RANGE = 'AgentSchedules'
SCHEDULE_TIMELINE_RANGE = 'ScheduleTimeline'

def current_hour():
    '''gets the current hour out of 24 as an int'''
    return datetime.datetime.now().hour


def to_24hour(hourstring):
    '''converts a time string like 8AM or 5PM to an int representing its 24 hour value'''
    offset = 12 if all(x not in hourstring for x in['12', 'AM']) else 0
    return (int(hourstring[:-2])+offset)%24


def get_service():
    store = file.Storage(TOKEN)
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets(CREDENTIALS, SCOPES)
        creds = tools.run_flow(flow, store)
    service = build('sheets', 'v4', http=creds.authorize(Http()))
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
        # print(f"Getting {agent}'s status for timeblock {timeblock}")
        try:
            agent_statuses[agent] = schedule[timeblock]
        except IndexError:
            # print(f"{row[0]} has nothing for timeblock {timeblock}")
            agent_statuses[agent] = ""
    return agent_statuses
