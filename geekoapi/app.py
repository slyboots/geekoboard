import os
import json
import geckoboard


DATASET_NAME = 'agents.active_groups'
CLIENT = geckoboard.client(os.getenv('GECKO_API_KEY'))


try:
    CLIENT.ping()
except:
    raise PermissionError('API key invalid.')


def get_schedule(schema):
    print(f"Retrieving gecko dataset: {DATASET_NAME}")
    return CLIENT.datasets.find_or_create(DATASET_NAME, schema)


def set_schedule(data, schema):
    print(f"Setting schedule with data:\n{json.dumps(data,indent=2)}")
    schedule = get_schedule(schema)
    schedule.put(data)


def delete_schedule():
    print(f"Deleting gecko dataset: {DATASET_NAME}")
    CLIENT.datasets.delete(DATASET_NAME)
