# DicoEvent

DicoEvent is an event management and ticketing platform built by DicoTech that enables organizers and administrators to publish events, sell tickets, manage attendee registrations, process payments, upload promotional posters, and send automated event reminders.

## Language

### Actors & Roles

**Superuser**:
The highest-privilege system administrator who has unrestricted access to all resources and exclusively manages role groups and user-role assignments.
_Avoid_: Root, owner, system user

**Admin**:
A back-office staff role authorized to manage all Users, Events, Tickets, Registrations, and Payments across the platform, but prohibited from creating role groups or assigning roles.
_Avoid_: Moderator, staff, manager

**Organizer**:
An event host role authorized to create Events and Tickets and to modify or delete only the Events they personally own.
_Avoid_: Creator, vendor, promoter, host

**User**:
A standard registered participant who can browse Events and Tickets, register for Events, and submit Payments for their Registrations.
_Avoid_: Customer, buyer, attendee, member, account

**Group**:
A named role definition (such as `admin` or `organizer`) assigned to Users to govern their permissions under Role-Based Access Control (RBAC).
_Avoid_: Role table, permission set, profile type

### Core Domain Entities

**Event**:
A scheduled gathering or activity (such as a seminar) hosted by an Organizer at a specific location and time window with a maximum attendee quota.
_Avoid_: Show, session, activity, concert

**Event Poster**:
A promotional image file (up to 500 KB) uploaded to object storage and associated with a specific Event as its visual identity.
_Avoid_: Banner, thumbnail, attachment, cover photo

**Ticket**:
A purchasable admission tier for a specific Event, defined by a name (such as VIP), price, sales window (`sales_start` to `sales_end`), and ticket quota.
_Avoid_: Pass, seat, tier, voucher

**Registration**:
A record of a User booking a specific Ticket for an Event, which triggers an asynchronous reminder notification prior to the Event.
_Avoid_: Booking, order, reservation, enrollment

**Payment**:
A financial settlement record linked to a Registration, capturing the payment method (such as QRIS), payment status, and amount paid.
_Avoid_: Invoice, transaction, receipt, bill
