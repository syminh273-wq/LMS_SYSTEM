from features.account.consumer.repositories.address_repository import AddressRepository
from features.account.consumer.serializers.address_serializer import (
    AddressReadSerializer,
    AddressUpsertSerializer,
)
from features.account.static_data import get_province, get_ward


class AddressService:

    def __init__(self):
        self.repo = AddressRepository()

    def get_for_owner(self, owner_id, owner_type: str):
        instance = self.repo.get_by_owner(owner_id, owner_type)
        if not instance:
            return None
        return AddressReadSerializer.from_model(instance)

    def upsert_for_owner(self, owner_id, owner_type: str, data: dict):
        serializer = AddressUpsertSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        clean = serializer.validated_data

        province = get_province(clean['province_code'])
        ward     = get_ward(clean['province_code'], clean['ward_code'])

        payload = {
            'type':          clean['type'],
            'label':         clean.get('label', '') or '',
            'line1':         clean.get('line1', '') or '',
            'line2':         clean.get('line2', '') or '',
            'province_code': province['code'],
            'province_name': province['name'],
            'ward_code':     ward['code'],
            'ward_name':     ward['name'],
            'country':       clean.get('country', 'Việt Nam') or 'Việt Nam',
        }
        instance = self.repo.upsert(owner_id, owner_type, payload)
        return AddressReadSerializer.from_model(instance)

    def soft_delete_for_owner(self, owner_id, owner_type: str) -> bool:
        instance = self.repo.get_by_owner(owner_id, owner_type)
        if not instance:
            return False
        instance.soft_delete()
        return True
