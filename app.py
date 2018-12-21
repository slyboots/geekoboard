import sys
import json
from geekoapi import app, schedules

#set_schedule(**EXAMPLE_DATA_STARTEND_TIMES)
#set_scheduleset(EXAMPLE_DATA)
#delete_schedule()

if len(sys.argv) == 2:
    if sys.argv[1] == 'reset':
        app.delete_schedule()
        sys.exit()
print(f"Getting {app.DATASET_NAME} dataset")
schedule_dataset = app.get_schedule(schedules.SCHEDULE_SCHEMA)
print(f"Getting current schedule state")
current_schedule = schedules.as_dataset()
print(f"Current schedule state:\n{json.dumps(current_schedule, indent=2)}")
app.set_schedule(current_schedule, schedules.SCHEDULE_SCHEMA)
print("Dataset updated!")
