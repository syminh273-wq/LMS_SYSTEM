"""Inspect address + consumer + space + portfolio for a given uid."""
import os
import sys
import uuid

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'LMS_SYSTEM.settings')

import django
django.setup()

UID = "25fd4bf8-71ab-4d95-8742-fd919f99ae4b"
target_uuid = uuid.UUID(UID)

print("=" * 80)
print(f"INSPECTING DB FOR uid={UID}")
print("=" * 80)

# 1. Address
print("\n[1] account_addresses for owner_id=uid, owner_type='consumer':")
try:
    from features.account.consumer.models.address import Address
    rows = list(Address.objects.filter(
        owner_id=target_uuid, owner_type='consumer', is_deleted=False
    ).allow_filtering())
    if not rows:
        print("    (no row found)")
    for r in rows:
        print(f"    uid={r.uid}")
        print(f"    owner_id={r.owner_id}, owner_type={r.owner_type}")
        print(f"    type={r.type}, label={r.label!r}")
        print(f"    line1={r.line1!r}")
        print(f"    line2={r.line2!r}")
        print(f"    ward_name={r.ward_name!r} (code={r.ward_code})")
        print(f"    province_name={r.province_name!r} (code={r.province_code})")
        print(f"    country={r.country!r}")
        print(f"    is_deleted={r.is_deleted}")
except Exception as e:
    print(f"    ERROR: {e}")

# 1b. Also check if a 'space' address exists (since public endpoint also handles Space)
print("\n[1b] account_addresses for owner_id=uid, owner_type='space':")
try:
    rows = list(Address.objects.filter(
        owner_id=target_uuid, owner_type='space', is_deleted=False
    ).allow_filtering())
    if not rows:
        print("    (no row found)")
    for r in rows:
        print(f"    uid={r.uid}, line1={r.line1!r}, ward_name={r.ward_name!r}, province_name={r.province_name!r}")
except Exception as e:
    print(f"    ERROR: {e}")

# 2. Consumer
print("\n[2] account_consumers by uid:")
try:
    from features.account.consumer.models.consumer import Consumer
    try:
        c = Consumer.objects.get(uid=target_uuid)
        print(f"    FOUND Consumer: uid={c.uid}, full_name={c.full_name!r}, email={c.email!r}, role={c.role!r}")
    except Consumer.DoesNotExist:
        print("    (not found as Consumer)")
except Exception as e:
    print(f"    ERROR: {e}")

# 3. Space
print("\n[3] account_spaces by uid:")
try:
    from features.account.space.models.space import Space
    try:
        s = Space.objects.get(uid=target_uuid)
        print(f"    FOUND Space: uid={s.uid}, name={s.name!r}, full_name={s.full_name!r}, slug={s.slug!r}")
    except Space.DoesNotExist:
        print("    (not found as Space)")
except Exception as e:
    print(f"    ERROR: {e}")

# 4. Portfolio education entries
print("\n[4] portfolios for owner_id=uid, owner_type='consumer' (any key):")
try:
    from features.portfolio.models.portfolio import Portfolio
    rows = list(Portfolio.objects.filter(
        owner_id=target_uuid, owner_type='consumer', is_deleted=False
    ).allow_filtering())
    if not rows:
        print("    (no portfolio rows)")
    for r in rows:
        print(f"    uid={r.uid}, key={r.key!r}, is_public={r.is_public}, display_order={r.display_order}")
        print(f"    value={r.value[:200] if r.value else None!r}")
except Exception as e:
    print(f"    ERROR: {e}")

# 5. StudentProfileSettings
print("\n[5] student_profile_settings for consumer_uid=uid:")
try:
    from features.account.consumer.models.student_profile_settings import StudentProfileSettings
    try:
        s = StudentProfileSettings.objects.get(consumer_uid=target_uuid)
        print(f"    FOUND: bio={s.bio!r}, address={s.address!r}, city={s.city!r}")
        print(f"    show_address={s.show_address}, profile_visibility={s.profile_visibility!r}")
    except StudentProfileSettings.DoesNotExist:
        print("    (no settings row)")
except Exception as e:
    print(f"    ERROR: {e}")

print("\n" + "=" * 80)
print("DONE")
print("=" * 80)
