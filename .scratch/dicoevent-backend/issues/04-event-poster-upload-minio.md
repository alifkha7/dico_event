# 04: Event Poster Upload & MinIO Object Storage

**What to build:** Allow Organizers, Admins, and Superusers to upload promotional Event Poster images (`<= 500 KB` and valid `image/*` MIME types) stored in MinIO via the MinIO SDK and persisted in the database, and allow Users to retrieve the list of uploaded posters for an Event.

**Blocked by:** 02: Events CRUD, Organizer Ownership RBAC & Paginated Queries

**Status:** ready-for-agent

- [ ] MinIO client credentials are configured strictly from `MINIO_ENDPOINT_URL`, `MINIO_ACCESS_KEY`, and `MINIO_SECRET_KEY` environment variables, using the official `minio` Python SDK.
- [ ] `EventPoster` entity uses a UUID primary key (`id`), references `Event` (`on_delete=CASCADE`), and stores the uploaded `image` filename/object key.
- [ ] `POST /api/events/upload/` accepts `multipart/form-data` with `image` (file) and `event` (Event UUID) and validates that the uploaded file has a valid `image/*` MIME type and size `<= 500 KB` (`512,000` bytes).
- [ ] Uploading a valid image (`<= 500 KB`) stores the file in MinIO, saves the `EventPoster` record in PostgreSQL, and returns `201 Created` with a JSON object containing non-empty string `id` and string `image`.
- [ ] Uploading a missing/non-image file or an image file larger than `500 KB` is rejected with `400 Bad Request` and a JSON error response object without storing the file.
- [ ] `GET /api/events/<eventId>/poster/` returns `200 OK` with a JSON array (`[...]`) containing at least the uploaded Event Poster items for that Event.
- [ ] Automated HTTP API tests verify all `[Mandatory] Upload Poster Event` Postman scenarios (valid image upload, non-image rejection, >500 KB image rejection, and poster list retrieval).
