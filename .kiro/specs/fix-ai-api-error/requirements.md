# Requirements Document

## Introduction

The content analysis system is experiencing a 400 Bad Request error when calling the JD Cloud AI API with the Gemini-2.5-pro model. The error occurs because the current implementation uses an incorrect API endpoint and request format that is incompatible with the JD Cloud AI service.

## Glossary

- **ContentAgent**: The main class responsible for content compliance checking and analysis
- **JD_Cloud_AI_API**: The JD Cloud AI service API endpoint
- **Chat_Completions_Format**: The OpenAI-compatible request format using messages array
- **Gemini_Format**: The Google Gemini-specific request format using contents and parts
- **API_Payload**: The JSON request body sent to the AI API

## Requirements

### Requirement 1

**User Story:** As a system administrator, I want the content analysis to work without API errors, so that users can successfully analyze content descriptions.

#### Acceptance Criteria

1. WHEN the ContentAgent calls the AI API for content analysis, THE system SHALL use the correct API endpoint format
2. WHEN constructing the API request payload, THE system SHALL use the proper request structure compatible with JD Cloud AI service
3. WHEN the API call is made, THE system SHALL receive a successful response instead of a 400 Bad Request error
4. WHEN the AI analysis completes successfully, THE system SHALL return properly parsed analysis results
5. WHEN API errors occur, THE system SHALL provide clear error messages for debugging

### Requirement 2

**User Story:** As a developer, I want the API client to be compatible with JD Cloud AI service, so that all AI-powered features work correctly.

#### Acceptance Criteria

1. WHEN making chat completion requests, THE system SHALL use the correct endpoint URL for the target model
2. WHEN the model is Gemini-based, THE system SHALL format requests using the contents/parts structure
3. WHEN the model is OpenAI-compatible, THE system SHALL format requests using the messages structure
4. WHEN parsing API responses, THE system SHALL handle both Gemini and OpenAI response formats
5. WHEN API configuration changes, THE system SHALL automatically adapt to the correct format

### Requirement 3

**User Story:** As a content analyst, I want consistent and reliable content analysis results, so that the system provides accurate categorization.

#### Acceptance Criteria

1. WHEN content is submitted for analysis, THE system SHALL successfully complete the AI analysis without errors
2. WHEN the analysis is complete, THE system SHALL return results in the expected format with all six dimensions
3. WHEN the API call fails, THE system SHALL implement proper retry logic with exponential backoff
4. WHEN multiple requests are made, THE system SHALL maintain consistent response parsing
5. WHEN caching is enabled, THE system SHALL store and retrieve analysis results correctly