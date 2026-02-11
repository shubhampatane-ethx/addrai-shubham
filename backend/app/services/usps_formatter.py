"""
USPS Address Standards Formatter
Based on USPS Publication 28 - WITHOUT using USPS API
"""
import re
import usaddress
from typing import Dict, Optional, Tuple

class USPSStandardsFormatter:
    """
    Format addresses according to USPS Publication 28 standards
    Uses open-source parsing - NO API calls required
    """
    
    # USPS Street Suffix Abbreviations (partial list - top 100)
    STREET_SUFFIXES = {
        'ALLEY': 'ALY', 'ALLEE': 'ALY', 'ALLY': 'ALY',
        'ANEX': 'ANX', 'ANNEX': 'ANX', 'ANNX': 'ANX',
        'ARCADE': 'ARC', 'AV': 'AVE', 'AVEN': 'AVE', 'AVENU': 'AVE', 'AVENUE': 'AVE', 'AVN': 'AVE', 'AVNUE': 'AVE',
        'BAYOO': 'BYU', 'BAYOU': 'BYU',
        'BEACH': 'BCH',
        'BEND': 'BND',
        'BLUF': 'BLF', 'BLUFF': 'BLF', 'BLUFFS': 'BLFS',
        'BOT': 'BTM', 'BOTTM': 'BTM', 'BOTTOM': 'BTM',
        'BOUL': 'BLVD', 'BOULEVARD': 'BLVD', 'BOULV': 'BLVD',
        'BRANCH': 'BR', 'BRNCH': 'BR',
        'BRDGE': 'BRG', 'BRIDGE': 'BRG',
        'BROOK': 'BRK', 'BROOKS': 'BRKS',
        'BURG': 'BG', 'BURGS': 'BGS',
        'BYPA': 'BYP', 'BYPAS': 'BYP', 'BYPASS': 'BYP', 'BYPS': 'BYP',
        'CAMP': 'CP', 'CMP': 'CP',
        'CANYN': 'CYN', 'CANYON': 'CYN', 'CNYN': 'CYN',
        'CAPE': 'CPE',
        'CAUSEWAY': 'CSWY', 'CAUSWAY': 'CSWY',
        'CEN': 'CTR', 'CENT': 'CTR', 'CENTER': 'CTR', 'CENTR': 'CTR', 'CENTRE': 'CTR', 'CNTER': 'CTR', 'CNTR': 'CTR', 'CTR': 'CTR', 'CENTERS': 'CTRS',
        'CIRC': 'CIR', 'CIRCL': 'CIR', 'CIRCLE': 'CIR', 'CRCL': 'CIR', 'CRCLE': 'CIR', 'CIRCLES': 'CIRS',
        'CLIFF': 'CLF', 'CLIFFS': 'CLFS',
        'CLUB': 'CLB',
        'COMMON': 'CMN', 'COMMONS': 'CMNS',
        'CORNER': 'COR', 'CORNERS': 'CORS',
        'COURSE': 'CRSE',
        'COURT': 'CT', 'CRT': 'CT', 'COURTS': 'CTS',
        'COVE': 'CV', 'COVES': 'CVS',
        'CREEK': 'CRK',
        'CRESCENT': 'CRES', 'CRSENT': 'CRES', 'CRSNT': 'CRES',
        'CREST': 'CRST',
        'CROSSING': 'XING', 'CRSSNG': 'XING',
        'CROSSROAD': 'XRD', 'CROSSROADS': 'XRDS',
        'CURVE': 'CURV',
        'DALE': 'DL',
        'DAM': 'DM',
        'DIV': 'DV', 'DIVIDE': 'DV', 'DVD': 'DV',
        'DR': 'DR', 'DRIV': 'DR', 'DRIVE': 'DR', 'DRV': 'DR', 'DRIVES': 'DRS',
        'ESTATE': 'EST', 'ESTATES': 'ESTS',
        'EXP': 'EXPY', 'EXPR': 'EXPY', 'EXPRESS': 'EXPY', 'EXPRESSWAY': 'EXPY', 'EXPW': 'EXPY',
        'EXTENSION': 'EXT', 'EXTN': 'EXT', 'EXTNSN': 'EXT', 'EXTENSIONS': 'EXTS',
        'FALL': 'FALL', 'FALLS': 'FLS',
        'FERRY': 'FRY',
        'FIELD': 'FLD', 'FIELDS': 'FLDS',
        'FLAT': 'FLT', 'FLATS': 'FLTS',
        'FORD': 'FRD', 'FORDS': 'FRDS',
        'FOREST': 'FRST', 'FORESTS': 'FRST',
        'FORG': 'FRG', 'FORGE': 'FRG', 'FORGES': 'FRGS',
        'FORK': 'FRK', 'FORKS': 'FRKS',
        'FORT': 'FT', 'FRT': 'FT',
        'FREEWAY': 'FWY', 'FREEWY': 'FWY', 'FRWAY': 'FWY', 'FRWY': 'FWY',
        'GARDEN': 'GDN', 'GARDN': 'GDN', 'GRDEN': 'GDN', 'GRDN': 'GDN', 'GARDENS': 'GDNS', 'GRDNS': 'GDNS',
        'GATEWAY': 'GTWY', 'GATEWY': 'GTWY', 'GATWAY': 'GTWY', 'GTWAY': 'GTWY',
        'GLEN': 'GLN', 'GLENS': 'GLNS',
        'GREEN': 'GRN', 'GREENS': 'GRNS',
        'GROV': 'GRV', 'GROVE': 'GRV', 'GROVES': 'GRVS',
        'HARB': 'HBR', 'HARBOR': 'HBR', 'HARBR': 'HBR', 'HRBOR': 'HBR', 'HARBORS': 'HBRS',
        'HAVEN': 'HVN',
        'HT': 'HTS', 'HEIGHT': 'HTS', 'HEIGHTS': 'HTS', 'HGTS': 'HTS', 'HT': 'HTS',
        'HIGHWAY': 'HWY', 'HIGHWY': 'HWY', 'HIWAY': 'HWY', 'HIWY': 'HWY', 'HWAY': 'HWY',
        'HILL': 'HL', 'HILLS': 'HLS',
        'HLLW': 'HOLW', 'HOLLOW': 'HOLW', 'HOLLOWS': 'HOLW', 'HOLWS': 'HOLW',
        'INLT': 'INLT', 'INLET': 'INLT',
        'IS': 'IS', 'ISLAND': 'IS', 'ISLND': 'IS', 'ISLANDS': 'ISS', 'ISLNDS': 'ISS',
        'ISLE': 'ISLE', 'ISLES': 'ISLE',
        'JCT': 'JCT', 'JCTION': 'JCT', 'JCTN': 'JCT', 'JUNCTION': 'JCT', 'JUNCTN': 'JCT', 'JUNCTON': 'JCT', 'JCTNS': 'JCTS', 'JUNCTIONS': 'JCTS',
        'KEY': 'KY', 'KEYS': 'KYS',
        'KNOL': 'KNL', 'KNOLL': 'KNL', 'KNOLLS': 'KNLS',
        'LK': 'LK', 'LAKE': 'LK', 'LAKES': 'LKS',
        'LAND': 'LAND', 'LANDING': 'LNDG', 'LNDNG': 'LNDG',
        'LANE': 'LN', 'LA': 'LN',
        'LGT': 'LGT', 'LIGHT': 'LGT', 'LIGHTS': 'LGTS',
        'LF': 'LF', 'LOAF': 'LF',
        'LCK': 'LCK', 'LOCK': 'LCK', 'LOCKS': 'LCKS',
        'LDG': 'LDG', 'LDGE': 'LDG', 'LODG': 'LDG', 'LODGE': 'LDG',
        'LOOP': 'LOOP', 'LOOPS': 'LOOP',
        'MALL': 'MALL',
        'MNR': 'MNR', 'MANOR': 'MNR', 'MANORS': 'MNRS',
        'MEADOW': 'MDW', 'MEADOWS': 'MDWS', 'MDW': 'MDW', 'MDWS': 'MDWS', 'MEDOWS': 'MDWS',
        'MEWS': 'MEWS',
        'MILL': 'ML', 'MILLS': 'MLS',
        'MISSION': 'MSN', 'MISSN': 'MSN', 'MSSN': 'MSN',
        'MOTORWAY': 'MTWY',
        'MNT': 'MT', 'MOUNT': 'MT', 'MT': 'MT', 'MOUNTAIN': 'MTN', 'MOUNTIN': 'MTN', 'MTIN': 'MTN', 'MNTN': 'MTN', 'MOUNTAINS': 'MTNS', 'MNTNS': 'MTNS',
        'NCK': 'NCK', 'NECK': 'NCK',
        'ORCH': 'ORCH', 'ORCHARD': 'ORCH', 'ORCHRD': 'ORCH',
        'OVAL': 'OVAL', 'OVL': 'OVAL',
        'OVERPASS': 'OPAS',
        'PARK': 'PARK', 'PRK': 'PARK', 'PARKS': 'PARK',
        'PARKWAY': 'PKWY', 'PARKWY': 'PKWY', 'PKWAY': 'PKWY', 'PKWY': 'PKWY', 'PKY': 'PKWY', 'PARKWAYS': 'PKWY', 'PKWYS': 'PKWY',
        'PASS': 'PASS',
        'PASSAGE': 'PSGE',
        'PATH': 'PATH', 'PATHS': 'PATH',
        'PIKE': 'PIKE', 'PIKES': 'PIKE',
        'PINE': 'PNE', 'PINES': 'PNES',
        'PL': 'PL', 'PLACE': 'PL',
        'PLAIN': 'PLN', 'PLAINS': 'PLNS',
        'PLAZA': 'PLZ', 'PLZA': 'PLZ',
        'POINT': 'PT', 'POINTS': 'PTS',
        'PORT': 'PRT', 'PORTS': 'PRTS',
        'PR': 'PR', 'PRAIRIE': 'PR', 'PRARIE': 'PR', 'PRR': 'PR',
        'RAD': 'RADL', 'RADIAL': 'RADL', 'RADIEL': 'RADL',
        'RANCH': 'RNCH', 'RANCHES': 'RNCH', 'RNCH': 'RNCH', 'RNCHS': 'RNCH',
        'RAPID': 'RPD', 'RAPIDS': 'RPDS',
        'REST': 'RST',
        'RDG': 'RDG', 'RDGE': 'RDG', 'RIDGE': 'RDG', 'RIDGES': 'RDGS',
        'RIV': 'RIV', 'RIVER': 'RIV', 'RIVR': 'RIV', 'RVR': 'RIV',
        'RD': 'RD', 'ROAD': 'RD', 'ROADS': 'RDS',
        'ROUTE': 'RTE',
        'ROW': 'ROW',
        'RUE': 'RUE',
        'RUN': 'RUN',
        'SHL': 'SHL', 'SHOAL': 'SHL', 'SHOALS': 'SHLS',
        'SHOAR': 'SHR', 'SHORE': 'SHR', 'SHOARS': 'SHRS', 'SHORES': 'SHRS',
        'SKYWAY': 'SKWY',
        'SPG': 'SPG', 'SPNG': 'SPG', 'SPRING': 'SPG', 'SPRNG': 'SPG', 'SPGS': 'SPGS', 'SPNGS': 'SPGS', 'SPRINGS': 'SPGS', 'SPRNGS': 'SPGS',
        'SPUR': 'SPUR', 'SPURS': 'SPUR',
        'SQ': 'SQ', 'SQR': 'SQ', 'SQRE': 'SQ', 'SQU': 'SQ', 'SQUARE': 'SQ', 'SQRS': 'SQS', 'SQUARES': 'SQS',
        'STA': 'STA', 'STATION': 'STA', 'STATN': 'STA', 'STN': 'STA',
        'STRA': 'STRA', 'STRAV': 'STRA', 'STRAVE': 'STRA', 'STRAVEN': 'STRA', 'STRAVENUE': 'STRA', 'STRAVN': 'STRA', 'STRVN': 'STRA', 'STRVNUE': 'STRA',
        'STREAM': 'STRM', 'STREME': 'STRM', 'STRM': 'STRM',
        'STREET': 'ST', 'STRT': 'ST', 'ST': 'ST', 'STR': 'ST', 'STREETS': 'STS',
        'SMT': 'SMT', 'SUMIT': 'SMT', 'SUMITT': 'SMT', 'SUMMIT': 'SMT',
        'TER': 'TER', 'TERR': 'TER', 'TERRACE': 'TER',
        'THROUGHWAY': 'TRWY',
        'TRACE': 'TRCE', 'TRACES': 'TRCE', 'TRCE': 'TRCE',
        'TRACK': 'TRAK', 'TRACKS': 'TRAK', 'TRAK': 'TRAK', 'TRK': 'TRAK', 'TRKS': 'TRAK',
        'TRAFFICWAY': 'TRFY',
        'TRAIL': 'TRL', 'TRAILS': 'TRL', 'TRL': 'TRL', 'TRLS': 'TRL',
        'TRAILER': 'TRLR', 'TRLR': 'TRLR', 'TRLRS': 'TRLR',
        'TUNEL': 'TUNL', 'TUNL': 'TUNL', 'TUNLS': 'TUNL', 'TUNNEL': 'TUNL', 'TUNNELS': 'TUNL', 'TUNNL': 'TUNL',
        'TPKE': 'TPKE', 'TRNPK': 'TPKE', 'TRPK': 'TPKE', 'TURNPIKE': 'TPKE', 'TURNPK': 'TPKE',
        'UNDERPASS': 'UPAS',
        'UN': 'UN', 'UNION': 'UN', 'UNIONS': 'UNS',
        'VALLEY': 'VLY', 'VALLY': 'VLY', 'VLLY': 'VLY', 'VLY': 'VLY', 'VALLEYS': 'VLYS',
        'VDCT': 'VIA', 'VIADCT': 'VIA', 'VIADUCT': 'VIA',
        'VIEW': 'VW', 'VIEWS': 'VWS',
        'VILL': 'VLG', 'VILLAG': 'VLG', 'VILLAGE': 'VLG', 'VILLG': 'VLG', 'VILLIAGE': 'VLG', 'VILLAGES': 'VLGS',
        'VILLE': 'VL', 'VL': 'VL',
        'VIST': 'VIS', 'VISTA': 'VIS', 'VST': 'VIS', 'VSTA': 'VIS',
        'WALK': 'WALK', 'WALKS': 'WALK',
        'WALL': 'WALL',
        'WY': 'WAY', 'WAY': 'WAY', 'WAYS': 'WAYS',
        'WELL': 'WL', 'WELLS': 'WLS',
    }
    
    # USPS Directional Abbreviations
    DIRECTIONALS = {
        'NORTH': 'N', 'SOUTH': 'S', 'EAST': 'E', 'WEST': 'W',
        'NORTHEAST': 'NE', 'NORTHWEST': 'NW', 'SOUTHEAST': 'SE', 'SOUTHWEST': 'SW',
        'N': 'N', 'S': 'S', 'E': 'E', 'W': 'W',
        'NE': 'NE', 'NW': 'NW', 'SE': 'SE', 'SW': 'SW'
    }
    
    # USPS Secondary Unit Designators
    SECONDARY_UNITS = {
        'APARTMENT': 'APT', 'APT': 'APT',
        'BASEMENT': 'BSMT', 'BSMT': 'BSMT',
        'BUILDING': 'BLDG', 'BLDG': 'BLDG',
        'DEPARTMENT': 'DEPT', 'DEPT': 'DEPT',
        'FLOOR': 'FL', 'FL': 'FL',
        'FRONT': 'FRNT', 'FRNT': 'FRNT',
        'HANGAR': 'HNGR', 'HNGR': 'HNGR',
        'LOBBY': 'LBBY', 'LBBY': 'LBBY',
        'LOT': 'LOT',
        'LOWER': 'LOWR', 'LOWR': 'LOWR',
        'OFFICE': 'OFC', 'OFC': 'OFC',
        'PENTHOUSE': 'PH', 'PH': 'PH',
        'PIER': 'PIER',
        'REAR': 'REAR',
        'ROOM': 'RM', 'RM': 'RM',
        'SIDE': 'SIDE',
        'SLIP': 'SLIP',
        'SPACE': 'SPC', 'SPC': 'SPC',
        'STOP': 'STOP',
        'SUITE': 'STE', 'STE': 'STE',
        'TRAILER': 'TRLR', 'TRLR': 'TRLR',
        'UNIT': 'UNIT',
        'UPPER': 'UPPR', 'UPPR': 'UPPR'
    }
    
    def parse_address(self, address_string: str) -> Tuple[Dict, bool]:
        """
        Parse address string using usaddress library
        Returns: (parsed_components, is_valid)
        """
        try:
            parsed, address_type = usaddress.tag(address_string)
            is_valid = address_type != 'Ambiguous'
            return parsed, is_valid
        except usaddress.RepeatedLabelError:
            return {}, False
    
    def standardize_address(self, address_components: Dict) -> Dict:
        """
        Apply USPS standardization to parsed address components
        Returns standardized delivery line and last line
        """
        parts = []
        
        # House number
        if 'AddressNumber' in address_components:
            parts.append(address_components['AddressNumber'])
        
        # Pre-directional
        if 'StreetNamePreDirectional' in address_components:
            parts.append(self._standardize_directional(
                address_components['StreetNamePreDirectional']
            ))
        
        # Street name
        if 'StreetName' in address_components:
            parts.append(address_components['StreetName'].upper())
        
        # Street suffix (type)
        if 'StreetNamePostType' in address_components:
            parts.append(self._standardize_suffix(
                address_components['StreetNamePostType']
            ))
        
        # Post-directional
        if 'StreetNamePostDirectional' in address_components:
            parts.append(self._standardize_directional(
                address_components['StreetNamePostDirectional']
            ))
        
        # Secondary unit
        if 'OccupancyType' in address_components:
            parts.append(self._standardize_secondary_unit(
                address_components['OccupancyType']
            ))
            if 'OccupancyIdentifier' in address_components:
                parts.append(address_components['OccupancyIdentifier'].upper())
        
        delivery_line = ' '.join(parts)
        
        # Build last line (City State ZIP)
        city = address_components.get('PlaceName', '').upper()
        state = address_components.get('StateName', '').upper()[:2]
        zip_code = address_components.get('ZipCode', '')
        
        last_line = f"{city} {state} {zip_code}".strip()
        
        return {
            'delivery_line_1': delivery_line,
            'last_line': last_line,
            'usps_formatted_full': f"{delivery_line}\n{last_line}",
            'city': city,
            'state': state,
            'zip': zip_code
        }
    
    def _standardize_suffix(self, suffix: str) -> str:
        """Standardize street suffix to USPS abbreviation"""
        suffix_upper = suffix.upper().strip()
        return self.STREET_SUFFIXES.get(suffix_upper, suffix_upper)
    
    def _standardize_directional(self, directional: str) -> str:
        """Standardize directional to USPS abbreviation"""
        dir_upper = directional.upper().strip()
        return self.DIRECTIONALS.get(dir_upper, dir_upper)
    
    def _standardize_secondary_unit(self, unit_type: str) -> str:
        """Standardize secondary unit type to USPS abbreviation"""
        unit_upper = unit_type.upper().strip()
        return self.SECONDARY_UNITS.get(unit_upper, unit_upper)
    
    def format_address_from_string(self, address_string: str) -> Dict:
        """
        One-stop method: parse and format address string
        Returns complete USPS formatted address with metadata
        """
        # Parse address
        components, is_valid = self.parse_address(address_string)
        
        if not is_valid or not components:
            return {
                'success': False,
                'error': 'Could not parse address',
                'original': address_string
            }
        
        # Apply USPS formatting
        formatted = self.standardize_address(components)
        
        return {
            'success': True,
            'delivery_line_1': formatted['delivery_line_1'],
            'delivery_line_2': '',  # Can be populated if needed
            'last_line': formatted['last_line'],
            'usps_formatted_full': formatted['usps_formatted_full'],
            'city': formatted['city'],
            'state': formatted['state'],
            'zip': formatted['zip'],
            'components': components,
            'is_valid': is_valid,
            'original': address_string
        }
