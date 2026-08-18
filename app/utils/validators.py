import phonenumbers
from phonenumbers.phonenumberutil import NumberParseException

def is_valid_phone(phone: str) -> bool:
    try:
        parsed = phonenumbers.parse(phone, "US")
        return (
            phonenumbers.is_valid_number(parsed)
            and phonenumbers.is_possible_number(parsed)
            and parsed.country_code == 1
        )
    except NumberParseException:
        return False
    
def normalize_phone(phone: str) -> str | None:
    try:
        parsed = phonenumbers.parse(phone, "US")

        if (
            phonenumbers.is_valid_number(parsed)
            and phonenumbers.is_possible_number(parsed)
            and parsed.country_code == 1
        ):
            return phonenumbers.format_number(
                parsed,
                phonenumbers.PhoneNumberFormat.E164
            )

        return None

    except NumberParseException:
        return None