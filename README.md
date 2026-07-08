# NiKode

A tiny text editor built with Python and pygame.

## Run

```
python main.py
```

## Features

- Basic text editing (insert, backspace, arrow keys)
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
├── editor.py   # Editor class, event handling, drawing
└── utils.py    # config, colorscheme, and state dataclasses
```

## TODO

- [ ] Make configuration of the editor easier
- [ ] Make writing new themes easier
- [ ] Move cursor when scrolling
- [ ] Scroll when selecting
- [ ] Implement a simple file explorer
- [ ] Add docstrings and comments
