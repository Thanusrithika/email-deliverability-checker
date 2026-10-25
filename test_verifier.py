import unittest
from verifier import verify_email, verify_emails_batch, check_syntax

class TestEmailVerifier(unittest.TestCase):
    def test_syntax_validation(self):
        valid, msg, _, _ = check_syntax("user@example.com")
        self.assertTrue(valid)

        invalid_cases = [
            "",
            "user",
            "@example.com",
            "user@",
            "user..name@example.com",
            "user@.com",
            "user@example",
        ]
        for email in invalid_cases:
            valid, _, _, _ = check_syntax(email)
            self.assertFalse(valid, f"Should be invalid: {email}")

    def test_invalid_syntax_bounce(self):
        res = verify_email("bad..user@example.com")
        self.assertEqual(res["category"], "likely_to_bounce")
        self.assertFalse(res["syntax_valid"])

    def test_nonexistent_domain_bounce(self):
        res = verify_email("hello@thisdomainabsolutelydoesnotexist999888777.com")
        self.assertEqual(res["category"], "likely_to_bounce")
        self.assertTrue(res["syntax_valid"])
        self.assertEqual(len(res["mx_records"]), 0)

    def test_disposable_domain(self):
        res = verify_email("test@mailinator.com")
        self.assertTrue(res["is_disposable"])

    def test_batch_processing(self):
        emails = [
            "syntax..error@test.com",
            "nobody@doesnotexist999888777.org",
            "admin@github.com"
        ]
        results = verify_emails_batch(emails)
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0]["category"], "likely_to_bounce")
        self.assertEqual(results[1]["category"], "likely_to_bounce")

if __name__ == "__main__":
    unittest.main()
