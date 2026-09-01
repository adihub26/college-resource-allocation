# College Event Resource Allocation System

A web application built with Flask for managing college events and allocating shared resources such as auditoriums, laboratories, projectors, microphones, cameras, and computers.

The system focuses on event management, resource management, resource requests, resource availability, conflict detection, resource suitability, alternative resource suggestions, approval/rejection, and database-based resource allocation.

---

# 1. Objective

The objective of this project is to develop a simple and functional web application that allows a college to manage events and shared resources efficiently.

The application prevents resource conflicts, validates resource requests, suggests alternatives when resources are unavailable or unsuitable, and manages the complete resource request and allocation workflow.

The main focus of the project is:

- Backend functionality
- Database usage
- Validation
- Resource allocation logic
- Conflict detection
- Error handling
- Simple and usable UI

---

# 2. Technology Used

The application is developed using the following technologies:

- Python 3.10+
- Flask
- Flask-SQLAlchemy
- SQLAlchemy
- SQLite
- HTML
- CSS
- Jinja2
- Tailwind CSS
- Basic JavaScript
- Flask-Migrate
- Git
- GitHub

---

# 3. Event Management

The application allows users to manage college events.

Users can:

- Create an event
- View events
- Edit an event
- Cancel an event
- Filter events by status
- Filter events by date

## Event Information

Each event contains:

- Event name
- Organizer
- Expected attendance
- Start date/time
- End date/time
- Status

## Event Statuses

The following statuses are supported:

- Draft
- Pending
- Approved
- Rejected
- Cancelled
- Completed

## Event Validation

The system validates:

- Event name
- Organizer
- Expected attendance
- Start date/time
- End date/time
- Event status

Expected attendance must be greater than zero.

The event end time must be after the event start time.

---

# 4. Resource Management

The application allows administrators to manage college resources.

Administrators can:

- Add resources
- Edit resources
- Activate resources
- Deactivate resources
- View resources
- View resource availability

## Resource Information

Each resource contains:

- Resource name
- Resource type
- Capacity, if applicable
- Active/inactive status

## Supported Resource Types

The application supports:

- Auditorium
- Laboratory
- Projector
- Microphone
- Camera
- Computer

Inactive resources cannot be allocated to events.

---

# 5. Resource Requests

Organizers can request one or more resources for an event.

A resource request contains:

- Event
- Start date/time
- End date/time
- Required resources
- Quantity of each resource

For example:

    Event: Technical Workshop
    Date: 20 September 2026
    Time: 10:00 AM - 2:00 PM

    Resources:
    - Auditorium
    - Projector
    - 2 Microphones

The system validates the request before it is submitted.

## Request Validation

The system checks:

- Whether the event exists
- Whether the selected event is valid
- Whether the requested time is valid
- Whether the request time is within the event schedule
- Whether the resources are active
- Whether the quantity is valid
- Whether the resource has sufficient capacity
- Whether the resource is already allocated

---

# 6. Preventing Double Booking

The application prevents a resource from being allocated to two events during overlapping time periods.

Conflict detection is performed on the backend.

The conflict condition is:

    Existing Allocation Start < Requested End
    AND
    Existing Allocation End > Requested Start

If both conditions are true, the requested resource has a time conflict.

## Example

Existing allocation:

    Auditorium
    10:00 AM - 2:00 PM

New request:

    Auditorium
    12:00 PM - 4:00 PM

Result:

    Rejected

The times overlap, so the resource cannot be allocated.

## Back-to-Back Allocation

Existing allocation:

    Auditorium
    10:00 AM - 2:00 PM

New request:

    Auditorium
    2:00 PM - 4:00 PM

Result:

    Allowed

An allocation ending exactly when another allocation starts is not considered a conflict.

---

# 7. Resource Suitability

The system checks whether a requested resource is suitable for the event.

## Capacity Check

If a resource has a defined capacity, its capacity must be greater than or equal to the expected event attendance.

Example:

    Event attendance: 200
    Resource capacity: 100

Result:

    Resource cannot be allocated.

If the resource does not have a defined capacity, the capacity check is not required.

## Resource Type

The system also checks resource type suitability.

A resource must be of the appropriate type for the requested requirement.

For example:

    Required type: Projector
    Resource type: Microphone

The resource is not suitable for the requirement.

---

# 8. Alternative Resources

If a requested resource is unavailable or unsuitable, the application searches for alternative resources.

Alternative resources are selected based on the following conditions:

1. The alternative must be active.
2. The alternative must have the same resource type.
3. The alternative must meet the required capacity.
4. The alternative must be available during the requested time.
5. The alternative must not have an overlapping active allocation.
6. The originally requested resource is excluded.

The suitable alternatives are displayed to the user.

## Example

Requested resource:

    Hall A
    Capacity: 150
    Time: 2:00 PM - 4:00 PM
    Status: Unavailable

Possible alternative:

    Hall B
    Capacity: 200
    Time: 2:00 PM - 4:00 PM
    Status: Available

Result:

    Hall B is suggested as an alternative.

---

# 9. Approval and Allocation

The resource request follows a basic approval workflow.

    Pending
       |
       v
    Approved
       |
       v
    Allocated

A request can also be rejected:

    Pending
       |
       v
    Rejected

## Approval

When an administrator approves a resource request:

1. The request is validated.
2. All requested resources are checked.
3. Resource conflicts are checked.
4. Resource capacity is checked.
5. Allocations are created.
6. The request status becomes Approved.
7. The event status becomes Approved.
8. The allocations receive the Allocated status.

---

# 10. Multiple Resource Transaction

If an event requests multiple resources, all resources must be available before any allocation is created.

For example:

    Auditorium  -> Available
    Projector   -> Available
    Microphone  -> Unavailable

The complete request fails.

The system does not allocate the auditorium and projector partially.

The application uses a database transaction to prevent partial allocation.

If an error occurs during allocation:

    db.session.rollback()

is used to roll back the changes.

This ensures that either all requested resources are allocated or none are allocated.

---

# 11. Cancellation

The application supports cancellation of events and resource requests.

## Event Cancellation

When an event is cancelled:

- The event status becomes Cancelled.
- Pending requests associated with the event are cancelled.
- Approved requests associated with the event are cancelled.
- Active allocations associated with those requests are cancelled.

This releases the resources for future use.

Completed events cannot be cancelled.

## Resource Request Cancellation

Approved requests can be cancelled.

When an approved request is cancelled:

- The request status becomes Cancelled.
- Associated active allocations become Cancelled.
- The resources become available for future requests.

Rejected and completed requests cannot be cancelled.

---

# 12. Automatic Event Completion

The application automatically checks for approved events whose end time has passed.

When an approved event reaches its end time:

    Event              -> Completed
    Resource Request   -> Completed
    Allocation         -> Completed

This keeps event and resource statuses synchronized with the actual event schedule.

Completed events and allocations are no longer considered active allocations.

---

# 13. Resource Availability

The application provides a Resource Availability page.

The page displays:

- Resource name
- Resource type
- Capacity
- Current status
- Current event
- Allocation time

A resource can have the following availability states:

- Available
- Allocated
- Inactive

An active resource with no current allocation is shown as Available.

An active resource currently being used is shown as Allocated.

An inactive resource is shown as Inactive.

---

# 14. Dashboard

The dashboard provides an overview of the system.

It displays:

- Total events
- Total resources
- Active resources
- Total resource requests
- Pending requests
- Active allocations
- Approved requests
- Recent events
- Recent resource requests

The dashboard provides quick access to the major sections of the application.

---

# 15. User Interface

The application provides simple and usable pages for:

- Dashboard
- Events
- Resources
- Resource Requests
- Resource Availability
- Allocations
- Create Event
- Edit Event
- Create Resource
- Edit Resource
- Create Resource Request

Tailwind CSS is used to provide basic styling and responsive layouts.

Basic JavaScript is used for functionality such as automatically filling the resource request time based on the selected event.

---

# 16. Validation and Error Handling

The application provides clear error messages for invalid operations.

The system handles cases such as:

- Missing required information
- Invalid attendance
- Negative attendance
- Invalid date/time
- End time before start time
- Invalid resource type
- Invalid resource quantity
- Inactive resource
- Insufficient capacity
- Resource already booked
- Invalid event
- Invalid resource request
- Attempting to approve an already processed request
- Attempting to cancel a completed request
- Database operation failures

The application uses flash messages to display user-friendly errors.

Python tracebacks are not intentionally displayed to users.

Database operations use rollback handling when an error occurs.

---

# 17. Database Design

The application uses SQLite with SQLAlchemy.

The main database tables are:

    events
    resources
    resource_requests
    request_resources
    allocations

## Events

Stores college event information.

Main fields include:

- id
- event_name
- organizer
- expected_attendance
- start_datetime
- end_datetime
- status
- created_at
- updated_at

## Resources

Stores college resource information.

Main fields include:

- id
- name
- type
- capacity
- is_active
- created_at
- updated_at

## Resource Requests

Stores resource requests made for events.

Main fields include:

- id
- event_id
- start_datetime
- end_datetime
- status
- created_at

## Request Resources

Connects resource requests with resources.

Main fields include:

- id
- request_id
- resource_id
- quantity

## Allocations

Stores the actual allocated resources.

Main fields include:

- id
- request_id
- resource_id
- quantity
- start_datetime
- end_datetime
- status
- created_at

SQLAlchemy relationships are used to connect the database models.

---

# 18. Database Setup and Migration

The application uses SQLite as the database.

The database configuration is:

    sqlite:///college.db

Flask-Migrate is included for database migration management.

If the migration environment has not been created, initialize it using:

    flask db init

Create a migration using:

    flask db migrate -m "Initial database"

Apply the migration using:

    flask db upgrade

If the migration files already exist in the repository, run:

    flask db upgrade

The database is created and updated through the migration system.

---

# 19. Installation

## Step 1: Clone the Repository

Clone the GitHub repository:

    git clone <YOUR_GITHUB_REPOSITORY_URL>

Move into the project directory:

    cd college-resource-allocation

---

## Step 2: Create a Virtual Environment

On Windows:

    python -m venv venv

Activate the virtual environment:

    venv\Scripts\activate

On Linux/macOS:

    python3 -m venv venv

Activate it:

    source venv/bin/activate

---

## Step 3: Install Dependencies

Install the required Python packages:

    pip install -r requirements.txt

---

## Step 4: Database Setup

If required, run:

    flask db upgrade

---

## Step 5: Run the Application

Run:

    python run.py

The application will normally be available at:

    http://127.0.0.1:5000

Open the address in a web browser.

---

# 20. Project Structure

    college-resource-allocation/
    |
    |-- app/
    |   |-- __init__.py
    |   |-- models.py
    |   |-- routes.py
    |   |-- services.py
    |   |
    |   |-- templates/
    |       |-- base.html
    |       |-- dashboard.html
    |       |
    |       |-- events/
    |       |   |-- list.html
    |       |   |-- create.html
    |       |   |-- edit.html
    |       |
    |       |-- resources/
    |       |   |-- list.html
    |       |   |-- create.html
    |       |   |-- edit.html
    |       |   |-- availability.html
    |       |
    |       |-- requests/
    |       |   |-- list.html
    |       |   |-- create.html
    |       |
    |       |-- allocations/
    |           |-- list.html
    |
    |-- tests/
    |
    |-- migrations/
    |
    |-- .env.example
    |-- .gitignore
    |-- requirements.txt
    |-- README.md
    |-- run.py

---

# 21. Important Assumptions

The application uses the following assumptions:

1. Event attendance must be greater than zero.

2. Event end date/time must be after the start date/time.

3. Resource request time must fall within the event's scheduled time.

4. Inactive resources cannot be requested or allocated.

5. Resources with a defined capacity must be able to accommodate the expected event attendance.

6. Auditoriums and laboratories allow a maximum requested quantity of one.

7. A resource cannot have two overlapping active allocations.

8. An allocation ending exactly when another allocation starts does not create a conflict.

9. If one resource in a multi-resource request is unavailable, the entire request fails.

10. Cancelled allocations release the resource for future requests.

11. Completed events cannot be cancelled.

12. Completed resource requests cannot be cancelled.

13. Resources without a defined capacity do not require an attendance capacity check.

14. The system is designed as a basic college resource allocation system and does not implement user authentication or role-based access control unless added separately.

---

# 22. Conflict Detection Logic

The backend checks existing allocations before approving a resource request.

The conflict condition is:

    Allocation.start_datetime < requested_end_datetime
    AND
    Allocation.end_datetime > requested_start_datetime

If the condition is satisfied, the existing allocation overlaps the requested time.

Therefore, the resource cannot be allocated.

This logic also allows back-to-back bookings.

Example:

    Existing: 10:00 AM - 2:00 PM
    New:      2:00 PM - 4:00 PM

There is no overlap, so the new allocation is allowed.

---

# 23. Alternative Resource Selection Logic

Alternative resources are selected using the following process:

    1. Exclude the originally requested resource.
    2. Check that the alternative resource is active.
    3. Check that it has the same resource type.
    4. Check that it has sufficient capacity.
    5. Check for an existing allocation conflict.
    6. Return the resources that satisfy all conditions.

This ensures that suggested alternatives are actually suitable and available for the requested event.

---

# 24. Git and GitHub

Git is used for version control and GitHub is used to store the project repository.

The repository should contain:

- Source code
- README.md
- requirements.txt
- Database migration files
- .env.example, if required

The virtual environment should not be uploaded to GitHub.

The `.gitignore` file should exclude the virtual environment and other unnecessary local files.

Example:

    venv/
    __pycache__/
    *.pyc
    .env
    instance/
    *.db

---

# 25. Testing

The project contains a `tests` directory for application testing.

Important functionality to test includes:

- Event creation
- Event validation
- Resource creation
- Resource activation/deactivation
- Resource request creation
- Capacity validation
- Inactive resource validation
- Double booking prevention
- Alternative resource selection
- Request approval
- Request rejection
- Request cancellation
- Event cancellation
- Automatic completion
- Transaction rollback

---

# 26. Hosted Web Application

The assignment requires a hosted web application.

Hosted application link:

    <ADD_YOUR_DEPLOYED_WEB_APPLICATION_LINK_HERE>

Replace the placeholder above with the actual deployed application URL after deployment.

---

# 27. GitHub Repository

GitHub repository:

    <https://github.com/adihub26/college-resource-allocation>

Replace the placeholder above with the actual GitHub repository URL.

---

# 28. Submission Checklist

Before submitting the project, verify that the repository contains:

    [ ] Source code
    [ ] README.md
    [ ] requirements.txt
    [ ] Database migration files
    [ ] .env.example if required
    [ ] .gitignore
    [ ] tests directory
    [ ] GitHub repository
    [ ] Hosted web application
    [ ] Working application

---

# 29. Conclusion

The College Event Resource Allocation System provides a simple solution for managing college events and shared resources.

The application supports event management, resource management, resource requests, availability checking, conflict detection, resource suitability validation, alternative resource suggestions, approval and rejection workflows, cancellation, automatic completion, and transaction-based allocation.

The backend ensures that resources are not double-booked and that multiple-resource requests are handled atomically to prevent partial allocation.

The application provides a simple web interface while focusing primarily on functionality, backend logic, database usage, validation, and problem-solving.

---

# Author

Developed as a technical assignment for the College Event Resource Allocation System.