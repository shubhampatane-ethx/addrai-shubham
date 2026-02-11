"""
Oracle Transformation Service - ENHANCED VERSION
REFACTORED: Supplier → Entity
Transforms validated addresses to Oracle Fusion compatible format
with intelligent address parsing

Oracle Standards Applied:
- Entity Name: ALL CAPS
- Address Lines: ALL CAPS with smart parsing
- City: ALL CAPS
- State: 2-letter code (CA, TX, WA, etc.)
- Country: "US" for all US addresses
- ZIP: ZIP+4 format (12345-6789) if available, else 5-digit (12345)
"""
import re
from typing import Dict, Optional

# US State name to 2-letter code mapping
STATE_CODES = {
    'ALABAMA': 'AL', 'ALASKA': 'AK', 'ARIZONA': 'AZ', 'ARKANSAS': 'AR',
    'CALIFORNIA': 'CA', 'COLORADO': 'CO', 'CONNECTICUT': 'CT', 'DELAWARE': 'DE',
    'FLORIDA': 'FL', 'GEORGIA': 'GA', 'HAWAII': 'HI', 'IDAHO': 'ID',
    'ILLINOIS': 'IL', 'INDIANA': 'IN', 'IOWA': 'IA', 'KANSAS': 'KS',
    'KENTUCKY': 'KY', 'LOUISIANA': 'LA', 'MAINE': 'ME', 'MARYLAND': 'MD',
    'MASSACHUSETTS': 'MA', 'MICHIGAN': 'MI', 'MINNESOTA': 'MN', 'MISSISSIPPI': 'MS',
    'MISSOURI': 'MO', 'MONTANA': 'MT', 'NEBRASKA': 'NE', 'NEVADA': 'NV',
    'NEW HAMPSHIRE': 'NH', 'NEW JERSEY': 'NJ', 'NEW MEXICO': 'NM', 'NEW YORK': 'NY',
    'NORTH CAROLINA': 'NC', 'NORTH DAKOTA': 'ND', 'OHIO': 'OH', 'OKLAHOMA': 'OK',
    'OREGON': 'OR', 'PENNSYLVANIA': 'PA', 'RHODE ISLAND': 'RI', 'SOUTH CAROLINA': 'SC',
    'SOUTH DAKOTA': 'SD', 'TENNESSEE': 'TN', 'TEXAS': 'TX', 'UTAH': 'UT',
    'VERMONT': 'VT', 'VIRGINIA': 'VA', 'WASHINGTON': 'WA', 'WEST VIRGINIA': 'WV',
    'WISCONSIN': 'WI', 'WYOMING': 'WY', 'DISTRICT OF COLUMBIA': 'DC', 'WASHINGTON DC': 'DC'
}

class OracleAddressTransformer:
    """
    Transform validated addresses to Oracle Fusion format with intelligent parsing
    """
    
    @staticmethod
    def fix_concatenated_directionals(address: str) -> str:
        """
        Fix common concatenated directional issues
        
        Examples:
        - NSHORE → N SHORE
        - SSHORE → S SHORE  
        - ESHORE → E SHORE
        - WSHORE → W SHORE
        - NMAIN → N MAIN
        - SLAKE → S LAKE
        
        Args:
            address: Address string to fix
            
        Returns:
            Fixed address string
        """
        if not address:
            return ""
        
        # Patterns for concatenated directionals at the start of a word
        patterns = [
            # N/S/E/W + SHORE
            (r'\bNSHORE\b', 'N SHORE'),
            (r'\bSSHORE\b', 'S SHORE'),
            (r'\bESHORE\b', 'E SHORE'),
            (r'\bWSHORE\b', 'W SHORE'),
            
            # N/S/E/W + Common street names
            (r'\bNMAIN\b', 'N MAIN'),
            (r'\bSMAIN\b', 'S MAIN'),
            (r'\bEMAIN\b', 'E MAIN'),
            (r'\bWMAIN\b', 'W MAIN'),
            
            (r'\bNLAKE\b', 'N LAKE'),
            (r'\bSLAKE\b', 'S LAKE'),
            (r'\bELAKE\b', 'E LAKE'),
            (r'\bWLAKE\b', 'W LAKE'),
            
            (r'\bNOAK\b', 'N OAK'),
            (r'\bSOAK\b', 'S OAK'),
            (r'\bEOAK\b', 'E OAK'),
            (r'\bWOAK\b', 'W OAK'),
            
            (r'\bNPARK\b', 'N PARK'),
            (r'\bSPARK\b', 'S PARK'),
            (r'\bEPARK\b', 'E PARK'),
            (r'\bWPARK\b', 'W PARK'),
            
            (r'\bNHILL\b', 'N HILL'),
            (r'\bSHILL\b', 'S HILL'),
            (r'\bEHILL\b', 'E HILL'),
            (r'\bWHILL\b', 'W HILL'),
            
            (r'\bNRIVER\b', 'N RIVER'),
            (r'\bSRIVER\b', 'S RIVER'),
            (r'\bERIVER\b', 'E RIVER'),
            (r'\bWRIVER\b', 'W RIVER'),
            
            # NE/NW/SE/SW combinations
            (r'\bNESHORE\b', 'NE SHORE'),
            (r'\bNWSHORE\b', 'NW SHORE'),
            (r'\bSESHORE\b', 'SE SHORE'),
            (r'\bSWSHORE\b', 'SW SHORE'),
            
            (r'\bNEMAIN\b', 'NE MAIN'),
            (r'\bNWMAIN\b', 'NW MAIN'),
            (r'\bSEMAIN\b', 'SE MAIN'),
            (r'\bSWMAIN\b', 'SW MAIN'),
        ]
        
        result = address.upper()
        for pattern, replacement in patterns:
            result = re.sub(pattern, replacement, result)
        
        return result
    
    @staticmethod
    def transform_entity_name(entity_name: Optional[str]) -> str:
        """
        Transform entity name to Oracle format
        
        Rules:
        - Convert to ALL CAPS
        - Remove extra whitespace
        - Limit to 240 characters (Oracle entity name limit)
        
        Args:
            entity_name: Entity name (Supplier, Customer, Employee, etc.)
            
        Returns:
            Oracle-formatted entity name
        """
        if not entity_name:
            return ""
        
        # Convert to uppercase
        oracle_name = entity_name.strip().upper()
        
        # Remove extra whitespace
        oracle_name = re.sub(r'\s+', ' ', oracle_name)
        
        # Limit length
        if len(oracle_name) > 240:
            oracle_name = oracle_name[:240]
        
        return oracle_name
    
    @staticmethod
    def transform_address_line(address: Optional[str]) -> str:
        """
        Transform address line to Oracle format with intelligent parsing
        
        Rules:
        - Fix concatenated directionals (NSHORE → N SHORE)
        - Convert to ALL CAPS
        - Remove extra whitespace
        - Standardize common abbreviations
        
        Args:
            address: Address line
            
        Returns:
            Oracle-formatted address
        """
        if not address:
            return ""
        
        # Convert to uppercase first
        oracle_address = address.strip().upper()
        
        # Fix concatenated directionals BEFORE other transformations
        oracle_address = OracleAddressTransformer.fix_concatenated_directionals(oracle_address)
        
        # Remove extra whitespace
        oracle_address = re.sub(r'\s+', ' ', oracle_address)
        
        # Standardize common street abbreviations (already uppercase)
        abbreviations = {
            ' STREET': ' ST',
            ' AVENUE': ' AVE',
            ' BOULEVARD': ' BLVD',
            ' DRIVE': ' DR',
            ' ROAD': ' RD',
            ' LANE': ' LN',
            ' COURT': ' CT',
            ' PLACE': ' PL',
            ' CIRCLE': ' CIR',
            ' PARKWAY': ' PKWY',
            ' HIGHWAY': ' HWY',
            ' SUITE': ' STE',
            ' BUILDING': ' BLDG',
            ' FLOOR': ' FL',
            ' APARTMENT': ' APT',
            ' NORTH': ' N',
            ' SOUTH': ' S',
            ' EAST': ' E',
            ' WEST': ' W',
            ' NORTHEAST': ' NE',
            ' NORTHWEST': ' NW',
            ' SOUTHEAST': ' SE',
            ' SOUTHWEST': ' SW'
        }
        
        for full, abbr in abbreviations.items():
            oracle_address = oracle_address.replace(full, abbr)
        
        return oracle_address
    
    @staticmethod
    def transform_city(city: Optional[str]) -> str:
        """
        Transform city to Oracle format
        
        Rules:
        - Convert to ALL CAPS
        - Remove extra whitespace
        
        Args:
            city: City name
            
        Returns:
            Oracle-formatted city
        """
        if not city:
            return ""
        
        oracle_city = city.strip().upper()
        oracle_city = re.sub(r'\s+', ' ', oracle_city)
        
        return oracle_city
    
    @staticmethod
    def transform_state(state: Optional[str]) -> str:
        """
        Transform state to Oracle format (2-letter code)
        
        Rules:
        - Convert full state names to 2-letter codes
        - If already 2-letter code, validate and uppercase
        
        Args:
            state: State name or code
            
        Returns:
            2-letter state code (uppercase)
        """
        if not state:
            return ""
        
        state_clean = state.strip().upper()
        
        # If already 2-letter code, validate it
        if len(state_clean) == 2:
            # Check if it's a valid state code
            if state_clean in STATE_CODES.values():
                return state_clean
        
        # Try to match full state name
        if state_clean in STATE_CODES:
            return STATE_CODES[state_clean]
        
        # Return as-is if can't convert (might be territory or foreign state)
        return state_clean[:2] if len(state_clean) >= 2 else state_clean
    
    @staticmethod
    def transform_zip(zip_code: Optional[str], zip_plus4: Optional[str] = None) -> str:
        """
        Transform ZIP code to Oracle format
        
        Rules:
        - Use ZIP+4 format (12345-6789) if available
        - Otherwise use 5-digit format (12345)
        - Never fabricate ZIP+4
        
        Args:
            zip_code: Base ZIP code (5 digits)
            zip_plus4: Optional ZIP+4 extension (4 digits)
            
        Returns:
            Oracle-formatted ZIP code
        """
        if not zip_code:
            return ""
        
        # Clean the ZIP code
        zip_clean = re.sub(r'[^\d-]', '', str(zip_code))
        
        # If already has ZIP+4 format
        if '-' in zip_clean:
            parts = zip_clean.split('-')
            if len(parts) == 2 and len(parts[0]) == 5 and len(parts[1]) == 4:
                return zip_clean
            # Otherwise use just the first part
            zip_clean = parts[0]
        
        # Ensure 5-digit base
        if len(zip_clean) >= 5:
            base_zip = zip_clean[:5]
        else:
            # Pad with zeros if less than 5 digits
            base_zip = zip_clean.zfill(5)
        
        # Add ZIP+4 if available
        if zip_plus4:
            plus4_clean = re.sub(r'[^\d]', '', str(zip_plus4))
            if len(plus4_clean) == 4:
                return f"{base_zip}-{plus4_clean}"
        
        # Check if original had more than 5 digits (might be ZIP+4 without hyphen)
        if len(zip_clean) == 9:
            return f"{zip_clean[:5]}-{zip_clean[5:9]}"
        
        return base_zip
    
    @staticmethod
    def transform_country(country: Optional[str], is_us_address: bool = True) -> str:
        """
        Transform country to Oracle format
        
        Rules:
        - Use "US" for all US addresses
        - Use ISO 2-letter country codes for others
        
        Args:
            country: Country name or code
            is_us_address: Whether this is a US address
            
        Returns:
            Oracle-formatted country code
        """
        if is_us_address:
            return "US"
        
        if not country:
            return "US"  # Default to US
        
        country_upper = country.strip().upper()
        
        # Common country mappings
        country_codes = {
            'UNITED STATES': 'US',
            'USA': 'US',
            'UNITED STATES OF AMERICA': 'US',
            'CANADA': 'CA',
            'MEXICO': 'MX',
            'UNITED KINGDOM': 'GB',
            'UK': 'GB'
        }
        
        if country_upper in country_codes:
            return country_codes[country_upper]
        
        # If already looks like 2-letter code
        if len(country_upper) == 2:
            return country_upper
        
        return country_upper[:2]
    
    @classmethod
    def transform_entity_address(cls, entity_data: Dict) -> Dict:
        """
        Transform complete entity address to Oracle format
        REFACTORED: vendor → entity_name
        
        Args:
            entity_data: Dictionary with address fields
            
        Returns:
            Dictionary with Oracle-formatted address fields
        """
        # Determine if US address
        is_us = True
        if entity_data.get('country_validated'):
            country_check = entity_data['country_validated'].upper()
            is_us = country_check in ['US', 'USA', 'UNITED STATES']
        
        transformed = {
            # Entity Name - ALL CAPS (Supplier, Customer, Employee, etc.)
            'oracle_entity_name': cls.transform_entity_name(
                entity_data.get('entity_name_validated') or entity_data.get('entity_name_original')
            ),
            
            # Address Line 1 - ALL CAPS with smart parsing
            'oracle_address1': cls.transform_address_line(
                entity_data.get('address1_validated') or entity_data.get('address1_original')
            ),
            
            # Address Line 2 - ALL CAPS with smart parsing
            'oracle_address2': cls.transform_address_line(
                entity_data.get('address2_validated') or entity_data.get('address2_original', '')
            ),
            
            # Address Line 3 - ALL CAPS with smart parsing
            'oracle_address3': cls.transform_address_line(
                entity_data.get('address3_original', '')
            ),
            
            # City - ALL CAPS
            'oracle_city': cls.transform_city(
                entity_data.get('city_validated') or entity_data.get('city_original')
            ),
            
            # State - 2-letter code
            'oracle_state': cls.transform_state(
                entity_data.get('state_validated') or entity_data.get('state_original')
            ),
            
            # ZIP - ZIP+4 if available, else 5-digit
            'oracle_zip': cls.transform_zip(
                entity_data.get('zip_validated') or entity_data.get('zip_original')
            ),
            
            # Country - "US" for US addresses
            'oracle_country': cls.transform_country(
                entity_data.get('country_validated') or entity_data.get('country_original'),
                is_us
            )
        }
        
        return transformed
    
    @classmethod
    def format_oracle_full_address(cls, oracle_data: Dict) -> str:
        """
        Format complete Oracle address as single string
        
        Args:
            oracle_data: Oracle-formatted address fields
            
        Returns:
            Formatted address string
        """
        lines = []
        
        if oracle_data.get('oracle_entity_name'):
            lines.append(oracle_data['oracle_entity_name'])
        
        if oracle_data.get('oracle_address1'):
            lines.append(oracle_data['oracle_address1'])
        
        if oracle_data.get('oracle_address2'):
            lines.append(oracle_data['oracle_address2'])
        
        # City, State ZIP
        city_state_zip = []
        if oracle_data.get('oracle_city'):
            city_state_zip.append(oracle_data['oracle_city'])
        
        state_zip = []
        if oracle_data.get('oracle_state'):
            state_zip.append(oracle_data['oracle_state'])
        if oracle_data.get('oracle_zip'):
            state_zip.append(oracle_data['oracle_zip'])
        
        if state_zip:
            city_state_zip.append(' '.join(state_zip))
        
        if city_state_zip:
            lines.append(', '.join(city_state_zip))
        
        if oracle_data.get('oracle_country'):
            lines.append(oracle_data['oracle_country'])
        
        return '\n'.join(lines)
