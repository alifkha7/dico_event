# DicoEvent

DicoEvent is an event management and ticketing platform built by DicoTech that enables Organizers and Admins to publish Events, sell Tickets, manage User Registrations, process Payments, upload Event Posters, and send automated Event reminders.

## Language

### Actors & Roles

**Superuser**:
The highest-privilege system administrator who has unrestricted access to all resources and exclusively manages role groups and user-role assignments.
_Avoid_: Root, owner, system user

**Admin**:
A back-office staff role authorized to manage all Users, Events, Tickets, Registrations, and Payments across the platform, but prohibited from creating role groups or assigning roles.
_Avoid_: Moderator, staff, manager

**Organizer**:
An event host role authorized to create Events and Tickets, modify or delete only the Events and Tickets they personally own, and view Registrations and Payments for their own Events.
_Avoid_: Creator, vendor, promoter, host

**User**:
A standard registered participant who can browse Events and Tickets, register for Events, submit Payments, and view their own Registrations and Payments.
_Avoid_: Customer, buyer, attendee, member, account

**Group**:
A named role definition (such as `admin` or `organizer`) assigned to Users to govern their permissions under Role-Based Access Control (RBAC).
_Avoid_: Role table, permission set, profile type

### Core Domain Entities

**Event**:
A scheduled gathering (such as a seminar) hosted by an Organizer at a specific location and time window with a maximum participant quota.
_Avoid_: Show, session, activity, concert

**Event Poster**:
A promotional image uploaded to object storage and associated with a specific Event as its visual identity, exposed with a time-limited access URL for viewing.
_Avoid_: Banner, thumbnail, attachment, cover photo

**Ticket**:
A purchasable admission category for a specific Event, defined by a name (such as VIP), price, active sales window, and ticket quota.
_Avoid_: Pass, seat, tier, voucher

**Registration**:
A record of a User claiming one spot in a specific Ticket and its parent Event within the active sales window, which triggers an asynchronous reminder notification prior to the Event.
_Avoid_: Booking, order, reservation, enrollment

**Payment**:
A financial settlement record linked to a Registration that settles the Ticket price and tracks canonical settlement states (`Pending`, `Completed`, `Failed`, `Refunded`).
_Avoid_: Invoice, transaction, receipt, bill
