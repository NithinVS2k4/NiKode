# NiKode

A tiny text editor built with Python and pygame.

## Run

```
python main.py
```

## Features

- Basic text editing (insert, backspace, arrow keys)
- Simple file explorer for directory navigation
- Mouse-based text selection and navigation
- Copy to clipboard (Ctrl/Cmd + C)
- Save (Ctrl/Cmd + S) and open (Ctrl/Cmd + O) files
- Configurable colorscheme


## Requirements

```
pip install pygame pyperclip
```
## Project Structure
 
```
.
├── main.py     # entry point
├── stage.py    # main loop
├── editor.py   # Main text editor
├── explorer.py # File explorer
└── utils.py    # config, colorscheme, and state dataclasses
```

## TODO

- [ ] Make configuration of the editor easier
- [ ] Make writing new themes easier
- [X] *~~Move cursor when scrolling~~*
- [X] *~~Scroll when selecting~~*
- [X] *~~Implement a simple file explorer~~*
- [ ] Add docstrings and comments
