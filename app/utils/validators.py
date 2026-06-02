import phonenumbers
from phonenumbers.phonenumberutil import NumberParseException

def is_valid_phone(phone: str, region: str = None) -> bool:
    try:
        parsed = phonenumbers.parse(phone, region)

        return (
            phonenumbers.is_valid_number(parsed) and
            phonenumbers.is_possible_number(parsed)
        )

    except NumberParseException:
        return False