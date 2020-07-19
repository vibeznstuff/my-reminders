import asana
import datetime
import random
import json
import pandas as pd

# Session object for performing CRUD operations on your
# Asana project.
class Session:

    # Initiates a Session object for modifying Asana project
    # The Session gets initialized using a JSON config file
    # which contains the relevent details about the Asana
    # project you wish to manipulate
    #
    # JSON Parameters:
    # 	"access_token": Asana access token (String)
    # 	"workspace_name": Asana workspace name (String)
    # 	"project_name": Asana Project name (String)
    # 	"late_threshold": Integer which flags tasks which are
    # 					  'Real Late' if their due date was this
    # 					  number of days old.
    def __init__(self, session_config_file):
        session = json.load(open(session_config_file))

        self.client = asana.Client.access_token(session["access_token"])
        self.wksp_name = session["workspace_name"]
        self.proj_name = session["project_name"]
        self.late_threshold = session["late_threshold"]  # In days
        self.today = datetime.datetime.now()
        try:
            self.sheets_url = session["sheets_url"]
        except:
            self.sheets_url = None

        workspace = [
            x
            for x in self.client.workspaces.find_all()
            if x["name"].upper() == self.wksp_name.upper()
        ][0]
        projects = list(self.client.projects.find_all({"workspace": workspace["gid"]}))
        project_id = [
            x for x in projects if x["name"].upper() == self.proj_name.upper()
        ][0]["gid"]

        self.wksp_id = workspace["gid"]
        self.proj_id = project_id

    # Gets section ID by name
    def get_section_id(self, section_name):
        sections = self.client.sections.find_by_project(self.proj_id)
        section = [x for x in sections if x["name"].upper() == section_name.upper()][0]
        return section["gid"]

    
    # Get list of users in workspace
    def get_user_gid(self, user_name):
        all_users = self.client.users.get_users({"workspace": self.wksp_id})

        for user in all_users:
            if user['name'].upper() == user_name.upper():
                return user['gid']

        print("User with user_name {} was not found in workspace.".format(user_name))
        return None
        

    # Creates an asana task with a due date
    # 	task_name: String description of task
    # 	due_date_offset: Number of days from today that
    # 					this task will be due.
    def create_task(self, task_name, section_name, due_date_offset, user_name):
        due_date = self.today + datetime.timedelta(days=due_date_offset)
        due_date = str(due_date)[0:10]
        section_id = self.get_section_id(section_name)

        user_gid = self.get_user_gid(user_name)

        if user_gid is None:
            raise ValueError("Could not find user name {} in workspace".format(user_name))

        self.client.tasks.create_in_workspace(
            self.wksp_id,
            {
                "name": task_name,
                "due_on": due_date,
                "projects": [self.proj_id],
                "assignee": user_gid,
                "memberships": [{"project": self.proj_id, "section": section_id}],
            },
        )

    # Get details associated with an Asana task by it's ID
    def get_task_details(self, task_id):
        return self.client.tasks.find_by_id(task_id)

    # Extracts a list of open (incomplete) tasks in the current
    # project.
    def get_open_tasks(self):
        task_list = self.client.tasks.find_all({"project": self.proj_id})
        open_list = []
        for task in task_list:
            det = self.get_task_details(task["gid"])
            if det["completed"] == False:
                open_list.append(det)
        return open_list

    # Deletes any and all asana tasks within the
    # project defined within the session having
    # task name task_name
    #
    # If multiple tasks exist with name task_name,
    # all of them will be deleted
    def delete_task(self, task_name):
        tasks = self.client.tasks.find_all({"project": self.proj_id})
        task_list = [x for x in tasks if x["name"].upper() == task_name.upper()]
        for task in task_list:
            self.client.tasks.delete(task["gid"])

    # Updates the due date of an past-due tasks
    # using a due date offset (in days)
    def update_due_dates(self, due_date_offset):
        tasks = self.client.tasks.find_all({"project": self.proj_id})
        date_push = datetime.timedelta(days=due_date_offset)
        threshold = datetime.timedelta(days=self.late_threshold)

        for task in tasks:
            det = self.get_task_details(task["gid"])
            if det["completed"] == False and det["due_on"] is not None:
                due_date = datetime.datetime.strptime(det["due_on"], "%Y-%m-%d")
                real_late = due_date + threshold < self.today
                if real_late:
                    new_due_date = self.today + date_push
                    new_due_date = str(new_due_date)[0:10]
                    self.client.tasks.update(task["gid"], {"due_on": new_due_date})

    # Archives tasks that have been completed for a while
    # Archived tasks to be stored in csv files/database for
    # reporting/analysis
    #
    # Archiving also will help ensure reasonable run-time over time
    # to keep number of tasks the Session methods will have
    # to search through low
    def archive_old_tasks(self):
        pass

    # Retrieves any open (incomplete) tasks which are past-due
    # Returns both the list of tasks as well as the count as
    # a tuple.
    #
    #
    def get_past_due_tasks(self):
        tasks = self.client.tasks.find_all({"project": self.proj_id})
        past_due_tasks = []

        for task in tasks:
            det = self.get_task_details(task["gid"])
            if det["completed"] == False and det["due_on"] is not None:
                due_date = datetime.datetime.strptime(det["due_on"], "%Y-%m-%d")
                past_due = due_date < self.today
                if past_due:
                    past_due_tasks.append(task)

        return (past_due_tasks, len(past_due_tasks))

    
    def load_tasks_from_google_sheets(self):

        tasks = pd.read_csv(self.sheets_url).to_dict('records')
        weekday = datetime.datetime.today().weekday()

        # Given actual weekday, resolve day_of_week to be the next week day
        # in order to create tasks for the following day tonight
        if weekday == 0:
            day_of_week = 'TUESDAY'
        elif weekday == 1:
            day_of_week = 'WEDNESDAY'
        elif weekday == 2:
            day_of_week = 'THURSDAY'
        elif weekday == 3:
            day_of_week = 'FRIDAY'
        elif weekday == 4:
            day_of_week = 'SATURDAY'
        elif weekday == 5:
            day_of_week = 'SUNDAY'
        elif weekday == 6:
            day_of_week = 'MONDAY'

        for task in tasks:
            if task['frequency'].upper() == 'DAILY':
                self.create_task(task['task_name'], task['section'], 1, task['owner'])

            if task['frequency'].upper() == 'WEEKLY':
                if day_of_week == task['dow'].upper():
                    self.create_task(task['task_name'], task['section'], 1, task['owner'])



