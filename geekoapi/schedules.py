import datetime
from .sheets import current_agent_statuses

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


def as_dataset():
    raw_schedule = current_agent_statuses()
    return [{'agent': k.upper(), 'group': v.upper(), 'online': 0} for k, v in raw_schedule.items()]
