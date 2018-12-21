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
    }
}


def as_dataset():
    raw_schedule = current_agent_statuses()
    return [{'agent': k, 'group': v} for k, v in raw_schedule.items()]
