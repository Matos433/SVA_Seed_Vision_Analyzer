import sys
import os
import cv2
import numpy as np
import shutil
import random
import multiprocessing
from datetime import datetime

# Tenta importar YAML e sai se não encontrar
try:
    import yaml
except ImportError:
    print("ERRO: A biblioteca 'PyYAML' não está instalada. Por favor, instale-a executando: pip install PyYAML")
    sys.exit(1)

# Força o Matplotlib a usar o backend correto antes de outros imports
os.environ['QT_API'] = 'pyside6'

from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QLineEdit, QFileDialog, 
    QHBoxLayout, QVBoxLayout, QGridLayout, QGroupBox, QMessageBox, QMainWindow,
    QTabWidget, QFormLayout, QComboBox, QProgressBar, QTextEdit
)
from PySide6.QtGui import QImage, QPixmap, QFont, QIcon, QMouseEvent, QPainter, QPen, QColor, QIntValidator
from PySide6.QtCore import Qt, QRect, QPoint, QSize, Signal, QThread, QObject
from ultralytics import YOLO
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# --- FUNÇÃO AUXILIAR ---
def resource_path(relative_path):
    """ Obtém o caminho absoluto para o recurso, funciona para dev e para PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

# --- LÓGICA DE TREINAMENTO (EXECUTADA EM PROCESSO SEPARADO) ---
def run_training_process(queue, data_yaml_path, training_base_path, class_name, epochs, batch_size, base_model_name):
    """
    Função que executa em um processo separado para isolar o treinamento.
    Comunica-se com a thread principal através de uma fila (queue).
    """
    class QueueStream:
        def __init__(self, q, stream_type):
            self.q = q
            self.stream_type = stream_type
        def write(self, text):
            self.q.put((self.stream_type, text))
        def flush(self):
            pass

    sys.stdout = QueueStream(queue, 'log')
    sys.stderr = QueueStream(queue, 'log')

    try:
        data_config = {
            'path': os.path.abspath(training_base_path).replace("\\", "/"),
            'train': 'images/train',
            'val': 'images/val',
            'nc': 1,
            'names': [class_name]
        }
        with open(data_yaml_path, 'w') as f:
            yaml.dump(data_config, f, default_flow_style=False)

        train_path = os.path.join(training_base_path, 'images', 'train')
        if not os.path.isdir(train_path) or not any(f.lower().endswith(('.png', '.jpg', '.jpeg')) for f in os.listdir(train_path)):
            raise Exception(f"A pasta de treinamento '{train_path}' não existe ou está vazia.")

        print("Iniciando treinamento... Isso pode levar vários minutos.")
        model = YOLO(base_model_name)

        def on_epoch_end_callback(trainer):
            progress = int(((trainer.epoch + 1) / epochs) * 100)
            queue.put(('progress', progress))
        model.add_callback("on_epoch_end", on_epoch_end_callback)

        results = model.train(
            data=data_yaml_path, epochs=epochs, batch=batch_size, imgsz=640, 
            project=training_base_path, name='runs', exist_ok=True, val=True
        )

        if not (results and hasattr(results, 'results_dict')):
            raise Exception("Treinamento concluído, mas não foi possível extrair as métricas.")

        metrics_dict = results.results_dict
        summary = {
            'map50_95': metrics_dict.get('metrics/mAP50-95(B)', 0.0),
            'map50': metrics_dict.get('metrics/mAP50(B)', 0.0),
            'precision': metrics_dict.get('metrics/precision(B)', 0.0),
            'recall': metrics_dict.get('metrics/recall(B)', 0.0),
            'save_dir': str(results.save_dir)
        }
        queue.put(('finished', summary))

    except Exception as e:
        queue.put(('error', str(e)))

# --- WORKER PARA GERENCIAR O PROCESSO DE TREINAMENTO ---
class YoloTrainerWorker(QObject):
    finished = Signal(dict)
    error = Signal(str)
    log_update = Signal(str)
    progress_update = Signal(int)

    def __init__(self, data_yaml_path, training_base_path, class_name, epochs, batch_size, base_model_name):
        super().__init__()
        self.data_yaml_path = data_yaml_path
        self.training_base_path = training_base_path
        self.class_name = class_name
        self.epochs = epochs
        self.batch_size = batch_size
        self.base_model_name = base_model_name
        self.process = None

    def run(self):
        queue = multiprocessing.Queue()
        args = (queue, self.data_yaml_path, self.training_base_path, self.class_name, self.epochs, self.batch_size, self.base_model_name)
        
        self.process = multiprocessing.Process(target=run_training_process, args=args)
        self.process.start()

        while self.process.is_alive() or not queue.empty():
            try:
                message_type, data = queue.get(timeout=0.1)
                if message_type == 'log': self.log_update.emit(data)
                elif message_type == 'progress': self.progress_update.emit(data)
                elif message_type == 'finished':
                    self.finished.emit(data)
                    break
                elif message_type == 'error':
                    self.error.emit(data)
                    break
            except Exception:
                pass
        self.process.join()

# --- WIDGET DA ABA DE TREINAMENTO ---
class YoloTrainingWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(15)
        left_panel.setFixedWidth(480)

        params_group = QGroupBox("Parâmetros de Treinamento")
        params_layout = QFormLayout(params_group)
        params_layout.setSpacing(12)
        params_layout.setContentsMargins(15, 20, 15, 15)

        self.class_name_edit = QLineEdit("semente")
        self.epochs_edit = QLineEdit("50")
        self.epochs_edit.setValidator(QIntValidator(1, 1000))
        self.batch_size_edit = QLineEdit("16")
        self.batch_size_edit.setValidator(QIntValidator(1, 128))
        
        self.base_path_edit = QLineEdit()
        self.base_path_edit.setReadOnly(True)
        default_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "SEEDS COUNTER", "Treinamento")
        self.base_path_edit.setText(default_path)
        
        select_path_button = QPushButton("Selecionar...")
        select_path_button.clicked.connect(self.select_base_path)

        path_layout = QHBoxLayout()
        path_layout.addWidget(self.base_path_edit)
        path_layout.addWidget(select_path_button)
        
        self.model_select_combo = QComboBox()
        self.model_select_combo.addItems(['yolov8n.pt', 'yolov8s.pt', 'yolov8m.pt', 'yolov8l.pt', 'yolov8x.pt'])

        params_layout.addRow("Pasta Base:", path_layout)
        params_layout.addRow("Nome da Classe:", self.class_name_edit)
        params_layout.addRow("Modelo Base:", self.model_select_combo)
        params_layout.addRow("Épocas:", self.epochs_edit)
        params_layout.addRow("Tamanho do Lote:", self.batch_size_edit)
        left_layout.addWidget(params_group)

        self.run_button = QPushButton("🚀 Iniciar Treinamento")
        self.run_button.clicked.connect(self.start_training)
        left_layout.addWidget(self.run_button)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        left_layout.addWidget(self.progress_bar)

        results_group = QGroupBox("Resultados do Treinamento")
        results_layout = QVBoxLayout(results_group)
        results_layout.setSpacing(10)
        results_layout.setContentsMargins(15, 20, 15, 15)
        
        metrics_container = QWidget()
        metrics_grid = QFormLayout(metrics_container)
        metrics_grid.setSpacing(8)
        
        self.map50_95_label = QLabel("—")
        self.map50_label = QLabel("—")
        self.precision_label = QLabel("—")
        self.recall_label = QLabel("—")
        
        metrics_grid.addRow("<b>mAP50-95:</b>", self.map50_95_label)
        metrics_grid.addRow("<b>mAP50:</b>", self.map50_label)
        metrics_grid.addRow("<b>Precisão:</b>", self.precision_label)
        metrics_grid.addRow("<b>Recall:</b>", self.recall_label)
        
        results_layout.addWidget(metrics_container)
        self.figure = Figure(figsize=(6, 3.5), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        results_layout.addWidget(self.canvas)
        left_layout.addWidget(results_group, 1)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(10)
        
        log_group = QGroupBox("Log do Treinamento")
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(15, 20, 15, 15)
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        log_layout.addWidget(self.log_display)
        right_layout.addWidget(log_group)

        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel, 1)

    def select_base_path(self):
        directory = QFileDialog.getExistingDirectory(self, "Selecione a Pasta Base", self.base_path_edit.text())
        if directory:
            self.base_path_edit.setText(directory)

    def start_training(self):
        self.run_button.setEnabled(False)
        self.run_button.setText("⏳ Treinando...")
        self.log_display.clear()
        self.clear_results()
        self.progress_bar.setValue(0)

        training_base_path = self.base_path_edit.text()
        if not os.path.isdir(training_base_path):
            QMessageBox.warning(self, "Aviso", "Por favor, selecione uma pasta base válida.")
            self.run_button.setEnabled(True)
            self.run_button.setText("🚀 Iniciar Treinamento")
            return

        data_yaml_path = os.path.join(training_base_path, "data.yaml")
        class_name = self.class_name_edit.text()
        epochs = int(self.epochs_edit.text())
        batch_size = int(self.batch_size_edit.text())
        base_model_name = self.model_select_combo.currentText()

        self.thread = QThread()
        self.worker = YoloTrainerWorker(data_yaml_path, training_base_path, class_name, epochs, batch_size, base_model_name)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_training_finished)
        self.worker.error.connect(self.on_training_error)
        self.worker.log_update.connect(self.update_log)
        self.worker.progress_update.connect(self.update_progress_bar)
        self.worker.finished.connect(self.thread.quit)
        self.worker.error.connect(self.thread.quit)
        self.thread.start()

    def clear_results(self):
        self.map50_95_label.setText("—")
        self.map50_label.setText("—")
        self.precision_label.setText("—")
        self.recall_label.setText("—")
        self.figure.clear()
        self.canvas.draw()

    def update_log(self, message): self.log_display.append(message)
    def update_progress_bar(self, value): self.progress_bar.setValue(value)

    def on_training_finished(self, summary):
        self.log_display.append("\n" + "="*50 + "\nTREINAMENTO CONCLUÍDO COM SUCESSO\n" + "="*50)
        
        if 'map50_95' in summary:
            self.map50_95_label.setText(f"{summary['map50_95']:.2%}")
            self.map50_label.setText(f"{summary['map50']:.2%}")
            self.precision_label.setText(f"{summary['precision']:.2%}")
            self.recall_label.setText(f"{summary['recall']:.2%}")
            self.plot_results(summary)
        else:
            self.log_display.append("\nNenhuma métrica de validação foi gerada. Verifique a pasta 'val'.")
            self.clear_results()

        if 'save_dir' in summary: self.log_display.append(f"\n📁 Modelo salvo em: {summary['save_dir']}")
        
        self.run_button.setEnabled(True)
        self.run_button.setText("🚀 Iniciar Treinamento")
        self.progress_bar.setValue(100)
        QMessageBox.information(self, "Sucesso", "Treinamento concluído com sucesso!")

    def on_training_error(self, error_message):
        self.log_display.append(f"\n" + "="*50 + "\n❌ ERRO NO TREINAMENTO\n" + "="*50 + f"\n{error_message}")
        self.run_button.setEnabled(True)
        self.run_button.setText("🚀 Iniciar Treinamento")
        self.progress_bar.setValue(0)
        QMessageBox.critical(self, "Erro de Treinamento", f"Ocorreu um erro:\n\n{error_message}")

    def plot_results(self, summary):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        metrics = {'mAP50-95': summary['map50_95'], 'mAP50': summary['map50'], 'Precisão': summary['precision'], 'Recall': summary['recall']}
        colors = ['#3b82f6', '#16a34a', '#f97316', '#ef4444']
        bars = ax.bar(metrics.keys(), metrics.values(), color=colors)
        ax.set_ylim(0, 1)
        ax.set_title('Métricas de Desempenho do Modelo')
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height, f'{height:.1%}', ha='center', va='bottom')
        self.figure.tight_layout()
        self.canvas.draw()

# ========== CORREÇÃO APLICADA AQUI ==========
# A classe AnnotationPainter foi movida para ANTES da AnnotationLabel

# --- CLASSE PARA PINTAR AS ANOTAÇÕES ---
class AnnotationPainter(QWidget):
    """Widget para desenhar sobre o QLabel de anotação."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rects = []
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def paintEvent(self, event):
        painter = QPainter(self)
        for annotation in self.rects:
            rect = annotation['rect']
            color = annotation['color']
            pen = QPen(color, 2, Qt.SolidLine)
            painter.setPen(pen)
            painter.drawRect(rect)

# --- CLASSE DE ANOTAÇÃO (LABEL) ---
class AnnotationLabel(QLabel):
    rect_drawn = Signal(QRect) 
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CrossCursor)
        self.setFocusPolicy(Qt.StrongFocus) 
        self.rects = [] 
        self.current_pixmap = None
        self.COLOR_UNICA = QColor("#60a5fa")      # Azul Claro
        self.COLOR_DUPLA = QColor("#fb923c")      # Laranja Claro
        self.painter_widget = AnnotationPainter(self)

    def setPixmap(self, pixmap):
        self.current_pixmap = pixmap
        super().setPixmap(pixmap)

    def mousePressEvent(self, event: QMouseEvent):
        if not self.current_pixmap: return
        if event.button() == Qt.LeftButton:
            rect_size = 15
            click_pos = event.position().toPoint()
            top_left = QPoint(click_pos.x() - rect_size // 2, click_pos.y() - rect_size // 2)
            new_rect = QRect(top_left, QSize(rect_size, rect_size))
            if new_rect.width() > 0 and new_rect.height() > 0:
                new_annotation = {'rect': new_rect, 'color': self.COLOR_UNICA, 'class_id': 0, 'base_size': rect_size}
                self.rects.append(new_annotation)
                self.painter_widget.rects = self.rects
                self.painter_widget.update()
        elif event.button() == Qt.RightButton:
            click_pos = event.position().toPoint()
            for i in range(len(self.rects) - 1, -1, -1):
                if self.rects[i]['rect'].contains(click_pos):
                    self.rects.pop(i)
                    self.painter_widget.rects = self.rects
                    self.painter_widget.update()
                    break

    def keyPressEvent(self, event: QMouseEvent):
        if event.key() == Qt.Key_A and self.rects:
            last_annotation = self.rects[-1]
            center_point = last_annotation['rect'].center()
            if last_annotation['class_id'] == 0:
                last_annotation['class_id'] = 1
                last_annotation['color'] = self.COLOR_DUPLA
                new_size = last_annotation['base_size'] * 2
            else:
                last_annotation['class_id'] = 0
                last_annotation['color'] = self.COLOR_UNICA
                new_size = last_annotation['base_size']
            new_top_left = QPoint(center_point.x() - new_size // 2, center_point.y() - new_size // 2)
            last_annotation['rect'] = QRect(new_top_left, QSize(new_size, new_size))
            self.painter_widget.update()

    def resizeEvent(self, event):
        self.painter_widget.resize(event.size())
        super().resizeEvent(event)

    def clear_rects(self):
        self.rects.clear()
        self.painter_widget.rects = []
        self.painter_widget.update()


# --- CLASSE PRINCIPAL DA APLICAÇÃO ---
class TrainingApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ferramenta de Anotação e Treinamento - Seeds Counter")
        self.setFixedSize(1320, 720) 
        
        self.VIDEO_FRAME_HEIGHT = 500
        self.VIDEO_FRAME_WIDTH = int(self.VIDEO_FRAME_HEIGHT * (16 / 9))

        self.cap = None
        self.video_path = None
        self.project_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "SEEDS COUNTER")
        self.acquisition_active = False
        self.acquisition_saved_frames = []
        self.current_acquisition_index = -1

        self.setup_ui()
        self.apply_theme()

    def setup_ui(self):
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)

        # --- ABA 1: Identificação de Sementes ---
        identification_tab = QWidget()
        main_layout = QHBoxLayout(identification_tab)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        left_panel = QWidget()
        left_panel.setFixedWidth(380)
        left_panel_layout = QVBoxLayout(left_panel)
        left_panel_layout.setContentsMargins(0, 0, 0, 0)
        left_panel_layout.setSpacing(20)

        video_group = QGroupBox("1. Seleção de Vídeo")
        video_layout = QVBoxLayout(video_group)
        self.select_video_btn = QPushButton("📂  Importar Vídeo")
        self.video_path_label = QLabel("Nenhum vídeo carregado.")
        self.video_path_label.setWordWrap(True)
        self.video_path_label.setObjectName("InfoLabel")
        video_layout.addWidget(self.select_video_btn)
        video_layout.addWidget(self.video_path_label)
        left_panel_layout.addWidget(video_group)

        acquisition_group = QGroupBox("2. Configurar Aquisição")
        acquisition_layout = QGridLayout(acquisition_group)
        acquisition_layout.addWidget(QLabel("Nº de Frames para Anotar:"), 0, 0)
        self.train_num_frames_edit = QLineEdit("30")
        acquisition_layout.addWidget(self.train_num_frames_edit, 0, 1)
        self.start_acquisition_btn = QPushButton("▶️  Iniciar Aquisição")
        acquisition_layout.addWidget(self.start_acquisition_btn, 1, 0, 1, 2)
        self.acquisition_status_label = QLabel("Status: Aguardando vídeo...")
        self.acquisition_status_label.setObjectName("InfoLabel")
        acquisition_layout.addWidget(self.acquisition_status_label, 2, 0, 1, 2)
        left_panel_layout.addWidget(acquisition_group)

        instructions_group = QGroupBox("💡 Como Anotar")
        instructions_layout = QVBoxLayout(instructions_group)
        instructions_text = QLabel(
            "<b>Clique Esquerdo:</b> Adiciona semente única (azul).\n"
            "<b>Pressione 'A':</b> Converte a última em semente dupla (laranja e maior).\n"
            "<b>Clique Direito:</b> Remove a semente sob o cursor.\n"
            "<b>Salvar e Próximo:</b> Salva anotações do frame atual.\n"
            "<b>Pular Frame:</b> Ignora o frame atual."
        )
        instructions_text.setWordWrap(True)
        instructions_layout.addWidget(instructions_text)
        left_panel_layout.addWidget(instructions_group)
        
        left_panel_layout.addStretch()
        main_layout.addWidget(left_panel)

        right_panel = QWidget()
        right_panel_layout = QVBoxLayout(right_panel)
        right_panel_layout.setAlignment(Qt.AlignTop)
        right_panel_layout.setContentsMargins(0, 0, 0, 0)
        right_panel_layout.setSpacing(15)

        self.training_video_frame = AnnotationLabel("Importe um vídeo para começar...")
        self.training_video_frame.setAlignment(Qt.AlignCenter)
        self.training_video_frame.setFixedSize(self.VIDEO_FRAME_WIDTH, self.VIDEO_FRAME_HEIGHT)
        right_panel_layout.addWidget(self.training_video_frame)

        nav_button_container = QWidget()
        nav_buttons_layout = QHBoxLayout(nav_button_container)
        nav_buttons_layout.setContentsMargins(0, 10, 0, 0)
        
        self.training_frame_info_label = QLabel("Frame 0 / 0")
        self.train_next_btn = QPushButton("Salvar e Próximo")
        self.skip_frame_btn = QPushButton("Pular Frame")
        self.train_finish_btn = QPushButton("Finalizar")

        nav_buttons_layout.addWidget(self.training_frame_info_label)
        nav_buttons_layout.addStretch()
        nav_buttons_layout.addWidget(self.skip_frame_btn)
        nav_buttons_layout.addWidget(self.train_next_btn)
        nav_buttons_layout.addWidget(self.train_finish_btn)
        right_panel_layout.addWidget(nav_button_container)
        right_panel_layout.addStretch()

        main_layout.addWidget(right_panel, 1)
        
        self.tab_widget.addTab(identification_tab, "Identificação de Sementes")

        # --- ABA 2: Treinamento YOLO ---
        yolo_training_widget = YoloTrainingWidget(self)
        self.tab_widget.addTab(yolo_training_widget, "Treinamento YOLO")

        # Conectar sinais
        self.select_video_btn.clicked.connect(self.select_video)
        self.start_acquisition_btn.clicked.connect(self.toggle_image_acquisition)
        self.train_next_btn.clicked.connect(self.save_and_next_acquisition_frame)
        self.skip_frame_btn.clicked.connect(self.skip_acquisition_frame)
        self.train_finish_btn.clicked.connect(self.finish_acquisition)
        
    def apply_theme(self):
        self.setStyleSheet("""
            QMainWindow, QWidget { 
                font-family: 'Segoe UI', Arial, sans-serif; 
                font-size: 10pt; 
                background-color: #f8fafc;
                color: #334155;
            }
            QTabWidget::pane { border-top: 1px solid #e2e8f0; }
            QTabBar::tab {
                background: #f1f5f9;
                border: 1px solid #e2e8f0;
                border-bottom: none;
                padding: 10px 20px;
                font-weight: bold;
                color: #64748b;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
            QTabBar::tab:selected {
                background: #ffffff;
                color: #3b82f6;
                border-color: #e2e8f0;
                border-bottom: 1px solid #ffffff;
                margin-bottom: -1px;
            }
            QTabBar::tab:hover {
                background: #e2e8f0;
                color: #3b82f6;
            }
            QGroupBox { 
                background-color: #ffffff;
                border: 1px solid #e2e8f0; 
                border-radius: 8px; 
                margin-top: 10px; 
                padding: 15px;
            }
            QGroupBox::title { 
                padding: 0 10px;
                margin-left: 10px;
                font-weight: bold; 
                font-size: 10pt;
                color: #0f172a; 
            }
            QLabel#InfoLabel { color: #64748b; font-size: 9pt; }
            QPushButton { 
                padding: 8px 16px; 
                border-radius: 6px; 
                border: 1px solid #93c5fd; 
                background-color: #dbeafe; 
                color: #1e40af; 
                font-weight: bold;
            }
            QPushButton:hover { 
                background-color: #93c5fd; 
                border-color: #60a5fa;
            }
            QPushButton:pressed { background-color: #60a5fa; }
            QLineEdit, QComboBox { 
                border: 1px solid #cbd5e1; 
                border-radius: 6px; 
                padding: 8px; 
                background-color: white;
                color: #334155;
            }
            QLineEdit:focus, QComboBox:focus { border: 1px solid #3b82f6; }
            AnnotationLabel {
                border: 2px dashed #cbd5e1; 
                background-color: #ffffff; 
                border-radius: 8px; 
                font-size: 16pt;
                color: #94a3b8;
            }
            QProgressBar {
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                text-align: center;
                background-color: white;
                color: #334155;
            }
            QProgressBar::chunk {
                background-color: #3b82f6;
                border-radius: 5px;
            }
            QTextEdit {
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                background-color: #f8fafc;
                font-family: 'Consolas', 'Courier New', monospace;
            }
        """)
    
    def select_video(self):
        start_dir = os.path.dirname(os.path.abspath(__file__))
        file_path, _ = QFileDialog.getOpenFileName(self, "Selecionar Vídeo", start_dir, "Arquivos de Vídeo (*.mp4 *.avi *.mov)")
        if file_path: self.load_video(file_path)

    def load_video(self, video_path):
        self.video_path = video_path
        if self.cap: self.cap.release()
        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
            QMessageBox.critical(self, "Erro", "Não foi possível abrir o arquivo de vídeo.")
            self.cap = None
            return
        self.video_path_label.setText(f"Carregado: {os.path.basename(self.video_path)}")
        self.acquisition_status_label.setText("Status: Vídeo pronto. Inicie a aquisição.")
        ret, frame = self.cap.read()
        if ret: self.display_frame(frame)

    def display_frame(self, frame):
        if frame is None: return
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        qt_format = QImage(frame.data, w, h, bytes_per_line, QImage.Format_BGR888)
        pixmap = QPixmap.fromImage(qt_format)
        self.training_video_frame.setPixmap(pixmap.scaled(self.training_video_frame.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def toggle_image_acquisition(self):
        if not self.cap:
            QMessageBox.warning(self, "Vídeo Necessário", "Por favor, carregue um vídeo primeiro.")
            return
        self.acquisition_active = True
        self.acquisition_saved_frames = []
        self.current_acquisition_index = -1
        self.training_video_frame.clear_rects()
        
        temp_dir = os.path.join(self.project_dir, "Treinamento", "_temp")
        if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
        os.makedirs(temp_dir, exist_ok=True)

        self.acquisition_status_label.setText("Status: Coletando frames aleatórios...")
        QApplication.processEvents()

        try:
            num_frames_to_sample = int(self.train_num_frames_edit.text())
        except ValueError:
            QMessageBox.warning(self, "Entrada Inválida", "Por favor, insira um número válido de frames.")
            self.acquisition_status_label.setText("Status: Erro na aquisição.")
            return
            
        total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if num_frames_to_sample > total_frames:
            QMessageBox.warning(self, "Aviso", f"O vídeo tem apenas {total_frames} frames. Serão usados todos.")
            num_frames_to_sample = total_frames

        frame_indices = sorted(random.sample(range(total_frames), num_frames_to_sample))
        for i, frame_pos in enumerate(frame_indices):
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_pos)
            ret, frame = self.cap.read()
            if not ret: continue
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            image_name, label_name = f"frame_{timestamp}_{i:04d}.jpg", f"frame_{timestamp}_{i:04d}.txt"
            image_path, label_path = os.path.join(temp_dir, image_name), os.path.join(temp_dir, label_name)
            cv2.imwrite(image_path, frame)
            self.acquisition_saved_frames.append((image_path, label_path))

        if self.acquisition_saved_frames:
            self.current_acquisition_index = 0
            self.display_current_acquisition_frame()
            self.acquisition_status_label.setText("Status: Anotando...")
        else:
            self.acquisition_status_label.setText("Status: Falha ao coletar frames.")

    def display_current_acquisition_frame(self):
        if 0 <= self.current_acquisition_index < len(self.acquisition_saved_frames):
            self.training_video_frame.clear_rects()
            image_path, _ = self.acquisition_saved_frames[self.current_acquisition_index]
            pixmap = QPixmap(image_path)
            self.training_video_frame.setPixmap(pixmap.scaled(self.training_video_frame.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.training_frame_info_label.setText(f"Frame {self.current_acquisition_index + 1} / {len(self.acquisition_saved_frames)}")

    def save_and_next_acquisition_frame(self):
        if not self.acquisition_active or self.current_acquisition_index == -1: return
        image_path, label_path = self.acquisition_saved_frames[self.current_acquisition_index]
        frame = cv2.imread(image_path)
        if frame is None:
            QMessageBox.critical(self, "Erro", f"Não foi possível ler a imagem: {image_path}")
            self.skip_acquisition_frame()
            return
        frame_height, frame_width, _ = frame.shape
        with open(label_path, 'w') as f:
            for annotation in self.training_video_frame.rects:
                rect, class_id = annotation['rect'], annotation['class_id']
                x1 = int(rect.x() * (frame_width / self.training_video_frame.width()))
                y1 = int(rect.y() * (frame_height / self.training_video_frame.height()))
                x2 = int((rect.x() + rect.width()) * (frame_width / self.training_video_frame.width()))
                y2 = int((rect.y() + rect.height()) * (frame_height / self.training_video_frame.height()))
                x_center, y_center = ((x1 + x2) / 2) / frame_width, ((y1 + y2) / 2) / frame_height
                width, height = (x2 - x1) / frame_width, (y2 - y1) / frame_height
                f.write(f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n")
        self.skip_acquisition_frame()

    def skip_acquisition_frame(self):
        if not self.acquisition_active or self.current_acquisition_index == -1: return
        if self.current_acquisition_index < len(self.acquisition_saved_frames) - 1:
            self.current_acquisition_index += 1
            self.display_current_acquisition_frame()
        else:
            QMessageBox.information(self, "Fim da Aquisição", "Você chegou ao último frame. Clique em 'Finalizar'.")

    def finish_acquisition(self):
        if not self.acquisition_active: return
        reply = QMessageBox.question(self, 'Finalizar Anotação', "Deseja salvar as anotações e organizar o dataset?", QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if reply == QMessageBox.No: return

        self.acquisition_status_label.setText("Status: Organizando dataset...")
        QApplication.processEvents()

        try:
            base_train_path = os.path.join(self.project_dir, "Treinamento")
            temp_dir = os.path.join(base_train_path, "_temp")
            paths = {
                "images_train": os.path.join(base_train_path, "images", "train"),
                "images_val": os.path.join(base_train_path, "images", "val"),
                "labels_train": os.path.join(base_train_path, "labels", "train"),
                "labels_val": os.path.join(base_train_path, "labels", "val"),
            }
            for path in paths.values(): os.makedirs(path, exist_ok=True)
            
            annotated_files = [(img, lbl) for img, lbl in self.acquisition_saved_frames if os.path.exists(lbl) and os.path.getsize(lbl) > 0]
            random.shuffle(annotated_files)
            split_index = int(len(annotated_files) * 0.8)

            for i, (img_path, lbl_path) in enumerate(annotated_files):
                dest_img_folder = paths["images_train"] if i < split_index else paths["images_val"]
                dest_lbl_folder = paths["labels_train"] if i < split_index else paths["labels_val"]
                shutil.move(img_path, os.path.join(dest_img_folder, os.path.basename(img_path)))
                shutil.move(lbl_path, os.path.join(dest_lbl_folder, os.path.basename(lbl_path)))
            
            if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
            
            QMessageBox.information(self, "Sucesso!", f"Dataset YOLO criado com sucesso em:\n{base_train_path}")
        
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Ocorreu um erro ao organizar o dataset: {e}")

        self.acquisition_active = False
        self.acquisition_status_label.setText("Status: Pronto para nova aquisição.")
        self.training_video_frame.clear_rects()
        self.training_video_frame.setPixmap(QPixmap())
        self.training_frame_info_label.setText("Frame 0 / 0")

if __name__ == '__main__':
    multiprocessing.freeze_support()
    app = QApplication(sys.argv)
    icon_path = resource_path("icone.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    window = TrainingApp()
    window.show()
    sys.exit(app.exec())