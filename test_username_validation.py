#!/usr/bin/env python3
"""
Test script to verify username validation is working correctly.
"""

import re
from typing import List, Tuple

# Username validation pattern: alphanumeric, underscore, hyphen only
USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{3,30}$')

# Reserved usernames
RESERVED_USERNAMES = ['admin', 'root', 'system', 'api', 'support', 'help', 'null', 'undefined']

def validate_username(username: str) -> Tuple[bool, str]:
    """
    Validate username format.
    Returns (is_valid, error_message)
    """
    if len(username) < 3:
        return False, "Username must be at least 3 characters"
    
    if len(username) > 30:
        return False, "Username must be at most 30 characters"
    
    if not USERNAME_PATTERN.match(username):
        return False, "Username must contain only alphanumeric characters, underscores, and hyphens"
    
    if username.lower() in RESERVED_USERNAMES:
        return False, "This username is reserved"
    
    return True, "Valid"

def run_tests():
    """Run comprehensive username validation tests."""
    
    test_cases = [
        # Valid usernames
        ("validuser", True, "Valid alphanumeric username"),
        ("user123", True, "Valid with numbers"),
        ("user_name", True, "Valid with underscore"),
        ("user-name", True, "Valid with hyphen"),
        ("abc", True, "Valid minimum length (3 chars)"),
        ("a" * 30, True, "Valid maximum length (30 chars)"),
        ("John_Doe-123", True, "Valid mixed characters"),
        
        # Invalid usernames - XSS attempts
        ("<script>alert('xss')</script>", False, "XSS script tag"),
        ("<a href='javascript:alert(1)'>click</a>", False, "XSS link tag"),
        ("user<img src=x onerror=alert(1)>", False, "XSS img tag"),
        ("'; DROP TABLE users; --", False, "SQL injection attempt"),
        
        # Invalid usernames - special characters
        ("user@example.com", False, "Email as username"),
        ("user name", False, "Space in username"),
        ("user.name", False, "Dot in username"),
        ("user!name", False, "Exclamation mark"),
        ("user#name", False, "Hash symbol"),
        ("user$name", False, "Dollar sign"),
        ("user%name", False, "Percent sign"),
        ("user&name", False, "Ampersand"),
        ("user*name", False, "Asterisk"),
        ("user(name)", False, "Parentheses"),
        ("user[name]", False, "Brackets"),
        ("user{name}", False, "Braces"),
        ("user|name", False, "Pipe"),
        ("user\\name", False, "Backslash"),
        ("user/name", False, "Forward slash"),
        ("user:name", False, "Colon"),
        ("user;name", False, "Semicolon"),
        ("user'name", False, "Single quote"),
        ('user"name', False, "Double quote"),
        ("user,name", False, "Comma"),
        ("user<name>", False, "Angle brackets"),
        ("user=name", False, "Equals sign"),
        ("user+name", False, "Plus sign"),
        ("user?name", False, "Question mark"),
        
        # Invalid usernames - length
        ("ab", False, "Too short (2 chars)"),
        ("a", False, "Too short (1 char)"),
        ("", False, "Empty string"),
        ("a" * 31, False, "Too long (31 chars)"),
        ("a" * 50, False, "Too long (50 chars)"),
        
        # Invalid usernames - reserved
        ("admin", False, "Reserved: admin"),
        ("root", False, "Reserved: root"),
        ("system", False, "Reserved: system"),
        ("api", False, "Reserved: api"),
        ("Admin", False, "Reserved: Admin (case insensitive)"),
        ("ADMIN", False, "Reserved: ADMIN (case insensitive)"),
        
        # Invalid usernames - unicode/emoji
        ("user😀", False, "Emoji in username"),
        ("usér", False, "Accented character"),
        ("用户", False, "Chinese characters"),
        ("пользователь", False, "Cyrillic characters"),
        
        # Invalid usernames - whitespace variants
        ("user name", False, "Space"),
        ("user\tname", False, "Tab character"),
        ("user\nname", False, "Newline character"),
        ("user\rname", False, "Carriage return"),
        (" username", False, "Leading space"),
        ("username ", False, "Trailing space"),
        ("  username  ", False, "Leading and trailing spaces"),
        
        # Edge cases
        ("---", True, "Only hyphens (valid)"),
        ("___", True, "Only underscores (valid)"),
        ("123", True, "Only numbers (valid)"),
        ("_-_", True, "Mixed hyphens and underscores (valid)"),
    ]
    
    print("\n" + "="*100)
    print("USERNAME VALIDATION TEST RESULTS")
    print("="*100)
    
    passed = 0
    failed = 0
    
    for username, expected_valid, description in test_cases:
        is_valid, error_msg = validate_username(username)
        
        # Check if test passed
        test_passed = (is_valid == expected_valid)
        
        if test_passed:
            passed += 1
            status = "✅ PASS"
        else:
            failed += 1
            status = "❌ FAIL"
        
        # Format username for display (show special chars)
        display_username = repr(username) if len(username) > 30 or any(c in username for c in [' ', '\t', '\n', '\r', '<', '>', '&']) else f"'{username}'"
        
        print(f"\n{status} | {description}")
        print(f"       Username: {display_username}")
        print(f"       Expected: {'Valid' if expected_valid else 'Invalid'}")
        print(f"       Result: {error_msg}")
    
    print("\n" + "="*100)
    print(f"SUMMARY: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("="*100 + "\n")
    
    return failed == 0

if __name__ == "__main__":
    import sys
    success = run_tests()
    sys.exit(0 if success else 1)





