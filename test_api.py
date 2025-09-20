#!/usr/bin/env python3
"""
Simple test script for Service Connect API
"""
import requests
import json
import sys

BASE_URL = "http://localhost:5000"

def test_api_docs():
    """Test if API documentation is accessible"""
    try:
        response = requests.get(f"{BASE_URL}/docs/")
        print(f"✓ API Docs accessible: {response.status_code}")
        return True
    except requests.exceptions.ConnectionError:
        print("✗ API server not running")
        return False

def test_user_register():
    """Test user registration endpoint"""
    data = {
        "full_name": "Test User",
        "email": "test@example.com",
        "address": "123 Test Street",
        "password": "password123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/auth/user/register", json=data)
        print(f"User Register: {response.status_code} - {response.json()}")
        return response.status_code == 201
    except Exception as e:
        print(f"User Register Error: {e}")
        return False

def test_user_login():
    """Test user login endpoint"""
    data = {
        "email": "test@example.com",
        "password": "password123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/auth/user/login", json=data)
        print(f"User Login: {response.status_code} - {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"User Login Error: {e}")
        return False

def test_provider_register():
    """Test provider registration endpoint"""
    data = {
        "business_name": "Test Business",
        "full_name": "Test Provider",
        "email": "provider@example.com",
        "address": "456 Business Ave",
        "password": "password123",
        "about": "Test provider description"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/auth/provider/register", json=data)
        print(f"Provider Register: {response.status_code} - {response.json()}")
        return response.status_code == 201
    except Exception as e:
        print(f"Provider Register Error: {e}")
        return False

def test_booking_calendar():
    """Test booking calendar endpoint"""
    try:
        # Test without parameters
        response = requests.get(f"{BASE_URL}/api/users/booking-calendar")
        print(f"Booking Calendar (no params): {response.status_code}")
        
        # Test with date range
        params = {
            'start_date': '2024-01-01',
            'end_date': '2024-12-31'
        }
        response = requests.get(f"{BASE_URL}/api/users/booking-calendar", params=params)
        print(f"Booking Calendar (with dates): {response.status_code}")
        
        # Test with user filter
        params = {'user_id': 1}
        response = requests.get(f"{BASE_URL}/api/users/booking-calendar", params=params)
        print(f"Booking Calendar (with user_id): {response.status_code}")
        
        return response.status_code in [200, 503]  # 503 if DB not available
    except Exception as e:
        print(f"Booking Calendar Error: {e}")
        return False

def test_booking_schedule_check():
    """Test booking schedule checker endpoint"""
    try:
        # Test with required fields only
        data = {
            "provider_service_id": 1,
            "booking_day": "Monday"
        }
        response = requests.post(f"{BASE_URL}/api/users/booking-schedule-check", json=data)
        print(f"Booking Schedule Check (basic): {response.status_code}")
        
        # Test with specific date
        data = {
            "provider_service_id": 1,
            "booking_day": "Monday",
            "date": "2024-01-15"
        }
        response = requests.post(f"{BASE_URL}/api/users/booking-schedule-check", json=data)
        print(f"Booking Schedule Check (with date): {response.status_code}")
        
        # Test with invalid day
        data = {
            "provider_service_id": 1,
            "booking_day": "InvalidDay"
        }
        response = requests.post(f"{BASE_URL}/api/users/booking-schedule-check", json=data)
        print(f"Booking Schedule Check (invalid day): {response.status_code}")
        
        return True
    except Exception as e:
        print(f"Booking Schedule Check Error: {e}")
        return False

def test_service_booking_create():
    """Test service booking creation endpoint with booking_date"""
    try:
        # Test with all required fields including booking_date
        data = {
            "user_id": 1,
            "provider_service_id": 1,
            "booking_date": "2024-01-15",
            "booking_day": "Monday",
            "booking_time": "10:30"
        }
        response = requests.post(f"{BASE_URL}/api/users/service-booking", json=data)
        print(f"Service Booking Create (with booking_date): {response.status_code}")
        
        # Test with missing booking_date
        data_missing = {
            "user_id": 1,
            "provider_service_id": 1,
            "booking_day": "Monday",
            "booking_time": "10:30"
        }
        response = requests.post(f"{BASE_URL}/api/users/service-booking", json=data_missing)
        print(f"Service Booking Create (missing booking_date): {response.status_code}")
        
        return True
    except Exception as e:
        print(f"Service Booking Create Error: {e}")
        return False

if __name__ == "__main__":
    print("Testing Service Connect API...\n")
    
    # Test if server is running
    if not test_api_docs():
        print("\nPlease start the API server first: python3 app.py")
        sys.exit(1)
    
    print("\nTesting endpoints:")
    test_user_register()
    test_user_login()
    test_provider_register()
    test_booking_calendar()
    test_booking_schedule_check()
    test_service_booking_create()
    
    print(f"\nAPI Documentation: {BASE_URL}/docs/")
    print("Test completed!")