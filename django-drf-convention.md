# Convention Guide — Django + DRF Multi-tenant Project

> Phiên bản generalize từ MyBranding project. Áp dụng cho mọi Django REST Framework project theo kiến trúc **Service-Oriented + Multi-tenant + Domain-Driven Design**.

---

## 1. Kiến trúc tổng thể

**Stack chuẩn:**

| Layer | Tech |
|---|---|
| Language | Python 3.13 |
| Framework | Django 5.2+ |
| API | Django REST Framework |
| Build / Deps | Poetry |
| Worker | Celery |
| DB (primary) | Cassandra / Scylla (multi-model) |
| Tenant isolation | Organization-scoped |

**Triết lý phân lớp:**

```
Model  →  Repository  →  Service  →  Serializer  →  View  →  Routing
(data)    (data access)  (logic)     (I/O contract)  (HTTP)   (URL)
```

**Cấu trúc thư mục gốc:**

```
project_root/
├── manage.py
├── pyproject.toml                    # Poetry
├── <project_name>/                   # Project config package (trùng tên root)
│   ├── __init__.py
│   ├── configs/                      # Tách riêng từng phần cấu hình
│   │   ├── installed_apps.py         # <-- Đăng ký app theo feature group
│   │   └── ...
│   ├── settings.py
│   ├── urls.py
│   ├── task.py                       # Celery config
│   ├── wsgi.py / asgi.py
├── core/                             # Base functionality dùng chung
├── <feature_a>/                      # Mỗi domain = 1 app
├── <feature_b>/
├── templates/
│   ├── emails/
│   ├── staticfiles/
│   └── scaffold/dummy/               # Template scaffold tạo app mới
├── storage/                          # logs, tmp, media
└── static/
```

---

## 2. Cách chia Module (App structure)

### 2.1 Feature-based modules

Mỗi feature = 1 Django app. Đăng ký tại `<project>/configs/installed_apps.py` theo **feature group** (tuple `{FEATURE}_APPS`).

**Các feature group phổ biến:**

| Group | Mục đích | Ví dụ app |
|---|---|---|
| `CORE_APPS` | Hạ tầng chung | `core`, `core.cache`, `core.system.*` |
| `TENANT_APPS` | Quản lý tenant | `tenants`, `tenants.organizations`, `tenants.user` |
| `ACCOUNT_APPS` | User & auth | `accounts`, `accounts.staff`, `accounts.user` |
| `COMMERCE_APPS` | Sản phẩm, đơn hàng | `commerce.products`, `commerce.orders` |
| `CRM_APPS` | Khách hàng, deal | `crm.contact`, `crm.lead`, `crm.sales.deals` |
| `REWARD_APPS` | Loyalty, điểm thưởng | `rewards.code`, `rewards.redemption` |
| `EVENT_APPS` | Sự kiện, campaign | `event.campaigns`, `event.sweepstakes` |
| `PAYMENT_APPS` | Cổng thanh toán | `payment.napas`, `payment.stripe` |
| `POS_APPS` | Point of sale | `pos.pos`, `pos.sale_channel` |

**Pattern đăng ký:**

```python
# <project>/configs/installed_apps.py
from <project>.settings import INSTALLED_APPS

# Feature group: tên nhóm + tuple
COMMERCE_APPS = (
    'commerce.products',
    'commerce.orders',       # <- thêm app mới ở đây
    'commerce.vouchers',
)

# Cuối file: combine tất cả groups
INSTALLED_APPS += (
    CORE_APPS + COMMERCE_APPS + ... + ()
)
```

**Tạo app mới (scaffold):**

```bash
python3 manage.py startapp_scaffold <app_name>
python3 manage.py startapp_scaffold <master>.<sub>      # nested app
python3 manage.py startapp_scaffold <app> --target-dir /path
```

### 2.2 Cấu trúc bắt buộc của 1 app

```
<app_name>/
├── __init__.py
├── apps.py                          # Django AppConfig
├── enums/                           # Hằng số & permission
│   ├── __init__.py
│   └── <app>_permissions.py
├── models/                          # Data models
│   ├── __init__.py
│   └── <model_name>.py              # 1 file / 1 model
├── repositories/                    # Data access layer
│   ├── __init__.py
│   └── <model>_repository.py
├── serializers/
│   ├── __init__.py
│   ├── <model>_serializer.py        # Response serializer
│   └── requests/
│       ├── create_<model>_request_serializer.py
│       └── update_<model>_request_serializer.py
├── services/                        # Business logic
│   ├── __init__.py
│   └── <model>_service.py
├── views/
│   └── api/
│       ├── __init__.py
│       ├── admin/                   # Admin-scope views
│       │   └── <model>_admin_model_view_set.py
│       ├── space/                   # Tenant-scope views
│       │   └── <model>_model_view_set.py
│       ├── consumer/                # Consumer-scope views
│       └── community/               # Community-scope views
├── routing/
│   └── api/
│       ├── __init__.py
│       ├── admin_urls.py
│       ├── space_urls.py
│       ├── consumer_urls.py
│       └── community_urls.py
└── locale/
```

---

## 3. Convention đặt tên

### 3.1 Module / file

| Loại | Convention | Ví dụ |
|---|---|---|
| App name | `snake_case` (số ít) | `accounts`, `commerce.products` |
| Model file | `<model_name>.py` (số ít) | `product.py` |
| Repository class | `<Model>Repository` | `ProductRepository` |
| Service class | `<Model>Service` | `ProductService` |
| Response serializer | `<Model>Serializer` | `ProductSerializer` |
| Request serializer (create) | `Create<Model>RequestSerializer` | `CreateProductRequestSerializer` |
| Request serializer (update) | `Update<Model>RequestSerializer` | `UpdateProductRequestSerializer` |
| ViewSet (space) | `<Model>ModelViewSet` | `ProductModelViewSet` |
| ViewSet (admin) | `<Model>AdminModelViewSet` | `ProductAdminModelViewSet` |
| ViewSet (consumer) | `<Model>ConsumerViewSet` | `ProductConsumerViewSet` |
| ViewSet (community) | `<Model>CommunityViewSet` | `ProductCommunityViewSet` |
| URL file | `<scope>_urls.py` | `space_urls.py`, `admin_urls.py` |
| Permission enum class | `<Model>Permissions` | `ProductPermissions` |
| App config class | `<Name>Config` | `ProductConfig` |

### 3.2 Biến / class / function

| Loại | Convention | Ví dụ |
|---|---|---|
| Class | `PascalCase` | `ProductService` |
| Function / method | `snake_case` | `get_all_by_organization()` |
| Biến thường | `snake_case` | `product_column`, `organization_uid` |
| Boolean | `is_*`, `has_*`, `can_*` | `is_active`, `has_permission` |
| Private | prefix `_` | `_internal_state` |
| Hằng số / Enum key | `UPPER_SNAKE_CASE` | `PRODUCT_READ`, `PRODUCT_WRITE` |
| UUID field (PK) | `uid` (luôn luôn) | `uid = columns.UUID(...)` |
| FK / organization | `*_uid` | `organization_uid`, `user_uid` |
| Table name | `snake_case` **số nhiều** | `__table_name__ = 'products'` |
| Permission key | `snake_case` **số nhiều** | `__permission_key__ = 'products'` |

### 3.3 Permission value format

```python
from core.enums import BaseStringEnum


class ProductPermissions(BaseStringEnum):
    PRODUCT_READ  = 'products.read'   # <permission_key>.<action>
    PRODUCT_WRITE = 'products.write'
```

Format chuẩn: **`<permission_key>.<action>`** · dùng `BaseStringEnum` từ `core.enums`.

### 3.4 URL pattern

| Scope | URL pattern | Router basename |
|---|---|---|
| Space (tenant) | `/api/space/<app>/<resource>/` | `api_space_<resource>` |
| Admin | `/api/admin/<app>/<resource>/` | `api_admin_<resource>` |
| Consumer | `/api/consumer/<app>/<resource>/` | `api_consumer_<resource>` |
| Community | `/api/community/<app>/<resource>/` | `api_community_<resource>` |

```python
from rest_framework import routers

router = routers.DefaultRouter(trailing_slash=False)
router.register(r'products', ProductModelViewSet, basename='api_space_products')
```

> **URLs tự động đăng ký** qua `core/routing/__init__.py` (auto-discovery). Không sửa `<project>/urls.py` thủ công.

---

## 4. Comment & Docstring convention

**Docstring style bắt buộc: Epytext Markup Language** (KHÔNG dùng Google / reST / Sphinx).

### 4.1 Class docstring

```python
class ProductModelViewSet(UserScopeProtectedModelViewSet):
    """
    Product model view set
    """
```

### 4.2 Method docstring (Epytext)

```python
@permission_required(ProductPermissions.PRODUCT_READ.value)
def list(self, request, *args, **kwargs):
    """
    Get product list
    @param request:
    @param args:
    @param kwargs:
    @return:
    """
    ...
```

### 4.3 Quy tắc comment

- **Module / class docstring**: bắt buộc ở `views`, có thể ngắn 1 dòng cho model / service.
- **Method docstring** trong ViewSet: dùng Epytext với `@param`, `@return`.
- **Inline comment** sau code, **2 space trước `#`**:
  ```python
  self.queryset = self.repository.all()  # lấy toàn bộ queryset
  ```
- **Block comment** trên đầu nhóm biến:
  ```python
  # Define filters, search and ordering rules
  filterset_fields = {
      'product_column': ['contains', 'exact'],
  }
  ```
- **Tách nhóm import** bằng 1 dòng trống:
  ```python
  from rest_framework.response import Response
  from rest_framework import status

  from core.decorators import permission_required
  from core.views.api.protected.user import UserScopeProtectedModelViewSet
  from <app>.repositories import <Model>Repository
  ```
- **Không comment thừa** — chỉ giải thích *tại sao* hoặc note nghiệp vụ quan trọng. Không mô tả lại *code đang làm gì*.

---

## 5. Model convention (Cassandra-style columns)

```python
from core.db.models import columns
from core.db.models import BaseTimeStampedModel, SoftDeletionMixin
from core.utils.uuid import generate_uuid


class Product(BaseTimeStampedModel):
    uid = columns.UUID(primary_key=True, default=generate_uuid)
    product_column = columns.Text(required=False, max_length=255)

    __table_name__ = 'products'                   # số nhiều, snake_case
    __permission_key__ = 'products'               # số nhiều, snake_case
    __permission_tenant_scope__ = True             # True nếu scope theo tenant

    class Meta:
        get_pk_field = 'uid'
```

**Rules:**

- **PK luôn là UUID** (`uid`), tạo bằng `generate_uuid`.
- **Columns import từ** `core.db.models.columns` (KHÔNG dùng `models.*` của Django).
- **Base class**: `BaseTimeStampedModel` (có thể mix `SoftDeletionMixin`).
- `__table_name__` & `__permission_key__` luôn **số nhiều snake_case**.

---

## 6. Repository / Service / View pattern

### 6.1 Repository

```python
from core.repositories import BaseRepository
from <app>.models import <Model>


class <Model>Repository(BaseRepository):
    def __init__(self):
        self.model = <Model>
```

### 6.2 Service (inject repo, cho phép override qua DI)

```python
from core.services import BaseService
from <app>.repositories import <Model>Repository


class <Model>Service(BaseService):
    repository: <Model>Repository

    def __init__(self, **kwargs):
        if kwargs.get('repository', None):
            self.repository = kwargs.get('repository')
        else:
            self.repository = <Model>Repository()
```

### 6.3 ViewSet

```python
class <Model>ModelViewSet(UserScopeProtectedModelViewSet):
    """
    <Model> model view set
    """
    # Define filters, search and ordering rules
    filterset_fields = {
        '<column>': ['contains', 'exact'],
    }
    search_fields = ['<column>']

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.serializer_class = <Model>Serializer
        self.repository = <Model>Repository()
        self.queryset = self.repository.all()
        self.service = <Model>Service(repository=self.repository)

    @permission_required(<Model>Permissions.<MODEL>_READ.value)
    def list(self, request, *args, **kwargs):
        """
        Get <model> list
        @param request:
        @param args:
        @param kwargs:
        @return:
        """
        organization = getattr(request, 'tenant', None)
        self.queryset = self.repository.get_all_by_organization(
            organization.uid if organization else None
        )
        return super().list(request, *args, **kwargs)
```

**Rules:**

- Scope view: `UserScopeProtectedModelViewSet` (space) hoặc `StaffScopeProtectedModelViewSet` (admin).
- **Mọi method phải có** `@permission_required(EnumValue.value)`.
- **Tenant**: lấy `organization = getattr(request, 'tenant', None)`.
- Method chuẩn: `list, create, retrieve, update, destroy`.
- Trong `__init__` phải set: `serializer_class`, `repository`, `queryset`, `service`.

---

## 7. Serializer convention

```python
# Response serializer
from core.serializers import BaseModelSerializer
from <app>.models import <Model>


class <Model>Serializer(BaseModelSerializer):
    class Meta:
        model = <Model>
        fields = '__all__'
```

```python
# Request serializer (create)
from rest_framework import serializers
from core.serializers.requests import BaseRequestSerializer


class Create<Model>RequestSerializer(BaseRequestSerializer):
    <column> = serializers.CharField(max_length=255, required=False, allow_null=True, allow_blank=True)

    class Meta:
        fields = ['<column>']
```

```python
# Request serializer (update) - kế thừa từ Create
from <app>.serializers.requests.create_<model>_request_serializer import Create<Model>RequestSerializer


class Update<Model>RequestSerializer(Create<Model>RequestSerializer):
    ...
```

---

## 8. Multi-tenancy rules

1. Model có `__permission_tenant_scope__ = True` nếu scope theo tenant.
2. Mọi query lọc theo `organization_uid`.
3. View luôn lấy `request.tenant`.
4. Service nhận `organization` làm tham số đầu tiên trong `create`:
   ```python
   instance = self.service.create(organization, serializer.validated_data)
   ```
5. Permission dùng `BaseStringEnum` kế thừa từ `core.enums`.

---

## 9. Workflow tạo feature mới

```
Models → Repositories → Services → Serializers → Views → Enums → (Routing auto) → Tests
```

1. Scaffold: `python3 manage.py startapp_scaffold <app_name>`.
2. Đăng ký app trong `<project>/configs/installed_apps.py` đúng feature group.
3. Implement theo thứ tự trên.
4. URL tự động — KHÔNG sửa `<project>/urls.py` root.
5. Test theo cùng cấu trúc trong `tests/`.

---

## 10. Code quality rules

- ✅ PEP 8.
- ✅ Type hints khi có thể.
- ✅ Docstring đầy đủ cho method public.
- ✅ Custom exceptions từ `core.exceptions`.
- ✅ Validate business rules ở **Service**, validate input ở **Serializer**.
- ✅ Mock external services trong tests.
- ✅ Celery cho async task — lưu ở `worker/tasks/`.
- ✅ Cache thông qua repository pattern (nếu có).

---

## 11. Những điểm hay quên (Anti-patterns)

| ❌ Đừng | ✅ Nên làm |
|---|---|
| Dùng `models.UUIDField()` của Django | Dùng `columns.UUID()` từ `core.db.models.columns` |
| Hardcode URL root | Để auto-discovery trong `core/routing/` |
| Tạo PK auto-increment | Chỉ dùng UUID qua `generate_uuid` |
| Docstring style Google/Sphinx | **Epytext** (`@param`, `@return`) |
| Bỏ `@permission_required` trên method view | Bắt buộc trên **mọi** method |
| Quên set `queryset`/`repository`/`service` trong `__init__` | Set đủ 4 thuộc tính |
| Truyền enum không có `.value` | Luôn `EnumValue.value` khi vào decorator |
| `__table_name__` / `__permission_key__` số ít | **Số nhiều** snake_case (`products`, không `product`) |
| Trộn Google/NumPy/Sphinx docstring | **Epytext** thống nhất toàn project |
| Import không nhóm | Nhóm: stdlib → 3rd-party → internal, cách 1 dòng trống |

---

## 12. Checklist tạo app mới (copy-paste)

```bash
# 1. Scaffold
python3 manage.py startapp_scaffold <app_name>

# 2. Đăng ký trong <project>/configs/installed_apps.py
#    Thêm '<app_name>' vào tuple feature group phù hợp

# 3. Implement theo thứ tự
#    - models/<app>/models/<model>.py
#    - repositories/<app>/repositories/<model>_repository.py
#    - services/<app>/services/<model>_service.py
#    - serializers/<app>/serializers/<model>_serializer.py
#    - serializers/requests/create_<model>_request_serializer.py
#    - serializers/requests/update_<model>_request_serializer.py
#    - enums/<app>/enums/<model>_permissions.py
#    - views/api/space/<model>_model_view_set.py
#    - views/api/admin/<model>_admin_model_view_set.py

# 4. (Optional) Test
#    tests/<app>/test_<model>.py

# 5. Chạy
python3 manage.py makemigrations <app_name>
python3 manage.py migrate <app_name>
```
