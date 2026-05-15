from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

def global_exception_handler(exc, context):
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    if response is not None:
        # If the exception is a ValidationError or similar, the data will be a dict or list
        if isinstance(response.data, dict):
            formatted_errors = {}
            for field, value in response.data.items():
                if isinstance(value, list) and len(value) > 0:
                    # Take the first error message
                    msg = str(value[0])
                    formatted_errors[field] = msg
                elif isinstance(value, dict):
                    # Handle nested dicts if any (take first error of first field)
                    first_key = next(iter(value))
                    first_val = value[first_key]
                    if isinstance(first_val, list) and len(first_val) > 0:
                        formatted_errors[field] = str(first_val[0])
                    else:
                        formatted_errors[field] = str(first_val)
                else:
                    formatted_errors[field] = str(value)
            
            response.data = formatted_errors
        elif isinstance(response.data, list):
            # If it's a list (e.g. non-field errors), handle it
            if len(response.data) > 0:
                response.data = {"detail": str(response.data[0])}

    return response
