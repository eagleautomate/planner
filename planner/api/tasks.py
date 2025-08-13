import frappe
from frappe.utils import add_days, date_diff


@frappe.whitelist()
def get_events(month_start, month_end, employee_filters={}, task_filters={}):
        tasks = get_tasks(month_start, month_end, employee_filters, task_filters)
        return tasks


def get_tasks(month_start: str, month_end: str, employee_filters: dict[str, str], task_filters):
        cond = "AND task.status != 'Template' "

        for key, value in task_filters.items():
                cond += f"AND task.{key} = '{value}' "

        tasks = frappe.db.sql(
                f"""
                SELECT task.name, task.exp_start_date as start_date, task.exp_end_date as end_date,
                       task.project, task.subject, task.status, todo.allocated_to as user,
                       task.color, task.completed_on
                FROM `tabTask` as task
                JOIN `tabToDo` as todo ON todo.reference_name = task.name
                        AND todo.reference_type = 'Task'
                        AND todo.status = 'Open'
                WHERE task.exp_start_date <= "{month_end}"
                AND task.exp_end_date >= "{month_start}"
                {cond}
                """,
                as_dict=True,
        )

        user_tasks = {}
        for task in tasks:
                if task.project:
                        task.project_name = frappe.db.get_value('Project', task.project, 'project_name')

                user = task.user
                if user not in user_tasks:
                        user_tasks[user] = []
                user_tasks[user].append(task)
                if not task.get('color'):
                        task.color = "#EFF6FE"

                if task.status == "Completed":
                        task.color = "#dcfae7"

                if task.status == "Overdue":
                        task.color = "#fdf0f0"

        return user_tasks


def get_leaves(month_start, month_end, employee_filters):
	LeaveApplication = frappe.qb.DocType("Leave Application")
	Employee = frappe.qb.DocType("Employee")

	query = (
		frappe.qb.select(
			LeaveApplication.name.as_("leave"),
			LeaveApplication.employee,
			LeaveApplication.leave_type,
			LeaveApplication.from_date,
			LeaveApplication.to_date,
		)
		.from_(LeaveApplication)
		.left_join(Employee)
		.on(LeaveApplication.employee == Employee.name)
		.where(
			(LeaveApplication.docstatus == 1)
			& (LeaveApplication.status == "Approved")
			& (LeaveApplication.from_date <= month_end)
			& (LeaveApplication.to_date >= month_start)
		)
	)

	for filter in employee_filters:
		query = query.where(Employee[filter] == employee_filters[filter])

	return group_by_employee(query.run(as_dict=True))

	
def group_by_employee(events: list[dict]) -> dict[str, list[dict]]:
	grouped_events = {}
	for event in events:
		grouped_events.setdefault(event["employee"], []).append(
			{k: v for k, v in event.items() if k != "employee"}
		)
	return grouped_events

@frappe.whitelist()
def create_task(task_doc):
	new_task = frappe.new_doc('Task')
	new_task.subject = task_doc.get('subject')
	new_task.exp_start_date = task_doc.get('start_date')
	new_task.exp_end_date = task_doc.get('end_date')
	new_task.description = task_doc.get('description')
	new_task.status = task_doc.get('status')
	new_task.priority = task_doc.get('priority')
	new_task.project = task_doc.get('project',None)

	employees = [e.get('value') for e in task_doc.get('employees')]
	for employee in employees:
		new_task.append("employees", {"employee": employee})

	new_task.save()



@frappe.whitelist()
def get_default_company():
	return frappe.defaults.get_user_default("Company")

@frappe.whitelist()
def get_task(name):
	task = frappe.get_doc("Task", name)
	return task.as_dict()

@frappe.whitelist()
def update_task(task_doc):
	task = frappe.get_doc("Task", task_doc.get('name'))
	task.exp_start_date = task_doc.get('exp_start_date')
	task.exp_end_date = task_doc.get('exp_end_date')
	task.description = task_doc.get('description')
	task.status = task_doc.get('status')
	task.priority = task_doc.get('priority')
	task.project = task_doc.get('project',None)
	task.completed_on = task_doc.get('completed_on',None)
	employees = [e.get('value') for e in task_doc.get('employees')]
	task.employees = []
	for employee in employees:
		task.append("employees", {"employee": employee})

	task.save()
