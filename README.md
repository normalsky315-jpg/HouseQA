# HouseQA

> Real Estate Data Quality Assurance System

HouseQA is an open-source quality assurance tool designed to compare and validate real estate project information from multiple sources.

It was originally developed for the NKUinfos project to automatically verify construction project data against 591 New House and other public sources.

## Features

- Compare project information with 591 New House
- Validate JSON schema
- Detect inconsistent project data
- Compare building materials and facilities
- Generate HTML reports
- Generate Excel reports
- Support fuzzy matching
- GitHub Actions automation

## Planned Data Sources

- 591 New House
- Builder Official Website
- Leju
- Google Maps
- Internal JSON

## Roadmap

- [x] Project initialization
- [ ] Data model
- [ ] JSON validator
- [ ] 591 Fetcher
- [ ] Compare Engine
- [ ] Report Generator
- [ ] Auto Fix
- [ ] GitHub Actions

## Project Structure

```
houseqa/

app/
compare/
fetchers/
models/
normalize/
parsers/
reports/
rules/
tests/
```

## License

MIT
