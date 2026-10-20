import unittest
from backend.detector import detect_repeated_login_failures


class DetectorTests(unittest.TestCase):
    def test_detects_five_failures_in_five_minutes(self):
        events = [
            {
                "timestamp": f"2026-10-20T10:0{i}:00+07:00",
                "source_ip": "192.0.2.10",
                "event_type": "login_failure",
                "username": "demo-user",
                "outcome": "failure",
            }
            for i in range(5)
        ]
        alerts = detect_repeated_login_failures(events)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["risk"], "high")

    def test_does_not_alert_for_four_failures(self):
        events = [
            {
                "timestamp": f"2026-10-20T10:0{i}:00+07:00",
                "source_ip": "192.0.2.10",
                "event_type": "login_failure",
                "username": "demo-user",
                "outcome": "failure",
            }
            for i in range(4)
        ]
        self.assertEqual(detect_repeated_login_failures(events), [])


if __name__ == "__main__":
    unittest.main()
