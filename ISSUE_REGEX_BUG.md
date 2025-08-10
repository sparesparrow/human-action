# GitHub Issue: Fix regex pattern error in PDF chapter detection

## Bug Description

A critical logic error exists in the PDF extractor's chapter detection regex pattern in `pdf_extractor.py` line 113.

## Current Issue
The regex pattern contains incorrect double backslashes:
```python
chapter_pattern = re.compile(r"^\\s*Kapitola\\s+(\\d+)\\.?\\s*(.*)$", re.IGNORECASE)
```

This pattern will literally match backslash characters instead of the intended:
- `\\s*` should be `\s*` (whitespace)
- `\\d+` should be `\d+` (digits)
- `\\.?` should be `\.?` (optional period)

## Impact
- Chapter detection will fail completely
- PDF processing will not properly split content into chapters
- May result in entire PDF being treated as single chapter

## Proposed Fix
```python
chapter_pattern = re.compile(r"^\s*Kapitola\s+(\d+)\.?\s*(.*)$", re.IGNORECASE)
```

## Testing Required
- Unit tests with sample Czech text containing "Kapitola 1", "Kapitola 2. Title" patterns
- Integration tests with actual PDF files
- Edge case testing for various chapter title formats

## Priority
High - This breaks core PDF processing functionality

## Status
- Identified: ✅
- Fix reverted pending proper testing
- Needs comprehensive test suite before implementation