import hashlib
import hmac
import json
import uuid
import requests
from django.conf import settings


class MoMoService:
    PARTNER_CODE = getattr(settings, 'MOMO_PARTNER_CODE', 'MOMO')
    ACCESS_KEY = getattr(settings, 'MOMO_ACCESS_KEY', 'F8BBA842ECF85')
    SECRET_KEY = getattr(settings, 'MOMO_SECRET_KEY', 'K951B6PE1waDMi640xX08PD3vg6EkVlz')
    ENDPOINT = getattr(settings, 'MOMO_ENDPOINT', 'https://test-payment.momo.vn/v2/gateway/api/create')
    REDIRECT_URL = getattr(settings, 'MOMO_REDIRECT_URL', 'http://localhost:3000/payment/result')
    IPN_URL = getattr(settings, 'MOMO_IPN_URL', 'http://localhost:8000/api/v1/consumer/payment/ipn/')

    def _sign(self, raw: str) -> str:
        return hmac.new(
            self.SECRET_KEY.encode('utf-8'),
            raw.encode('utf-8'),
            hashlib.sha256,
        ).hexdigest()

    def create_payment(self, order_id: str, amount: int, order_info: str, extra_data: str = '') -> dict:
        request_id = str(uuid.uuid4())
        raw = (
            f"accessKey={self.ACCESS_KEY}"
            f"&amount={amount}"
            f"&extraData={extra_data}"
            f"&ipnUrl={self.IPN_URL}"
            f"&orderId={order_id}"
            f"&orderInfo={order_info}"
            f"&partnerCode={self.PARTNER_CODE}"
            f"&redirectUrl={self.REDIRECT_URL}"
            f"&requestId={request_id}"
            f"&requestType=payWithMethod"
        )
        signature = self._sign(raw)
        payload = {
            "partnerCode": self.PARTNER_CODE,
            "accessKey": self.ACCESS_KEY,
            "requestId": request_id,
            "amount": amount,
            "orderId": order_id,
            "orderInfo": order_info,
            "redirectUrl": self.REDIRECT_URL,
            "ipnUrl": self.IPN_URL,
            "extraData": extra_data,
            "requestType": "payWithMethod",
            "signature": signature,
            "lang": "vi",
        }
        response = requests.post(self.ENDPOINT, json=payload, timeout=15)
        response.raise_for_status()
        data = response.json()
        return {"request_id": request_id, **data}

    def verify_ipn(self, data: dict) -> bool:
        raw = (
            f"accessKey={self.ACCESS_KEY}"
            f"&amount={data.get('amount')}"
            f"&extraData={data.get('extraData', '')}"
            f"&message={data.get('message', '')}"
            f"&orderId={data.get('orderId')}"
            f"&orderInfo={data.get('orderInfo', '')}"
            f"&orderType={data.get('orderType', '')}"
            f"&partnerCode={data.get('partnerCode')}"
            f"&payType={data.get('payType', '')}"
            f"&requestId={data.get('requestId')}"
            f"&responseTime={data.get('responseTime')}"
            f"&resultCode={data.get('resultCode')}"
            f"&transId={data.get('transId')}"
        )
        expected = self._sign(raw)
        return hmac.compare_digest(expected, data.get('signature', ''))
