#!/usr/bin/env python3
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.widgets import Tree, Static, Header, Footer
from textual.binding import Binding
from textual import events
from textual.screen import Screen
import os
from pathlib import Path
from typing import Any
import logging

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    filename='viewer_debug.log',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ioccc_viewer')

"""
v1
(1) There's no way to jump right to the viewer, let's add a capability to do that and scroll throughout the text
(2) Add support to open/collapse the menu bar using `zo` and `zc`
(3) Add syntax highlighting support
(4) Add support to view html and markdown files. Is this even possible?
(5) I'll need to make and run all the files locally so the output can be displayed on the terminal
"""


class ContentView(ScrollableContainer):
    """A scrollable content viewer with vim-like navigation."""

    DEFAULT_CSS = """
    ContentView {
        height: 100%;
        border-left: solid green;
        overflow-y: scroll;
        padding: 1 2;
        width: 70%;
    }
    
    ContentView:focus {
        border-left: solid yellow;
    }
    """

    BINDINGS = [
        Binding("j", "scroll_down", "Scroll down", show=False),
        Binding("k", "scroll_up", "Scroll up", show=False),
        Binding("g,g", "scroll_home", "Scroll to top", show=False),
        Binding("G", "scroll_end", "Scroll to bottom", show=False),
        Binding("ctrl+d", "page_down", "Page down", show=False),
        Binding("ctrl+u", "page_up", "Page up", show=False),
        Binding("enter", "return_to_tree", "Return to tree", show=False),
    ]

    def compose(self) -> ComposeResult:
        """Create child widgets for the container."""
        yield Static(self.render_text, markup=True)

    def __init__(self, text: str = "", *, markup: bool = False, **kwargs):
        """Initialize with text content."""
        super().__init__(**kwargs)
        self.render_text = text
        self.markup = markup

    def update(self, text: str) -> None:
        """Update the content."""
        self.render_text = text
        if self.is_mounted:
            self.query_one(Static).update(self.render_text)

    def on_focus(self) -> None:
        """Handle focus event."""
        logger.debug("ContentView on_focus called")
        self.has_focus = True
        self.refresh()

    def on_blur(self) -> None:
        """Handle blur event."""
        logger.debug("ContentView on_blur called")
        self.has_focus = False
        self.refresh()

    def on_key(self, event: events.Key) -> None:
        """Handle key events."""
        logger.debug(f"ContentView received key event: {event.key}")
        if event.key == "j":
            self.action_scroll_down()
            event.prevent_default()
        elif event.key == "k":
            self.action_scroll_up()
            event.prevent_default()
        elif event.key == "g":
            self.action_scroll_home()
            event.prevent_default()
        elif event.key == "G":
            self.action_scroll_end()
            event.prevent_default()
        elif event.key == "ctrl+d":
            self.action_page_down()
            event.prevent_default()
        elif event.key == "ctrl+u":
            self.action_page_up()
            event.prevent_default()
        elif event.key == "enter":
            self.action_return_to_tree()
            event.prevent_default()

    def action_scroll_down(self) -> None:
        """Scroll content down."""
        logger.debug("ContentView scrolling down")
        self.scroll_y += 1

    def action_scroll_up(self) -> None:
        """Scroll content up."""
        logger.debug("ContentView scrolling up")
        self.scroll_y -= 1

    def action_scroll_home(self) -> None:
        """Scroll to the top."""
        logger.debug("ContentView scrolling to top")
        self.scroll_y = 0

    def action_scroll_end(self) -> None:
        """Scroll to the bottom."""
        logger.debug("ContentView scrolling to bottom")
        self.scroll_y = self.virtual_size.height

    def action_page_down(self) -> None:
        """Scroll down by a page."""
        logger.debug("ContentView paging down")
        self.scroll_y += self.size.height - 2

    def action_page_up(self) -> None:
        """Scroll up by a page."""
        logger.debug("ContentView paging up")
        self.scroll_y -= self.size.height - 2

    def action_return_to_tree(self) -> None:
        """Return focus to the file tree."""
        tree = self.app.query_one("#file_tree")
        self.blur()
        tree.focus()


class FileTree(Tree):
    """Tree widget for displaying files and folders."""
    
    BINDINGS = [
        Binding("zo", "expand_node", "Expand node", show=False),
        Binding("zc", "collapse_node", "Collapse node", show=False),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.visible = True

    def toggle_visibility(self) -> None:
        """Toggle the tree visibility."""
        self.visible = not self.visible
        self.styles.width = "30%" if self.visible else "0"
        self.styles.display = "block" if self.visible else "none"
        content = self.app.query_one(ContentView)
        content.styles.width = "70%" if self.visible else "100%"
        self.refresh()
        content.refresh()
        # Focus the tree if it becomes visible
        if self.visible:
            self.focus()

    def on_mount(self) -> None:
        """Handle the mount event to set up initial tree state."""
        self.root.expand()
        # Load the file structure
        self.load_directory("assets")
        logger.debug("FileTree mounted and loaded directory")
    
    def watch_has_focus(self, has_focus: bool) -> None:
        """Watch for focus changes."""
        if has_focus:
            logger.debug("FileTree gained focus")
        else:
            logger.debug("FileTree lost focus")

    def load_directory(self, path: str) -> None:
        """Recursively load a directory into the tree."""
        root_path = Path(path)
        
        def add_to_tree(node: Any, path: Path) -> None:
            # Sort directories first, then files
            paths = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
            
            for item in paths:
                # Skip hidden files and __pycache__
                if item.name.startswith('.') or item.name == '__pycache__':
                    continue
                
                # Create node data with the full path for later use
                data = {'path': str(item)}
                
                if item.is_dir():
                    # Add directory and recursively process its contents
                    branch = node.add(f"📁 {item.name}", data=data)
                    add_to_tree(branch, item)
                else:
                    # Add file with an icon based on extension
                    if item.suffix in ['.c', '.h']:
                        icon = "📄"
                    elif item.suffix in ['.txt', '.md', '.info']:
                        icon = "📝"
                    elif item.suffix in ['.mk', 'Makefile']:
                        icon = "🔧"
                    else:
                        icon = "📎"
                    node.add_leaf(f"{icon} {item.name}", data=data)
        
        # Start the recursive process from the root
        add_to_tree(self.root, root_path)

    def on_tree_node_highlighted(self, event: Tree.NodeHighlighted) -> None:
        """Event handler called when a tree node is highlighted."""
        if event.node and event.node.data:
            path = event.node.data.get('path', '')
            if path and os.path.isfile(path):
                try:
                    with open(path, 'r', encoding='utf-8', errors='replace') as f:
                        content = f.read()
                    # If it's a C file, add syntax highlighting hint
                    if path.endswith('.c'):
                        content = f"```c\n{content}\n```"
                    elif path.endswith('.h'):
                        content = f"```c\n{content}\n```"
                    elif path.endswith('.mk') or 'Makefile' in path:
                        content = f"```makefile\n{content}\n```"
                    self.app.update_content(event.node.label, content)
                except Exception as e:
                    self.app.update_content(event.node.label, f"Error reading file: {str(e)}")
            else:
                # For directories, show some info about the contents
                if os.path.isdir(path):
                    try:
                        num_files = len([f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))])
                        num_dirs = len([d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))])
                        content = f"# {os.path.basename(path)}\n\n"
                        content += f"This directory contains:\n"
                        content += f"- {num_files} files\n"
                        content += f"- {num_dirs} directories\n\n"
                        content += "Select a file to view its contents."
                        self.app.update_content(event.node.label, content)
                    except Exception as e:
                        self.app.update_content(event.node.label, f"Error reading directory: {str(e)}")

    def on_key(self, event: events.Key) -> None:
        """Handle key events."""
        logger.debug(f"FileTree received key event: {event.key}")
        if event.key == "j":
            self.action_cursor_down()
            event.prevent_default()
        elif event.key == "k":
            self.action_cursor_up()
            event.prevent_default()
        elif event.key == "enter":
            if self.cursor_node:
                if self.cursor_node.children:
                    # Toggle expansion for directories
                    if self.cursor_node.is_expanded:
                        self.cursor_node.collapse()
                    else:
                        self.cursor_node.expand()
                else:
                    # Switch focus to viewer for files
                    content = self.app.query_one(ContentView)
                    self.blur()
                    content.focus()
            event.prevent_default()

    def action_expand_node(self) -> None:
        """Expand the current node."""
        if self.cursor_node and self.cursor_node.children and not self.cursor_node.is_expanded:
            logger.debug(f"Expanding node: {self.cursor_node.label}")
            self.cursor_node.expand()

    def action_collapse_node(self) -> None:
        """Collapse the current node."""
        if self.cursor_node and self.cursor_node.children and self.cursor_node.is_expanded:
            logger.debug(f"Collapsing node: {self.cursor_node.label}")
            self.cursor_node.collapse()


class MainScreen(Screen):
    """Main application screen."""

    BINDINGS = [
        Binding("tab", "switch_focus", "Switch focus", show=True),
        Binding("q", "quit", "Quit", show=True),
        Binding("~", "toggle_sidebar", "Toggle sidebar", show=True),
        Binding("f,k", "focus_viewer", "Focus viewer", show=True),
        Binding("f,h", "focus_tree", "Focus sidebar", show=True),
    ]

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header("IOCCC Submissions Viewer")
        yield Container(
            Horizontal(
                FileTree("Files", id="file_tree"),
                ContentView(
                    "Welcome to IOCCC Submissions Viewer!\n\n"
                    "Navigation:\n"
                    "- j/k: Move up/down in tree or scroll content\n"
                    "- Enter: Open/close folders in tree, focus viewer for files\n"
                    "- Enter (in viewer): Return to tree\n"
                    "- zo/zc: Expand/collapse directories\n"
                    "- fk: Focus viewer\n"
                    "- fh: Focus sidebar\n"
                    "- Tab: Switch between tree and content\n"
                    "- ~: Toggle sidebar\n"
                    "- q: Quit\n\n"
                    "Content View Additional Controls:\n"
                    "- Ctrl+u/Ctrl+d: Page up/down\n"
                    "- gg/G: Jump to top/bottom",
                    id="content",
                    markup=True
                ),
            )
        )
        yield Footer()

    def on_mount(self) -> None:
        """Handle screen mount."""
        logger.debug("MainScreen mounted")
        self.query_one("#file_tree").focus()

    def on_key(self, event: events.Key) -> None:
        """Handle key events."""
        logger.debug(f"MainScreen received key event: {event.key}")
        if event.key == "tab":
            logger.debug("Tab key pressed in MainScreen")
            self.action_switch_focus()
            event.prevent_default()

    def action_switch_focus(self) -> None:
        """Switch focus between tree and content views."""
        tree = self.query_one("#file_tree")
        content = self.query_one("#content")
        
        logger.debug(f"Current focus - Tree: {tree.has_focus}, Content: {content.has_focus}")
        
        # Force focus change and refresh both widgets
        if tree.has_focus:
            logger.debug("Switching focus from tree to content")
            tree.blur()
            content.focus()
            tree.refresh()
            content.refresh()
        else:
            logger.debug("Switching focus from content to tree")
            content.blur()
            tree.focus()
            content.refresh()
            tree.refresh()
            
        logger.debug(f"After switch - Tree: {tree.has_focus}, Content: {content.has_focus}")

    def action_toggle_sidebar(self) -> None:
        """Toggle the sidebar visibility."""
        tree = self.query_one("#file_tree")
        tree.toggle_visibility()

    def action_focus_viewer(self) -> None:
        """Focus the content viewer."""
        content = self.query_one("#content")
        tree = self.query_one("#file_tree")
        tree.blur()
        content.focus()

    def action_focus_tree(self) -> None:
        """Focus the file tree."""
        content = self.query_one("#content")
        tree = self.query_one("#file_tree")
        content.blur()
        tree.focus()


class IOCCCViewer(App):
    """Main application class for viewing IOCCC submissions."""
    
    CSS = """
    Horizontal {
        width: 100%;
        height: 100%;
        layout: horizontal;
    }

    FileTree {
        width: 30%;
        border-right: solid green;
        dock: left;
        transition: all 200ms linear;
    }

    ContentView {
        dock: right;
        width: 70%;
        transition: all 200ms linear;
    }

    Tree {
        padding: 1;
    }

    Tree--cursor {
        background: $accent-darken-2;
        color: $text;
    }

    Tree:focus Tree--cursor {
        background: $accent;
        color: $text;
    }
    """

    def on_mount(self) -> None:
        """Handle application mount."""
        logger.debug("Application mounted")
        self.push_screen(MainScreen())

    def update_content(self, label: str, content: str = '') -> None:
        """Update the content area with file contents or directory info."""
        screen = self.screen
        if screen and isinstance(screen, MainScreen):
            content_widget = screen.query_one(ContentView)
            if content:
                content_widget.update(content)
            else:
                content_widget.update(f"No content available for {label}")


if __name__ == "__main__":
    logger.debug("Starting application")
    app = IOCCCViewer()
    app.run()