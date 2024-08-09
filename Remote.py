import sys
import os
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QSystemTrayIcon, QMenu
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import Qt, QSize, QTimer, QObject, pyqtSignal
import numpy as np
import subprocess
import functools
import configparser
import tempfile

# Get absolute path to resource, works for dev and for PyInstaller
def resource_path(relative_path):
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    gui_path = os.path.join(base_path, 'GUI')
    return os.path.join(gui_path, relative_path).replace("\\", "/")

def run_without_console(command):
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    subprocess.Popen(command, startupinfo=startupinfo, creationflags=subprocess.CREATE_NO_WINDOW)

# Funktion zum Generieren einer Sinus-Wellenform für das gewünschte Signal mit ASK-Modulation
def generate_ask_signal_waveform(bit_sequence, symbol_duration, sample_rate, carrier_freq, amplitude):
    waveform = np.array([], dtype=np.float32)
    for bit in bit_sequence:
        if bit == '1':
            symbol = amplitude * np.sin(2 * np.pi * carrier_freq * np.linspace(0, symbol_duration, int(symbol_duration * sample_rate)))
        else:
            symbol = np.zeros(int(symbol_duration * sample_rate))
        waveform = np.concatenate((waveform, symbol))
    return waveform

# Funktion zum Invertieren der Bit-Sequenz
def invert_bit_sequence(bit_sequence):
    inverted_sequence = ''.join(['1' if bit == '0' else '0' for bit in bit_sequence])
    return inverted_sequence

# Funktion zum Senden der Wellenform per HackRF
def send_waveform_to_hackrf(waveform_bytes):

    with tempfile.NamedTemporaryFile(mode='wb', delete=False) as temp_file:
        temp_file.write(waveform_bytes)
        temp_file.flush()  # Daten in die Datei schreiben

        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    
    # STARTF_USESHOWWINDOW flag setzen, um das Konsolenfenster zu verstecken
        hackrf_process = subprocess.Popen(['hackrf_transfer', '-t', temp_file.name, '-f', '433975000', '-a', '1', '-x', '30'],
                                           startupinfo=startupinfo,
                                           stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE,
                                           creationflags=subprocess.CREATE_NO_WINDOW)
    
        # Kommunikation mit dem Prozess ermöglichen
        stdout, stderr = hackrf_process.communicate()
    
    # Die temporäre Datei im RAM wird automatisch gelöscht, wenn sie geschlossen wird
    return stdout, stderr

# Funktion zum Lesen der Einstellungen aus der INI-Datei
def read_settings():
    config = configparser.ConfigParser()
    config.read('settings.ini')
    soft_regulation = config.getboolean('Settings', 'Soft Regulation', fallback=False)
    return soft_regulation

# Funktion zum Schreiben der Einstellungen in die INI-Datei
def write_settings(soft_regulation):
    config = configparser.ConfigParser()
    config['Settings'] = {'Soft Regulation': '1' if soft_regulation else '0'}
    with open('settings.ini', 'w') as configfile:
        config.write(configfile)

# Signalparameter
carrier_freq = 19119  # 19,119 kHz in Hz
symbol_duration = 1 / 1200  # 1200 Samples pro Symbol bei 1 MSps
sample_rate = 2900000  # 2,9 MSps
pause_samples = 71400  # Pause zwischen den Nachrichten
amplitude = 1  # Amplitude des Trägersignals

# Globale Variable für "Soft Regulation"
soft_regulation_global = read_settings()

class CustomButton(QPushButton):
    def __init__(self, normal_image_path, hover_image_path, pressed_image_path, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.normal_stylesheet = f"QPushButton{{ border-image: url({normal_image_path}); }}"
        self.hover_stylesheet = f"QPushButton:hover{{ border-image: url({hover_image_path}); }}"
        self.pressed_stylesheet = f"QPushButton:pressed{{ border-image: url({pressed_image_path}); }}"
        self.setStyleSheet(self.normal_stylesheet + self.hover_stylesheet + self.pressed_stylesheet)
        self.setCursor(Qt.PointingHandCursor)
        self.setText("")

class TransparentWindow(QWidget):
    soft_regulation_changed = pyqtSignal(bool)

    def __init__(self, image_path, led_image_path, bit_sequences, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.scaled = False

        # Bild laden und skaliert anzeigen
        pixmap = QPixmap(resource_path(image_path))
        screen_geometry = QApplication.desktop().screenGeometry()
        scaled_pixmap = pixmap.scaledToHeight(int(screen_geometry.height() * 0.75))
        self.label = QLabel(self)
        self.label.setPixmap(scaled_pixmap)
        self.resize(scaled_pixmap.width(), scaled_pixmap.height())
        
        # LED-Bild laden und skaliert anzeigen
        led_pixmap = QPixmap(resource_path(led_image_path))
        scaled_led_pixmap = led_pixmap.scaledToHeight(int(screen_geometry.height() * 0.012))
        self.led_label = QLabel(self)
        self.led_label.setPixmap(scaled_led_pixmap)
        
        # Berechne die Position relativ zur Fenstergröße
        led_x = int(159 * self.width() / pixmap.width())
        led_y = int(133 * self.height() / pixmap.height())
        
        self.led_label.move(led_x, led_y)  # Position anpassen
        self.led_label.setVisible(False)  # Die LED zunächst unsichtbar machen

        # Benutzerdefinierte Button-Positionen
        button_positions = {
            'on_off': (115, 220),
            'sun': (320, 710),
            'moon': (520, 220),
            'brighter': (320, 445),
            'darker': (320, 970),
            'cold': (60, 710),
            'warm': (585, 705),
            'read': (320, 1470),
            'timer0': (120, 1690),
            'timer1': (520, 1690),
        }

        # Buttons erstellen und positionieren
        button_height = int(screen_geometry.height() * 0.060)
        for button_name, (x, y) in button_positions.items():
            button = CustomButton(resource_path(f"{button_name}.png"), resource_path(f"{button_name}_hover.png"), resource_path(f"{button_name}_pressed.png"), button_name, self)
            button.setFixedSize(QSize(button_height, button_height))
            button.move(int(x * self.width() / pixmap.width()), int(y * self.height() / pixmap.height()))
            if button_name in ['brighter', 'darker', 'warm', 'cold']:
                button.clicked.connect(functools.partial(self.send_waveform, bit_sequences[button_name][0], button_name))
            else:
                button.clicked.connect(functools.partial(self.send_waveform, bit_sequences[button_name][0]))

        self.create_context_menu()

    def create_context_menu(self):
        self.tray_menu = QMenu(self)
        self.soft_regulation_action = self.tray_menu.addAction("Soft Regulation")
        self.soft_regulation_action.setCheckable(True)
        self.soft_regulation_action.setChecked(soft_regulation_global)
        self.soft_regulation_action.triggered.connect(self.toggle_soft_regulation)
        self.tray_menu.addSeparator()
        self.pairing_action = self.tray_menu.addAction("Pairing")
        self.pairing_action.triggered.connect(self.pair_device)
        self.tray_menu.addSeparator()
        self.exit_action = self.tray_menu.addAction("Exit")
        self.exit_action.triggered.connect(sys.exit)
        
    def pair_device(self):
        # Koppelsignal senden
        bit_sequence = bit_sequences['Pairing'][0]  # Koppelsignal aus bit_sequences holen
        self.send_waveform(bit_sequence)  # Signal senden

    def mousePressEvent(self, event):
        if event.buttons() == Qt.LeftButton and not self.scaled:
            self.dragPosition = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and not self.scaled:
            self.move(event.globalPos() - self.dragPosition)
            event.accept()

    def contextMenuEvent(self, event):
        self.tray_menu.exec_(event.globalPos())

    def toggle_soft_regulation(self):
        global soft_regulation_global
        soft_regulation_global = not soft_regulation_global
        self.soft_regulation_action.setChecked(soft_regulation_global)
        write_settings(soft_regulation_global)
        self.soft_regulation_changed.emit(soft_regulation_global)
        
    def mouseDoubleClickEvent(self, event):
        tray_icon.onTrayIconActivated(QSystemTrayIcon.DoubleClick)
        
    def toggleWindowState(self):
        if self.isVisible():
            self.hide()  # Wenn sichtbar, minimiere
        else:
            self.show()  # Wenn nicht sichtbar, maximiere
        
    def turn_off_led(self):
        # Hier wird die LED wieder unsichtbar gemacht
        self.led_label.setVisible(False)
    
    def send_waveform(self, bit_sequence, button_name=None):
        # Hier wird die LED sichtbar gemacht, wenn der Button geklickt wird
        self.led_label.setVisible(True)
    
        # Bitsequenz invertieren
        inverted_sequence = invert_bit_sequence(bit_sequence)

        # Wellenform generieren mit ASK-Modulation
        waveform = generate_ask_signal_waveform(inverted_sequence, symbol_duration, sample_rate, carrier_freq, amplitude)

        # Wellenform wiederholen und Pausen einfügen
        num_repeats = 20 if soft_regulation_global and button_name in ['brighter', 'darker', 'warm', 'cold'] else 4
        waveform_with_pause = np.concatenate([waveform, np.zeros(pause_samples)])
        repeated_waveform = np.tile(waveform_with_pause, num_repeats)

        # Wellenform in RAW-Datei schreiben
        #waveform_filename = 'ask_signal.raw'
        #with open(waveform_filename, 'wb') as f:
            #waveform_bytes = repeated_waveform.astype(np.float32).tobytes()
            #f.write(waveform_bytes)
            
        # Wellenform als BytesIO-Objekt speichern
        #waveform_buffer = io.BytesIO()
        #np.save(waveform_buffer, repeated_waveform)
        #waveform_buffer.seek(0)
        #waveform_bytes = waveform_buffer.read()
        waveform_bytes = repeated_waveform.astype(np.float32).tobytes()

        # Wellenform an HackRF übergeben
        #send_waveform_to_hackrf(waveform_filename)
        send_waveform_to_hackrf(waveform_bytes)

        # Löschen der RAW-Datei
        #os.remove(waveform_filename)
        
        # Timeout setzen, um die LED nach einer bestimmten Zeit wieder auszuschalten
        QTimer.singleShot(700, self.turn_off_led)  # 1000 ms = 1 Sekunde

class SystemTrayIcon(QSystemTrayIcon):
    def __init__(self, icon, parent=None):
        super().__init__(icon, parent)
        self.setToolTip("Vatato Light Remote Control")
        menu = QMenu(parent)
        self.soft_regulation_action = menu.addAction("Soft Regulation")
        self.soft_regulation_action.setCheckable(True)
        self.soft_regulation_action.setChecked(soft_regulation_global)
        self.soft_regulation_action.triggered.connect(self.toggle_soft_regulation)
        menu.addSeparator()
        exitAction = menu.addAction("Exit")
        exitAction.triggered.connect(sys.exit)
        self.setContextMenu(menu)
        self.activated.connect(self.onTrayIconActivated)
 
    def onTrayIconActivated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.parent().toggleWindowState()
                
    def toggle_soft_regulation(self):
        global soft_regulation_global
        soft_regulation_global = not soft_regulation_global
        self.parent().soft_regulation_action.setChecked(soft_regulation_global)
        write_settings(soft_regulation_global)
        
    def on_soft_regulation_changed(self, soft_regulation_global):
        self.soft_regulation_action.setChecked(soft_regulation_global)

if __name__ == '__main__':
    # Nachrichten im Bit-Format für verschiedene Buttons
    bit_sequences = {
        'on_off': ('0111011101110001000100010111011101110111000100010001000101110111011101110111011101110111011100010',),
        'sun': ('0111011101110001000100010111011101110111000100010001000101110111011101110111011101110001011100010',),
        'moon': ('0111011101110001000100010111011101110111000100010001000101110111011101110111011101110111000101110',),
        'brighter': ('0111011101110001000100010111011101110111000100010001000101110111011101110111011101110111000100010',),
        'darker': ('0111011101110001000100010111011101110111000100010001000101110111011101110111011101110001000100010',),
        'warm': ('0111011101110001000100010111011101110111000100010001000101110111011101110111011101110001000101110',),
        'cold': ('0111011101110001000100010111011101110111000100010001000101110111011101110111011101110001011101110',),
        'read': ('0111011101110001000100010111011101110111000100010001000101110111011101110111000101110111011101110',),
        'timer0': ('0111011101110001000100010111011101110111000100010001000101110111011101110111000101110111011100010',),
        'timer1': ('0111011101110001000100010111011101110111000100010001000101110111011101110111000101110111000101110',),
        'Pairing': ('0111011101110001000100010111011101110111000100010001000101110111011101110001000100010001000100010',),
    }

    app = QApplication(sys.argv)
    window = TransparentWindow('remote.png', 'led.png', bit_sequences)
    window.setWindowTitle("Vatato Light Fernbedienung")
    window.setWindowIcon(QIcon(resource_path('icon.ico')))
    
    tray_icon = SystemTrayIcon(QIcon(resource_path('icon.ico')), window)
    window.soft_regulation_changed.connect(tray_icon.on_soft_regulation_changed)

    tray_icon.show()

    sys.exit(app.exec_())
 