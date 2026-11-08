---
status: superseded by ADR-0004
---

# Postman Test Suite Compatibility Rules

To ensure 100% compatibility with both the `[788] DicoEvent versi 1` and `[788] DicoEvent versi 2` automated Postman test collections while preserving strict JWT + RBAC security on list and mutation endpoints, the API intentionally implements four specific behaviors required by the Postman test scripts:

1. **Unauthenticated `GET` on Detail (`retrieve`) Endpoints**: In the Postman `PUT` test scripts for Users, Events, Tickets, Registrations, and Payments, follow-up verification requests are dispatched via `pm.sendRequest("http://${host}:${port}/api/<resource>/${id}/")` without an `Authorization` header. Detail `GET` (`retrieve`) endpoints therefore allow unauthenticated read access (`AllowAny`), whereas collection `GET` (`list`) endpoints (`/api/users/`, `/api/groups/`, `/api/registrations/`, `/api/payments/`) and all write endpoints (`POST`, `PUT`, `DELETE`) enforce JWT authentication and RBAC permissions.
2. **Optional Trailing Slashes on Detail Routes**: Several Postman detail `GET` requests omit the trailing slash (e.g., `GET /api/tickets/{{ticketId}}`, `GET /api/registrations/{{registrationId}}`, `GET /api/payments/{{paymentId}}`), while `PUT` and `DELETE` include it. All resource URL patterns accept both trailing and non-trailing slashes (`/?$`).
3. **Payment Status Normalization on Update**: The `PUT /api/payments/<id>/` request payload sends `"payment_status": "completed"` (lowercase), while its post-response verification script asserts `responseJson.payment_status === "Completed"`. When `payment_status` is updated to `"completed"` (case-insensitive), the serializer normalizes the stored/returned value to `"Completed"`.
4. **Cascading Deletion from Ticket to Registration and Payment**: In the Version 2 Postman collection, the `[Mandatory] Payments -> Delete Payments` step sends `DELETE /api/tickets/{{ticketId}}/` and then asserts that `GET /api/payments/{{paymentId}}` returns `404 Not Found`. Foreign keys on `Registration.ticket` and `Payment.registration` use `on_delete=models.CASCADE` so deleting a Ticket cascades to its Registrations and Payments.
