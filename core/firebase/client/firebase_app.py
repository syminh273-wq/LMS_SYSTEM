import logging

import firebase_admin
from firebase_admin import credentials, db, messaging
from decouple import config

logger = logging.getLogger(__name__)


class FirebaseApp:
    _app = None

    @classmethod
    def init_app(cls):
        if cls._app:
            return cls._app
        try:
            cls._app = firebase_admin.get_app()
            return cls._app
        except ValueError:
            private_key = config('FIREBASE_PRIVATE_KEY', default=None)
            if private_key:
                private_key = private_key.replace('\\n', '\n')

            project_id = config('FIREBASE_PROJECT_ID', default=None)
            region = config('FIREBASE_REGION', default='asia-southeast1')

            cred_dict = {
                "type": "service_account",
                "project_id": project_id,
                "private_key_id": config('FIREBASE_PRIVATE_KEY_ID', default=None),
                "private_key": private_key,
                "client_email": config('FIREBASE_CLIENT_EMAIL', default=None),
                "client_id": config('FIREBASE_CLIENT_ID', default=None),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": config('FIREBASE_CLIENT_X509_CERT_URL', default=None),
            }

            cred = credentials.Certificate(cred_dict)
            database_url = f"https://{project_id}-default-rtdb.{region}.firebasedatabase.app"

            cls._app = firebase_admin.initialize_app(cred, {"databaseURL": database_url})
            return cls._app

    @classmethod
    def db_ref(cls, path: str):
        cls.init_app()
        return db.reference(path)

    @classmethod
    def get_value(cls, path: str):
        try:
            return cls.db_ref(path).get()
        except Exception as e:
            logger.error(f"[Firebase] get_value failed at {path}: {e}")
            return None

    @classmethod
    def set_value(cls, path: str, data):
        try:
            cls.db_ref(path).set(data)
            return True
        except Exception as e:
            logger.error(f"[Firebase] set_value failed at {path}: {e}")
            return False

    @classmethod
    def push_value(cls, path: str, data):
        """Append a new child with auto-generated key (Firebase list push)."""
        try:
            return cls.db_ref(path).push(data)
        except Exception as e:
            logger.error(f"[Firebase] push_value failed at {path}: {e}")
            return None

    @classmethod
    def update_value(cls, path: str, data):
        try:
            cls.db_ref(path).update(data)
            return True
        except Exception as e:
            logger.error(f"[Firebase] update_value failed at {path}: {e}")
            return False

    @classmethod
    def send_fcm(cls, message):
        cls.init_app()
        try:
            return messaging.send(message)
        except Exception as e:
            logger.error(f"[Firebase] send_fcm failed: {e}")
            return None
