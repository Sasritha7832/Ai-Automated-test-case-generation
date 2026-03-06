import re
import random
import string
from typing import Dict, Any

class TestDataGenerator:
    """
    Generates realistic input values for testing.
    Uses deterministic rules rather than LLM hallucination for generating
    valid and invalid data payloads.
    """
    
    def __init__(self):
        pass

    def generate_email(self, valid: bool = True) -> str:
        """Generates a valid or invalid email address."""
        if valid:
            domains = ["example.com", "test.org", "demo.co.uk", "mail.net"]
            chars = string.ascii_lowercase + string.digits
            name = ''.join(random.choice(chars) for _ in range(8))
            return f"{name}@{random.choice(domains)}"
        else:
            invalid_formats = [
                "plainaddress",
                "#@%^%#$@#$@#.com",
                "@example.com",
                "Joe Smith <email@example.com>",
                "email.example.com",
                "email@example@example.com",
                ".email@example.com",
                "email.@example.com",
                "email..email@example.com"
            ]
            return random.choice(invalid_formats)

    def generate_password(self, valid: bool = True) -> str:
        """Generates a password (valid means complex enough)."""
        if valid:
            # At least 8 chars, 1 upper, 1 lower, 1 digit, 1 special
            lower = ''.join(random.choice(string.ascii_lowercase) for _ in range(3))
            upper = ''.join(random.choice(string.ascii_uppercase) for _ in range(3))
            digit = ''.join(random.choice(string.digits) for _ in range(2))
            special = ''.join(random.choice("!@#$%^&*") for _ in range(2))
            pwd = list(lower + upper + digit + special)
            random.shuffle(pwd)
            return ''.join(pwd)
        else:
            return "pass123" # Too simple/short

    def generate_number(self, min_val: float = 0, max_val: float = 100, valid: bool = True, boundary: bool = False) -> Any:
        """Generates a numeric value within or outside bounds."""
        if valid:
            if boundary:
                return random.choice([min_val, max_val])
            return random.uniform(min_val, max_val)
        else:
            return random.choice([min_val - 1, max_val + 1, "NaN", None])

    def generate_string(self, min_len: int = 1, max_len: int = 50, valid: bool = True, boundary: bool = False) -> Any:
        """Generates a string of specific length."""
        chars = string.ascii_letters + string.digits + " "
        
        if valid:
            if boundary:
                length = random.choice([min_len, max_len])
            else:
                length = random.randint(min_len, max_len)
            return ''.join(random.choice(chars) for _ in range(length))
        else:
            return random.choice([
                "", # Empty usually invalid if min_len > 0
                ''.join(random.choice(chars) for _ in range(max_len + 10)), # Too long
                None
            ])

    def generate_data_for_field(self, field_name: str, field_type: str = "string", rules: Dict = None) -> Dict[str, Any]:
        """
        Generates both valid and invalid testing data for a specific field based on heuristics.
        """
        rules = rules or {}
        field_name_lower = field_name.lower()
        
        valid_val = None
        invalid_val = None
        
        if "email" in field_name_lower:
            valid_val = self.generate_email(valid=True)
            invalid_val = self.generate_email(valid=False)
        elif "password" in field_name_lower:
            valid_val = self.generate_password(valid=True)
            invalid_val = self.generate_password(valid=False)
        elif field_type == "number" or "age" in field_name_lower or "amount" in field_name_lower:
            min_v = rules.get("min", 0)
            max_v = rules.get("max", 1000)
            valid_val = self.generate_number(min_val=min_v, max_val=max_v, valid=True)
            invalid_val = self.generate_number(min_val=min_v, max_val=max_v, valid=False)
        else:
            min_l = rules.get("min_length", 1)
            max_l = rules.get("max_length", 50)
            valid_val = self.generate_string(min_len=min_l, max_len=max_l, valid=True)
            invalid_val = self.generate_string(min_len=min_l, max_len=max_l, valid=False)
            
        return {
            "field": field_name,
            "valid_input": valid_val,
            "invalid_input": invalid_val
        }
