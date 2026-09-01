from datetime import datetime

from app import db


# =========================================================
# EVENT
# =========================================================

class Event(db.Model):

    __tablename__ = "events"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    event_name = db.Column(
        db.String(200),
        nullable=False
    )

    organizer = db.Column(
        db.String(150),
        nullable=False
    )

    expected_attendance = db.Column(
        db.Integer,
        nullable=False
    )

    start_datetime = db.Column(
        db.DateTime,
        nullable=False
    )

    end_datetime = db.Column(
        db.DateTime,
        nullable=False
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="Draft"
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # -----------------------------------------------------
    # Resource Requests
    # -----------------------------------------------------

    requests = db.relationship(
        "ResourceRequest",
        back_populates="event",
        cascade="all, delete-orphan"
    )


# =========================================================
# RESOURCE
# =========================================================

class Resource(db.Model):

    __tablename__ = "resources"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(150),
        nullable=False
    )

    type = db.Column(
        db.String(50),
        nullable=False
    )

    capacity = db.Column(
        db.Integer,
        nullable=True
    )

    is_active = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # -----------------------------------------------------
    # Requested Resources
    # -----------------------------------------------------

    request_resources = db.relationship(
        "RequestResource",
        back_populates="resource"
    )

    # -----------------------------------------------------
    # Allocations
    # -----------------------------------------------------

    allocations = db.relationship(
        "Allocation",
        back_populates="resource"
    )


# =========================================================
# RESOURCE REQUEST
# =========================================================

class ResourceRequest(db.Model):

    __tablename__ = "resource_requests"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    event_id = db.Column(
        db.Integer,
        db.ForeignKey("events.id"),
        nullable=False
    )

    start_datetime = db.Column(
        db.DateTime,
        nullable=False
    )

    end_datetime = db.Column(
        db.DateTime,
        nullable=False
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="Pending"
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    # -----------------------------------------------------
    # Event
    # -----------------------------------------------------

    event = db.relationship(
        "Event",
        back_populates="requests"
    )

    # -----------------------------------------------------
    # Requested Resources
    # -----------------------------------------------------

    request_resources = db.relationship(
        "RequestResource",
        back_populates="request",
        cascade="all, delete-orphan"
    )

    # -----------------------------------------------------
    # Allocations
    # -----------------------------------------------------

    allocations = db.relationship(
        "Allocation",
        back_populates="request",
        cascade="all, delete-orphan"
    )


# =========================================================
# REQUEST RESOURCE
# =========================================================

class RequestResource(db.Model):

    __tablename__ = "request_resources"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    request_id = db.Column(
        db.Integer,
        db.ForeignKey("resource_requests.id"),
        nullable=False
    )

    resource_id = db.Column(
        db.Integer,
        db.ForeignKey("resources.id"),
        nullable=False
    )

    quantity = db.Column(
        db.Integer,
        nullable=False,
        default=1
    )

    # -----------------------------------------------------
    # Resource Request
    # -----------------------------------------------------

    request = db.relationship(
        "ResourceRequest",
        back_populates="request_resources"
    )

    # -----------------------------------------------------
    # Resource
    # -----------------------------------------------------

    resource = db.relationship(
        "Resource",
        back_populates="request_resources"
    )


# =========================================================
# ALLOCATION
# =========================================================

class Allocation(db.Model):

    __tablename__ = "allocations"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    request_id = db.Column(
        db.Integer,
        db.ForeignKey("resource_requests.id"),
        nullable=False
    )

    resource_id = db.Column(
        db.Integer,
        db.ForeignKey("resources.id"),
        nullable=False
    )

    quantity = db.Column(
        db.Integer,
        nullable=False,
        default=1
    )

    start_datetime = db.Column(
        db.DateTime,
        nullable=False
    )

    end_datetime = db.Column(
        db.DateTime,
        nullable=False
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="Allocated"
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    # -----------------------------------------------------
    # Resource Request
    # -----------------------------------------------------

    request = db.relationship(
        "ResourceRequest",
        back_populates="allocations"
    )

    # -----------------------------------------------------
    # Resource
    # -----------------------------------------------------

    resource = db.relationship(
        "Resource",
        back_populates="allocations"
    )