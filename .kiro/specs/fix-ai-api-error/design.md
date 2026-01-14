# Design Document - Fix AI API Error

## Overview

This design addresses the 400 Bad Request error occurring in the ContentAgent when calling the JD Cloud AI API. The root cause is a mismatch between the API request format being used (OpenAI chat completions format) and what the JD Cloud AI service expects (Gemini-specific format with contents/parts structure).

The solution involves creating an intelligent API client that can automatically detect the appropriate request format based on the model being used and format requests accordingly.

## Architecture

The fix will implement a smart API adapter pattern that:

1. **Model Detection**: Automatically detects whether the target model requires Gemini format or OpenAI format
2. **Request Transformation**: Converts between different API request formats transparently
3. **Response Parsing**: Handles multiple response formats uniformly
4. **Error Handling**: Provides better error messages and retry logic

```
ContentAgent
    ↓
SmartAIClient (New)
    ↓
[Format Detection] → [Request Transformation] → [HTTP Client] → [Response Parsing]
    ↓
JD Cloud AI API
```

## Components and Interfaces

### 1. SmartAIClient Class

A new intelligent AI client that wraps the existing HTTP client functionality:

```python
class SmartAIClient:
    def __init__(self, api_url: str, api_key: str, default_model: str)
    def chat_completion(self, messages: List[Dict], model: str = None) -> str
    def _detect_model_format(self, model: str) -> str
    def _format_openai_request(self, messages: List[Dict], model: str) -> Dict
    def _format_gemini_request(self, messages: List[Dict], model: str) -> Dict
    def _parse_response(self, response_data: Dict, format_type: str) -> str
```

### 2. Enhanced ContentAgent

Update the ContentAgent to use the new SmartAIClient:

```python
class ContentAgent:
    def __init__(self):
        self.ai_client = SmartAIClient(api_url, api_key, model)
    
    def _analyze_content_combined(self, content: str) -> Dict[str, str]:
        # Use smart client instead of direct HTTP calls
        result = self.ai_client.chat_completion(messages, self.analysis_model)
```

### 3. Model Format Detection

Logic to determine the correct API format based on model name:

- **Gemini Format**: Models containing "Gemini", "gemini", or specific JD Cloud model names
- **OpenAI Format**: Models like "gpt-", "claude-", or other standard chat models

## Data Models

### Request Format Structures

**OpenAI Format (Current)**:
```json
{
    "model": "Gemini-2.5-pro",
    "messages": [
        {"role": "system", "content": "..."},
        {"role": "user", "content": "..."}
    ],
    "stream": false
}
```

**Gemini Format (Required)**:
```json
{
    "model": "Gemini-2.5-pro", 
    "contents": [
        {
            "role": "user",
            "parts": [{"text": "System: ...\n\nUser: ..."}]
        }
    ],
    "stream": false
}
```

### Response Format Handling

The client will handle multiple response formats:
- OpenAI: `choices[0].message.content`
- Gemini: `candidates[0].content.parts[0].text`
- Direct: `output_text` or `content`

## Correctness Properties

<function_calls>
<invoke name="prework">
<parameter name="featureName">fix-ai-api-error

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

Property 1: Correct API endpoint selection
*For any* model name, when making an API request, the system should select the appropriate endpoint URL based on the model type (Gemini vs OpenAI compatible)
**Validates: Requirements 2.1**

Property 2: Gemini request format compliance
*For any* Gemini-based model and message input, the generated request payload should use the contents/parts structure instead of the messages structure
**Validates: Requirements 1.2, 2.2**

Property 3: OpenAI request format compliance  
*For any* OpenAI-compatible model and message input, the generated request payload should use the messages structure
**Validates: Requirements 2.3**

Property 4: Successful API communication
*For any* valid content analysis request, the system should receive a successful HTTP response (200) instead of client errors (400)
**Validates: Requirements 1.3**

Property 5: Response parsing consistency
*For any* valid API response in either Gemini or OpenAI format, the parser should extract the same semantic content regardless of the response structure
**Validates: Requirements 1.4, 2.4**

Property 6: Analysis result completeness
*For any* successful content analysis, the returned result should contain all six required dimensions (表情, 动作, 上装, 下装, 头戴, 手持)
**Validates: Requirements 3.2**

Property 7: Format adaptation consistency
*For any* model configuration change, the system should automatically switch to the appropriate request format without manual intervention
**Validates: Requirements 2.5**

Property 8: Retry behavior correctness
*For any* failed API request, the system should implement exponential backoff retry logic with increasing delays between attempts
**Validates: Requirements 3.3**

Property 9: Cache consistency
*For any* content input, cached analysis results should be identical to fresh API analysis results for the same input
**Validates: Requirements 3.5**

## Error Handling

### Error Detection and Recovery

1. **400 Bad Request Errors**: Detect format mismatches and automatically retry with correct format
2. **429 Rate Limiting**: Implement exponential backoff with respect for Retry-After headers
3. **Network Timeouts**: Retry with increasing timeouts up to maximum attempts
4. **Invalid Responses**: Graceful degradation with fallback parsing strategies

### Error Reporting

- Clear error messages indicating the specific issue (format mismatch, network error, etc.)
- Include debugging information like model name, endpoint used, and request format
- Log detailed error context for troubleshooting

## Testing Strategy

### Unit Testing

Unit tests will verify specific components and edge cases:

- Model format detection logic with various model names
- Request payload transformation for both formats
- Response parsing with different response structures
- Error handling for various failure scenarios

### Property-Based Testing

Property-based tests will verify universal properties across many inputs using **Hypothesis** for Python:

- Each property-based test will run a minimum of 100 iterations
- Tests will generate random model names, message content, and API responses
- Each test will be tagged with comments referencing the design document properties

**Property Test Tags Format**: `**Feature: fix-ai-api-error, Property {number}: {property_text}**`

The dual testing approach ensures both concrete correctness (unit tests) and general correctness (property tests), providing comprehensive coverage of the API client functionality.

## Implementation Notes

### Backward Compatibility

The new SmartAIClient will maintain backward compatibility with existing code by:
- Preserving the same public interface as the current HTTP client
- Automatically detecting and handling format conversion transparently
- Maintaining existing error handling behavior where appropriate

### Performance Considerations

- Format detection will be cached to avoid repeated string matching
- Request transformation will be optimized to minimize object creation
- Response parsing will use efficient string operations

### Configuration

The system will support configuration for:
- Custom model format mappings
- API endpoint overrides
- Retry behavior parameters
- Debug logging levels