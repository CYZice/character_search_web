# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains scripts to parse PDFs using the MinerU API and extract character-to-image mappings for Chinese stone inscription research (遼代漢文石刻文字研究).

## Scripts

| File | Purpose |
|------|---------|
| `test_mineru.py` | Uses MinerU v1 API (`https://mineru.net/api/v1/agent`) to parse PDFs |
| `test_mineru_v4.py` | Uses MinerU v4 API (`https://mineru.net/api/v4`) for batch PDF parsing |
| `extract_char_images.py` | Utility for extracting character images |

## PDF Format

The target PDFs have a **two-column layout**:
- Each column starts with a character title enclosed in 【】
- Followed by vertically stacked images belonging to that character
- Reading order: left column top-to-bottom, then right column

## Running Scripts

```bash
# Run v1 API test
python test_mineru.py

# Run v4 API test
python test_mineru_v4.py
```

## Configuration

Scripts contain hardcoded local paths and API tokens:
- `PDF_PATH`: Source PDF location
- `OUTPUT_DIR`: Extraction output directory
- `TOKEN`: MinerU API bearer token (already configured)
- `BASE_URL`: MinerU API endpoint

## Architecture

```
MinerU API → Parse PDF → Download ZIP → Extract → content_list_v2.json → Character-Image Mapping
```

The `content_list_v2.json` contains nested block structures with `title` and `image` block types. The mapping logic associates images with the preceding title character until the next title appears.
