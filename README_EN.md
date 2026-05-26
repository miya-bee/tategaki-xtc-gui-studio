# TategakiXTC GUI Studio

**TategakiXTC GUI Studio** is a Windows GUI tool for converting Aozora Bunko text, EPUB, Markdown, plain text, and images into Japanese vertical-writing **XTC / XTCH** files for **Xteink X3 / X4**.

It is designed for Japanese vertical reading on small E Ink devices, especially Xteink X3 and Xteink X4.

The tool focuses on:

- Japanese vertical writing
- Aozora Bunko style text
- EPUB conversion
- Ruby text support
- Page number display
- Margin and line spacing adjustment
- Japanese punctuation position adjustment
- XTC / XTCH output
- Fixed-layout output for E Ink reading

## What this tool is for

This application is mainly intended for users who want to read Japanese books, Aozora Bunko texts, or EPUB files on Xteink X3 / X4 in a comfortable vertical-writing layout.

Typical use cases:

- Convert Aozora Bunko text into XTC / XTCH files
- Convert EPUB files into Xteink-friendly fixed-layout pages
- Read Japanese novels with ruby text on Xteink X3 / X4
- Adjust margins, line spacing, font size, and page numbers
- Preview converted pages before sending them to the device
- Use a Windows GUI instead of command-line conversion tools

## Supported input

Main supported input formats:

- Aozora Bunko style text
- Plain text
- Markdown
- EPUB
- Images
- Image archive based input

This tool is best suited for text-heavy Japanese books, novels, essays, and public-domain literature.

## Output formats

Main output formats:

- XTC
- XTCH

XTC / XTCH are fixed-layout display formats used in the Xteink ecosystem.

This tool renders the source text or EPUB into page images adjusted for the Xteink display size, then packs them into XTC / XTCH files.

## Main features

### Japanese vertical writing

The tool creates vertical-writing pages for Japanese reading.

It supports common Japanese layout needs such as:

- Vertical text flow
- Ruby text
- Japanese punctuation
- Margin adjustment
- Line spacing adjustment
- Font size adjustment

### Ruby text support

Ruby text can be displayed in the converted output.

There is also a ruby-hide mode for users who want to remove ruby text and use more screen space for the main body text.

### Page number display

Page numbers can be shown at the bottom-right of the output page.

This is useful for longer books where it is helpful to know the current reading position.

### EPUB robustness

The EPUB parser has been improved for text-focused EPUB files.

It includes handling for:

- EPUB spine entries
- Ruby / rtc structures
- CSS display rules
- Embedded images
- Large chapters in some conversion paths

This does not mean that every EPUB file can be perfectly reproduced.  
The main goal is to convert text-focused EPUB files into readable fixed-layout Japanese vertical pages for Xteink devices.

### XTC / XTCH viewer

The application can open existing XTC / XTCH files and preview their contents.

This is useful for checking converted files before transferring them to the device.

### Batch conversion

Multiple files can be converted in a batch.

Folder structure preservation and existing-file handling are also supported.

## Current public version

The current GitHub public version is **v1.3.6**.

GitHub provides the Python source version.

A Windows portable / exe version for users who do not want to set up Python is distributed separately via note.

## Windows portable / exe version

The GitHub version requires Python.

For users who want to use the application without installing Python, a Windows portable / exe version is available via note.

Japanese distribution article:

https://note.com/miya_bee_note/n/n8e8424e96e4e

Support article:

https://note.com/miya_bee_note/n/n0e172d7d2acb

Xteink related article index:

https://note.com/miya_bee_note/n/n1b5ef2af20d3

## Requirements

Recommended environment:

- Windows 10 / 11
- Python 3.10 / 3.11 / 3.12
- PySide6
- Pillow
- numpy

Install dependencies from `requirements.txt`.

## Quick start

On Windows, open Command Prompt in the extracted folder.

Check Python:

```cmd
python --version

py -3.12 --version
```

Install requirements:

```cmd
install_requirements.bat
```

Start the GUI:

```cmd
run_gui.bat
```

Or run manually:

```cmd
.venv\Scripts\python.exe -B ^
  tategakiXTC_gui_studio.py
```

## Recommended documents

- `README.md`
  - Main Japanese README
- `WINDOWS_SETUP.md`
  - Windows setup guide
- `FAQ.md`
  - Frequently asked questions
- `KNOWN_LIMITATIONS.md`
  - Known limitations
- `RELEASE_NOTES_v1_3_6.md`
  - Release notes for v1.3.6
- `CHANGELOG.md`
  - Version history

## Notes

This project is primarily developed for Japanese vertical writing and Xteink X3 / X4.

It may also be useful as a fixed-layout Japanese text conversion tool for E Ink reading workflows, but the main tested target is Xteink.

## License

This project is **Source Available**, not Open Source.

You may view and study the source code for personal use only.  
Redistribution, commercial use, and distribution of modified versions are not permitted.

See `LICENSE.txt` for details.

Bundled Noto fonts are distributed under the SIL Open Font License 1.1.  
See `LICENSE_OFL.txt` for details.

## Keywords

Xteink X3, Xteink X4, xteink, XTC, XTCH, Aozora Bunko, EPUB, Japanese vertical writing, ruby text, Japanese ebook converter, E Ink, Windows GUI, Python GUI.
