import phonenumbers
from phonenumbers.phonenumberutil import NumberParseException

def is_valid_us_phone(phone: str) -> bool:
    try:
        parsed = phonenumbers.parse(phone, "US")
        return (
            phonenumbers.is_valid_number(parsed)
            and phonenumbers.is_possible_number(parsed)
            and parsed.country_code == 1
        )
    except NumberParseException:
        return False