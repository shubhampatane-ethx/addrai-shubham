"""
Test Script for Enhanced OSM Validator
Validates that PO Box detection and Suite cleanup work correctly
"""

# Test data from actual failed addresses
test_cases = [
    {
        'name': 'PO Box - Simple',
        'address': {
            'address1': 'PO BOX 2895',
            'city': 'Renton',
            'state': 'WA',
            'zip': '98056'
        },
        'expected_po_box': True,
        'expected_box_number': '2895'
    },
    {
        'name': 'PO Box - With Periods',
        'address': {
            'address1': 'P.O. BOX 1549',
            'city': 'Lake Grove',
            'state': 'OR',
            'zip': '97035'
        },
        'expected_po_box': True,
        'expected_box_number': '1549'
    },
    {
        'name': 'PO Box - Large Number',
        'address': {
            'address1': 'PO BOX 371956',
            'city': 'Pittsburgh',
            'state': 'PA',
            'zip': '15250-7956'
        },
        'expected_po_box': True,
        'expected_box_number': '371956'
    },
    {
        'name': 'Suite Number - Full Word',
        'address1': '8701 Elmwood Ave, Suite 400',
        'expected_cleaned': '8701 Elmwood Ave',
        'expected_suite_number': '400',
        'expected_suite_type': 'Suite'
    },
    {
        'name': 'Suite Number - Abbreviated',
        'address1': '3300 NW 32nd AVE STE A',
        'expected_cleaned': '3300 NW 32nd AVE',
        'expected_suite_number': 'A',
        'expected_suite_type': 'Ste'
    },
    {
        'name': 'Unit Number',
        'address1': '123 Main St Unit 5B',
        'expected_cleaned': '123 Main St',
        'expected_suite_number': '5B',
        'expected_suite_type': 'Unit'
    },
    {
        'name': 'Pound Sign',
        'address1': '456 Oak Ave #200',
        'expected_cleaned': '456 Oak Ave',
        'expected_suite_number': '200',
        'expected_suite_type': '#'
    },
    {
        'name': 'Regular Address - No Change',
        'address1': '449 15th Street',
        'expected_cleaned': '449 15th Street',
        'expected_suite_number': '',
        'expected_suite_type': ''
    }
]

def run_tests():
    """Run all test cases"""
    import sys
    sys.path.insert(0, '/app')
    
    from backend.app.services.osm_validator import OSMNominatimValidator
    
    validator = OSMNominatimValidator()
    
    print("=" * 70)
    print("TESTING ENHANCED OSM VALIDATOR")
    print("=" * 70)
    
    # Test PO Box Detection
    print("\n📦 TESTING PO BOX DETECTION:")
    print("-" * 70)
    
    po_box_tests = [tc for tc in test_cases if 'expected_po_box' in tc]
    passed_po_box = 0
    
    for test in po_box_tests:
        is_po_box, info = validator._detect_po_box(test['address'])
        
        # Check if PO Box detected correctly
        if is_po_box == test['expected_po_box']:
            # Check box number
            if info.get('po_box_number') == test['expected_box_number']:
                print(f"✅ {test['name']}")
                print(f"   Address: {test['address']['address1']}")
                print(f"   Detected: PO Box #{info['po_box_number']}")
                passed_po_box += 1
            else:
                print(f"❌ {test['name']} - Box number mismatch")
                print(f"   Expected: {test['expected_box_number']}")
                print(f"   Got: {info.get('po_box_number')}")
        else:
            print(f"❌ {test['name']} - Detection failed")
        print()
    
    print(f"PO Box Tests: {passed_po_box}/{len(po_box_tests)} passed")
    
    # Test Suite Cleanup
    print("\n🧹 TESTING SUITE NUMBER CLEANUP:")
    print("-" * 70)
    
    suite_tests = [tc for tc in test_cases if 'address1' in tc and 'expected_cleaned' in tc]
    passed_suite = 0
    
    for test in suite_tests:
        cleaned = validator._clean_address_for_geocoding(test['address1'])
        
        if cleaned == test['expected_cleaned']:
            print(f"✅ {test['name']}")
            print(f"   Original: {test['address1']}")
            print(f"   Cleaned:  {cleaned}")
            passed_suite += 1
        else:
            print(f"❌ {test['name']}")
            print(f"   Original:  {test['address1']}")
            print(f"   Expected:  {test['expected_cleaned']}")
            print(f"   Got:       {cleaned}")
        print()
    
    print(f"Suite Cleanup Tests: {passed_suite}/{len(suite_tests)} passed")
    
    # Test Suite Extraction
    print("\n📍 TESTING SUITE EXTRACTION (For Oracle Fields):")
    print("-" * 70)
    
    extraction_tests = suite_tests  # Same test cases
    passed_extraction = 0
    
    for test in extraction_tests:
        suite_number, suite_type = validator._extract_suite_info(test['address1'])
        
        if (suite_number == test['expected_suite_number'] and 
            suite_type == test['expected_suite_type']):
            print(f"✅ {test['name']}")
            print(f"   Address: {test['address1']}")
            if suite_number:
                print(f"   Extracted: {suite_type} {suite_number}")
            else:
                print(f"   Extracted: (no suite)")
            passed_extraction += 1
        else:
            print(f"❌ {test['name']}")
            print(f"   Address:  {test['address1']}")
            print(f"   Expected: {test['expected_suite_type']} {test['expected_suite_number']}")
            print(f"   Got:      {suite_type} {suite_number}")
        print()
    
    print(f"Suite Extraction Tests: {passed_extraction}/{len(extraction_tests)} passed")
    
    # Test Complete Flow (Extract → Clean → Restore)
    print("\n♻️  TESTING COMPLETE FLOW (Extract → Clean → Restore):")
    print("-" * 70)
    
    flow_tests = [
        {
            'address': '8701 Elmwood Ave, Suite 400',
            'expected_for_osm': '8701 Elmwood Ave',
            'expected_final': '8701 Elmwood Ave Suite 400'
        },
        {
            'address': '3300 NW 32nd AVE STE A',
            'expected_for_osm': '3300 NW 32nd AVE',
            'expected_final': '3300 NW 32nd AVE Ste A'
        },
        {
            'address': '456 Oak Ave #200',
            'expected_for_osm': '456 Oak Ave',
            'expected_final': '456 Oak Ave #200'
        }
    ]
    
    passed_flow = 0
    
    for test in flow_tests:
        # Step 1: Extract suite
        suite_number, suite_type = validator._extract_suite_info(test['address'])
        
        # Step 2: Clean for OSM
        cleaned = validator._clean_address_for_geocoding(test['address'])
        
        # Step 3: Restore (simulate what validate() does)
        if suite_number and suite_type:
            if suite_type == '#':
                final = f"{cleaned} #{suite_number}"
            else:
                final = f"{cleaned} {suite_type} {suite_number}"
        else:
            final = cleaned
        
        if cleaned == test['expected_for_osm'] and final == test['expected_final']:
            print(f"✅ Flow Test")
            print(f"   Original:      {test['address']}")
            print(f"   For OSM Query: {cleaned}")
            print(f"   Final Oracle:  {final}")
            passed_flow += 1
        else:
            print(f"❌ Flow Test Failed")
            print(f"   Original:      {test['address']}")
            print(f"   Expected OSM:  {test['expected_for_osm']}")
            print(f"   Got OSM:       {cleaned}")
            print(f"   Expected Final: {test['expected_final']}")
            print(f"   Got Final:      {final}")
        print()
    
    print(f"Complete Flow Tests: {passed_flow}/{len(flow_tests)} passed")
    
    # Final Summary
    print("\n" + "=" * 70)
    print("SUMMARY:")
    print("=" * 70)
    total_tests = len(po_box_tests) + len(suite_tests) + len(extraction_tests) + len(flow_tests)
    total_passed = passed_po_box + passed_suite + passed_extraction + passed_flow
    
    print(f"PO Box Detection:     {passed_po_box}/{len(po_box_tests)}")
    print(f"Suite Cleanup:        {passed_suite}/{len(suite_tests)}")
    print(f"Suite Extraction:     {passed_extraction}/{len(extraction_tests)}")
    print(f"Complete Flow:        {passed_flow}/{len(flow_tests)}")
    print(f"{'=' * 70}")
    print(f"Total Tests: {total_passed}/{total_tests} passed")
    
    if total_passed == total_tests:
        print("✅ ALL TESTS PASSED - Enhancements working correctly!")
        print("✅ Suite numbers are preserved in Oracle fields!")
        return 0
    else:
        print("❌ SOME TESTS FAILED - Check implementation")
        return 1

if __name__ == '__main__':
    exit_code = run_tests()
    exit(exit_code)
