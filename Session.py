import asana
import datetime
import random
import json

# Session object for performing CRUD operations on your
# Asana project.
class Session:
	
	# Initiates a Session object for modifying Asana project
	def __init__(self,session_config_file):
		session = json.load(open(session_config_file))
		
		self.client = asana.Client.access_token(session["access_token"])
		self.wksp_name = session['workspace_name']
		self.proj_name = session['project_name']
		self.late_threshold = session['late_threshold'] # In days
		self.today = datetime.datetime.now()
		
		workspace = [x for x in self.client.workspaces.find_all() if x['name'].upper() == self.wksp_name.upper()][0]
		projects = list(self.client.projects.find_all({'workspace': workspace['id']}))
		project_id = [x for x in projects if x['name'].upper() == self.proj_name.upper()][0]['id']
		
		self.wksp_id = workspace['id']
		self.proj_id = project_id
	
	# Creates an asana task with a due date
	# 	task_name: String description of task
	#	due_date_offset: Number of days from today that
	#					this task will be due.
	def create_task(self,task_name,due_date_offset):
		due_date = self.today + datetime.timedelta(days=due_date_offset)
		due_date = str(due_date)[0:10]
		self.client.tasks.create_in_workspace(self.wksp_id,{'name':task_name,'due_on':due_date, 'projects': [self.proj_id]})

	# Get details associated with an Asana task by it's ID
	def get_task_details(self,task_id):
		return self.client.tasks.find_by_id(task_id)
	
	# Deletes any and all asana tasks within the
	# project defined within the session having
	# task name task_name
	#
	# If multiple tasks exist with name task_name,
	# all of them will be deleted
	def delete_task(self,task_name):
		tasks = self.client.tasks.find_all({'project':self.proj_id})
		task_list = [x for x in tasks if x['name'].upper()==task_name.upper()]
		for task in task_list:
			self.client.tasks.delete(task['id'])
			
	
	# Updates the due date of an past-due tasks
	# using a due date offset (in days)
	def update_due_dates(self,due_date_offset):
		tasks = self.client.tasks.find_all({'project':self.proj_id})
		date_push = datetime.timedelta(days=due_date_offset)
		threshold = datetime.timedelta(days=self.late_threshold)
		
		for task in tasks:
			det = self.get_task_details(task['id'])
			if det['completed']==False and det['due_on'] is not None:
				due_date = datetime.datetime.strptime(det['due_on'],'%Y-%m-%d')
				real_late = due_date + threshold < self.today
				if real_late:
					new_due_date = self.today + date_push
					new_due_date = str(new_due_date)[0:10]
					self.client.tasks.update(task['id'],{'due_on':new_due_date})
			