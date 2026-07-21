# Classroom Module — Requirements

## Requirement Types

- **BR** — Business Requirement
- **UR** — User Requirement
- **FR** — Functional Requirement
- **NFR** — Non-Functional Requirement

---

## Requirements Table

| ID | Type | Description | Parent | Priority | Acceptance Criteria | Release |
|---|---|---|---|---|---|---|
| BR-CLS-01 | BR | A classroom must be owned by exactly one Space account. Only the owner can create, update, or delete the classroom. | — | High | Requests to modify a classroom by a non-owner return 403. | v1.0 |
| BR-CLS-02 | BR | Students must join a classroom before they can access its content. | — | High | Consumer cannot access classroom content without a ClassroomMember record. | v1.0 |
| BR-CLS-03 | BR | Classrooms must support shareable invite links so teachers can onboard students without manual entry. | — | Medium | A sharing link created for a classroom adds the user as a member when accessed. | v1.0 |
| BR-CLS-04 | BR | A classroom must support a maximum student cap, with `0` meaning unlimited. | BR-CLS-01 | Low | Creating a membership when `member_count >= max_students` (and `max_students > 0`) is rejected. | v1.0 |
| BR-CLS-05 | BR | Classroom deletion must follow a soft-delete pattern. | — | High | Deleted classrooms are hidden from queries; data is retained in Cassandra. | v1.0 |
| UR-CLS-01 | UR | As a teacher, I want to create a classroom so that I can organize my students and content. | BR-CLS-01 | High | POST to classroom endpoint creates a record; teacher becomes the owner. | v1.0 |
| UR-CLS-02 | UR | As a teacher, I want to add students to my classroom so that they can access content. | BR-CLS-02 | High | Teacher adds Consumer by uid; ClassroomMember record created with role=student. | v1.0 |
| UR-CLS-03 | UR | As a teacher, I want to generate an invite link for my classroom so that students can join without manual addition. | BR-CLS-03 | Medium | Sharing link created for classroom; accessing link adds the user as a member. | v1.0 |
| UR-CLS-04 | UR | As a teacher, I want to remove a student from my classroom so that I can manage access. | BR-CLS-01 | Medium | Member record soft-deleted; student no longer appears in member list. | v1.0 |
| UR-CLS-05 | UR | As a student, I want to see all classrooms I have joined so that I can navigate to my content. | BR-CLS-02 | High | Consumer list endpoint returns all classrooms where a ClassroomMember record exists for that Consumer. | v1.0 |
| FR-CLS-01 | FR | The system shall store classrooms in the `account_classrooms` table with `bucket` as partition key and `uid` (UUID v7) as clustering key DESC. | BR-CLS-01 | High | Classroom queries use bucket + uid for efficient retrieval. | v1.0 |
| FR-CLS-02 | FR | The system shall store classroom members in `course_classroom_members` with `classroom_uid` as partition key and `member_id` as clustering key ASC. | BR-CLS-02 | High | Member list for a classroom is retrieved with a single partition scan. | v1.0 |
| FR-CLS-03 | FR | The system shall index `teacher_id` on the classroom table to support teacher-scoped classroom listing. | BR-CLS-01 | High | Teacher list endpoint returns only classrooms where `teacher_id = space.uid`. | v1.0 |
| FR-CLS-04 | FR | The system shall cache `member_name` and `member_avatar` on the ClassroomMember record at join time. | BR-CLS-02 | Medium | Member list response includes display name and avatar without secondary lookups. | v1.0 |
| FR-CLS-05 | FR | The system shall expose a `resolve_link` cached property on Classroom that returns the associated sharing link if one exists. | BR-CLS-03 | Medium | Classroom detail response includes `sharing_link` field populated from the Sharing module. | v1.0 |
| NFR-CLS-01 | NFR | Member list queries must return results in under 300ms for classrooms with up to 500 members. | — | High | Load test with 500-member classroom; p95 latency ≤ 300ms. | v1.0 |
| NFR-CLS-02 | NFR | Classroom ownership must be validated on every write operation without an additional database query. | BR-CLS-01 | High | Ownership check uses `teacher_id` from the classroom record retrieved in the same request. | v1.0 |

### Paid classroom + preview folder (LMS-paid-classroom-preview-folder)

| ID | Type | Description | Parent | Priority | Acceptance Criteria | Release |
|---|---|---|---|---|---|---|
| BR-CLS-06 | BR | A classroom can be free or paid. Paid classrooms require a successful MoMo payment before students can access folders outside the Preview folder. | — | High | `Classroom.pricing_type ∈ {free, paid}`; `Classroom.price_vnd` ≥ 1000 when paid. | v1.1 |
| BR-CLS-07 | BR | Every classroom (free or paid) auto-creates a Preview folder where the teacher uploads free materials. For a paid classroom, only this folder is visible to non-paid consumers. | BR-CLS-06 | High | At most one `ResourceFolder.is_preview_only=True` per classroom; auto-created on classroom creation. | v1.1 |
| BR-CLS-08 | BR | A successful MoMo payment for a paid classroom must immediately auto-approve the student (no teacher approval). | BR-CLS-06 | High | On MoMo IPN with `resource_type='classroom'`, `ClassroomMemberService.approve_paid_member` is invoked and the student gets `status='approved'`, `has_paid=True`. | v1.1 |
| UR-CLS-06 | UR | As a teacher, I want to mark a folder as Preview so that it is the default free content of a paid classroom. | BR-CLS-07 | High | Toggling `is_preview_only` on a folder persists; setting it on a second folder is rejected with 400. | v1.1 |
| UR-CLS-07 | UR | As a student, I want to see all folders and docs of a paid classroom after I have paid. | BR-CLS-06 | High | After payment + IPN, `ClassroomDocService.list_tree` returns the full tree, not just the preview folder. | v1.1 |
| FR-CLS-06 | FR | The system shall add `pricing_type`, `price_vnd` columns to `account_classrooms` (additive migration via `sync_cassandra`). | BR-CLS-06 | High | `sync_cassandra` shows the new columns on the live keyspace. | v1.1 |
| FR-CLS-07 | FR | The system shall add `has_paid`, `paid_at` columns to `course_classroom_members`. | BR-CLS-08 | High | New columns present in the keyspace after `sync_cassandra`. | v1.1 |
| FR-CLS-08 | FR | The system shall add `is_preview_only` column to `resource_folders` and enforce the at-most-one rule on create and update. | BR-CLS-07 | High | Repository + service refuse to create/update a second preview folder with 400. | v1.1 |
| FR-CLS-09 | FR | The consumer classroom `retrieve` endpoint shall return `requires_payment: true` and `has_paid: false` for paid classrooms where the consumer has not paid. | BR-CLS-06 | High | Consumer can read basic classroom info; `docs/tree` returns only the preview folder when the consumer has not paid. | v1.1 |
| FR-CLS-10 | FR | The consumer classroom `join` endpoint shall call `PaymentService.initiate(resource_type='classroom')` for paid classrooms and return the MoMo `pay_url`. | BR-CLS-06 | High | Calling `POST /api/v1/consumer/course/classrooms/join/` with a paid classroom pid returns `{requires_payment: true, pay_url, order_id, amount}`. | v1.1 |
| FR-CLS-11 | FR | The system shall expose `GET /api/v1/consumer/course/classrooms/{uid}/preview-folder/` returning the preview folder and its docs without auth. | BR-CLS-07 | High | Endpoint returns `{folder, docs}` or `{folder: null, docs: []}` if no preview folder exists. | v1.1 |
| FR-CLS-12 | FR | The system shall expose `POST /api/v1/consumer/course/classrooms/{uid}/checkout/` to initiate a MoMo payment for a paid classroom. | BR-CLS-06 | High | Endpoint returns `{classroom_uid, amount, order_id, pay_url}`. | v1.1 |
| FR-CLS-13 | FR | The system shall expose `GET /api/v1/consumer/course/classrooms/{uid}/access/` to poll payment status. | BR-CLS-06 | High | Endpoint returns `{has_access, has_paid, pricing_type, is_paid_classroom, pending_payment}`. | v1.1 |
| NFR-CLS-03 | NFR | Folder listing for paid + unpaid consumers must not degrade beyond 100ms additional latency. | BR-CLS-06 | High | p95 latency of `/docs/tree/` for paid classrooms ≤ 350ms (baseline + 100ms). | v1.1 |

### Discover + quick join (LMS-discover-classrooms)

| ID | Type | Description | Parent | Priority | Acceptance Criteria | Release |
|---|---|---|---|---|---|---|
| BR-CLS-09 | BR | Classrooms must be classifiable by a fixed category enum so the consumer can browse them in a Discover page. | — | High | `Classroom.category` ∈ {math, physics, chemistry, biology, language, programming, business, design, music, other}. | v1.1 |
| BR-CLS-10 | BR | Classrooms must support a public/private visibility flag. Public classrooms are browsable and joinable directly; private ones are joinable only by invite code. | BR-CLS-09 | High | `Classroom.visibility_type ∈ {public, private}`. `private` is hidden from `/discover/`. | v1.1 |
| UR-CLS-08 | UR | As a teacher, I want to choose a category and visibility when creating/editing a classroom so that students can find it (or not) on the Discover page. | BR-CLS-09, BR-CLS-10 | High | Create/edit form has a category dropdown and a public/private radio. | v1.1 |
| UR-CLS-09 | UR | As a student, I want to browse public classrooms, filter by category and price type, search by name, and join directly from the list. | BR-CLS-09, BR-CLS-10 | High | `/consumer/discover` page shows a grid with filter bar and search; clicking "Tham gia" calls the quick-join endpoint. | v1.1 |
| FR-CLS-14 | FR | The system shall expose `GET /api/v1/consumer/course/classrooms/discover/` accepting `category`, `pricing_type`, `search`, `page` and returning paginated public classrooms. | BR-CLS-09, BR-CLS-10 | High | Endpoint returns paginated results with `is_joined` flag per row. | v1.1 |
| FR-CLS-15 | FR | The system shall expose `POST /api/v1/consumer/course/classrooms/quick-join/` with body `{classroom_uid}`. Free → auto-join; Paid → MoMo pay_url. | BR-CLS-10 | High | Endpoint returns `{joined, requires_payment, classroom_uid, pay_url?}` shape. | v1.1 |
| FR-CLS-16 | FR | The system shall enforce at most one `is_preview_only` folder per classroom. | BR-CLS-07 | High | `ResourceFolderService.create_folder` rejects a second preview folder with 400. | v1.1 |
| FR-CLS-17 | FR | The system shall add `category` and `visibility_type` columns to `account_classrooms` (additive migration). | BR-CLS-09, BR-CLS-10 | High | New columns present in the keyspace after `sync_cassandra`. | v1.1 |
| NFR-CLS-04 | NFR | Discover listing must remain p95 ≤ 300ms even with 5,000 public classrooms. | BR-CLS-09 | Medium | Load test with 5k rows; p95 ≤ 300ms. | v1.1 |

### Preview page (LMS-classroom-preview-page)

| ID | Type | Description | Parent | Priority | Acceptance Criteria | Release |
|---|---|---|---|---|---|---|
| BR-CLS-11 | BR | A consumer must be able to open a public classroom preview page that shows the teacher info, the free Preview folder contents, and the next action to take (Join for free, Pay with MoMo for paid, or "you are a member" when already enrolled). | BR-CLS-06, BR-CLS-07, BR-CLS-10 | High | `GET /consumer/course/classrooms/{uid}/preview/` returns the documented shape for free, paid, joined, and unjoined states. | v1.2 |
| BR-CLS-12 | BR | A free classroom requires the consumer to join before they can see non-Preview folders, chat, or interact. | BR-CLS-02, BR-CLS-07 | High | The free-classroom `actions.type` is `join` until the consumer has an approved member record; after approval, `actions.type` is `none`. | v1.2 |
| BR-CLS-13 | BR | A paid classroom requires a successful MoMo payment before the consumer can see non-Preview folders. | BR-CLS-06 | High | The paid-classroom `actions.type` is `checkout` (with `pay_url`) until `has_paid` is true and membership is `approved`. | v1.2 |
| UR-CLS-10 | UR | As a student, I want to see the teacher's name and avatar, the free lessons, and clear "Tham gia" / "Thanh toán MoMo" actions on the preview page so I can decide before joining. | BR-CLS-11, BR-CLS-12, BR-CLS-13 | High | Preview endpoint payload contains `classroom`, `preview.folder`, `preview.docs`, and `actions`. | v1.2 |
| FR-CLS-18 | FR | The system shall expose `GET /api/v1/consumer/course/classrooms/{uid}/preview/` returning `{classroom, preview: {folder, docs}, actions: {type, requires_payment, membership_status, pay_url, amount}}`. | BR-CLS-11 | High | Endpoint returns the documented shape; `actions.type ∈ {none, join, checkout}`. | v1.2 |
| FR-CLS-19 | FR | The preview endpoint shall return `actions.type='checkout'` and a MoMo `pay_url` for a paid classroom where the consumer is not yet paid, by calling `PaymentService.initiate(resource_type='classroom')`. | BR-CLS-13 | High | `pay_url` present on response; payment row created with `status=pending`. | v1.2 |
| FR-CLS-20 | FR | The preview endpoint shall return `actions.type='join'` for a free classroom where the consumer is not yet an approved member, and `actions.type='none'` when the consumer is already an approved member. | BR-CLS-12 | High | Verify both transitions in test. | v1.2 |
| FR-CLS-21 | FR | The preview endpoint shall return 403 for inactive, deleted, or private classrooms (when the caller is not an approved member), and 404 if the classroom does not exist. | BR-CLS-10 | High | Endpoint returns 403/404 for those states. | v1.2 |
| NFR-CLS-05 | NFR | The preview endpoint must respond in p95 ≤ 250ms. | BR-CLS-11 | Medium | Load test the endpoint; p95 ≤ 250ms. | v1.2 |

### Favorite classroom (LMS-favorite-classroom)

| ID | Type | Description | Parent | Priority | Acceptance Criteria | Release |
|---|---|---|---|---|---|---|
| BR-CLS-14 | BR | A consumer can mark any public classroom as favorite and retrieve the list of favorited classrooms. | — | High | `ClassroomFavorite` table populated; toggle/list endpoints work. | v1.2 |
| BR-CLS-15 | BR | Favorite records are personal; favoriting does not grant access to a classroom. | BR-CLS-14, BR-CLS-02 | High | Favoriting a paid classroom does not bypass the payment gate. | v1.2 |
| UR-CLS-11 | UR | As a student, I want to favorite a classroom so I can quickly find it later from my favorites list. | BR-CLS-14 | High | Toggle endpoint persists the favorite; favorites list returns the favorited classroom. | v1.2 |
| UR-CLS-12 | UR | As a student, I want to see whether a classroom is favorited on the discover page, the detail page, and the preview page so I can decide to favorite or unfavorite. | BR-CLS-14 | High | `is_favorited` and `favorite_count` present on the discover, detail, and preview responses when the caller is authenticated. | v1.2 |
| FR-CLS-22 | FR | The system shall expose `POST /api/v1/consumer/social/classrooms/{uid}/favorite/` toggling the favorite. | BR-CLS-14 | High | Endpoint returns `{is_favorited, favorite_count}`. | v1.2 |
| FR-CLS-23 | FR | The system shall expose `GET /api/v1/consumer/social/classrooms/{uid}/favorite/status/` returning `{is_favorited, favorite_count}`. | BR-CLS-14 | High | Endpoint returns the current favorite state. | v1.2 |
| FR-CLS-24 | FR | The system shall expose `GET /api/v1/consumer/social/classrooms/favorites/` returning the consumer's paginated list of favorited classrooms. | BR-CLS-14 | High | Endpoint returns `ClassroomResponseSerializer`-shaped items joined with `created_at`. | v1.2 |
| FR-CLS-25 | FR | The system shall add the `classroom_favorites` Cassandra table partitioned by `consumer_uid`. | BR-CLS-14 | High | `sync_cassandra` shows the new table. | v1.2 |
| FR-CLS-26 | FR | The `ClassroomResponseSerializer` shall expose `is_favorited` and `favorite_count` (default `false` / `0` when called without context). | UR-CLS-12 | High | Serializer includes both fields; default values applied when not populated. | v1.2 |
| NFR-CLS-06 | NFR | Favoriting a classroom must complete in p95 ≤ 150ms. | BR-CLS-14 | Medium | Load test the toggle endpoint; p95 ≤ 150ms. | v1.2 |
