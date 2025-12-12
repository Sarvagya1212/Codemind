// lib/utils/errorHandler.ts

/**
 * Extracts a readable error message from various error formats
 * Handles: Axios errors, FastAPI errors, Pydantic validation errors
 */
export function extractErrorMessage(error: any): string {
  // Handle null/undefined
  if (!error) return 'An unknown error occurred';

  // Direct string error
  if (typeof error === 'string') return error;

  // Axios error response
  if (error.response?.data) {
    const data = error.response.data;

    // FastAPI Pydantic validation errors (array format)
    // Format: [{ type: "...", loc: [...], msg: "...", input: "...", url: "..." }]
    if (Array.isArray(data.detail)) {
      return data.detail
        .map((err: any) => {
          const location = err.loc?.slice(1).join('.') || 'field';
          return `${location}: ${err.msg}`;
        })
        .join('; ');
    }

    // FastAPI string error
    if (typeof data.detail === 'string') {
      return data.detail;
    }

    // Generic data.detail object
    if (data.detail && typeof data.detail === 'object') {
      return data.detail.message || data.detail.msg || JSON.stringify(data.detail);
    }

    // data.message (some APIs use this)
    if (data.message) {
      return data.message;
    }

    // Stringify the entire data object as last resort
    if (typeof data === 'object') {
      return JSON.stringify(data);
    }
  }

  // Axios error without response (network error, timeout, etc.)
  if (error.message) {
    return error.message;
  }

  // Error object with custom message
  if (error.msg) {
    return error.msg;
  }

  // Last resort
  return 'An unexpected error occurred';
}

/**
 * Formats error for display in UI components
 * Ensures the error is always a string
 */
export function formatErrorForDisplay(error: any, fallback?: string): string {
  const message = extractErrorMessage(error);
  return message || fallback || 'An error occurred';
}

/**
 * Safe error renderer for React components
 */
export function safeRenderError(error: any, fallback?: string): string {
  if (typeof error === 'string') return error;
  return formatErrorForDisplay(error, fallback);
}