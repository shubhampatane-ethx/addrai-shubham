"""
OpenStreetMap Nominatim Validator
ENHANCED VERSION with PO Box detection and Suite number cleanup
"""
import requests
import time
import re
from typing import Dict, Optional, Tuple
from fuzzywuzzy import fuzz
from backend.app.services.usps_formatter import USPSStandardsFormatter
from backend.app.core.config import settings

class OSMNominatimValidator:
    """
    OpenStreetMap Nominatim-based address validator
    FREE - No API key required
    Rate limit: 1 request per second
    
    ENHANCEMENTS:
    - PO Box detection (OSM can't geocode PO Boxes)
    - Suite/Unit number cleanup (improves geocoding success)
    - Better error handling
    """
    
    def __init__(self):
        self.base_url = "https://nominatim.openstreetmap.org/search"
        self.rate_limit_delay = 1.0 / settings.OSM_RATE_LIMIT  # seconds between requests
        self.last_request_time = 0
        self.usps_formatter = USPSStandardsFormatter()
        self.validator_name = "OSM_Nominatim"
    
    def validate(self, address_data: Dict) -> Dict:
        """
        Validate address using OSM Nominatim + USPS formatting
        
        Args:
            address_data: {
                'entity_name': str (optional),
                'address1': str,
                'address2': str (optional),
                'city': str,
                'state': str,
                'zip': str,
                'country': str
            }
        
        Returns:
            {
                'success': bool,
                'validated_address': {...},
                'confidence_score': float (0-100),
                'validation_source': str,
                'metadata': {...},
                'error': Optional[str]
            }
        """
        # Check if this is a PO Box
        is_po_box, po_box_info = self._detect_po_box(address_data)
        
        if is_po_box:
            return self._handle_po_box(address_data, po_box_info)
        
        # Extract suite info BEFORE cleaning (to preserve for Oracle fields)
        original_address1 = address_data.get('address1', '')
        suite_number, suite_type = self._extract_suite_info(original_address1)
        
        # Clean address for better geocoding (remove suite numbers)
        cleaned_address = self._clean_address_for_geocoding(original_address1)
        
        # Build search query with cleaned address
        query_data = address_data.copy()
        query_data['address1'] = cleaned_address
        query = self._build_query(query_data)
        
        # Query Nominatim
        osm_result = self._query_nominatim(query, address_data)
        
        if not osm_result['success']:
            return osm_result
        
        # Apply USPS formatting
        usps_result = self._apply_usps_formatting(osm_result)
        
        # Calculate confidence
        confidence = self._calculate_confidence(address_data, osm_result, usps_result)
        
        # Extract entity name from OSM
        entity_info = self._extract_entity_info(osm_result, address_data.get('entity_name', ''))
        
        # Build validated address from OSM components
        # Priority: USPS formatted > OSM components > display_name
        if usps_result.get('success') and usps_result.get('delivery_line_1'):
            # USPS successfully formatted the address
            validated_address1 = usps_result.get('delivery_line_1')
        else:
            # USPS failed - build from OSM components
            osm_address_parts = []
            if osm_result.get('house_number'):
                osm_address_parts.append(osm_result['house_number'])
            if osm_result.get('road'):
                osm_address_parts.append(osm_result['road'])
            
            if osm_address_parts:
                # Successfully built from components
                validated_address1 = ' '.join(osm_address_parts)
            else:
                # Last resort: use display_name (full formatted address)
                # This shouldn't normally happen if OSM geocoded successfully
                validated_address1 = osm_result.get('display_name', address_data.get('address1', ''))
        
        # RE-ADD suite information to validated address for Oracle fields
        if suite_number and suite_type:
            # Format suite info properly
            if suite_type == '#':
                validated_address1 = f"{validated_address1} #{suite_number}"
            else:
                validated_address1 = f"{validated_address1} {suite_type} {suite_number}"
        
        return {
            'success': True,
            'validated_address': {
                'address1': validated_address1,  # ← Now includes suite number!
                'address2': '',
                'city': usps_result.get('city', osm_result.get('city', '')),
                'state': usps_result.get('state', osm_result.get('state', '')),
                'zip': usps_result.get('zip', osm_result.get('postcode', '')),
                'country': 'US',
                'latitude': osm_result.get('lat'),
                'longitude': osm_result.get('lon')
            },
            'usps_formatted': {
                'delivery_line_1': usps_result.get('delivery_line_1', ''),
                'last_line': usps_result.get('last_line', ''),
                'full': usps_result.get('usps_formatted_full', '')
            },
            'confidence_score': confidence,
            'validation_source': self.validator_name,
            'entity_info': entity_info,
            'metadata': {
                'osm_place_id': osm_result.get('place_id'),
                'osm_type': osm_result.get('type'),
                'osm_class': osm_result.get('class'),
                'osm_display_name': osm_result.get('display_name'),
                'osm_house_number': osm_result.get('house_number'),  # NEW: Track components
                'osm_road': osm_result.get('road'),  # NEW: Track components
                'usps_parse_success': usps_result.get('success', False),
                'has_geocoding': bool(osm_result.get('lat') and osm_result.get('lon')),
                'is_po_box': False,
                'address_cleaned': cleaned_address != original_address1,
                'suite_preserved': bool(suite_number),  # Track if suite was preserved
                'suite_info': f"{suite_type} {suite_number}" if suite_number else None,
                'address_source': 'usps_formatted' if usps_result.get('success') else 'osm_components'  # NEW: Track source
            },
            'error': None
        }
    
    def _detect_po_box(self, address_data: Dict) -> Tuple[bool, Dict]:
        """
        Detect if address is a PO Box
        
        Returns:
            (is_po_box: bool, info: Dict)
        """
        address1 = address_data.get('address1', '').upper()
        address2 = address_data.get('address2', '').upper()
        
        # PO Box patterns
        po_box_patterns = [
            r'\bP\.?\s*O\.?\s*BOX\b',
            r'\bPOB\b',
            r'\bPOST\s+OFFICE\s+BOX\b',
            r'\bBOX\s+\d+\b',  # Just "BOX 123" 
        ]
        
        # Check address1 and address2
        for pattern in po_box_patterns:
            if re.search(pattern, address1):
                box_number = re.search(r'(?:BOX|POB)\s+(\d+)', address1)
                return True, {
                    'po_box_number': box_number.group(1) if box_number else None,
                    'full_address': address1
                }
            if re.search(pattern, address2):
                box_number = re.search(r'(?:BOX|POB)\s+(\d+)', address2)
                return True, {
                    'po_box_number': box_number.group(1) if box_number else None,
                    'full_address': address2
                }
        
        return False, {}
    
    def _handle_po_box(self, address_data: Dict, po_box_info: Dict) -> Dict:
        """
        Handle PO Box addresses (OSM can't geocode these)
        Return LOW confidence with original data
        """
        return {
            'success': False,
            'error': 'PO Box addresses cannot be geocoded',
            'validated_address': {
                'address1': address_data.get('address1', ''),
                'address2': address_data.get('address2', ''),
                'city': address_data.get('city', ''),
                'state': address_data.get('state', ''),
                'zip': address_data.get('zip', ''),
                'country': address_data.get('country', 'US'),
                'latitude': None,
                'longitude': None
            },
            'confidence_score': 0,
            'validation_source': 'ORIGINAL_DATA',
            'metadata': {
                'is_po_box': True,
                'po_box_number': po_box_info.get('po_box_number'),
                'reason': 'PO Boxes cannot be geocoded - physical address required',
                'has_geocoding': False
            }
        }
    
    def _extract_suite_info(self, address: str) -> Tuple[str, str]:
        """
        Extract suite/unit information from address
        
        Returns:
            (suite_number, suite_type) e.g., ("400", "Suite") or ("5B", "Ste")
        
        Examples:
            "123 Main St Suite 400" → ("400", "Suite")
            "456 Oak Ave Ste 5B" → ("5B", "Ste")
            "789 Elm St Unit 12" → ("12", "Unit")
            "100 Park Ave #200" → ("200", "#")
            "123 Main St" → ("", "")
        """
        if not address:
            return "", ""
        
        # Patterns to extract suite info
        patterns = [
            (r'\s+(Suite)\s+([\dA-Z-]+)', 'Suite'),
            (r'\s+(Ste\.?)\s+([\dA-Z-]+)', 'Ste'),
            (r'\s+(Unit)\s+([\dA-Z-]+)', 'Unit'),
            (r'\s+(#)\s*([\dA-Z-]+)', '#'),
            (r'\s+(Apt\.?)\s+([\dA-Z-]+)', 'Apt'),
            (r'\s+(Floor)\s+([\dA-Z-]+)', 'Floor'),
            (r',\s*(Suite)\s+([\dA-Z-]+)', 'Suite'),
            (r',\s*(Ste\.?)\s+([\dA-Z-]+)', 'Ste'),
        ]
        
        for pattern, suite_type in patterns:
            match = re.search(pattern, address, re.IGNORECASE)
            if match:
                suite_number = match.group(2)
                return suite_number, suite_type
        
        return "", ""
    
    def _clean_address_for_geocoding(self, address: str) -> str:
        """
        Clean address for better OSM geocoding
        Removes suite/unit numbers that can confuse geocoding
        
        NOTE: Suite info should be extracted BEFORE cleaning
        and re-added to final validated address for Oracle fields
        
        Examples:
            "123 Main St Suite 400" → "123 Main St"
            "456 Oak Ave Ste 5B" → "456 Oak Ave"
            "789 Elm St Unit 12" → "789 Elm St"
            "100 Park Ave #200" → "100 Park Ave"
        """
        if not address:
            return address
        
        # Patterns to remove
        patterns = [
            r'\s+Suite\s+[\dA-Z-]+',
            r'\s+Ste\.?\s+[\dA-Z-]+',
            r'\s+Unit\s+[\dA-Z-]+',
            r'\s+#\s*[\dA-Z-]+',
            r'\s+Apt\.?\s+[\dA-Z-]+',
            r'\s+Floor\s+[\dA-Z-]+',
            r',\s*Suite\s+[\dA-Z-]+',
            r',\s*Ste\.?\s+[\dA-Z-]+',
        ]
        
        cleaned = address
        for pattern in patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Clean up extra spaces and commas
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = re.sub(r',\s*,', ',', cleaned)
        cleaned = cleaned.strip().strip(',').strip()
        
        return cleaned
    
    def _build_query(self, address_data: Dict) -> str:
        """Build search query for Nominatim"""
        parts = []
        
        # NOTE: Entity name is NOT included in query as it reduces match rate
        # OSM Nominatim works better with just the physical address components
        # Entity name matching is done AFTER geocoding succeeds
        
        # Address components only
        if address_data.get('address1'):
            parts.append(address_data['address1'])
        if address_data.get('city'):
            parts.append(address_data['city'])
        if address_data.get('state'):
            parts.append(address_data['state'])
        if address_data.get('zip'):
            parts.append(address_data['zip'])
        
        return ', '.join(parts)
    
    def _query_nominatim(self, query: str, address_data: Dict) -> Dict:
        """Query OpenStreetMap Nominatim API"""
        # Rate limiting
        time_since_last = time.time() - self.last_request_time
        if time_since_last < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - time_since_last)
        
        params = {
            'q': query,
            'format': 'json',
            'addressdetails': 1,
            'limit': 1,
            'countrycodes': 'us'  # US only for now
        }
        
        try:
            response = requests.get(
                self.base_url,
                params=params,
                headers={'User-Agent': 'AddressValidationPlatform/1.0'},
                timeout=10
            )
            self.last_request_time = time.time()
            
            if response.status_code != 200:
                return {
                    'success': False,
                    'error': f'Nominatim returned status {response.status_code}'
                }
            
            results = response.json()
            
            if not results:
                return {
                    'success': False,
                    'error': 'No results found'
                }
            
            # Take first result
            result = results[0]
            address = result.get('address', {})
            
            return {
                'success': True,
                'place_id': result.get('place_id'),
                'lat': result.get('lat'),
                'lon': result.get('lon'),
                'display_name': result.get('display_name'),
                'type': result.get('type'),
                'class': result.get('class'),
                'house_number': address.get('house_number'),
                'road': address.get('road'),
                'city': address.get('city') or address.get('town') or address.get('village'),
                'state': address.get('state'),
                'postcode': address.get('postcode'),
                'country': address.get('country'),
                'raw_address': result.get('display_name'),
                'full_result': result
            }
            
        except requests.exceptions.Timeout:
            return {'success': False, 'error': 'Request timeout'}
        except requests.exceptions.RequestException as e:
            return {'success': False, 'error': f'Request error: {str(e)}'}
        except Exception as e:
            return {'success': False, 'error': f'Unexpected error: {str(e)}'}
    
    def _apply_usps_formatting(self, osm_result: Dict) -> Dict:
        """Apply USPS formatting to OSM result"""
        if not osm_result.get('success'):
            return {'success': False}
        
        # Build address string from OSM components
        address_parts = []
        if osm_result.get('house_number'):
            address_parts.append(osm_result['house_number'])
        if osm_result.get('road'):
            address_parts.append(osm_result['road'])
        
        address_string = ' '.join(address_parts)
        
        if not address_string:
            # Fallback to display name
            address_string = osm_result.get('display_name', '')
        
        # Parse and format with USPS standards
        usps_result = self.usps_formatter.format_address_from_string(address_string)
        
        # If USPS parsing failed, use OSM data directly
        if not usps_result.get('success'):
            return {
                'success': False,
                'delivery_line_1': address_string,
                'city': osm_result.get('city', ''),
                'state': osm_result.get('state', ''),
                'zip': osm_result.get('postcode', '')
            }
        
        return usps_result
    
    def _calculate_confidence(self, original: Dict, osm: Dict, usps: Dict) -> float:
        """
        Calculate confidence score (0-100) based on:
        - OSM geocoding success
        - USPS parsing success
        - Component completeness
        - Match quality
        """
        score = 0.0
        
        # Base score for successful geocoding (40 points)
        if osm.get('lat') and osm.get('lon'):
            score += 40
        
        # USPS parsing success (30 points)
        if usps.get('success'):
            score += 30
        
        # Component completeness (30 points)
        if osm.get('house_number'):
            score += 10
        if osm.get('road'):
            score += 5
        if osm.get('city'):
            score += 5
        if osm.get('state'):
            score += 5
        if osm.get('postcode'):
            score += 5
        
        # Bonus for exact ZIP match
        if original.get('zip') and osm.get('postcode'):
            if original['zip'][:5] == osm['postcode'][:5]:
                score += 10
            else:
                score -= 10  # Penalize ZIP mismatch
        
        return min(max(score, 0.0), 100.0)
    
    def _extract_entity_info(self, osm_result: Dict, original_entity_name: str) -> Dict:
        """
        Extract entity/business name from OSM and compare with original
        REFACTORED: vendor → entity_name
        """
        osm_name = osm_result.get('full_result', {}).get('name', '')
        
        if not osm_name or not original_entity_name:
            return {
                'entity_name_from_osm': osm_name,
                'entity_match_score': 0.0,
                'entity_confidence': 'NONE'
            }
        
        # Fuzzy match score
        match_score = fuzz.ratio(original_entity_name.upper(), osm_name.upper())
        
        # Determine confidence level
        if match_score >= 95:
            confidence = 'HIGH'
        elif match_score >= 80:
            confidence = 'MEDIUM'
        elif match_score >= 60:
            confidence = 'LOW'
        else:
            confidence = 'MISMATCH'
        
        return {
            'entity_name_from_osm': osm_name,
            'entity_match_score': float(match_score),
            'entity_confidence': confidence
        }
    
    def health_check(self) -> bool:
        """Test if Nominatim is accessible"""
        try:
            response = requests.get(
                f"{self.base_url}?q=test&format=json",
                timeout=5,
                headers={'User-Agent': 'AddressValidationPlatform/1.0'}
            )
            return response.status_code == 200
        except:
            return False
