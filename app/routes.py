from flask import Blueprint, render_template, request, redirect, url_for, flash
from datetime import datetime

from app import db

from app.models import (
    Event,
    Resource,
    RequestResource,
    ResourceRequest,
    Allocation
)

from app.services import (
    approve_resource_request,
    find_alternative_resources
)


main = Blueprint("main", __name__)


# =========================================================
# EVENT STATUS SYNCHRONIZATION
# =========================================================

def sync_event_status(event):
    """
    Synchronize event status according to its
    resource requests.

    Rules:

    Approved request exists
        -> Event = Approved

    No Approved request but Pending request exists
        -> Event = Pending

    All requests are Cancelled/Rejected
        -> Event = Cancelled

    Completed event
        -> Remains Completed
    """

    if not event:
        return

    # Never automatically change a completed event
    if event.status == "Completed":
        return

    resource_requests = ResourceRequest.query.filter_by(
        event_id=event.id
    ).all()

    # No requests = keep existing status
    if not resource_requests:
        return

    has_approved = any(
        resource_request.status == "Approved"
        for resource_request in resource_requests
    )

    has_pending = any(
        resource_request.status == "Pending"
        for resource_request in resource_requests
    )

    # Approved has highest priority
    if has_approved:

        event.status = "Approved"

    elif has_pending:

        event.status = "Pending"

    else:

        # All requests are Rejected/Cancelled/Completed
        event.status = "Cancelled"


# =========================================================
# AUTOMATIC EVENT COMPLETION
# =========================================================

def update_completed_events():

    now = datetime.now()

    events_to_complete = Event.query.filter(
        Event.status == "Approved",
        Event.end_datetime <= now
    ).all()

    if not events_to_complete:
        return

    try:

        for event in events_to_complete:

            # -------------------------------------------------
            # Complete event
            # -------------------------------------------------

            event.status = "Completed"

            # -------------------------------------------------
            # Complete approved requests
            # -------------------------------------------------

            resource_requests = ResourceRequest.query.filter(
                ResourceRequest.event_id == event.id,
                ResourceRequest.status == "Approved"
            ).all()

            for resource_request in resource_requests:

                resource_request.status = "Completed"

                # -------------------------------------------------
                # Complete allocations
                # -------------------------------------------------

                allocations = Allocation.query.filter(
                    Allocation.request_id == resource_request.id,
                    Allocation.status == "Allocated"
                ).all()

                for allocation in allocations:

                    allocation.status = "Completed"

        db.session.commit()

    except Exception:

        db.session.rollback()


# =========================================================
# DASHBOARD
# =========================================================

@main.route("/")
def dashboard():

    update_completed_events()

    total_events = Event.query.count()

    total_resources = Resource.query.count()

    total_requests = ResourceRequest.query.count()

    total_allocations = Allocation.query.filter_by(
        status="Allocated"
    ).count()

    pending_requests = ResourceRequest.query.filter_by(
        status="Pending"
    ).count()

    approved_requests = ResourceRequest.query.filter_by(
        status="Approved"
    ).count()

    active_resources = Resource.query.filter_by(
        is_active=True
    ).count()

    recent_events = Event.query.order_by(
        Event.created_at.desc()
    ).limit(5).all()

    recent_requests = ResourceRequest.query.order_by(
        ResourceRequest.created_at.desc()
    ).limit(5).all()

    return render_template(
        "dashboard.html",
        total_events=total_events,
        total_resources=total_resources,
        total_requests=total_requests,
        total_allocations=total_allocations,
        pending_requests=pending_requests,
        approved_requests=approved_requests,
        active_resources=active_resources,
        recent_events=recent_events,
        recent_requests=recent_requests
    )


# =========================================================
# CREATE EVENT
# =========================================================

@main.route(
    "/events/create",
    methods=["GET", "POST"]
)
def create_event():

    if request.method == "POST":

        event_name = request.form.get(
            "event_name",
            ""
        ).strip()

        organizer = request.form.get(
            "organizer",
            ""
        ).strip()

        attendance = request.form.get(
            "expected_attendance",
            ""
        ).strip()

        start_datetime = request.form.get(
            "start_datetime",
            ""
        ).strip()

        end_datetime = request.form.get(
            "end_datetime",
            ""
        ).strip()

        status = request.form.get(
            "status",
            ""
        ).strip()

        # -------------------------------------------------
        # Required fields
        # -------------------------------------------------

        if not all([
            event_name,
            organizer,
            attendance,
            start_datetime,
            end_datetime,
            status
        ]):

            flash(
                "All fields are required.",
                "error"
            )

            return render_template(
                "events/create.html"
            )

        # -------------------------------------------------
        # Attendance validation
        # -------------------------------------------------

        try:

            attendance = int(attendance)

        except ValueError:

            flash(
                "Attendance must be a valid number.",
                "error"
            )

            return render_template(
                "events/create.html"
            )

        if attendance <= 0:

            flash(
                "Expected attendance must be greater than 0.",
                "error"
            )

            return render_template(
                "events/create.html"
            )

        # -------------------------------------------------
        # Date/time validation
        # -------------------------------------------------

        try:

            start = datetime.fromisoformat(
                start_datetime
            )

            end = datetime.fromisoformat(
                end_datetime
            )

        except ValueError:

            flash(
                "Invalid date or time.",
                "error"
            )

            return render_template(
                "events/create.html"
            )

        if start >= end:

            flash(
                "End date/time must be after start date/time.",
                "error"
            )

            return render_template(
                "events/create.html"
            )

        # -------------------------------------------------
        # Status validation
        # -------------------------------------------------

        valid_statuses = {
            "Draft",
            "Pending",
            "Approved",
            "Rejected",
            "Cancelled",
            "Completed"
        }

        if status not in valid_statuses:

            flash(
                "Invalid event status.",
                "error"
            )

            return render_template(
                "events/create.html"
            )

        # -------------------------------------------------
        # Create event
        # -------------------------------------------------

        event = Event(
            event_name=event_name,
            organizer=organizer,
            expected_attendance=attendance,
            start_datetime=start,
            end_datetime=end,
            status=status
        )

        try:

            db.session.add(event)

            db.session.commit()

            flash(
                "Event created successfully.",
                "success"
            )

            return redirect(
                url_for("main.dashboard")
            )

        except Exception:

            db.session.rollback()

            flash(
                "Unable to create event. Please try again.",
                "error"
            )

    return render_template(
        "events/create.html"
    )


# =========================================================
# EDIT EVENT
# =========================================================

@main.route(
    "/events/<int:event_id>/edit",
    methods=["GET", "POST"]
)
def edit_event(event_id):

    event = Event.query.get_or_404(
        event_id
    )

    if request.method == "POST":

        event_name = request.form.get(
            "event_name",
            ""
        ).strip()

        organizer = request.form.get(
            "organizer",
            ""
        ).strip()

        attendance = request.form.get(
            "expected_attendance",
            ""
        ).strip()

        start_datetime = request.form.get(
            "start_datetime",
            ""
        ).strip()

        end_datetime = request.form.get(
            "end_datetime",
            ""
        ).strip()

        status = request.form.get(
            "status",
            event.status
        ).strip()

        # -------------------------------------------------
        # Required fields
        # -------------------------------------------------

        if not all([
            event_name,
            organizer,
            attendance,
            start_datetime,
            end_datetime
        ]):

            flash(
                "All fields are required.",
                "error"
            )

            return render_template(
                "events/edit.html",
                event=event
            )

        # -------------------------------------------------
        # Attendance validation
        # -------------------------------------------------

        try:

            attendance = int(attendance)

        except ValueError:

            flash(
                "Attendance must be a valid number.",
                "error"
            )

            return render_template(
                "events/edit.html",
                event=event
            )

        if attendance <= 0:

            flash(
                "Expected attendance must be greater than 0.",
                "error"
            )

            return render_template(
                "events/edit.html",
                event=event
            )

        # -------------------------------------------------
        # Date/time validation
        # -------------------------------------------------

        try:

            start = datetime.fromisoformat(
                start_datetime
            )

            end = datetime.fromisoformat(
                end_datetime
            )

        except ValueError:

            flash(
                "Invalid date or time.",
                "error"
            )

            return render_template(
                "events/edit.html",
                event=event
            )

        if start >= end:

            flash(
                "End date/time must be after start date/time.",
                "error"
            )

            return render_template(
                "events/edit.html",
                event=event
            )

        # -------------------------------------------------
        # Status validation
        # -------------------------------------------------

        valid_statuses = {
            "Draft",
            "Pending",
            "Approved",
            "Rejected",
            "Cancelled",
            "Completed"
        }

        if status not in valid_statuses:

            flash(
                "Invalid event status.",
                "error"
            )

            return render_template(
                "events/edit.html",
                event=event
            )

        # -------------------------------------------------
        # Update event
        # -------------------------------------------------

        event.event_name = event_name
        event.organizer = organizer
        event.expected_attendance = attendance
        event.start_datetime = start
        event.end_datetime = end
        event.status = status

        try:

            db.session.commit()

            flash(
                "Event updated successfully.",
                "success"
            )

            return redirect(
                url_for("main.events")
            )

        except Exception:

            db.session.rollback()

            flash(
                "Unable to update event. Please try again.",
                "error"
            )

    return render_template(
        "events/edit.html",
        event=event
    )


# =========================================================
# CANCEL EVENT
# =========================================================

@main.route(
    "/events/<int:event_id>/cancel",
    methods=["POST"]
)
def cancel_event(event_id):

    event = Event.query.get_or_404(
        event_id
    )

    if event.status == "Cancelled":

        flash(
            "Event is already cancelled.",
            "error"
        )

        return redirect(
            url_for("main.events")
        )

    if event.status == "Completed":

        flash(
            "Completed events cannot be cancelled.",
            "error"
        )

        return redirect(
            url_for("main.events")
        )

    try:

        # -------------------------------------------------
        # Cancel event
        # -------------------------------------------------

        event.status = "Cancelled"

        # -------------------------------------------------
        # Find active requests
        # -------------------------------------------------

        resource_requests = ResourceRequest.query.filter(
            ResourceRequest.event_id == event.id,
            ResourceRequest.status.in_([
                "Pending",
                "Approved"
            ])
        ).all()

        for resource_request in resource_requests:

            resource_request.status = "Cancelled"

            # -------------------------------------------------
            # Cancel allocations
            # -------------------------------------------------

            allocations = Allocation.query.filter(
                Allocation.request_id == resource_request.id,
                Allocation.status == "Allocated"
            ).all()

            for allocation in allocations:

                allocation.status = "Cancelled"

        db.session.commit()

        flash(
            "Event cancelled and associated resources released.",
            "success"
        )

    except Exception:

        db.session.rollback()

        flash(
            "Unable to cancel event. Please try again.",
            "error"
        )

    return redirect(
        url_for("main.events")
    )


# =========================================================
# EVENTS LIST
# =========================================================

@main.route("/events")
def events():

    update_completed_events()

    # Synchronize event statuses
    all_events = Event.query.all()

    try:

        for event in all_events:

            sync_event_status(event)

        db.session.commit()

    except Exception:

        db.session.rollback()

    status = request.args.get(
        "status",
        ""
    ).strip()

    event_date = request.args.get(
        "date",
        ""
    ).strip()

    query = Event.query

    # -------------------------------------------------
    # Status filter
    # -------------------------------------------------

    if status:

        query = query.filter(
            Event.status == status
        )

    # -------------------------------------------------
    # Date filter
    # -------------------------------------------------

    if event_date:

        try:

            selected_date = datetime.strptime(
                event_date,
                "%Y-%m-%d"
            ).date()

            query = query.filter(
                db.func.date(
                    Event.start_datetime
                ) == selected_date
            )

        except ValueError:

            flash(
                "Invalid date format.",
                "error"
            )

    all_events = query.order_by(
        Event.start_datetime.asc()
    ).all()

    return render_template(
        "events/list.html",
        events=all_events,
        selected_status=status,
        selected_date=event_date
    )


# =========================================================
# RESOURCES LIST
# =========================================================

@main.route("/resources")
def resources():

    update_completed_events()

    all_resources = Resource.query.order_by(
        Resource.name.asc()
    ).all()

    return render_template(
        "resources/list.html",
        resources=all_resources
    )


# =========================================================
# RESOURCE AVAILABILITY
# =========================================================

@main.route("/resources/availability")
def resource_availability():

    update_completed_events()

    resources = Resource.query.order_by(
        Resource.name.asc()
    ).all()

    now = datetime.now()

    availability_data = []

    for resource in resources:

        active_allocation = Allocation.query.filter(
            Allocation.resource_id == resource.id,
            Allocation.status == "Allocated",
            Allocation.start_datetime <= now,
            Allocation.end_datetime > now
        ).first()

        if active_allocation:

            status = "Allocated"

            event = active_allocation.request.event

            event_name = (
                event.event_name
                if event
                else "Unknown Event"
            )

            allocation_start = (
                active_allocation.start_datetime
            )

            allocation_end = (
                active_allocation.end_datetime
            )

        else:

            status = "Available"

            event_name = None
            allocation_start = None
            allocation_end = None

        availability_data.append({
            "resource": resource,
            "status": status,
            "event_name": event_name,
            "allocation_start": allocation_start,
            "allocation_end": allocation_end
        })

    return render_template(
        "resources/availability.html",
        availability_data=availability_data
    )


# =========================================================
# CREATE RESOURCE
# =========================================================

@main.route(
    "/resources/create",
    methods=["GET", "POST"]
)
def create_resource():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        resource_type = request.form.get(
            "type",
            ""
        ).strip()

        capacity = request.form.get(
            "capacity",
            ""
        ).strip()

        is_active = (
            request.form.get("is_active") == "on"
        )

        # -------------------------------------------------
        # Required fields
        # -------------------------------------------------

        if not name or not resource_type:

            flash(
                "Resource name and type are required.",
                "error"
            )

            return render_template(
                "resources/create.html"
            )

        # -------------------------------------------------
        # Valid resource types
        # -------------------------------------------------

        valid_types = {
            "Auditorium",
            "Laboratory",
            "Projector",
            "Microphone",
            "Camera",
            "Computer"
        }

        if resource_type not in valid_types:

            flash(
                "Invalid resource type.",
                "error"
            )

            return render_template(
                "resources/create.html"
            )

        # -------------------------------------------------
        # Capacity validation
        # -------------------------------------------------

        if capacity:

            try:

                capacity = int(capacity)

            except ValueError:

                flash(
                    "Capacity must be a valid number.",
                    "error"
                )

                return render_template(
                    "resources/create.html"
                )

            if capacity <= 0:

                flash(
                    "Capacity must be greater than 0.",
                    "error"
                )

                return render_template(
                    "resources/create.html"
                )

        else:

            capacity = None

        # -------------------------------------------------
        # Create resource
        # -------------------------------------------------

        resource = Resource(
            name=name,
            type=resource_type,
            capacity=capacity,
            is_active=is_active
        )

        try:

            db.session.add(resource)

            db.session.commit()

            flash(
                "Resource created successfully.",
                "success"
            )

            return redirect(
                url_for("main.resources")
            )

        except Exception:

            db.session.rollback()

            flash(
                "Unable to create resource. Please try again.",
                "error"
            )

    return render_template(
        "resources/create.html"
    )


# =========================================================
# EDIT RESOURCE
# =========================================================

@main.route(
    "/resources/<int:resource_id>/edit",
    methods=["GET", "POST"]
)
def edit_resource(resource_id):

    resource = Resource.query.get_or_404(
        resource_id
    )

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        resource_type = request.form.get(
            "type",
            ""
        ).strip()

        capacity = request.form.get(
            "capacity",
            ""
        ).strip()

        # -------------------------------------------------
        # Required fields
        # -------------------------------------------------

        if not name or not resource_type:

            flash(
                "Resource name and type are required.",
                "error"
            )

            return render_template(
                "resources/edit.html",
                resource=resource
            )

        # -------------------------------------------------
        # Valid resource types
        # -------------------------------------------------

        valid_types = {
            "Auditorium",
            "Laboratory",
            "Projector",
            "Microphone",
            "Camera",
            "Computer"
        }

        if resource_type not in valid_types:

            flash(
                "Invalid resource type.",
                "error"
            )

            return render_template(
                "resources/edit.html",
                resource=resource
            )

        # -------------------------------------------------
        # Capacity validation
        # -------------------------------------------------

        if capacity:

            try:

                capacity = int(capacity)

            except ValueError:

                flash(
                    "Capacity must be a valid number.",
                    "error"
                )

                return render_template(
                    "resources/edit.html",
                    resource=resource
                )

            if capacity <= 0:

                flash(
                    "Capacity must be greater than 0.",
                    "error"
                )

                return render_template(
                    "resources/edit.html",
                    resource=resource
                )

        else:

            capacity = None

        # -------------------------------------------------
        # Update resource
        # -------------------------------------------------

        resource.name = name
        resource.type = resource_type
        resource.capacity = capacity

        try:

            db.session.commit()

            flash(
                "Resource updated successfully.",
                "success"
            )

            return redirect(
                url_for("main.resources")
            )

        except Exception:

            db.session.rollback()

            flash(
                "Unable to update resource. Please try again.",
                "error"
            )

    return render_template(
        "resources/edit.html",
        resource=resource
    )


# =========================================================
# TOGGLE RESOURCE
# =========================================================

@main.route(
    "/resources/<int:resource_id>/toggle",
    methods=["POST"]
)
def toggle_resource(resource_id):

    resource = Resource.query.get_or_404(
        resource_id
    )

    try:

        resource.is_active = not resource.is_active

        db.session.commit()

        if resource.is_active:

            flash(
                "Resource activated successfully.",
                "success"
            )

        else:

            flash(
                "Resource deactivated successfully.",
                "success"
            )

    except Exception:

        db.session.rollback()

        flash(
            "Unable to change resource status.",
            "error"
        )

    return redirect(
        url_for("main.resources")
    )


# =========================================================
# CREATE RESOURCE REQUEST
# =========================================================

@main.route(
    "/resource-requests/create",
    methods=["GET", "POST"]
)
def create_resource_request():

    update_completed_events()

    events = Event.query.order_by(
        Event.start_datetime.asc()
    ).all()

    resources = Resource.query.filter_by(
        is_active=True
    ).order_by(
        Resource.name.asc()
    ).all()

    if request.method == "POST":

        event_id = request.form.get(
            "event_id",
            ""
        ).strip()

        start_datetime = request.form.get(
            "start_datetime",
            ""
        ).strip()

        end_datetime = request.form.get(
            "end_datetime",
            ""
        ).strip()

        # -------------------------------------------------
        # Required fields
        # -------------------------------------------------

        if not event_id or not start_datetime or not end_datetime:

            flash(
                "Event, start date/time and end date/time are required.",
                "error"
            )

            return render_template(
                "requests/create.html",
                events=events,
                resources=resources
            )

        # -------------------------------------------------
        # Validate event ID
        # -------------------------------------------------

        try:

            event_id = int(event_id)

        except ValueError:

            flash(
                "Invalid event selected.",
                "error"
            )

            return render_template(
                "requests/create.html",
                events=events,
                resources=resources
            )

        # -------------------------------------------------
        # Get event
        # -------------------------------------------------

        event = db.session.get(
            Event,
            event_id
        )

        if not event:

            flash(
                "Selected event does not exist.",
                "error"
            )

            return render_template(
                "requests/create.html",
                events=events,
                resources=resources
            )

        # -------------------------------------------------
        # Prevent invalid events
        # -------------------------------------------------

        if event.status in [
            "Completed",
            "Cancelled",
            "Rejected"
        ]:

            flash(
                f"Resource requests cannot be created for a "
                f"{event.status.lower()} event.",
                "error"
            )

            return render_template(
                "requests/create.html",
                events=events,
                resources=resources
            )

        # -------------------------------------------------
        # Date/time validation
        # -------------------------------------------------

        try:

            start = datetime.fromisoformat(
                start_datetime
            )

            end = datetime.fromisoformat(
                end_datetime
            )

        except ValueError:

            flash(
                "Invalid date or time.",
                "error"
            )

            return render_template(
                "requests/create.html",
                events=events,
                resources=resources
            )

        if start >= end:

            flash(
                "End date/time must be after start date/time.",
                "error"
            )

            return render_template(
                "requests/create.html",
                events=events,
                resources=resources
            )

        # -------------------------------------------------
        # Request must be inside event time
        # -------------------------------------------------

        if (
            start < event.start_datetime
            or
            end > event.end_datetime
        ):

            flash(
                "Resource request time must be within the event's scheduled time.",
                "error"
            )

            return render_template(
                "requests/create.html",
                events=events,
                resources=resources
            )

        # -------------------------------------------------
        # Selected resources
        # -------------------------------------------------

        selected_resources = []

        for resource in resources:

            quantity_value = request.form.get(
                f"quantity_{resource.id}",
                "0"
            ).strip()

            try:

                quantity = int(
                    quantity_value
                )

            except (ValueError, TypeError):

                flash(
                    f"Invalid quantity for {resource.name}.",
                    "error"
                )

                return render_template(
                    "requests/create.html",
                    events=events,
                    resources=resources
                )

            if quantity < 0:

                flash(
                    f"Quantity for {resource.name} cannot be negative.",
                    "error"
                )

                return render_template(
                    "requests/create.html",
                    events=events,
                    resources=resources
                )

            # -------------------------------------------------
            # Physical spaces only allow quantity 1
            # -------------------------------------------------

            if resource.type in [
                "Auditorium",
                "Laboratory"
            ]:

                if quantity > 1:

                    flash(
                        f"Only 1 {resource.type} can be requested at a time.",
                        "error"
                    )

                    return render_template(
                        "requests/create.html",
                        events=events,
                        resources=resources
                    )

            if quantity > 0:

                # -------------------------------------------------
                # Active check
                # -------------------------------------------------

                if not resource.is_active:

                    flash(
                        f"{resource.name} is inactive.",
                        "error"
                    )

                    return render_template(
                        "requests/create.html",
                        events=events,
                        resources=resources
                    )

                # -------------------------------------------------
                # Capacity check
                # -------------------------------------------------

                if resource.capacity is not None:

                    if resource.capacity < event.expected_attendance:

                        alternatives = find_alternative_resources(
                            resource,
                            event.expected_attendance,
                            start,
                            end
                        )

                        flash(
                            f"{resource.name} has capacity "
                            f"{resource.capacity}, but the event expects "
                            f"{event.expected_attendance} attendees.",
                            "error"
                        )

                        if alternatives:

                            alternative_names = ", ".join(
                                alternative.name
                                for alternative in alternatives
                            )

                            flash(
                                f"Suggested alternatives: "
                                f"{alternative_names}",
                                "error"
                            )

                        return render_template(
                            "requests/create.html",
                            events=events,
                            resources=resources
                        )

                selected_resources.append(
                    (resource, quantity)
                )

        # -------------------------------------------------
        # At least one resource
        # -------------------------------------------------

        if not selected_resources:

            flash(
                "Select at least one resource.",
                "error"
            )

            return render_template(
                "requests/create.html",
                events=events,
                resources=resources
            )

        # -------------------------------------------------
        # Create resource request
        # -------------------------------------------------

        resource_request = ResourceRequest(
            event_id=event.id,
            start_datetime=start,
            end_datetime=end,
            status="Pending"
        )

        try:

            db.session.add(
                resource_request
            )

            for resource, quantity in selected_resources:

                request_resource = RequestResource(
                    resource=resource,
                    quantity=quantity
                )

                resource_request.request_resources.append(
                    request_resource
                )

            # Draft event becomes Pending
            if event.status == "Draft":

                event.status = "Pending"

            db.session.commit()

            flash(
                "Resource request created successfully.",
                "success"
            )

            return redirect(
                url_for("main.resource_requests")
            )

        except Exception:

            db.session.rollback()

            flash(
                "Unable to create resource request. Please try again.",
                "error"
            )

    return render_template(
        "requests/create.html",
        events=events,
        resources=resources
    )


# =========================================================
# RESOURCE REQUESTS LIST
# =========================================================

@main.route("/resource-requests")
def resource_requests():

    update_completed_events()

    # Synchronize all event statuses
    all_events = Event.query.all()

    try:

        for event in all_events:

            sync_event_status(event)

        db.session.commit()

    except Exception:

        db.session.rollback()

    requests = ResourceRequest.query.order_by(
        ResourceRequest.created_at.desc()
    ).all()

    return render_template(
        "requests/list.html",
        requests=requests
    )


# =========================================================
# APPROVE REQUEST
# =========================================================

@main.route(
    "/resource-requests/<int:request_id>/approve",
    methods=["POST"]
)
def approve_request(request_id):

    success, message, alternatives = (
        approve_resource_request(
            request_id
        )
    )

    if success:

        resource_request = ResourceRequest.query.get(
            request_id
        )

        if resource_request:

            event = db.session.get(
                Event,
                resource_request.event_id
            )

            if event:

                # Approved request means event is approved
                event.status = "Approved"

                try:

                    db.session.commit()

                except Exception:

                    db.session.rollback()

                    flash(
                        "Request was approved, but event status could not be updated.",
                        "error"
                    )

                    return redirect(
                        url_for("main.resource_requests")
                    )

        flash(
            message,
            "success"
        )

    else:

        flash(
            message,
            "error"
        )

        # -------------------------------------------------
        # Show alternatives
        # -------------------------------------------------

        for item in alternatives:

            if item["alternatives"]:

                alternative_names = ", ".join(
                    resource.name
                    for resource in item["alternatives"]
                )

                flash(
                    f"Alternatives for "
                    f"{item['resource'].name}: "
                    f"{alternative_names}",
                    "error"
                )

    return redirect(
        url_for("main.resource_requests")
    )


# =========================================================
# REJECT REQUEST
# =========================================================

@main.route(
    "/resource-requests/<int:request_id>/reject",
    methods=["POST"]
)
def reject_request(request_id):

    resource_request = ResourceRequest.query.get_or_404(
        request_id
    )

    if resource_request.status != "Pending":

        flash(
            f"Request is already {resource_request.status}.",
            "error"
        )

        return redirect(
            url_for("main.resource_requests")
        )

    try:

        resource_request.status = "Rejected"

        # Synchronize event
        event = resource_request.event

        if event:

            sync_event_status(event)

        db.session.commit()

        flash(
            "Resource request rejected successfully.",
            "success"
        )

    except Exception:

        db.session.rollback()

        flash(
            "Unable to reject resource request.",
            "error"
        )

    return redirect(
        url_for("main.resource_requests")
    )


# =========================================================
# CANCEL RESOURCE REQUEST
# =========================================================

@main.route(
    "/resource-requests/<int:request_id>/cancel",
    methods=["POST"]
)
def cancel_resource_request(request_id):

    resource_request = ResourceRequest.query.get_or_404(
        request_id
    )

    # -------------------------------------------------
    # Rejected request
    # -------------------------------------------------

    if resource_request.status == "Rejected":

        flash(
            "Rejected requests cannot be cancelled.",
            "error"
        )

        return redirect(
            url_for("main.resource_requests")
        )

    # -------------------------------------------------
    # Already cancelled
    # -------------------------------------------------

    if resource_request.status == "Cancelled":

        flash(
            "Request is already cancelled.",
            "error"
        )

        return redirect(
            url_for("main.resource_requests")
        )

    # -------------------------------------------------
    # Completed request
    # -------------------------------------------------

    if resource_request.status == "Completed":

        flash(
            "Completed requests cannot be cancelled.",
            "error"
        )

        return redirect(
            url_for("main.resource_requests")
        )

    try:

        # -------------------------------------------------
        # Cancel request
        # -------------------------------------------------

        resource_request.status = "Cancelled"

        # -------------------------------------------------
        # Cancel associated allocations
        # -------------------------------------------------

        allocations = Allocation.query.filter_by(
            request_id=resource_request.id,
            status="Allocated"
        ).all()

        for allocation in allocations:

            allocation.status = "Cancelled"

        # -------------------------------------------------
        # Synchronize event
        # -------------------------------------------------

        event = resource_request.event

        if event:

            sync_event_status(event)

        # -------------------------------------------------
        # Commit
        # -------------------------------------------------

        db.session.commit()

        flash(
            "Resource request cancelled and resources released.",
            "success"
        )

    except Exception:

        db.session.rollback()

        flash(
            "Unable to cancel resource request.",
            "error"
        )

    return redirect(
        url_for("main.resource_requests")
    )


# =========================================================
# ALLOCATIONS
# =========================================================

@main.route("/allocations")
def allocations():

    update_completed_events()

    all_allocations = Allocation.query.order_by(
        Allocation.start_datetime.asc()
    ).all()

    return render_template(
        "allocations/list.html",
        allocations=all_allocations
    )