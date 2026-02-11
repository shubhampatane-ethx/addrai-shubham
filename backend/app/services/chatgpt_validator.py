"""
ChatGPT/OpenAI Address Validator
REFACTORED: Supplier → Entity
Uses GPT-4 to enhance low-confidence addresses and standardize to USPS format
"""
import openai
import json
from typing import Dict, Optional
from backend.app.core.config import settings

class ChatGPTAddressValidator:
    """
    ChatGPT-powered address validator for:
    1. Fixing incomplete/messy addresses
    2. Enriching data with missing components
    3. USPS standardization
    4. Confidence boost for low-quality records
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        if self.api_key:
            openai.api_key = self.api_key
        self.model = "gpt-4"  # Use GPT-4 for best accuracy
        self.validator_name = "ChatGPT_GPT4"
        self.enabled = bool(self.api_key)
    
    def validate(self, address_data: Dict, context: Optional[Dict] = None) -> Dict:
        """
        Validate and enhance address using ChatGPT
        
        Args:
            address_data: {
                'entity_name': str,
                'address1': str,
                'address2': str,
                'city': str,
                'state': str,
                'zip': str,
                'country': str
            }
            context: Optional context from previous validators (OSM result)
        
        Returns:
            {
                'success': bool,
                'validated_address': {...},
                'confidence_score': float (0-100),
                'validation_source': str,
                'metadata': {...}
            }
        """
        if not self.enabled:
            return {
                'success': False,
                'error': 'ChatGPT validator is not enabled (missing API key)'
            }
        
        # Build prompt for GPT-4
        prompt = self._build_enhancement_prompt(address_data, context)
        
        try:
            # Call OpenAI API
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,  # Low temperature for consistency
                max_tokens=500,
                response_format={"type": "json_object"}  # Force JSON response
            )
            
            # Parse response
            result_text = response.choices[0].message.content
            result = json.loads(result_text)
            
            # Calculate confidence based on completeness
            confidence = self._calculate_confidence(result, address_data)
            
            return {
                'success': True,
                'validated_address': {
                    'address1': result.get('address1', ''),
                    'address2': result.get('address2', ''),
                    'city': result.get('city', ''),
                    'state': result.get('state', ''),
                    'zip': result.get('zip', ''),
                    'country': result.get('country', 'US'),
                    'latitude': None,  # ChatGPT doesn't provide coordinates
                    'longitude': None
                },
                'usps_formatted': {
                    'delivery_line_1': result.get('usps_delivery_line_1', ''),
                    'delivery_line_2': result.get('usps_delivery_line_2', ''),
                    'last_line': result.get('usps_last_line', ''),
                    'full': f"{result.get('usps_delivery_line_1', '')}\n{result.get('usps_last_line', '')}"
                },
                'confidence_score': confidence,
                'validation_source': self.validator_name,
                'metadata': {
                    'model': self.model,
                    'tokens_used': response.usage.total_tokens,
                    'issues_found': result.get('issues', []),
                    'corrections_made': result.get('corrections', []),
                    'enhancement_applied': True,
                    'original_incomplete': result.get('original_incomplete', False)
                },
                'entity_info': {
                    'entity_name_from_gpt': result.get('entity_name', ''),
                    'entity_name_standardized': result.get('entity_name_standardized', ''),
                    'entity_match_score': 0.0  # GPT doesn't do fuzzy matching
                },
                'error': None
            }
            
        except openai.error.AuthenticationError:
            return {
                'success': False,
                'error': 'Invalid OpenAI API key'
            }
        except openai.error.RateLimitError:
            return {
                'success': False,
                'error': 'OpenAI rate limit exceeded'
            }
        except openai.error.APIError as e:
            return {
                'success': False,
                'error': f'OpenAI API error: {str(e)}'
            }
        except json.JSONDecodeError:
            return {
                'success': False,
                'error': 'Failed to parse ChatGPT response as JSON'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}'
            }
    
    def _get_system_prompt(self) -> str:
        """System prompt for ChatGPT - defines its role and output format"""
        return """You are an expert address standardization system specializing in US addresses.

Your task:
1. Clean and standardize addresses to USPS Publication 28 format
2. Fill in missing components when obvious from context
3. Correct common errors (typos, abbreviations, formatting)
4. Apply proper USPS abbreviations (ST, AVE, BLVD, APT, etc.)
5. Standardize directionals (N, S, E, W, NE, NW, SE, SW)
6. Standardize secondary units (APT, STE, FL, RM, etc.)
7. Ensure proper capitalization (ALL CAPS for USPS format)
8. Validate and format ZIP codes (5-digit or ZIP+4)
9. Standardize state to 2-letter code

CRITICAL RULES:
- NEVER invent information that isn't clearly implied
- If data is missing and cannot be inferred, leave it blank
- Mark 'original_incomplete' as true if critical data is missing
- Apply ALL CAPS for final USPS format
- Use standard USPS abbreviations ONLY
- List all corrections made in 'corrections' array
- List all issues found in 'issues' array

Output MUST be valid JSON with this EXACT structure:
{
  "address1": "STREET ADDRESS WITH USPS ABBREVIATIONS",
  "address2": "SECONDARY UNIT (APT, STE, etc.) OR EMPTY",
  "city": "CITY NAME IN CAPS",
  "state": "2-LETTER STATE CODE",
  "zip": "5-DIGIT ZIP OR ZIP+4",
  "country": "US",
  "usps_delivery_line_1": "FULL ADDRESS LINE 1 IN USPS FORMAT",
  "usps_delivery_line_2": "FULL ADDRESS LINE 2 OR EMPTY",
  "usps_last_line": "CITY STATE ZIP",
  "entity_name": "CLEANED ENTITY NAME",
  "entity_name_standardized": "ENTITY NAME WITH PROPER CAPITALIZATION",
  "issues": ["List of issues found in original data"],
  "corrections": ["List of corrections applied"],
  "original_incomplete": false
}"""
    
    def _build_enhancement_prompt(self, address_data: Dict, context: Optional[Dict]) -> str:
        """Build user prompt with address data and context"""
        prompt_parts = [
            "Please validate, clean, and standardize this US address to USPS format:\n"
        ]
        
        # Original address data
        prompt_parts.append("ORIGINAL ADDRESS:")
        if address_data.get('entity_name'):
            prompt_parts.append(f"Entity Name: {address_data['entity_name']}")
        if address_data.get('address1'):
            prompt_parts.append(f"Address Line 1: {address_data['address1']}")
        if address_data.get('address2'):
            prompt_parts.append(f"Address Line 2: {address_data['address2']}")
        if address_data.get('city'):
            prompt_parts.append(f"City: {address_data['city']}")
        if address_data.get('state'):
            prompt_parts.append(f"State: {address_data['state']}")
        if address_data.get('zip'):
            prompt_parts.append(f"ZIP: {address_data['zip']}")
        
        # Add context from OSM if available
        if context and context.get('osm_result'):
            osm = context['osm_result']
            prompt_parts.append("\nADDITIONAL CONTEXT FROM GEOCODING:")
            if osm.get('display_name'):
                prompt_parts.append(f"Geocoded Address: {osm['display_name']}")
            if osm.get('house_number'):
                prompt_parts.append(f"House Number: {osm['house_number']}")
            if osm.get('road'):
                prompt_parts.append(f"Street: {osm['road']}")
        
        prompt_parts.append("\nPlease return the cleaned, standardized address in the required JSON format.")
        
        return "\n".join(prompt_parts)
    
    def _calculate_confidence(self, result: Dict, original: Dict) -> float:
        """
        Calculate confidence score based on:
        1. Completeness of output
        2. Number of corrections made
        3. Issues found
        4. Data enrichment
        """
        score = 0.0
        
        # Completeness (50 points)
        if result.get('address1'):
            score += 15
        if result.get('city'):
            score += 10
        if result.get('state'):
            score += 10
        if result.get('zip'):
            score += 15
        
        # USPS formatting quality (30 points)
        if result.get('usps_delivery_line_1'):
            score += 15
        if result.get('usps_last_line'):
            score += 15
        
        # Data quality (20 points)
        issues_count = len(result.get('issues', []))
        if issues_count == 0:
            score += 20
        elif issues_count == 1:
            score += 15
        elif issues_count == 2:
            score += 10
        else:
            score += 5
        
        # Bonus for enrichment
        corrections_made = len(result.get('corrections', []))
        if corrections_made > 0:
            score += min(corrections_made * 2, 10)  # Up to 10 bonus points
        
        # Penalty for incomplete original data
        if result.get('original_incomplete'):
            score -= 15
        
        return min(max(score, 0.0), 100.0)
    
    def enhance_low_confidence_batch(
        self, 
        entities: list, 
        threshold: float = 90.0
    ) -> Dict:
        """
        Enhance all low-confidence records in a batch
        
        Args:
            entities: List of Entity objects
            threshold: Confidence threshold below which to enhance
        
        Returns:
            {
                'total_processed': int,
                'enhanced': int,
                'failed': int,
                'avg_confidence_before': float,
                'avg_confidence_after': float
            }
        """
        stats = {
            'total_processed': 0,
            'enhanced': 0,
            'failed': 0,
            'total_confidence_before': 0.0,
            'total_confidence_after': 0.0
        }
        
        for entity in entities:
            # Only process low-confidence records
            if entity.overall_confidence_score >= threshold:
                continue
            
            stats['total_processed'] += 1
            stats['total_confidence_before'] += float(entity.overall_confidence_score or 0)
            
            # Build address data
            address_data = {
                'entity_name': entity.entity_name_original or '',
                'address1': entity.address1_original or '',
                'address2': entity.address2_original or '',
                'city': entity.city_original or '',
                'state': entity.state_original or '',
                'zip': entity.zip_original or '',
                'country': entity.country_original or 'US'
            }
            
            # Build context from existing validation
            context = {
                'osm_result': json.loads(entity.validation_metadata or '{}')
            } if entity.validation_metadata else None
            
            # Validate with ChatGPT
            result = self.validate(address_data, context)
            
            if result['success']:
                stats['enhanced'] += 1
                stats['total_confidence_after'] += result['confidence_score']
                
                # Update entity record would happen here
                # (This is just a stats method, actual update happens in service layer)
            else:
                stats['failed'] += 1
                stats['total_confidence_after'] += float(entity.overall_confidence_score or 0)
        
        # Calculate averages
        if stats['total_processed'] > 0:
            stats['avg_confidence_before'] = stats['total_confidence_before'] / stats['total_processed']
            stats['avg_confidence_after'] = stats['total_confidence_after'] / stats['total_processed']
        
        return stats
    
    def health_check(self) -> bool:
        """Test if ChatGPT API is accessible with valid key"""
        if not self.enabled:
            return False
        
        try:
            # Simple test call
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",  # Cheaper model for health check
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            return True
        except:
            return False
    
    def estimate_cost(self, num_addresses: int) -> Dict:
        """
        Estimate cost for validating N addresses with GPT-4
        
        Current GPT-4 pricing (as of Dec 2024):
        - Input: $0.03 per 1K tokens
        - Output: $0.06 per 1K tokens
        - Average: ~400 tokens per address validation
        """
        avg_tokens_per_address = 400
        total_tokens = num_addresses * avg_tokens_per_address
        
        # Assuming 60% input, 40% output
        input_tokens = total_tokens * 0.6
        output_tokens = total_tokens * 0.4
        
        input_cost = (input_tokens / 1000) * 0.03
        output_cost = (output_tokens / 1000) * 0.06
        total_cost = input_cost + output_cost
        
        return {
            'num_addresses': num_addresses,
            'estimated_tokens': total_tokens,
            'estimated_cost_usd': round(total_cost, 2),
            'cost_per_address': round(total_cost / num_addresses, 4) if num_addresses > 0 else 0,
            'model': self.model,
            'note': 'Estimate only - actual cost may vary based on address complexity'
        }
