from app import db

from app.models import (
    Event,
    Resource,
    ResourceRequest,
    RequestResource,
    Allocation
)


# =========================================================
# CHECK RESOURCE CONFLICT
# =========================================================

def check_resource_conflict(
    resource_id,
    start_datetime,
    end_datetime
):
    """
    Check whether a resource is already allocated
    during the requested time period.
    """

    conflicting_allocation = (
        db.session.query(Allocation)
        .filter(
            Allocation.resource_id == resource_id,
            Allocation.status == "Allocated",
            Allocation.start_datetime < end_datetime,
            Allocation.end_datetime > start_datetime
        )
        .first()
    )

    return conflicting_allocation


# =========================================================
# CHECK RESOURCE CAPACITY
# =========================================================

def check_resource_capacity(
    resource,
    expected_attendance
):
    """
    Check whether the resource has enough capacity
    for the expected event attendance.
    """

    # Resources without capacity do not require
    # an attendance capacity check.

    if resource.capacity is None:
        return True

    return resource.capacity >= expected_attendance


# =========================================================
# CHECK RESOURCE SUITABILITY
# =========================================================

def check_resource_suitability(
    resource,
    required_type,
    expected_attendance
):
    """
    Check whether a resource is suitable for an event.
    """

    # Check resource type

    if resource.type != required_type:
        return False

    # Check capacity

    if resource.capacity is not None:

        if resource.capacity < expected_attendance:
            return False

    return True


# =========================================================
# FIND ALTERNATIVE RESOURCES
# =========================================================

def find_alternative_resources(
    resource,
    expected_attendance,
    start_datetime,
    end_datetime
):
    """
    Find suitable alternative resources.

    Alternatives must:
    - Be active
    - Have the same resource type
    - Have sufficient capacity
    - Be available during the requested time
    """

    alternatives = Resource.query.filter(
        Resource.id != resource.id,
        Resource.type == resource.type,
        Resource.is_active.is_(True)
    ).order_by(
        Resource.capacity.asc()
    ).all()

    suitable_alternatives = []

    for alternative in alternatives:

        # Check capacity

        if not check_resource_capacity(
            alternative,
            expected_attendance
        ):
            continue

        # Check conflict

        conflict = check_resource_conflict(
            alternative.id,
            start_datetime,
            end_datetime
        )

        if conflict:
            continue

        suitable_alternatives.append(
            alternative
        )

    return suitable_alternatives


# =========================================================
# VALIDATE RESOURCE REQUEST
# =========================================================

def validate_resource_request(
    event,
    resource,
    quantity,
    start_datetime,
    end_datetime
):
    """
    Validate a resource before allocation.

    Returns:

        True,
        message,
        alternatives

    or:

        False,
        message,
        alternatives
    """

    # -----------------------------------------------------
    # Quantity check
    # -----------------------------------------------------

    if quantity <= 0:

        return (
            False,
            "Resource quantity must be greater than 0.",
            []
        )

    # -----------------------------------------------------
    # Active check
    # -----------------------------------------------------

    if not resource.is_active:

        alternatives = find_alternative_resources(
            resource,
            event.expected_attendance,
            start_datetime,
            end_datetime
        )

        return (
            False,
            f"{resource.name} is inactive.",
            alternatives
        )

    # -----------------------------------------------------
    # Capacity check
    # -----------------------------------------------------

    if not check_resource_capacity(
        resource,
        event.expected_attendance
    ):

        alternatives = find_alternative_resources(
            resource,
            event.expected_attendance,
            start_datetime,
            end_datetime
        )

        return (
            False,
            f"{resource.name} does not have enough capacity.",
            alternatives
        )

    # -----------------------------------------------------
    # Conflict check
    # -----------------------------------------------------

    conflict = check_resource_conflict(
        resource.id,
        start_datetime,
        end_datetime
    )

    if conflict:

        alternatives = find_alternative_resources(
            resource,
            event.expected_attendance,
            start_datetime,
            end_datetime
        )

        return (
            False,
            f"{resource.name} is already allocated for this time.",
            alternatives
        )

    return (
        True,
        "Resource is suitable and available.",
        []
    )


# =========================================================
# APPROVE RESOURCE REQUEST
# =========================================================

def approve_resource_request(request_id):
    """
    Approve a resource request and create allocations.

    Successful flow:

        Resource Request
        Pending
            ↓
        Approved

        Event
        Pending
            ↓
        Approved

        Allocation
            ↓
        Allocated

    All resources are validated before allocation.

    If even one resource fails validation,
    no allocation is created.
    """

    # -----------------------------------------------------
    # Get resource request
    # -----------------------------------------------------

    resource_request = db.session.get(
        ResourceRequest,
        request_id
    )

    if not resource_request:

        return (
            False,
            "Resource request not found.",
            []
        )

    # -----------------------------------------------------
    # Only pending requests can be approved
    # -----------------------------------------------------

    if resource_request.status != "Pending":

        return (
            False,
            f"Request is already {resource_request.status}.",
            []
        )

    # -----------------------------------------------------
    # Get associated event
    # -----------------------------------------------------

    event = resource_request.event

    if not event:

        return (
            False,
            "The event associated with this request was not found.",
            []
        )

    alternatives = []

    # =====================================================
    # STEP 1: VALIDATE EVERY REQUESTED RESOURCE
    # =====================================================

    for request_resource in resource_request.request_resources:

        resource = request_resource.resource

        quantity = request_resource.quantity

        valid, message, resource_alternatives = (
            validate_resource_request(
                event,
                resource,
                quantity,
                resource_request.start_datetime,
                resource_request.end_datetime
            )
        )

        if not valid:

            alternatives.append({
                "resource": resource,
                "message": message,
                "alternatives": resource_alternatives
            })

            # Nothing has been allocated yet.

            return (
                False,
                message,
                alternatives
            )

    # =====================================================
    # STEP 2: CREATE ALL ALLOCATIONS
    # =====================================================

    try:

        for request_resource in resource_request.request_resources:

            allocation = Allocation(
                request_id=resource_request.id,
                resource_id=request_resource.resource_id,
                quantity=request_resource.quantity,
                start_datetime=resource_request.start_datetime,
                end_datetime=resource_request.end_datetime,
                status="Allocated"
            )

            db.session.add(
                allocation
            )

        # =================================================
        # STEP 3: UPDATE RESOURCE REQUEST STATUS
        # =================================================

        resource_request.status = "Approved"

        # =================================================
        # STEP 4: UPDATE EVENT STATUS
        # =================================================

        event.status = "Approved"

        # =================================================
        # STEP 5: SAVE EVERYTHING
        # =================================================

        db.session.commit()

        return (
            True,
            "Resource request approved and resources allocated successfully.",
            []
        )

    except Exception:

        # Roll back ALL changes if anything fails.

        db.session.rollback()

        return (
            False,
            "Unable to allocate resources. All changes were rolled back.",
            []
        )