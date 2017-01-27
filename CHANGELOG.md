# Self Service Printer Installer Changelog

Things may move fast!

## [0.1.2] - 2017-01-27

### New
- Moved the default printer driver path to a configuration variable rather than
  hard coding it in the program logic.
- `generator.py` checks for [Required Fields](https://github.com/haircut/self-service-printer-installer/wiki/Creating-Printer-Queue-Definitions#required-fields)
   when processing your input CSV

### Changed
- Removed superfluous 'Label' field from required fields in the input CSV. The
  'DisplayName' field is now used as the JSON array name/label.
- Removed 'CUPSName' field from required fields in the input CSV. The field is
  now optional and used to check for already-mapped queues if available.

## 0.1.1 – 2017-01-27

### Changed
- Replaced temporary rudimentary argument parsing with `argparse` implementation

[0.1.2]: https://github.com/haircut/self-service-printer-installer/compare/v0.1.1...v0.1.2
