"""Verify the address join logic for the test uid, without HTTP."""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'LMS_SYSTEM.settings')
import django
django.setup()

import uuid
from features.account.consumer.services.student_profile_service import StudentProfileService
from features.account.consumer.services.address_service import AddressService
from features.account.consumer.services import ConsumerService
from features.account.consumer.serializers import ConsumerAccountSerializer
from features.account.space.models.space import Space

UID = "25fd4bf8-71ab-4d95-8742-fd919f99ae4b"


def _format_address_public(addr_dict):
    if not addr_dict:
        return ''
    parts = []
    for key in ('line1', 'ward_name', 'province_name'):
        value = (addr_dict.get(key) or '').strip()
        if value:
            parts.append(value)
    return ', '.join(parts)


svc = StudentProfileService()
settings = svc.get_or_create(UID)
data = svc.serialize(settings)

print("=" * 80)
print("PublicStudentProfileView logic trace for uid:", UID)
print("=" * 80)
print(f"show_address = {data.get('show_address')}")
print(f"profile_visibility = {data.get('profile_visibility')!r}")
print(f"data['address'] BEFORE join = {data.get('address')!r}")

# Determine owner_type
owner_type = None
consumer_dict = None
try:
    consumer = ConsumerService().find(UID)
    consumer_dict = ConsumerAccountSerializer(consumer).data
    owner_type = 'consumer'
    print(f"  -> resolved as Consumer: full_name={consumer_dict.get('full_name')!r}")
except Exception as e:
    print(f"  -> NOT a Consumer: {e}")

if not consumer_dict:
    try:
        space_rows = list(Space.objects.filter(uid=uuid.UUID(UID)).limit(1))
        if space_rows:
            owner_type = 'space'
            print(f"  -> resolved as Space: name={space_rows[0].name!r}")
    except Exception as e:
        print(f"  -> NOT a Space: {e}")

print(f"owner_type = {owner_type!r}")

if data.get('show_address') and owner_type:
    addr_dict = AddressService().get_for_owner(UID, owner_type)
    print(f"  addr_dict = {addr_dict}")
    formatted = _format_address_public(addr_dict or {})
    print(f"data['address'] AFTER join = {formatted!r}")
else:
    print("SKIPPED join (show_address=False or owner_type=None)")
