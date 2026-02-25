import secrets
import string

def generate_tracking_code(length: int = 12) -> str:
    """
    Generates a secure, unpredictable alphanumeric tracking code.
    E.g., X9F2KQ8P4MW1
    """
    alphabet = string.ascii_uppercase + string.digits
    # Exclude confusing characters like O, 0, I, 1
    safe_alphabet = ''.join(c for c in alphabet if c not in 'O0I1')
    return ''.join(secrets.choice(safe_alphabet) for _ in range(length))
