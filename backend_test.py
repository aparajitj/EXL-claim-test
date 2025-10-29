import requests
import sys
import json
import tempfile
import os
from datetime import datetime

class InsuranceClaimAPITester:
    def __init__(self, base_url="https://claim-analyzer-5.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.token = None
        self.user_data = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED")
        else:
            print(f"❌ {name} - FAILED: {details}")
        
        self.test_results.append({
            "test": name,
            "success": success,
            "details": details
        })

    def run_test(self, name, method, endpoint, expected_status, data=None, files=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        headers = {}
        
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        
        if not files:
            headers['Content-Type'] = 'application/json'

        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        print(f"   Method: {method}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                if files:
                    response = requests.post(url, headers={k: v for k, v in headers.items() if k != 'Content-Type'}, 
                                           data=data, files=files, timeout=60)
                else:
                    response = requests.post(url, json=data, headers=headers, timeout=30)

            success = response.status_code == expected_status
            details = f"Status: {response.status_code}"
            
            if not success:
                details += f" (Expected {expected_status})"
                try:
                    error_data = response.json()
                    details += f" - {error_data.get('detail', 'Unknown error')}"
                except:
                    details += f" - {response.text[:200]}"

            self.log_test(name, success, details)
            
            if success:
                try:
                    return True, response.json()
                except:
                    return True, {}
            else:
                return False, {}

        except Exception as e:
            self.log_test(name, False, f"Exception: {str(e)}")
            return False, {}

    def test_user_registration(self):
        """Test user registration"""
        test_email = f"test_user_{datetime.now().strftime('%H%M%S')}@example.com"
        user_data = {
            "email": test_email,
            "password": "TestPass123!",
            "full_name": "Test User"
        }
        
        success, response = self.run_test(
            "User Registration",
            "POST",
            "auth/register",
            200,
            data=user_data
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            self.user_data = response['user']
            return True
        return False

    def test_user_login(self):
        """Test user login with existing user"""
        if not self.user_data:
            return False
            
        login_data = {
            "email": self.user_data['email'],
            "password": "TestPass123!"
        }
        
        success, response = self.run_test(
            "User Login",
            "POST",
            "auth/login",
            200,
            data=login_data
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            return True
        return False

    def test_get_current_user(self):
        """Test getting current user info"""
        success, response = self.run_test(
            "Get Current User",
            "GET",
            "auth/me",
            200
        )
        return success

    def create_test_pdf(self, content="Test PDF content"):
        """Create a temporary test PDF file"""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        # Create a minimal PDF structure
        pdf_content = f"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj

4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
({content}) Tj
ET
endstream
endobj

xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000206 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
300
%%EOF"""
        
        temp_file.write(pdf_content.encode())
        temp_file.close()
        return temp_file.name

    def test_claim_analysis(self):
        """Test claim analysis with file uploads"""
        try:
            # Create test PDF files
            policy_file = self.create_test_pdf("Insurance Policy Document - Coverage includes medical expenses up to $10,000")
            claim_file = self.create_test_pdf("Claim Form - Requesting $500 for medical treatment")
            bills_file = self.create_test_pdf("Medical Bills - Doctor visit $500")
            doctor_file = self.create_test_pdf("Doctor Notes - Patient treated for minor injury")
            
            files = {
                'policy': ('policy.pdf', open(policy_file, 'rb'), 'application/pdf'),
                'claim': ('claim.pdf', open(claim_file, 'rb'), 'application/pdf'),
                'bills': ('bills.pdf', open(bills_file, 'rb'), 'application/pdf'),
                'doctor_notes': ('doctor_notes.pdf', open(doctor_file, 'rb'), 'application/pdf')
            }
            
            success, response = self.run_test(
                "Claim Analysis",
                "POST",
                "claims/analyze",
                200,
                files=files
            )
            
            # Close and cleanup files
            for file_tuple in files.values():
                file_tuple[1].close()
            
            os.unlink(policy_file)
            os.unlink(claim_file)
            os.unlink(bills_file)
            os.unlink(doctor_file)
            
            if success:
                # Verify response structure
                required_fields = ['id', 'decision', 'reasoning', 'analyzed_at']
                missing_fields = [field for field in required_fields if field not in response]
                if missing_fields:
                    self.log_test("Claim Analysis Response Structure", False, f"Missing fields: {missing_fields}")
                    return False
                else:
                    self.log_test("Claim Analysis Response Structure", True, "All required fields present")
                    return True
            
            return success
            
        except Exception as e:
            self.log_test("Claim Analysis", False, f"Exception: {str(e)}")
            return False

    def test_claim_history(self):
        """Test getting claim history"""
        success, response = self.run_test(
            "Get Claim History",
            "GET",
            "claims/history",
            200
        )
        
        if success:
            if isinstance(response, list):
                self.log_test("Claim History Response Format", True, f"Returned {len(response)} claims")
                return True
            else:
                self.log_test("Claim History Response Format", False, "Response is not a list")
                return False
        return success

    def test_invalid_login(self):
        """Test login with invalid credentials"""
        invalid_data = {
            "email": "nonexistent@example.com",
            "password": "wrongpassword"
        }
        
        success, response = self.run_test(
            "Invalid Login",
            "POST",
            "auth/login",
            401,
            data=invalid_data
        )
        return success

    def test_unauthorized_access(self):
        """Test accessing protected endpoint without token"""
        original_token = self.token
        self.token = None
        
        success, response = self.run_test(
            "Unauthorized Access",
            "GET",
            "auth/me",
            403  # Should return 403 or 401 for unauthorized
        )
        
        # If 403 didn't work, try 401
        if not success:
            success, response = self.run_test(
                "Unauthorized Access (401)",
                "GET",
                "auth/me",
                401
            )
        
        self.token = original_token
        return success

    def run_all_tests(self):
        """Run all tests in sequence"""
        print("🚀 Starting Insurance Claim API Tests")
        print(f"📍 Base URL: {self.base_url}")
        print("=" * 60)
        
        # Test sequence
        tests = [
            ("User Registration", self.test_user_registration),
            ("User Login", self.test_user_login),
            ("Get Current User", self.test_get_current_user),
            ("Claim Analysis", self.test_claim_analysis),
            ("Claim History", self.test_claim_history),
            ("Invalid Login", self.test_invalid_login),
            ("Unauthorized Access", self.test_unauthorized_access),
        ]
        
        for test_name, test_func in tests:
            try:
                test_func()
            except Exception as e:
                self.log_test(test_name, False, f"Unexpected error: {str(e)}")
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        # Print failed tests
        failed_tests = [result for result in self.test_results if not result['success']]
        if failed_tests:
            print("\n❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"   • {test['test']}: {test['details']}")
        
        return self.tests_passed == self.tests_run

def main():
    tester = InsuranceClaimAPITester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())