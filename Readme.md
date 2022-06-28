# Personal Scheduler

* loads events (meeting, appointments) from CalDAV, e.g. Nextcloud
* loads todos from CalDAV, e.g. Nextcloud
* tries to schedule the todos on your work days in the slots between the events
  * todos are schedules with a earliest deadline-first approach combined with a priority scheduling

* Important:
  * supports hierarchical todos, i.e., todos with subtodos. Subtodos are interpreted as dependencies of todos.
  * Only todos with deadlines are scheduled.
  * Todos need to have the first line `DURATION=hours`, where `hours` is the estimated duration of the todo as float.
  * Partial completion of a todo can be indicated by the partial-completion field.

* Configuration: With .env-file with the fields
  * `caldav_url` url of the caldav-server that has the events, e.g. 'https://nc.exmple.de/remote.php/dav'
  * `username` username of the caldav-server that has the events
  * `password` password of the caldav-server that has the events
  * `cal` name of the calendar that has the events
  * `caldav_url2` url of the caldav-server that has the todos, e.g. 'https://nc.exmple.de/remote.php/dav'
  * `username2` username of the caldav-server that has the todos
  * `password2` password of the caldav-server that has the todos
  * `cal2` name of the calendar that has the todos
  * `scheduledays` schedule this many days into the future, e.g. 30 for 30 days
  * `timeslice` length of a scheduling time slice in minutes, e.g. 30 minutes
  * `startofwork` hour of day where the work starts, e.g. 9 for 9:00 local time
  * `endofwork` hour of day where the work ends, e.g. 17 for 17:00 local time

* Output:
  * Either a message complaining about missing information
  * Either a message that the todos couldn't be scheduled, aka. too much to do and not enough time
  * or a list of scheduled slots and a files `plan.html` with Gantt chart for the next few days
