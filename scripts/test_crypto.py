"""Test script for crypto_utils.py"""
import sys
import json
from crypto_utils import ExpenseEncryptor

def test_encryption():
    # Test data
    test_expense = {
        'date': '2023-01-01',
        'amount': 42.50,
        'category': 'Food',
        'description': 'Lunch at cafe'
    }
    
    # Get passphrase from command line or use default for testing
    passphrase = sys.argv[1] if len(sys.argv) > 1 else 'my-secret-passphrase'
    
    print(f"Using passphrase: {passphrase}")
    
    # Create encryptor (generates new salt)
    encryptor = ExpenseEncryptor(passphrase)
    print(f"Generated salt: {encryptor.salt_hex}")
    
    # Encrypt the data
    encrypted = encryptor.encrypt_expense(test_expense)
    print("\nEncrypted data:")
    print(json.dumps(encrypted, indent=2))
    
    # Create a new encryptor with the same salt to simulate loading
    encryptor2 = ExpenseEncryptor.from_salt_hex(passphrase, encryptor.salt_hex)
    
    # Decrypt the data
    decrypted = encryptor2.decrypt_expense(encrypted)
    print("\nDecrypted data:")
    print(json.dumps(decrypted, indent=2))
    
    # Verify decryption
    assert decrypted['date'] == test_expense['date']
    assert decrypted['amount'] == test_expense['amount']
    assert decrypted['category'] == test_expense['category']
    assert decrypted['description'] == test_expense['description']
    print("\n✅ Test passed: Decrypted data matches original!")

if __name__ == "__main__":
    test_encryption()
