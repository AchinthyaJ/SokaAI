import sys
import ctypes
import requests
from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtGui import QColor, QPainter, QKeyEvent
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLineEdit,
    QTextEdit, QScrollBar
)

# === Together.ai free API settings ===
API_KEY = "your_api_key_here"  # Replace with your actual API key
MODEL = "mistralai/Mistral-7B-Instruct-v0.2"
ENDPOINT = "https://api.together.xyz/v1/chat/completions"

class ChatBotWindow(QWidget):
    def __init__(self):
        super().__init__()

        # Window flags and transparency
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(420, 200)
        self.setMouseTracking(True)

        # Color states - slightly more visible to see rounded borders
        self.normal_color = QColor(40, 40, 40, 45)   # Slightly more visible for rounded borders
        self.hover_color = QColor(50, 50, 50, 65)    # More visible on hover  
        self.drag_color = QColor(70, 70, 70, 100)    # Clear visibility for dragging
        self.current_color = self.normal_color
        

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Input box
        self.input_box = QLineEdit(self)
        self.input_box.setPlaceholderText("Ask Anything Here")
        self.input_box.setStyleSheet("background: transparent; color: white; border: none; font-size: 16px;")
        self.input_box.returnPressed.connect(self.handle_input)

        # Output box
        self.output_box = QTextEdit(self)
        self.output_box.setReadOnly(True)
        self.output_box.setVerticalScrollBar(QScrollBar())
        self.output_box.setStyleSheet("background: transparent; color: white; border: none; font-size: 14px;")
        
        # Show manual on startup
        self.show_manual()

        layout.addWidget(self.input_box)
        layout.addWidget(self.output_box)

        # ESC handling, minimize toggle, and drag
        self.esc_once = False
        self.drag_position = None
        self.is_minimized = False
        self.manual_shown = True
        
        # Simple timer to check for Ctrl+M periodically
        self.hotkey_timer = QTimer()
        self.hotkey_timer.timeout.connect(self.check_hotkey)
        self.hotkey_timer.start(100)  # Check every 100ms
        self.ctrl_pressed = False
        self.m_pressed = False

        # Apply blur behind from Windows API
        self.apply_blur_effect()

    def show_manual(self):
        """Display the quick manual for first-time users"""
        manual_text = """📖 QUICK MANUAL - FLying AI
        
🔹 HOTKEYS:
   • Ctrl+M: Toggle minimize/restore window
   • ESC: Press twice to exit program
   • Enter: Send message (or dismiss this manual)

🔹 USAGE:
   • Type your question in the input box
   • Window stays on top and can be dragged anywhere
   • Translucent background shows desktop behind
   • Hover over window to see it more clearly

🔹 CONTROLS:
   • Left-click and drag to move window
   • Window becomes more opaque while dragging
   • Hover for better visibility
   
   

✨ Press Enter to dismiss this manual and start chatting!"""
        
        self.output_box.setText(manual_text)

    def apply_blur_effect(self):
        # Enable DWM blur behind (no opaque layer)
        hwnd = int(self.winId())

        class ACCENTPOLICY(ctypes.Structure):
            _fields_ = [
                ("AccentState", ctypes.c_int),
                ("AccentFlags", ctypes.c_int),
                ("GradientColor", ctypes.c_int),
                ("AnimationId", ctypes.c_int)
            ]

        class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
            _fields_ = [
                ("Attribute", ctypes.c_int),
                ("Data", ctypes.c_void_p),
                ("SizeOfData", ctypes.c_size_t)
            ]

        accent = ACCENTPOLICY()
        accent.AccentState = 3  # ACCENT_ENABLE_BLURBEHIND
        accent.GradientColor = 0x00000000  # Fully transparent gradient
        accent.AccentFlags = 0  # No additional flags
        accent.AnimationId = 0

        accent_ptr = ctypes.pointer(accent)
        data = WINDOWCOMPOSITIONATTRIBDATA()
        data.Attribute = 19  # WCA_ACCENT_POLICY
        data.Data = ctypes.cast(accent_ptr, ctypes.c_void_p)
        data.SizeOfData = ctypes.sizeof(accent)

        ctypes.windll.user32.SetWindowCompositionAttribute(hwnd, ctypes.byref(data))

    def paintEvent(self, event):
        # Draw only rounded translucent background
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(self.current_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 20, 20)

    def enterEvent(self, event):
        self.current_color = self.hover_color
        self.update()

    def leaveEvent(self, event):
        self.current_color = self.normal_color
        self.update()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            if self.esc_once:
                self.close()
            else:
                self.output_box.setText("⚠️ Press Esc again to exit.")
                self.esc_once = True
                QTimer.singleShot(3000, self.reset_esc_flag)

    def reset_esc_flag(self):
        self.esc_once = False

    def check_hotkey(self):
        # Check if Ctrl+M is currently pressed using Windows API
        user32 = ctypes.windll.user32
        VK_CONTROL = 0x11
        VK_M = 0x4D
        
        ctrl_state = user32.GetAsyncKeyState(VK_CONTROL) & 0x8000
        m_state = user32.GetAsyncKeyState(VK_M) & 0x8000
        
        if ctrl_state and m_state:
            if not (self.ctrl_pressed and self.m_pressed):
                # Keys just pressed
                self.toggle_minimize()
            self.ctrl_pressed = True
            self.m_pressed = True
        else:
            self.ctrl_pressed = False
            self.m_pressed = False

    def toggle_minimize(self):
        if self.is_minimized:
            # Restore the window
            self.show()
            self.activateWindow()
            self.raise_()
            self.is_minimized = False
        else:
            # Minimize the window
            self.hide()
            self.is_minimized = True
    
    def closeEvent(self, event):
        # Clean up timer when closing
        if hasattr(self, 'hotkey_timer'):
            self.hotkey_timer.stop()
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.current_color = self.drag_color  # Apply solid color during drag
            self.update()
            self.drag_position = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = None
            from PySide6.QtGui import QCursor
            pos = self.mapFromGlobal(QCursor.pos())
            if self.rect().contains(pos):
                self.current_color = self.hover_color
            else:
                self.current_color = self.normal_color
            self.update()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.drag_position:
            delta = event.globalPosition().toPoint() - self.drag_position
            self.move(self.pos() + delta)
            self.drag_position = event.globalPosition().toPoint()
            self.current_color = self.drag_color  # Keep solid color during drag
            self.update()

    def handle_input(self):
        # If manual is showing, dismiss it on first Enter press
        if self.manual_shown:
            self.manual_shown = False
            self.output_box.setText("🤖 Ready! Ask me anything...")
            self.input_box.clear()
            return
            
        prompt = self.input_box.text().strip()
        if not prompt:
            self.output_box.setText("❌ Please type something.")
            return
        self.output_box.setText("⏳ Thinking...")
        try:
            response = requests.post(
                ENDPOINT,
                headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 512,
                    "temperature": 0.7,
                    "top_p": 0.9
                }
            )
            response.raise_for_status()
            data = response.json()
            text = data["choices"][0]["message"]["content"].strip()
            self.output_box.setText(text)
        except Exception as e:
            self.output_box.setText(f"❌ Error: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ChatBotWindow()
    window.move(30, 30)
    window.show()
    sys.exit(app.exec())