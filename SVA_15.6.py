import sys, os, cv2
import threading
import numpy as np
import json
import pickle
from datetime import datetime, timedelta
import csv
import random, time
import requests
import shutil
from PySide6.QtCore import Qt, QTimer, Signal, QThread, QObject, QBuffer, QMutex, QUrl
import smtplib, ssl
from email.mime.text import MIMEText
import urllib.request
import webbrowser

from PySide6.QtWidgets import (QButtonGroup,
    QApplication, QWidget, QLabel, QPushButton, QCheckBox, QComboBox, QFrame, QScrollArea, QGroupBox, QTabWidget, QRadioButton,
    QLineEdit, QFileDialog, QHBoxLayout, QVBoxLayout, QGridLayout, QSlider, QTableWidget, QTableWidgetItem, QGraphicsDropShadowEffect, QGraphicsScene, QGraphicsView, QGraphicsRectItem, QListWidget, QAbstractItemView,
    QSizePolicy, QMessageBox, QSplitter, QDialog, QTextEdit, QStyle, QHeaderView, QFormLayout, QProgressBar 
)
from PySide6.QtGui import QImage, QPixmap, QFont, QIcon, QPalette, QColor, QDoubleValidator, QIntValidator, QPainter, QPen, QBrush, QPainterPath, QDesktopServices
from PySide6.QtGui import QMouseEvent
from PySide6.QtCore import QRect, QPoint, QSize
import subprocess
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pyqtgraph as pg
from io import BytesIO

# --- INÍCIO DAS NOVAS DEFINIÇÕES DE CAMINHO ---
# Determina o diretório base (funciona tanto para .py quanto para .exe compilado)
if getattr(sys, 'frozen', False):
    # Estamos rodando em um .exe compilado
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # Estamos rodando em um script .py normal
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Define os diretórios padrão baseados no BASE_DIR
PROJECTS_DIR = os.path.join(BASE_DIR, "Meus Projetos")
DOWNLOAD_DIR = os.path.join(BASE_DIR, "SVA")
print(f"DEBUG: Diretório Base (BASE_DIR) definido como: {BASE_DIR}")
print(f"DEBUG: Diretório de Projetos (PROJECTS_DIR) definido como: {PROJECTS_DIR}")
print(f"DEBUG: Diretório de Downloads (DOWNLOAD_DIR) definido como: {DOWNLOAD_DIR}")

# --- FIM DAS NOVAS DEFINIÇÕES DE CAMINHO ---

# Carrega o token de uma variável de ambiente. Se não existir, fica None.
GITHUB_TOKEN = os.environ.get("SVA_GITHUB_TOKEN")
GITHUB_REPO = "Matos433/SVA_Seed_Vision_Analyzer"
TARGET_FILENAME = "best.pt"
TARGET_DATE_STR = "09/11/2025"
TARGET_DATE = datetime.strptime(TARGET_DATE_STR, "%d/%m/%Y")
GITHUB_LAUNCHER = GITHUB_REPO

# URL para a API de Releases do GitHub para obter a última versão
GITHUB_RELEASES_API_URL = f"https://api.github.com/repos/{GITHUB_LAUNCHER}/releases/latest"
# --- NOVO: VARIÁVEL GLOBAL DE VERSÃO (SSOT) ---
CURRENT_VERSION = "v2025.1.17"
SOFTWARE_FILENAME = f"SVA_{CURRENT_VERSION}.exe"
# --- FIM NOVO ---
REMOTE_VERSION = f"{CURRENT_VERSION}" 
REMOTE_DOWNLOAD_URL = ""

# Linha 80 (Adicione este bloco de estilo global)

# --- ESTILO GLOBAL PARA QMESSAGEBOX (TEMA ESCURO) ---
DARK_MESSAGE_BOX_STYLE = """
    QMessageBox { background-color: #1e293b; border: 1px solid #475569; } /* Fundo Escuro */
    QLabel { color: #f8fafc; } /* Texto Branco */
    QPushButton { 
        background-color: #334155; 
        color: white; 
        border: 1px solid #475569; 
        padding: 6px 15px; 
        border-radius: 4px; 
        min-width: 70px; /* Garante que os botões tenham tamanho suficiente */
    }
    QPushButton:hover { background-color: #475569; }
"""
# --- FIM ESTILO GLOBAL ---

# --------------------------------- FUNÇÕES AUXILIARES DE REDE ----------------------------------------------

def is_version_greater(latest_version, current_version):
    """Compara duas versões e retorna True se a versão mais recente for superior à atual."""
    
    # Função de limpeza para remover 'v' ou 'vv' e espaços em branco
    def clean_version_str(version_str):
        if not isinstance(version_str, str):
            return str(version_str)
        # Remove 'v' ou 'vv' e espaços
        return version_str.lower().lstrip('v').lstrip('vv').strip() 

    def parse_version(version_str):
        try:
            # Usa a função de limpeza antes de dividir
            clean_version = clean_version_str(version_str)
            parts = []
            for part in clean_version.split("."):
                numeric_part = "".join(filter(str.isdigit, part))
                if numeric_part:
                    parts.append(int(numeric_part))
                else:
                    parts.append(0)
            return parts
        except Exception:
            return [0]
            
    try:
        latest_parts = parse_version(latest_version)
        current_parts = parse_version(current_version)

        max_len = max(len(latest_parts), len(current_parts))
        latest_parts.extend([0] * (max_len - len(latest_parts)))
        current_parts.extend([0] * (max_len - len(current_parts)))

        for latest_part, current_part in zip(latest_parts, current_parts):
            if latest_part > current_part:
                return True
            elif latest_part < current_part:
                return False
        return False
    except Exception:
        # Fallback se a comparação baseada em números falhar (compara strings limpas)
        return clean_version_str(latest_version) != clean_version_str(current_version)


# Linha 111 (Substitua esta função inteira)
def get_yolo_asset_url(url):
    """Busca a URL de download (asset_url) para o best.pt na release mais recente."""
    print(f"Buscando asset YOLO na URL: {url}")
    
    headers = {"Accept": "application/vnd.github.v3+json"}
    
    # Adiciona o token APENAS SE ele existir
    if GITHUB_TOKEN:
        print("Usando token de autenticação para a API.")
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    else:
        print("AVISO: GITHUB_TOKEN não definido. Usando API pública (pode ter limite de taxa).")
        
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status() 
        data = response.json()
        
        # Procura o Asset URL para o best.pt
        download_url = None
        if 'assets' in data and len(data['assets']) > 0:
            for asset in data['assets']:
                if asset.get('name', '') == TARGET_FILENAME: 
                    download_url = asset.get('url') 
                    break
        
        if not download_url:
            print(f"AVISO: Arquivo '{TARGET_FILENAME}' não foi localizado nos assets da release.")
            return None
            
        print(f"URL do Asset YOLO encontrada: {download_url}")
        return download_url

    except requests.exceptions.HTTPError as http_err:
        print(f"Erro HTTP: {http_err}")
    except Exception as e:
        print(f"Erro ao buscar asset YOLO: {e}")
        return None

# Linha 150 (Substitua esta função inteira)
def get_latest_version(url):
    """Busca a última versão e a URL de download do executável no GitHub Releases."""
    
    headers = {"Accept": "application/vnd.github.v3+json"}

    # Adiciona o token APENAS SE ele existir
    if GITHUB_TOKEN:
        print("Usando token de autenticação para a API.")
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    else:
        print("AVISO: GITHUB_TOKEN não definido. Usando API pública (pode ter limite de taxa).")
        
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # 1. Extrai a versão da tag
        latest_version = data.get('tag_name', 'v0.0.0').lstrip('v')

        # 2. Procura o Asset URL do executável (.exe)
        download_url = None
        exe_asset_name = None
        if 'assets' in data and len(data['assets']) > 0:
            for asset in data['assets']:
                asset_name = asset.get('name', '')
                if asset_name.endswith(".exe"):
                    exe_asset_name = asset_name
                    download_url = asset.get('url') 
                    break 

        if not download_url:
            print(f"AVISO: Versão {latest_version} encontrada, mas URL de download (.exe) não foi localizada nos 'assets'.")
            print(f"DEBUG: Assets disponíveis na Release: {[a.get('name') for a in data.get('assets', [])]}")
            return latest_version, None

        print(f"DEBUG: Executável encontrado: {exe_asset_name}")
        return latest_version, download_url

    except requests.exceptions.HTTPError as http_err:
        print(f"Erro HTTP: {http_err}")
    except Exception as e:
        print(f"Erro ao buscar última versão ou assets: {e}")
        
    return "0.0.0", None

# Linha 192 (Substitua a classe completa)
class Downloader(QThread ):
    """Classe unificada para gerenciar o download de arquivos do GitHub em uma thread separada."""
    finished = Signal(bool, str) 
    progress_updated = Signal(int) # NOVO: Sinal para a barra de progresso

    def __init__(self, url, filepath, parent=None):
        super().__init__(parent)
        self.url = url 
        self.filepath = filepath

    def run(self):
        """Baixa o arquivo da URL fornecida e salva no caminho especificado, emitindo o progresso."""
        try:
            session = requests.Session()
            
            # 1. Configura os cabeçalhos para o download de Asset
            headers = {"Accept": "application/octet-stream"}
            
            global GITHUB_TOKEN
            if GITHUB_TOKEN:
                headers["Authorization"] = f"token {GITHUB_TOKEN}"
                
            session.headers.update(headers)
            
            # 2. Faz a requisição na URL do Asset
            # Aumenta o timeout para downloads maiores
            response = session.get(self.url, stream=True, allow_redirects=True, timeout=30) 
            response.raise_for_status() 
            
            # 3. Obtém o tamanho total para cálculo do progresso
            total_size = int(response.headers.get('Content-Length', 0))
            downloaded_size = 0
            
            # 4. Salva o conteúdo em chunks, emitindo o progresso
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            with open(self.filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=32768): # 32 KB chunks
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        if total_size > 0:
                            # Emite a porcentagem de progresso
                            progress_pct = int((downloaded_size / total_size) * 100)
                            self.progress_updated.emit(progress_pct)

            self.finished.emit(True, self.filepath)
        except Exception as e:
            print(f"Erro ao baixar {self.filepath}: {e}")
            self.finished.emit(False, self.filepath)

    def save_response_content(self, response):
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        with open(self.filepath, "wb") as f:
            for chunk in response.iter_content(chunk_size=32768):
                if chunk:
                    f.write(chunk)

class UpdateDialog(QDialog):
    """Janela de diálogo para verificar e gerenciar atualizações."""
    update_signal = Signal(object)
    
    def __init__(self, parent=None, current_version=""):
        super().__init__(parent)
        self.setWindowTitle("Gerenciador de Atualizações")
        self.setFixedSize(750, 300)
        self.current_version = current_version
        
        # Garante que o diretório de download (SVA) exista
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        
        self.setup_ui()
        self.downloader = None 
        self.update_signal.connect(self.update_version_ui)
        self.check_status()

    def style_status_label(self, label, text, color):
        """Aplica o estilo visual padronizado para labels de status."""
        label.setText(text)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet(f"background-color: transparent; color: {color}; border: 2px solid {color}; border-radius: 5px; padding: 5px 8px; font-size: 10px; font-weight: bold;")
    
    # Linha 292 (Substitua a função completa)
    def setup_ui(self):
        """Configura a interface gráfica do diálogo de atualização."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # 1. Mensagem de Alerta (Conexão com a Internet)
        self.alert_label = QLabel("ATENÇÃO: Conecte-se à internet para verificações das versões.")
        self.alert_label.setAlignment(Qt.AlignCenter)
        self.alert_label.setStyleSheet("color: white; background-color: #f59e0b; padding: 5px; border-radius: 4px; font-weight: bold;")
        main_layout.addWidget(self.alert_label)

        # 2. Tabela de Status
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Item", "Versão/Data", "Status", "Ação"])
        # CORREÇÃO: Coluna 0 (Item) expande para o espaço restante
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch) 
        # CORREÇÃO: Colunas 1, 2 e 3 (Versão/Data, Status, Ação) com larguras fixas maiores
        self.table.setColumnWidth(1, 150) # Versão/Data
        self.table.setColumnWidth(2, 120) # Status (Aumentado de 100)
        self.table.setColumnWidth(3, 120) # Ação (Aumentado de 80)
        self.table.setRowCount(2)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.setFixedSize(710, 150)

        # Linha 320 (Substitua este bloco de definição de itens)
        # Linha 1: Software
        self.label_version = QTableWidgetItem("Baixar nova versão do Software")
        self.version_display = QLabel("N/A") # CORREÇÃO: Usar QLabel para permitir setStyleSheet
        self.version_display.setAlignment(Qt.AlignCenter) # Centraliza o texto no QLabel
        self.status_version = QLabel("N/A")
        self.btn_version = QPushButton("Baixar")
        self.style_status_label(self.status_version, "N/A", "#64748b")
        
        self.table.setItem(0, 0, self.label_version)
        self.table.setCellWidget(0, 1, self.version_display) # NOVO: Insere o QLabel na coluna 1
        self.table.setCellWidget(0, 2, self.status_version)
        self.table.setCellWidget(0, 3, self.btn_version)

        # Linha 2: Modelo YOLO
        self.label_yolo = QTableWidgetItem("Baixar novo modelo YOLO")
        self.yolo_date_display = QTableWidgetItem("00/00/0000 00:00")
        self.yolo_date_display.setTextAlignment(Qt.AlignCenter)
        self.status_yolo = QLabel("N/A")
        self.btn_yolo = QPushButton("Baixar")
        self.style_status_label(self.status_yolo, "N/A", "#64748b")
        self.table.setItem(1, 0, self.label_yolo)
        self.table.setItem(1, 1, self.yolo_date_display)
        self.table.setCellWidget(1, 2, self.status_yolo)
        self.table.setCellWidget(1, 3, self.btn_yolo)
        
        main_layout.addWidget(self.table)

        # 3. Barra de Progresso (NOVO ELEMENTO)
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False) # Começa oculta
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("Baixando... %p%") 
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                background-color: #f1f5f9; 
                color: #000000;
                text-align: center;
                height: 20px;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #16a34a; /* Verde */
                border-radius: 4px;
            }
        """)
        main_layout.addWidget(self.progress_bar)

        # 4. Botão Fechar
        self.btn_close = QPushButton("Fechar")
        self.btn_close.clicked.connect(self.accept)
        self.btn_close.setFixedSize(120, 30)
        
        close_layout = QHBoxLayout()
        close_layout.addStretch()
        close_layout.addWidget(self.btn_close)
        
        main_layout.addLayout(close_layout)
        
        # 5. Conexões de botões
        self.btn_version.clicked.connect(self.download_new_version)
        self.btn_yolo.clicked.connect(self.download_new_yolo)
        
        # Estilo geral (Revertido para fundo branco/claro)
        self.setStyleSheet("""
            QDialog { background-color: white; }
            QLabel { color: black; }
            QTableWidget { 
                background-color: #f8fafc; 
                border: 1px solid #cbd5e1;
                gridline-color: #cbd5e1;
                color: black;
            }
            QHeaderView::section {
                background-color: #e2e8f0;
                color: black;
                border: 1px solid #cbd5e1;
            }
            QPushButton {
                background-color: #16a34a; 
                color: white;
                border: none;
            }
            QPushButton:hover { background-color: #15803d; }
        """)

   # Linha 407 (Substitua a função completa)
    def check_status(self):
        """Verifica o status da versão e do modelo YOLO."""
        
        # 1. Status da Versão (Verificação via API em thread separada)
        self.set_status(self.status_version, "Verificando...", "#f59e0b")
        self.btn_version.setEnabled(False)       
        
        def check_software_update():
            global REMOTE_VERSION, REMOTE_DOWNLOAD_URL       
            latest_version, download_url = get_latest_version(GITHUB_RELEASES_API_URL)
            
            print(f"Versão encontrada no GitHub: {latest_version}")
            
            is_update_available = False
            if latest_version and download_url:
                # CORREÇÃO: Usa a variável global CURRENT_VERSION
                current_version_clean = CURRENT_VERSION 
                is_update_available = is_version_greater(latest_version, current_version_clean)
            
            result = None
            if is_update_available:
                result = (latest_version, download_url)
            
            self.update_signal.emit(result)
            
        threading.Thread(target=check_software_update).start()

    # 2. Status do Modelo YOLO
        # CORREÇÃO: Usa o DOWNLOAD_DIR (pasta SVA)
        yolo_path = os.path.join(DOWNLOAD_DIR, TARGET_FILENAME)
        is_yolo_outdated = True
        
        if os.path.exists(yolo_path):
            file_mod_time = datetime.fromtimestamp(os.path.getmtime(yolo_path))
            yolo_date_str = file_mod_time.strftime("%d/%m/%Y %H:%M")
            self.yolo_date_display.setText(f"{yolo_date_str} (OK)")
            
            # Se o arquivo existir, consideramos ele atualizado.
            is_yolo_outdated = False 
        else:
            self.yolo_date_display.setText("Modelo não encontrado")
            
        
        if is_yolo_outdated:
            self.set_status(self.status_yolo, "Baixar", "#f97316")
            self.btn_yolo.setEnabled(True)
            # Estilo Ativo: Verde
            self.btn_yolo.setStyleSheet("background-color: #10b981; color: white; border: none;")
        else:
            self.set_status(self.status_yolo, "Atualizado", "#3b82f6")
            self.btn_yolo.setEnabled(False)
            # CORREÇÃO: Estilo Desabilitado: Cinza/Claro (Igual ao do Software)
            self.btn_yolo.setStyleSheet("background-color: #e2e8f0; color: #475569; border: none;")

    # Linha 468 (Substitua a função completa)
    def update_version_ui(self, result):
        """Atualiza a interface de usuário da versão após a verificação da thread."""
        global REMOTE_VERSION, REMOTE_DOWNLOAD_URL
        
        # 1. Lógica: Atualização Disponível
        if result and len(result) == 2:
            latest_version, download_url = result
            REMOTE_VERSION = latest_version
            REMOTE_DOWNLOAD_URL = download_url
            
            # ATUALIZAÇÃO: Exibe a versão remota e aplica estilo de alerta (Agora funciona!)
            self.version_display.setText(f"{latest_version} (Remota)")
            self.version_display.setStyleSheet("font-weight: bold; color: #dc2626;")
            
            self.set_status(self.status_version, "Desatualizado", "#f97316")
            self.btn_version.setEnabled(True)
            self.btn_version.setStyleSheet("QPushButton { background-color: #10b981; color: white; border: none; } QPushButton:hover { background-color: #059669; }")
            
        # 2. Lógica: Sem Atualização ou Erro
        else:
            # CORREÇÃO: Exibe a versão local (CURRENT_VERSION)
            global CURRENT_VERSION
            self.version_display.setText(f"{CURRENT_VERSION} (Local)")
            self.version_display.setStyleSheet("font-weight: normal; color: black;") # Limpa estilo de alerta

            if REMOTE_VERSION == "0.0.0": 
                # Estado de Erro na Conexão
                self.set_status(self.status_version, "Erro/Atualizado", "#dc2626")
                self.btn_version.setEnabled(False)
            else:
                # Estado de Atualizado
                self.set_status(self.status_version, "Atualizado", "#3b82f6")
                self.btn_version.setEnabled(False)
                self.btn_version.setStyleSheet("QPushButton { background-color: #e2e8f0; color: #475569; border: none; }")

    def set_status(self, label, text, color):
        label.setText(text)
        label.setStyleSheet(f"background-color: transparent; color: {color}; border: 2px solid {color}; border-radius: 5px; padding: 5px 8px; font-size: 10px; font-weight: bold;")

    # Linha 517 (Substitua a função completa)
    def download_new_version(self):
        """Inicia o download da nova versão do software."""
        
        # Verifica se o downloader já está ativo
        if self.downloader and self.downloader.isRunning():
            QMessageBox.warning(self, "Download em Andamento", "Um download já está em andamento. Por favor, aguarde.")
            return

        if REMOTE_DOWNLOAD_URL:
            # --- CORREÇÃO: Criação manual do QMessageBox ---
            
            # 1. Cria o objeto
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Atualização de Software")
            msg_box.setText(f"Uma nova versão do software está disponível!\n\nSua versão: {self.current_version}\nÚltima versão: {REMOTE_VERSION}\n\nO download do arquivo '{SOFTWARE_FILENAME}' será iniciado.")
            msg_box.setIcon(QMessageBox.Information) # Define o ícone
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            
            # 2. Aplica o estilo (AO OBJETO)
            msg_box.setStyleSheet(DARK_MESSAGE_BOX_STYLE) 
            
            # 3. Executa
            msg_box.exec()
            
            # --- FIM DA CORREÇÃO ---

            target_path = os.path.join(DOWNLOAD_DIR, SOFTWARE_FILENAME)
            self.start_download(REMOTE_DOWNLOAD_URL, target_path, self.status_version, self.btn_version)
        else:
            QMessageBox.information(self, "Informação", "Não há URL de download disponível no momento.")

    # Linha 551 (Substitua a função completa)
    def start_download(self, url, file_path, status_label, button):
        """Inicia o download unificado."""
        if self.downloader and self.downloader.isRunning():
            QMessageBox.warning(self, "Download em Andamento", "Um download já está em andamento. Por favor, aguarde.")
            return

        self.downloader = Downloader(url, file_path, self)
        
        # Conexão principal para o término do download
        self.downloader.finished.connect(lambda success, path: self.download_finished(success, path, status_label, button))
        
        # --- NOVO: Conexão e Controle do Progresso ---
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True) # Mostra a barra
        
        # Conecta o sinal de progresso (Assume-se que o Downloader tem progress_updated)
        if hasattr(self.downloader, 'progress_updated'):
            self.downloader.progress_updated.connect(self.progress_bar.setValue)
        
        # Oculta a barra quando o download terminar (sucesso ou falha)
        self.downloader.finished.connect(lambda: self.progress_bar.setVisible(False)) 
        
        # Garante que os botões não sejam clicáveis durante o download
        self.btn_version.setEnabled(False)
        self.btn_yolo.setEnabled(False)
        
        self.set_status(status_label, "Baixando...", "#f59e0b")
        
        self.downloader.start()

    def download_finished(self, success, file_path, status_label, button):
        """
        Chamado quando o download (em thread) é concluído.
        Inicia a reinicialização automática se for o software.
        """
        if success:
            filename = os.path.basename(file_path)
            
            # --- LÓGICA PARA O MODELO YOLO (best.pt) ---
            if filename == TARGET_FILENAME:
                # Atualiza o status do YOLO na UI
                self.check_status() 
                self.set_status(status_label, "Baixado", "#3b82f6")
                button.setEnabled(False)
                
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Modelo Atualizado")
                msg_box.setText(f"O modelo {filename} foi baixado com sucesso para a pasta SVA.")
                msg_box.setIcon(QMessageBox.Icon.Information)
                msg_box.setStyleSheet(DARK_MESSAGE_BOX_STYLE) 
                msg_box.exec()

            # --- LÓGICA PARA O SOFTWARE (.exe) ---
            elif filename == SOFTWARE_FILENAME:
                
                # VERIFICA SE ESTAMOS RODANDO COMO .EXE COMPILADO
                if not getattr(sys, 'frozen', False):
                    # Estamos rodando como .py, mostramos a msg antiga
                    msg_reiniciar = QMessageBox(self)
                    msg_reiniciar.setWindowTitle("Download Concluído")
                    msg_reiniciar.setText(f"O novo arquivo '{filename}' foi baixado na pasta SVA.\n\n"
                                          "(Modo .py) Por favor, feche o script e execute o novo arquivo manualmente.")
                    msg_reiniciar.setIcon(QMessageBox.Icon.Information)
                    # --- CORREÇÃO: Adiciona o estilo escuro ---
                    msg_reiniciar.setStyleSheet("""
                        QMessageBox { background-color: #374151; }
                        QLabel { color: white; }
                        QPushButton { background-color: #4b5563; color: white; border: none; padding: 6px 12px; border-radius: 5px; }
                        QPushButton:hover { background-color: #6b7280; }
                    """)
                    msg_reiniciar.exec()
                    self.set_status(status_label, "Baixado", "#3b82f6")
                    button.setEnabled(False)
                    return

                # --- ESTAMOS RODANDO COMO .EXE, EXECUTA O REINICIO AUTOMÁTICO ---
                # Linha 612 (Dentro do bloco 'elif filename == SOFTWARE_FILENAME:')

                # --- ESTAMOS RODANDO COMO .EXE, EXECUTA O REINICIO AUTOMÁTICO ---
                try:
                    old_exe_path = sys.executable
                    new_exe_path = file_path # Este é o caminho completo do download
                    
                    updater_path = self.create_updater_script(old_exe_path, new_exe_path)
                    
                    if updater_path:
                        msg_restarting = QMessageBox.information(self, "Reiniciando...", 
                                                "Download concluído. O SVA será reiniciado para aplicar a atualização.")
                        msg_restarting.setStyleSheet(DARK_MESSAGE_BOX_STYLE)
                        msg_restarting.exec()

                        if self.parent():
                            self.parent().close()
                        else:
                            sys.exit(0) # Força a saída
                    else:
                        raise Exception("Falha ao criar script de update.")
                        
                except Exception as e:
                    # Este erro é o FileNotFoundError que você está vendo
                    print(f"Erro ao tentar reiniciar: {e}")
                    msg_error = QMessageBox.critical(self, "Erro na Atualização", 
                                         f"Falha ao iniciar o processo de reinicialização automática.\n\n"
                                         f"Por favor, feche o programa e execute manualmente o novo arquivo baixado em:\n{file_path}")
                    msg_error.setStyleSheet(DARK_MESSAGE_BOX_STYLE)
                    msg_error.exec()
        else:
            # O download falhou
            msg_fail = QMessageBox.critical(self, "Erro de Download", f"Falha ao baixar o arquivo de {file_path}.")
            self.set_status(status_label, "Falha", "#ef4444")
            button.setEnabled(True)
            # --- CORREÇÃO: Adiciona o estilo escuro ---
            msg_fail.setStyleSheet(DARK_MESSAGE_BOX_STYLE)
            msg_fail.exec()
    
    # (Esta função deve estar dentro da classe UpdateDialog)
    def create_updater_script(self, old_exe_path, new_exe_path):
        """
        Cria um script .bat no diretório base para lidar com a 
        substituição do executável.
        """
        updater_path = os.path.join(BASE_DIR, "update_sva.bat")
        
        # Conteúdo do script .bat
        # %1 = Caminho do .exe antigo (ex: C:\App\SVA.exe)
        # %2 = Caminho do .exe novo (ex: C:\App\SVA\SVA_new.exe)
        
        # Dentro do create_updater_script (Linha 648)
        script_content = f"""@echo off
echo SVA Updater - Aguarde...

:: Espera 3 segundos para o SVA principal fechar
timeout /t 3 /nobreak > nul

:: Deleta o executavel antigo (que acabou de fechar)
echo Removendo versao antiga...
del "{old_exe_path}"

:: Move o novo executavel (da pasta SVA) para o local do antigo
echo Instalando nova versao...
move "{new_exe_path}" "{old_exe_path}"

:: Inicia o novo .exe
echo Iniciando SVA...
start "" "{old_exe_path}"

:: Auto-deleta este script
(goto) 2>nul & del "%~f0"
"""
        try:
            with open(updater_path, "w", encoding="utf-8") as f:
                f.write(script_content)
            return updater_path
        except Exception as e:
            print(f"Erro ao criar script de update: {e}")
            return None
        
    def download_new_yolo(self):
        """Inicia o download do novo modelo YOLO (best.pt) do GitHub."""
        
        # 1. Busca a URL do Asset do best.pt (Usando a API de Releases)
        yolo_asset_url = get_yolo_asset_url(GITHUB_RELEASES_API_URL) # CORREÇÃO: Chamada para a função renomeada
        
        if not yolo_asset_url:
            msg=QMessageBox.critical(self, "Erro de Download", 
                                 "Não foi possível encontrar a URL do arquivo best.pt na Release mais recente. "
                                 "Verifique se o token é válido e se o arquivo 'best.pt' foi anexado como Asset na Release do repositório.")
            msg.setStyleSheet(DARK_MESSAGE_BOX_STYLE)
            msg.exec()
            return

        # 2. Define o caminho de salvamento (CORREÇÃO: usa DOWNLOAD_DIR)
        # (A pasta já foi criada no __init__)
        target_path = os.path.join(DOWNLOAD_DIR, TARGET_FILENAME)
        
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Atualização de Modelo")
        msg_box.setText(f"Deseja baixar a versão mais recente do modelo YOLO ({TARGET_FILENAME})?")
        
        msg_box.setStyleSheet(DARK_MESSAGE_BOX_STYLE) 
        msg_box.exec()
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if msg_box.exec() == QMessageBox.StandardButton.Yes:
            
            # 3. Inicia o download usando a URL do Asset
            self.start_download(yolo_asset_url, target_path, self.status_yolo, self.btn_yolo)

# ... (Restante do código original segue aqui)
import base64

def resource_path(relative_path):
    """ Obtém o caminho absoluto para o recurso, funciona para dev e para PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

class DownloadWorker(QObject):
    """Worker para baixar arquivos em uma thread separada."""
    progress = Signal(int)
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, url, save_path, parent=None):
        super().__init__()
        self.url = url
        self.save_path = save_path
        self._is_running = True
    # Dentro da classe UpdateDialog (por volta da Linha 270)

    def run(self):
        """Executa o download usando requests para lidar com a confirmação do Google Drive."""
        try:
            os.makedirs(os.path.dirname(self.save_path), exist_ok=True)

            # Extrai o ID do arquivo da URL fornecida
            file_id = self.url.split('/d/')[1].split('/')[0] if '/d/' in self.url else self.url
            URL = "https://docs.google.com/uc?export=download"

            # Inicia uma sessão para manter os cookies
            session = requests.Session()
            
            # Primeira requisição para obter o cookie de confirmação
            response = session.get(URL, params={'id': file_id}, stream=True)
            token = self.get_confirm_token(response)

            # Se um token for encontrado, faz uma segunda requisição com ele
            if token:
                params = {'id': file_id, 'confirm': token}
                response = session.get(URL, params=params, stream=True)

            total_size = int(response.headers.get('content-length', 0))
            with open(self.save_path, 'wb') as f:
                downloaded_size = 0
                for data in response.iter_content(chunk_size=32768): # Baixa em pedaços (chunks)
                    if not self._is_running:
                        self.error.emit("Download cancelado.")
                        return
                    f.write(data)
                    downloaded_size += len(data)
                    if total_size > 0: self.progress.emit(int(100 * downloaded_size / total_size))
            self.finished.emit(self.save_path)
        except Exception as e:
            self.error.emit(f"Falha no download do modelo. Verifique sua conexão e o link do arquivo.\nDetalhe: {e}")

    def get_confirm_token(self, response):
        """Extrai o token de confirmação dos cookies da resposta do Google."""
        for key, value in response.cookies.items():
            if key.startswith('download_warning'):
                return value
        return None

    def stop(self):
        """Permite que o download seja interrompido."""
        self._is_running = False

class SplashScreen(QWidget):
    """Tela de carregamento simples com a logo."""
    def __init__(self):
        super().__init__()
        self.setFixedSize(500, 400)
        self.setWindowFlags(Qt.SplashScreen | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        main_layout = QVBoxLayout(self)
        self.setLayout(main_layout)
        main_layout.addStretch()

        shadow_effect = QGraphicsDropShadowEffect(self)
        shadow_effect.setBlurRadius(25)
        shadow_effect.setColor(QColor(0, 0, 0, 80))
        shadow_effect.setOffset(0, 3)

        self.logo_label = QLabel()
        self.logo_label.setGraphicsEffect(shadow_effect)
        logo_pixmap = QPixmap(resource_path("logo.png"))
        self.logo_label.setPixmap(logo_pixmap.scaled(300, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.logo_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.logo_label)

        self.title_label = QLabel("SEED VISION ANALYSER")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("color: white; font-size: 30px; font-weight: bold; background: transparent;")

        text_shadow = QGraphicsDropShadowEffect(self)
        text_shadow.setBlurRadius(10)
        text_shadow.setColor(QColor(0, 0, 0, 90))
        text_shadow.setOffset(1, 1)
        self.title_label.setGraphicsEffect(text_shadow)
        main_layout.addWidget(self.title_label)

        self.version_label = QLabel(f"By TSM Soluções Agrícolas - {CURRENT_VERSION}")
        self.version_label.setAlignment(Qt.AlignCenter)
        self.version_label.setStyleSheet("color: #cccccc; font-size: 15px; background: transparent; margin-top: -2px;")
        main_layout.addWidget(self.version_label)
        
        main_layout.addStretch()

class SpeedRulerWidget(QWidget):
    """Widget de régua customizado para controle de velocidade."""
    valueChanged = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 60)
        self.setFixedHeight(60)
        self.margin = 15  # Define a margem aqui (ex: 20 pixels)
        self.speeds = [0.10, 1.0, 5.0, 10.0]
        self.current_index = 1
        self.setMouseTracking(True)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#ffffff"))
        pen = QPen(QColor("#2e2e2e"), 2)
        painter.setPen(pen)
        line_y = self.height() // 2 - 15 # Ajusta a posição Y da linha
        painter.drawLine(self.margin, line_y, self.width() - self.margin, line_y)
        font = QFont("Segoe UI", 8)
        painter.setFont(font)
        num_speeds = len(self.speeds)
        for i, speed in enumerate(self.speeds):
            x_pos = self.margin + i * (self.width() - 2 * self.margin) / (num_speeds - 1)
            if i == self.current_index:
                painter.setBrush(QColor("#3b82f6"))
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(int(x_pos) - 6, line_y - 6, 12, 12)
                painter.setPen(QColor("#1e40af"))
                painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
            else:
                painter.setBrush(QColor("#cbd5e1"))
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(int(x_pos) - 4, line_y - 4, 8, 8)
                painter.setPen(QColor("#475569"))
                painter.setFont(QFont("Segoe UI", 8))
            painter.drawText(int(x_pos) - 15, line_y + 15, 30, 15, Qt.AlignCenter, f"{speed}x")

    def mousePressEvent(self, event):
        # CORREÇÃO: Muda de event.pos().x() para event.position().x()
        self.update_value(event.position().x())

    def update_value(self, x_pos):
        num_speeds = len(self.speeds)
        click_pos_ratio = (x_pos - 10) / (self.width() - 20)
        new_index = round(click_pos_ratio * (num_speeds - 1))
        new_index = max(0, min(num_speeds - 1, new_index))
        if new_index != self.current_index:
            self.current_index = new_index
            self.valueChanged.emit(self.current_index)
            self.update()

    def setValue(self, index):
        if 0 <= index < len(self.speeds) and index != self.current_index:
            self.current_index = index
            self.valueChanged.emit(self.current_index)
            self.update()

class ClickableLabel(QLabel):
    """QLabel que detecta cliques do mouse."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = None

    def mousePressEvent(self, event: QMouseEvent):
        if self.parent_app is not None and hasattr(self.parent_app, 'video_label_clicked'):
            self.parent_app.video_label_clicked(event)

class HelpWindow(QDialog):
    """Janela de ajuda com instruções detalhadas."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ajuda - SVA")
        self.setStyleSheet("background-color: white;")
        self.setMinimumSize(800, 600)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(25, 20, 25, 20) # Adiciona margens
        layout.setSpacing(15)

        title = QLabel("📚 Guia de Uso - Contador de Sementes")
        title.setAlignment(Qt.AlignLeft) # Alinha o título à esquerda
        title_font = QFont("Segoe UI", 20, QFont.Bold)
        title.setFont(title_font)
        title.setStyleSheet("color: #1e40af; padding-bottom: 5px; border-bottom: 2px solid #e2e8f0;")
        layout.addWidget(title)

        help_content = '''
        <div style="font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; text-align: left;">
            <h2 style="color: #1e40af; border-bottom: 2px solid #3b82f6;">▶️ 1. Início e Configuração do Ensaio</h2>
            <p><strong>Configuração (Janela Inicial):</strong></p>
            <ul>
                <li><strong>E-mail e Nome do Teste:</strong> Preencha para identificação e salvamento.</li>
                <li><strong>Parâmetros:</strong> Insira o Tipo de Semente, Delineamento (Tratamento), Velocidade (km/h) e outros dados do seu ensaio.</li>
                <li><strong>Projetos Recentes:</strong> Use a tabela ou o botão "Buscar Projeto" para carregar ensaios salvos anteriormente.</li>
            </ul>

            <h2 style="color: #1e40af; border-bottom: 2px solid #3b82f6;">⚙️ 2. Preparação e Calibração</h2>
            <p><strong>Aba Analisar (Passos Iniciais):</strong></p>
            <ol>
                <li><strong>Carregar Vídeo:</strong> Clique em "📂 Selecionar Vídeo".</li>
                <li><strong>Ajuste de Parâmetros:</strong> 
                    <ul>
                        <li>Selecione <strong>Semente</strong>, <strong>Deliniamento</strong> e <strong>Velocidade</strong> nos combos.</li>
                        <li>Preencha a <strong>Qtd. de Sementes/m</strong> e <strong>Esp. de Fileiras</strong>.</li>
                        <li>(Opcional) Ajuste o valor de <strong>"Nº Sementes"</strong> para configurar o Salvamento Automático.</li>
                    </ul>
                </li>
                <li><strong>Calibração:</strong> O valor **Pixels/cm** é crucial.
                    <ul>
                        <li>Clique em **"Calibrar"** para ir à aba de calibração.</li>
                        <li>Na imagem, clique em **2 pontos** de uma trena ou régua.</li>
                        <li>Digite a <strong>Distância real (cm)</strong> e clique em <strong>"Calcular e Aplicar"</strong>.</li>
                    </ul>
                </li>
            </ol>
            
            <h2 style="color: #1e40af; border-bottom: 2px solid #3b82f6;">🔍 3. Seleção do Método de Análise</h2>
            <p>Escolha o melhor método para as condições do seu vídeo:</p>
            <ul>
                <li><strong>YOLO:</strong> Usa apenas o modelo de Deep Learning (IA). Ideal para sementes com pouco contraste ou condições variáveis. Requer o modelo treinado (best.pt) na pasta SVA.</li>
                <li><strong>HSV (Cor):</strong> Método rápido baseado em cor e tamanho (configurado internamente para Soja). Ideal para sementes com bom contraste de cor.</li>
                <li><strong>Combinado (YOLO + HSV):</strong> Usa o YOLO para localizar e o HSV para refinar, classificando sementes duplas com mais precisão. Oferece maior robustez.</li>
            </ul>

            <h2 style="color: #1e40af; border-bottom: 2px solid #3b82f6;">▶️ 4. Execução e Ajustes Visuais</h2>
            <ol>
                <li><strong>Controle:</strong> Use "▶️ Iniciar" / "⏸️ Pausar" para controlar o vídeo. "🔄 Retornar" zera a contagem e volta ao início.</li>
                <li><strong>Velocidade:</strong> Ajuste a régua de velocidade para ver a análise mais rápido (10x) ou em câmera lenta (0.1x).</li>
                <li><strong>Ajustes Visuais:</strong> Use os sliders de **Temperatura (K)** e **Saturação (%)** para melhorar o contraste da imagem se a iluminação do vídeo for ruim. Estes ajustes são apenas visuais e não alteram a detecção original (exceto a saturação que pode ajudar o método HSV).</li>
                <li><strong>Salvar:</strong> Clique em "💾 Salvar" para salvar o resultado da análise atual na aba "Relatórios" e continuar a análise do vídeo.</li>
            </ol>
            
            <h2 style="color: #1e40af; border-bottom: 2px solid #3b82f6;">📊 5. Relatórios, Estatísticas e Plantabilidade</h2>
            <ul>
                <li><strong>Aba Relatórios:</strong> Exibe o histórico de todas as análises salvas. Cada cartão permite:
                    <ul>
                        <li>Visualizar estatísticas detalhadas e o histograma de espaçamento.</li>
                        <li>Adicionar **Observações** manuais.</li>
                        <li>Gerar um **Relatório PDF** individual com gráficos e discussão.</li>
                    </ul>
                </li>
                <li><strong>Aba Estatística (ANOVA):</strong> Permite importar dados via CSV ou usar análises salvas para executar:
                    <ul>
                        <li>Cálculo de Estatísticas Descritivas (Média, CV, etc.)</li>
                        <li>Teste de Comparação Múltipla (**Tukey HSD**), com letras de significância.</li>
                        <li>Geração de **Gráfico de Interação** e salvamento do resultado completo em PDF.</li>
                    </ul>
                </li>
                <li><strong>Aba Plantabilidade:</strong> Calculadora para determinar o espaçamento ideal e a taxa de sementes/m, com base em: População, Espaçamento de Fileiras e Taxa de Emergência.</li>
            </ul>
            
            <h2 style="color: #1e40af; border-bottom: 2px solid #3b82f6;">⚠️ 6. Interpretação do Espaçamento</h2>
            <p>Os contadores e o gráfico de espaçamento usam as seguintes cores e limiares (baseados no Espaçamento Ideal):</p>
            <ul>
                <li><strong style="color: #059669;">Aceitável (Verde):</strong> Espaçamento entre 0,5x e 1,5x o Espaçamento Ideal.</li>
                <li><strong style="color: #dc2626;">Falha (Vermelho):</strong> Espaçamento maior ou igual a 1,5x o Espaçamento Ideal.</li>
                <li><strong style="color: #7c3aed;">Múltipla (Roxo):</strong> Espaçamento menor ou igual a 0,5x o Espaçamento Ideal.</li>
            </ul>
        </div>'''
        
        # ... (O restante da função setup_ui da HelpWindow continua)
        help_text = QTextEdit()
        help_text.setHtml(help_content)
        help_text.setReadOnly(True)
        help_text.setStyleSheet("border: none; background-color: transparent;") # Remove bordas
        layout.addWidget(help_text) # Adiciona diretamente ao layout principal

        close_btn = QPushButton("✅ Fechar")
        close_btn.setStyleSheet("QPushButton { background-color: #3b82f6; color: white; border: none; padding: 10px 30px; border-radius: 6px; font-weight: bold; font-size: 12px; } QPushButton:hover { background-color: #2563eb; }")
        close_btn.clicked.connect(self.accept)
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        self.setLayout(layout)

class SetupDialog(QDialog):
    """Janela de configuração inicial para inserir os dados do ensaio."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuração Inicial do Ensaio")
        self.setWindowIcon(QIcon(resource_path("icone.ico")))
        self.setMinimumSize(950, 680) # Diminui a altura e aumenta a largura
        self.setup_ui()
        # --- NOVO: Carrega a lista de projetos ao iniciar ---
        self.populate_projects_list()
        # Conecta o clique na célula da tabela à função de carregar
        self.projects_list.itemClicked.connect(self.load_selected_project)

    def setup_ui(self): # type: ignore
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # Função auxiliar para criar os labels (MOVIDA PARA CIMA)
        def create_label_widget(title, description):
            widget = QWidget()
            layout = QVBoxLayout(widget)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            title_label = QLabel(title)
            desc_label = QLabel(description)
            desc_label.setObjectName("descriptionLabel")
            layout.addWidget(title_label)
            layout.addWidget(desc_label)
            return widget

        # Lado Esquerdo: Logo e Título
        left_layout = QVBoxLayout()
        left_layout.setSpacing(15) # Diminui o espaçamento entre os itens do layout esquerdo
        left_layout.setAlignment(Qt.AlignCenter)
        
        logo_label = QLabel()
        logo_pixmap = QPixmap(resource_path("logo2.png"))
        logo_label.setPixmap(logo_pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo_label.setAlignment(Qt.AlignCenter)

        #title_label = QLabel(f"versão: {MainWindow.CURRENT_VERSION}")
        #title_label.setAlignment(Qt.AlignCenter)
        #title_label.setObjectName("SetupTitle")
        
        left_layout.addWidget(logo_label)
        #left_layout.addWidget(title_label)

        # --- NOVO: Adiciona o texto de versão abaixo do título ---
        version_text = f"Software de Visão Computacional {CURRENT_VERSION}\nBy TSM Soluções Agrícolas"
        version_label = QLabel(version_text)
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setObjectName("versionLabel")
        left_layout.addWidget(version_label)

        # --- NOVO: Caixa de texto com instruções resumidas ---
        instructions_text = QTextEdit()
        instructions_text.setReadOnly(True)
        instructions_text.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff) # Remove a barra de rolagem vertical
        instructions_text.setHtml(
            """
            <div style="font-family: 'Segoe UI', Sofia, sans-serif; font-size: 9pt; color:  #64748b; text-align: left;">
                <p><strong>Bem-vindo ao Seed Vision Analyser!</strong></p>
                <p>Este software utiliza visão computacional para analisar a qualidade da distribuição de sementes.</p>
                <p style="font-size: 9pt; color: #64748b;"><strong>Instruções Rápidas:</strong></p>
                <ul style="padding-left: 15px; font-size: 9pt; color: #475569;">
                    <li>Preencha os dados do ensaio ou carregue um projeto.</li>
                    <li>Clique em "Iniciar" para ir à tela de análise.</li>
                    <li>Na tela de análise, carregue um vídeo e calibre o sistema.</li>
                </ul>
                <p style="font-size: 9pt; color: #64748b;"><strong>Funcionalidades:</strong></p>
                <ul style="padding-left: 15px; font-size: 9pt; color: #475569;">
                    <li>Visão computacional de sementes em esteira de plantabilidade.</li>
                    <li>Gerar relatórios precisos e gráficos prontos.</li>
                    <li>Gerar estatística diretamente da interface.</li>
                </ul>
                <p style="font-size: 9pt; color:  #64748b margin-top: 15px;">Desenvolvido por: <strong>Talisson Sáteles Matos</strong><br/>
                Instituição: <strong>Universidade Federal de Mato Grosso</strong></p>
            </div>
            """
        )
        instructions_text.setStyleSheet("background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px;")
        left_layout.addWidget(instructions_text)

        # O stretch foi removido para permitir que a caixa de texto se expanda

        main_layout.addLayout(left_layout, 2)

        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(separator)

        # Lado Direito: Formulário
        right_v_layout = QVBoxLayout()
        right_v_layout.setSpacing(15)

        # --- NOVO: Caixa de Identificação movida para o lado direito, acima dos parâmetros ---
        email_group = QGroupBox("Identificação do Usuário")
        email_grid = QGridLayout(email_group)
        email_grid.setVerticalSpacing(10)
        self.email_input = QLineEdit()
        email_grid.addWidget(create_label_widget("📧 <b>E-mail:</b>", "Para registro de atualizações e suporte."), 0, 0)
        email_grid.addWidget(self.email_input, 0, 1)
        email_grid.setColumnStretch(1, 2) # Mantém a largura da caixa de e-mail
        right_v_layout.addWidget(email_group)

        # Função auxiliar para criar os labels (mantida, pois é usada em outros lugares)
        def create_label_widget(title, description):
            widget = QWidget()
            layout = QVBoxLayout(widget)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            title_label = QLabel(title)
            desc_label = QLabel(description)
            desc_label.setObjectName("descriptionLabel")
            layout.addWidget(title_label)
            layout.addWidget(desc_label)
            return widget
        
        # Caixa de Parâmetros
        form_group = QGroupBox("Parâmetros do Ensaio")
        params_grid = QGridLayout(form_group)
        params_grid.setVerticalSpacing(15)
        
        # Campos com ícones restaurados
        self.test_name_input = QLineEdit()
        params_grid.addWidget(create_label_widget("📝 <b>Nome do Teste:</b>", "Nome único para o ensaio. Ex: T1 vs T2"), 0, 0)
        params_grid.addWidget(self.test_name_input, 0, 1)

        self.seed_type_input = QLineEdit()
        params_grid.addWidget(create_label_widget("🌱 <b>Tipo de Semente:</b>", "Cultura analisada. Ex: Soja, Milho"), 1, 0)
        params_grid.addWidget(self.seed_type_input, 1, 1)

        self.test_design_input = QLineEdit()
        params_grid.addWidget(create_label_widget("📋 <b>Delineamento do Teste:</b>", "Variável ou tratamento. Ex: Tratamento A"), 2, 0)
        params_grid.addWidget(self.test_design_input, 2, 1)
        
        self.speed_input = QLineEdit()
        params_grid.addWidget(create_label_widget("⚡ <b>Velocidade (km/h):</b>", "Velocidade de plantio. Ex: 5"), 3, 0)
        params_grid.addWidget(self.speed_input, 3, 1)

        params_grid.setColumnStretch(1, 1)
        right_v_layout.addWidget(form_group)
        right_v_layout.addStretch()

        # --- CORREÇÃO: Quadro de Projetos Recentes (agora sempre visível) ---
        self.projects_group = QGroupBox("Projetos Recentes") # Made instance variable
        self.projects_group.setObjectName("ProjectsGroup") # Adiciona um nome de objeto para estilização
        projects_layout = QVBoxLayout(self.projects_group)
        # --- ALTERAÇÃO: Usa QTableWidget para ter múltiplas colunas ---
        self.projects_list = QTableWidget()
        self.projects_list.setColumnCount(2)
        self.projects_list.setHorizontalHeaderLabels(["Nome do Projeto", "Data de Modificação"])
        self.projects_list.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.projects_list.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.projects_list.setShowGrid(False)
        self.projects_list.verticalHeader().setVisible(False)
        # ... (código anterior)

        self.projects_list.verticalHeader().setVisible(True)
        # self.projects_list.horizontalHeader().setStretchLastSection(False) # Não é necessário com o Stretch
        
        # --- NOVO AJUSTE DE LARGURA DA TABELA ---
        # 1. Coluna 0 ("Nome do Projeto") preenche todo o espaço restante
        self.projects_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch) 
        
        # 2. Coluna 1 ("Data de Modificação") se ajusta ao tamanho do conteúdo
        self.projects_list.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        # ------------------------------------------

        self.projects_list.setToolTip("Clique em um projeto para carregar seus dados.")
        self.projects_list.setMaximumHeight(150) # Define uma altura máxima para a lista
        # --- NOVO: Adiciona um estilo para a lista de projetos ---
        
        self.projects_list.setStyleSheet("""
            QTableWidget { border: 1px solid #e2e8f0; border-radius: 6px; background-color: white; color: black; }
            QTableWidget::item:selected { background-color: #dbeafe; color: #1e3a8a; }
            /* --- NOVO: Estilo para o conteúdo da tabela --- */
            QTableWidget::item { font-size: 9pt; padding: 3px; } 
            /* --- NOVO: Estilo para o cabeçalho da tabela --- */
            QHeaderView::section { font-size: 9pt; padding: 4px; }
        """)

        self.projects_list.setCursor(Qt.PointingHandCursor)
        projects_layout.addWidget(self.projects_list)
        
        # --- CORREÇÃO: Botão Buscar Projeto DENTRO da caixa de projetos ---
        # --- Botão Buscar Projeto DENTRO da caixa de projetos ---
        load_project_button_layout = QHBoxLayout()
        load_project_button_layout.addStretch()
        self.load_button = QPushButton("📂 Buscar Projeto")
        self.load_button.clicked.connect(self.load_project)
        self.load_button.setStyleSheet("QPushButton { background-color: #e2e8f0; color: #475569; padding: 4px 10px; font-size: 9pt; } QPushButton:hover { background-color: #cbd5e1; }")
        load_project_button_layout.addWidget(self.load_button)
        projects_layout.addLayout(load_project_button_layout)
        right_v_layout.addWidget(self.projects_group)
        # self.projects_group.setVisible(False) # Removido para que seja sempre visível

        # Botão "Iniciar Análise" (reposicionado)
        ok_button_layout = QHBoxLayout()
        ok_button_layout.addStretch()
        self.ok_button = QPushButton("✅ Iniciar")
        self.ok_button.setFixedWidth(150) # Diminui a largura do botão
        self.ok_button.clicked.connect(self.accept)
        ok_button_layout.addWidget(self.ok_button)
        right_v_layout.addLayout(ok_button_layout)
        # --- CORREÇÃO: Ajusta a proporção do layout principal ---
        main_layout.addLayout(right_v_layout, 3) # Proporção 3 para o lado direito (mais espaço)

        # Linha 1279 (Substitua todo o bloco de estilo setStyleSheet)
        # Estilo
        self.setStyleSheet("""
            QDialog { background-color: #f8fafc; }
            QGroupBox {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                margin-top: 10px;
                padding: 15px;
            }
            QGroupBox::title {
                color: #1e40af; /* Título padrão AZUL */
                font-weight: bold;
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                left: 10px;
            }
            QGroupBox#ProjectsGroup::title {
                font-size: 9pt; /* Tamanho de fonte menor para "Projetos Recentes" */
                color: #1e40af; /* Garante que Projetos Recentes seja AZUL */
            }
            QLabel { 
                color: black; 
                font-size: 8pt;
                font-weight: normal; 
            }
            QLabel#descriptionLabel {
                color: #64748b;
                font-size: 8pt;
            }
            QLabel#SetupTitle {
                font-size: 24px;
                font-weight: bold;
                color: black;
                margin-bottom: 10px
            }
            QLabel#versionLabel {
                color: #64748b;
                font-size: 9pt;
                margin-top: -5px;
            }
            QLineEdit {
                color: black; 
                background-color: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                padding: 5px;
                font-size: 9pt;
            }
            QLineEdit:focus { border: 1px solid #3b82f6; }
            QPushButton {
                background-color: #16a34a; 
                color: white;
                padding: 6px 12px; 
                font-size: 10pt;
                font-weight: bold; 
                border-radius: 5px;
                border: none;
            }
            QPushButton:hover { background-color: #15803d; }
            
            /* --- CORREÇÃO DA TABELA DE PROJETOS --- */
            QTableWidget {
                border: 1px solid #e2e8f0;
            }
            QHeaderView::section {
                /* CORREÇÃO: Fundo da célula AZUL */
                background-color: #f0f2f7; 
                /* CORREÇÃO: Texto do cabeçalho BRANCO */
                color: black; 
                border: 1px solid #f0f2f7;
                font-size: 9pt 
                padding: 4px;
                font-weight: bold;
            }
            QTableWidget::item:selected {
                background-color: #dbeafe;
                color: #1e3a8a;
            }
        """)
    def get_data(self):
        """Retorna os dados preenchidos no formulário."""
        if not all([self.email_input.text(), self.test_name_input.text(), 
                    self.seed_type_input.text(), self.test_design_input.text(), 
                    self.speed_input.text()]):
            QMessageBox.warning(self, "Campos Obrigatórios", "Por favor, preencha todos os campos do formulário.")
            return None

        return {
            "user_email": self.email_input.text(),
            "test_name": self.test_name_input.text(),
            "seed_type": self.seed_type_input.text(),
            "test_design": self.test_design_input.text(),
            "speed": self.speed_input.text(),
            "tube_type": "N/A", 
            "seeds_per_m": "0",
            "row_spacing": "0"
        }

    def accept(self):
        if self.get_data() is not None:
            super().accept()

    def load_project(self): # Esta função agora é para o botão "Buscar Projeto"
        """Abre um diálogo para carregar um arquivo de projeto (.json)."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Carregar Projeto", "", "Projeto JSON (*.json)")
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    project_data = json.load(f)

                # Preenche os campos da SetupDialog
                self.set_data(project_data)

                # Armazena os dados do projeto carregado para a MainWindow acessar
                self.loaded_project_data = project_data

                msg = QMessageBox.information(self, "Sucesso", f"Projeto '{project_data.get('test_name', 'Sem Nome')}' carregado com sucesso. Clique em 'Iniciar Análise' para continuar.")
                msg.setStyleSheet(DARK_MESSAGE_BOX_STYLE)
                msg.exec()

            except Exception as e:
                msg=QMessageBox.critical(self, "Erro ao Carregar", f"Não foi possível carregar o projeto:\n{e}")
                msg.setStyleSheet(DARK_MESSAGE_BOX_STYLE)
                msg.exec()

    def get_loaded_project_data(self):
        """Retorna os dados do projeto carregado, se houver."""
        return getattr(self, 'loaded_project_data', None)

    def set_data(self, data):
        """Preenche os campos do formulário com dados fornecidos."""
        self.email_input.setText(data.get("user_email", ""))
        self.test_name_input.setText(data.get("test_name", ""))
        self.seed_type_input.setText(data.get("seed_type", ""))
        self.test_design_input.setText(data.get("test_design", ""))
        self.speed_input.setText(data.get("speed", ""))

    def populate_projects_list(self):
        """Busca projetos na pasta 'Meus Projetos' e os exibe na lista."""
        self.projects_list.setRowCount(0) # Limpa a tabela
        
        # CORREÇÃO: Usa o PROJECTS_DIR e garante que ele exista
        os.makedirs(PROJECTS_DIR, exist_ok=True)
        
        if not os.path.isdir(PROJECTS_DIR):
            return

        project_files = [f for f in os.listdir(PROJECTS_DIR) if f.endswith('.json')]
        if not project_files:
            return

        # Prepara os dados para ordenação por data
        projects_with_dates = []
        for filename in project_files:
            file_path = os.path.join(PROJECTS_DIR, filename)
            try:
                mod_time = os.path.getmtime(file_path)
                projects_with_dates.append((filename, mod_time))
            except OSError:
                continue

        # Ordena os projetos do mais recente para o mais antigo
        projects_with_dates.sort(key=lambda x: x[1], reverse=True)

        self.projects_list.setRowCount(len(projects_with_dates))
        for row, (filename, mod_time) in enumerate(projects_with_dates):
            date_str = datetime.fromtimestamp(mod_time).strftime('%d/%m/%Y %H:%M')
            
            name_item = QTableWidgetItem(filename)
            date_item = QTableWidgetItem(date_str)
            date_item.setTextAlignment(Qt.AlignCenter)

            self.projects_list.setItem(row, 0, name_item)
            self.projects_list.setItem(row, 1, date_item)

    def load_selected_project(self, item):
        """Carrega os dados de um projeto selecionado na lista."""
        # Para QTableWidget, o item clicado é uma célula. Pegamos o item da primeira coluna.
        filename_item = self.projects_list.item(item.row(), 0)
        if not filename_item:
            return
        filename = filename_item.text()
        
        # CORREÇÃO: Usa o PROJECTS_DIR
        file_path = os.path.join(PROJECTS_DIR, filename)

        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    project_data = json.load(f)
                self.set_data(project_data)
            except Exception as e:
                msg=QMessageBox.critical(self, "Erro", f"Não foi possível ler o arquivo do projeto:\n{e}")
                msg.setStyleSheet(DARK_MESSAGE_BOX_STYLE)
                msg.exec()

class AnalysisCard(QGroupBox):
    """Cartão compacto para exibir resultados de uma análise."""
    close_requested = Signal(int)
    notes_updated = Signal(int, str)
    def __init__(self, analysis_data, card_id, version_string):
        super().__init__()
        self.analysis_data = analysis_data
        self.card_id = card_id
        self.version_string = version_string
        self.setup_ui()

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(15)
        left_panel = QVBoxLayout()
        left_panel.setSpacing(10)
        right_panel = QVBoxLayout()
        right_panel.setSpacing(8)
        header_grid = QGridLayout()
        header_grid.setContentsMargins(0, 0, 0, 5)
        header_grid.setColumnStretch(0, 1)
        header_grid.setColumnStretch(1, 0)
        video_source = self.analysis_data.get('video_path', 'Análise')
        title_text = f"🎬 {os.path.basename(str(video_source))}"
        title_label = QLabel(title_text)
        title_font = QFont("Segoe UI", 11, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #1e40af; margin-bottom: 3px;")
        header_grid.addWidget(title_label, 0, 0)
        datetime_str = self.analysis_data.get('datetime', datetime.now().strftime("%d/%m/%Y %H:%M"))
        datetime_label = QLabel(f"🕒 {datetime_str}")
        datetime_label.setStyleSheet("color: #64748b; font-size: 12px;")
        header_grid.addWidget(datetime_label, 1, 0)
        seed_type = self.analysis_data.get('seed_type', 'Soja')
        speed = self.analysis_data.get('planting_speed', '3')
        seeds_per_m = self.analysis_data.get('seeds_per_meter', '14')
        params_label = QLabel(f"🌱 {seed_type} | ⚡ {speed}km/h | 📏 {seeds_per_m}/m")
        params_label.setStyleSheet("color: #1e40af; font-size: 10px; font-weight: bold;")
        header_grid.addWidget(params_label, 2, 0)
        duration = self.analysis_data.get('duration', '00:00')
        total_seeds = self.analysis_data.get('total_seeds', 0)
        info_label = QLabel(f"⏱️ Duração: {duration}")
        info_label.setStyleSheet("color: #64748b; font-size: 12px;")
        info_label.setAlignment(Qt.AlignRight)
        header_grid.addWidget(info_label, 0, 1)
        total_label = QLabel(f"🌾 Total de Sementes: <b>{total_seeds}</b>")
        total_label.setStyleSheet("color: #1e40af; font-size: 14px;")
        total_label.setAlignment(Qt.AlignRight)
        header_grid.addWidget(total_label, 1, 1)
        try:
            seeds_per_meter_val = float(self.analysis_data.get('seeds_per_meter', 0))
            ideal_spacing_cm = 100.0 / seeds_per_meter_val if seeds_per_meter_val > 0 else 0
        except (ValueError, TypeError):
            ideal_spacing_cm = 0
        if ideal_spacing_cm > 0:
            ideal_spacing_label = QLabel(f"<b>Espaçamento Ideal: {ideal_spacing_cm:.1f} cm</b>")
            ideal_spacing_label.setStyleSheet("color: #059669; font-size: 11px;")
            ideal_spacing_label.setAlignment(Qt.AlignRight)
            header_grid.addWidget(ideal_spacing_label, 2, 1)
        right_panel.addLayout(header_grid)
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("color: #e2e8f0;")
        right_panel.addWidget(separator)
        aceitavel = self.analysis_data.get('aceitavel', 0)
        falha = self.analysis_data.get('falha', 0)
        multipla = self.analysis_data.get('multipla', 0)
        total = aceitavel + falha + multipla
        aceitavel_pct = (aceitavel / total * 100) if total > 0 else 0
        falha_pct = (falha / total * 100) if total > 0 else 0
        multipla_pct = (multipla / total * 100) if total > 0 else 0
        multipla_threshold = 0.5 * ideal_spacing_cm
        falha_threshold = 1.5 * ideal_spacing_cm
        stats_data = [
            ("✅ Aceitável", f"{multipla_threshold:.1f} a {falha_threshold:.1f} cm", aceitavel, aceitavel_pct, "#059669"),
            ("❌ Falha", f"&gt; {falha_threshold:.1f} cm", falha, falha_pct, "#dc2626"),
            ("🔄 Múltipla", f"&lt; {multipla_threshold:.1f} cm", multipla, multipla_pct, "#7c3aed")
        ]
        stats_v_layout = QVBoxLayout()
        stats_v_layout.setSpacing(4)
        for i, (label_text, range_text, count, pct, color) in enumerate(stats_data):
            row_layout = QHBoxLayout()
            if ideal_spacing_cm > 0:
                category_label = QLabel(f"{label_text} <span style='color:#475569; font-size:9px; font-weight:normal;'>({range_text})</span>")
            else:
                category_label = QLabel(label_text)
            category_label.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 12px;")
            category_label.setWordWrap(True)
            row_layout.addWidget(category_label)
            value_label = QLabel(f"{count} ({pct:.1f}%)")
            value_label.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold;")
            value_label.setAlignment(Qt.AlignRight)
            row_layout.addWidget(value_label)
            stats_v_layout.addLayout(row_layout)
        right_panel.addLayout(stats_v_layout)
        stats_table_group = self.create_statistics_table()
        right_panel.addWidget(stats_table_group)
        right_panel.addSpacing(10)
        results_group = self.create_results_discussion_box()
        right_panel.addWidget(results_group)
        right_panel.addStretch()
        notes_group = self.create_notes_box()
        right_panel.addWidget(notes_group)
        right_panel.addStretch()
        bottom_buttons_layout = QHBoxLayout()
        self.close_card_btn = QPushButton("❌ Fechar")
        self.close_card_btn.setStyleSheet("QPushButton { background-color: #ef4444; color: white; } QPushButton:hover { background-color: #dc2626; }")
        self.close_card_btn.clicked.connect(lambda: self.close_requested.emit(self.card_id))
        bottom_buttons_layout.addWidget(self.close_card_btn)
        self.pdf_button = QPushButton("📄 Baixar Relatório PDF")
        self.pdf_button.setStyleSheet("QPushButton { background-color: #4b5563; color: white; } QPushButton:hover { background-color: #374151; }")
        self.pdf_button.clicked.connect(self.generate_pdf_report)
        bottom_buttons_layout.addWidget(self.pdf_button)
        right_panel.addLayout(bottom_buttons_layout)
        self.create_spacing_histogram()
        histogram_group = QGroupBox("Histograma de Espaçamento")
        histogram_layout = QVBoxLayout(histogram_group)
        histogram_layout.addWidget(self.histogram_label)
        left_panel.addWidget(histogram_group)
        self.create_compact_chart()
        boxplot_group = QGroupBox("Boxplot de Espaçamento")
        boxplot_layout = QVBoxLayout(boxplot_group)
        boxplot_layout.addWidget(self.chart_label)
        left_panel.addWidget(boxplot_group)
        main_layout.addLayout(right_panel, 1)
        main_layout.addLayout(left_panel, 1)
        self.setLayout(main_layout)
        self.setStyleSheet("QGroupBox { border: 2px solid #e2e8f0; border-radius: 12px; margin: 3px; padding: 8px; background-color: #ffffff; } QGroupBox:hover { border-color: #9ca3af; background-color: #f8fafc; }")
        self.setFixedSize(1220, 820)

    def create_spacing_histogram(self):
        spacing_data_cm = [d['spacing_cm'] for d in self.analysis_data.get('spacing_data', [])]
        try:
            seeds_per_meter_val = float(str(self.analysis_data.get('seeds_per_meter', 0)).replace(',', '.'))
            ideal_spacing_cm = 100.0 / seeds_per_meter_val if seeds_per_meter_val > 0 else 0
        except (ValueError, TypeError):
            ideal_spacing_cm = 0
        fig, ax = plt.subplots(figsize=(6, 2.5))
        fig.patch.set_facecolor('white')
        if spacing_data_cm and ideal_spacing_cm > 0:
            multipla_threshold = 0.5 * ideal_spacing_cm
            falha_threshold = 1.5 * ideal_spacing_cm
            ax.axvspan(0, multipla_threshold, facecolor='#f3e8ff', alpha=0.7, zorder=0)
            ax.axvspan(multipla_threshold, falha_threshold, facecolor='#dcfce7', alpha=0.7, zorder=0)
            max_spacing = max(spacing_data_cm) if spacing_data_cm else falha_threshold
            ax.axvspan(falha_threshold, max_spacing * 1.1, facecolor='#fee2e2', alpha=0.7, zorder=0)
            n, bins, patches = ax.hist(spacing_data_cm, bins=25, facecolor='none', edgecolor='black', linewidth=0.5, alpha=0.9)
            for i in range(len(patches)):
                bin_center = (bins[i] + bins[i+1]) / 2
                if bin_center <= multipla_threshold:
                    patches[i].set_edgecolor('#7c3aed')
                    patches[i].set_linewidth(1.2)
                elif bin_center >= falha_threshold:
                    patches[i].set_edgecolor('#dc2626')
                    patches[i].set_linewidth(1.2)
                else:
                    patches[i].set_edgecolor('#059669')
                    patches[i].set_linewidth(1.2)
            ax.set_ylabel("Frequência", fontsize=9, color="#475569")
            ax.set_xlabel("Espaçamento (cm)", fontsize=9, color="#475569")
        else:
            ax.text(0.5, 0.5, 'Dados de espaçamento insuficientes', ha='center', va='center', transform=ax.transAxes)
            ax.set_xlabel("Espaçamento (cm)", fontsize=9, color="#475569")
            ax.set_ylabel("Frequência", fontsize=9, color="#475569")
        ax.tick_params(axis='both', which='major', labelsize=8)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.grid(axis='y', linestyle='--', alpha=0.5)
        plt.tight_layout(pad=1.0)
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight', transparent=True)
        buffer.seek(0)
        pixmap = QPixmap()
        pixmap.loadFromData(buffer.getvalue())
        self.histogram_label = QLabel()
        self.histogram_label.setPixmap(pixmap.scaled(580, 220, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.histogram_label.setAlignment(Qt.AlignCenter)
        plt.close(fig)
        buffer.close()
    
    def create_compact_chart(self):
        spacing_data = self.analysis_data.get('spacing_data', [])
        try:
            seeds_per_meter_val = float(str(self.analysis_data.get('seeds_per_meter', 0)).replace(',', '.'))
            ideal_spacing_cm = 100.0 / seeds_per_meter_val if seeds_per_meter_val > 0 else None
        except (ValueError, TypeError):
            ideal_spacing_cm = None
        fig, ax = plt.subplots(figsize=(6, 2.8))
        fig.patch.set_facecolor('white')
        if spacing_data:
            data_by_class = {
                'aceitavel': [d['spacing_cm'] for d in spacing_data if d['class'] == 'aceitavel'],
                'falha': [d['spacing_cm'] for d in spacing_data if d['class'] == 'falha'],
                'multipla': [d['spacing_cm'] for d in spacing_data if d['class'] == 'multipla']
            }
            labels = ['Aceitável', 'Falha', 'Múltipla']
            data_to_plot = [data_by_class['aceitavel'], data_by_class['falha'], data_by_class['multipla']]
            border_colors = ['#059669', '#dc2626', '#7c3aed']
            bp = ax.boxplot(data_to_plot, labels=labels, patch_artist=True, vert=True, widths=0.6)
            for patch, border_color in zip(bp['boxes'], border_colors):
                patch.set_facecolor('none')
                patch.set_edgecolor(border_color)
                patch.set_linewidth(1.5)
            if ideal_spacing_cm is not None and ideal_spacing_cm > 0:
                multipla_threshold = 0.5 * ideal_spacing_cm
                falha_threshold = 1.5 * ideal_spacing_cm
                ax.axhspan(0, multipla_threshold, facecolor='#f3e8ff', alpha=0.6, zorder=0)
                ax.axhspan(multipla_threshold, falha_threshold, facecolor='#dcfce7', alpha=0.6, zorder=0)
                ax.axhspan(falha_threshold, ax.get_ylim()[1], facecolor='#fee2e2', alpha=0.6, zorder=0)
            for i, median in enumerate(bp['medians']):
                median.set_color('black')
                median.set_linewidth(1.5)
                median_val = median.get_ydata()[0]
                ax.text(i + 1, median_val, f'{median_val:.1f}', ha='center', va='bottom', fontsize=8, color='black', fontweight='bold', bbox=dict(boxstyle='round,pad=0.2', fc='yellow', alpha=0.6))
            ax.set_ylabel('Espaçamento (cm)', fontsize=9, color="#475569")
            ax.tick_params(axis='both', labelsize=8)
            ax.grid(axis='y', linestyle='--', alpha=0.6)
            if ideal_spacing_cm is not None and ideal_spacing_cm > 0:
                ax.axhline(y=ideal_spacing_cm, color='#16a34a', linestyle='--', linewidth=1.5, label=f'Ideal ({ideal_spacing_cm:.1f}cm)')
            ax.legend(fontsize='x-small')
            ax.tick_params(axis='both', labelsize=8)
        else:
            ax.text(0.5, 0.5, 'Sem dados de espaçamento', ha='center', va='center')
        plt.tight_layout(pad=1.5)
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight', transparent=True)
        buffer.seek(0)
        image_data = buffer.getvalue()
        pixmap = QPixmap()
        pixmap.loadFromData(image_data)
        self.chart_label = QLabel()
        self.chart_label.setPixmap(pixmap.scaled(580, 240, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.chart_label.setAlignment(Qt.AlignCenter)
        plt.close(fig)
        buffer.close()
    
    def create_results_discussion_box(self):
        results_group = QGroupBox("Resultados e Discussão")
        results_layout = QHBoxLayout(results_group)
        results_layout.setSpacing(15)
        analysis_label = QLabel()
        analysis_label.setWordWrap(True)
        analysis_label.setAlignment(Qt.AlignTop)
        analysis_label.setStyleSheet("padding: 5px; line-height: 1.4;")
        params_label = QLabel()
        params_label.setWordWrap(True)
        params_label.setAlignment(Qt.AlignTop)
        params_label.setStyleSheet("padding: 5px; line-height: 1.4; background-color: #f8fafc; border-radius: 5px;")
        aceitavel = self.analysis_data.get('aceitavel', 0)
        falha = self.analysis_data.get('falha', 0)
        multipla = self.analysis_data.get('multipla', 0)
        total = aceitavel + falha + multipla
        aceitavel_pct = (aceitavel / total * 100) if total > 0 else 0
        falha_pct = (falha / total * 100) if total > 0 else 0
        multipla_pct = (multipla / total * 100) if total > 0 else 0
        spacing_values = [d['spacing_cm'] for d in self.analysis_data.get('spacing_data', [])]
        cv_percentage = 0
        if spacing_values:
            mean_spacing = np.mean(spacing_values)
            std_dev = np.std(spacing_values)
            cv_percentage = (std_dev / mean_spacing * 100) if mean_spacing > 0 else 0
        analysis_html = '<b>Análise Geral:</b>'
        if aceitavel_pct >= 80:
            analysis_html += '<p style="color: #059669;">✅ <b>Excelente qualidade de plantio.</b> A distribuição está dentro dos padrões ideais.</p>'
        elif aceitavel_pct >= 60:
            analysis_html += '<p style="color: #ca8a04;">⚠️ <b>Qualidade satisfatória.</b> Há espaço para melhorias, principalmente na redução de falhas ou múltiplas.</p>'
        else:
            analysis_html += '<p style="color: #dc2626;">❌ <b>Atenção necessária.</b> A distribuição apresenta problemas significativos que podem impactar a produtividade.</p>'
        recommendations = []
        if falha_pct > 20: recommendations.append("Verificar o sistema de dosagem (possível entupimento ou falha no disco).")
        if multipla_pct > 15: recommendations.append("Calibrar o singulador para evitar sementes duplas/múltiplas.")
        if cv_percentage > 30: recommendations.append("Investigar a uniformidade do plantio (velocidade, vibração da linha).")
        if recommendations:
            analysis_html += '<p style="font-size: 10px; color: #475569;"><b>Sugestões:</b><br>• ' + '<br>• '.join(recommendations) + '</p>'
        analysis_label.setText(analysis_html)
        params_html = '<p style="font-size: 10px; color: #475569;"><b>Parâmetros de Referência:</b><br>• <b>Aceitável:</b> Ideal > 80%.<br>• <b>Falhas:</b> Ideal < 10-15%.<br>• <b>Múltiplas:</b> Ideal < 5-10%.</p><hr style="border: 1px solid #e2e8f0;">'
        params_html += f'<p style="font-size: 10px; color: #475569;"><b>Coeficiente de Variação (CV):</b><br>• <b>Resultado: {cv_percentage:.1f}%</b> (Ideal < 30%)<br><i>Um CV alto indica grande irregularidade no espaçamento, afetando a competição entre plantas.</i></p>'
        params_label.setText(params_html)
        results_layout.addWidget(analysis_label, 2)
        results_layout.addWidget(params_label, 1)
        results_group.setMinimumHeight(120)
        return results_group

    def create_notes_box(self):
        notes_group = QGroupBox("Observações")
        notes_layout = QVBoxLayout(notes_group)
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Insira suas anotações manuais aqui...")
        self.notes_edit.setStyleSheet("background-color: #fefce8; border: 1px solid #fde047; padding: 4px; color: black;")
        self.notes_edit.setFixedHeight(50)
        existing_notes = self.analysis_data.get('notes', '')
        self.notes_edit.setText(existing_notes)
        self.notes_edit.textChanged.connect(self.on_notes_changed)
        notes_layout.addWidget(self.notes_edit)
        return notes_group

    def on_notes_changed(self):
        self.notes_updated.emit(self.card_id, self.notes_edit.toPlainText())

    def create_statistics_table(self):
        stats_group = QGroupBox("Estatísticas Detalhadas de Espaçamento")
        stats_layout = QVBoxLayout(stats_group)
        stats_layout.setContentsMargins(5, 5, 5, 5)
        table = QTableWidget()
        table.setRowCount(6)
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["✅ Aceitável", "❌ Falha", "🔄 Múltipla"])
        table.setVerticalHeaderLabels(["Média (cm)", "Mediana (cm)", "Máximo (cm)", "Mínimo (cm)", "Desvio Padrão", "CV (%)"])
        table.setMinimumHeight(220)
        spacing_data = self.analysis_data.get('spacing_data', [])
        data_by_class = {
            'aceitavel': [d['spacing_cm'] for d in spacing_data if d['class'] == 'aceitavel'],
            'falha': [d['spacing_cm'] for d in spacing_data if d['class'] == 'falha'],
            'multipla': [d['spacing_cm'] for d in spacing_data if d['class'] == 'multipla']
        }
        col_map = {'aceitavel': 0, 'falha': 1, 'multipla': 2}
        for class_name, data in data_by_class.items():
            col = col_map[class_name]
            if not data:
                for row in range(6):
                    item = QTableWidgetItem("-")
                    item.setTextAlignment(Qt.AlignCenter)
                    table.setItem(row, col, item)
                continue
            mean_val = np.mean(data)
            median_val = np.median(data)
            max_val = np.max(data)
            min_val = np.min(data)
            std_val = np.std(data)
            cv_val = (std_val / mean_val * 100) if mean_val > 0 else 0
            stats_values = [
                f"{mean_val:.2f}", f"{median_val:.2f}", f"{max_val:.2f}", f"{min_val:.2f}",
                f"{std_val:.2f}", f"{cv_val:.2f}"
            ]
            for row, value_str in enumerate(stats_values):
                item = QTableWidgetItem(value_str)
                item.setTextAlignment(Qt.AlignCenter)
                if row == 5 and cv_val > 30:
                    item.setBackground(QColor("#fef2f2"))
                    item.setForeground(QColor("#b91c1c"))
                    item.setFont(QFont("Segoe UI", 9, QFont.Bold))
                table.setItem(row, col, item)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setStyleSheet("QTableWidget { gridline-color: #e2e8f0; border: none; } QTableWidget::item { color: #1e293b; padding: 4px; } QHeaderView::section:horizontal { background-color: #f1f5f9; color: #1e293b; font-weight: bold; border: 1px solid #e2e8f0; padding: 4px; } QHeaderView::section:vertical { background-color: #f8fafc; color: #475569; font-weight: bold; border: 1px solid #e2e8f0; }")
        stats_layout.addWidget(table)
        return stats_group

    def generate_pdf_report(self):
        try:
            video_source_path = self.analysis_data.get('video_path')
            if video_source_path and os.path.isdir(os.path.dirname(video_source_path)):
                save_dir = os.path.dirname(video_source_path)
            else:
                save_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "SVA")
            os.makedirs(save_dir, exist_ok=True)
            default_filename = os.path.join(save_dir, f"relatorio_analise_{self.card_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
            filename, _ = QFileDialog.getSaveFileName(self, f"Salvar Relatório - Análise {self.card_id}", default_filename, "PDF Files (*.pdf)")
            if not filename: return
            styles = getSampleStyleSheet()
            styles.add(ParagraphStyle(name='Small', fontSize=8, leading=10, textColor=colors.HexColor('#475569')))
            styles.add(ParagraphStyle(name='StatLabel', fontSize=9, fontName='Helvetica'))
            styles.add(ParagraphStyle(name='StatValue', fontSize=9, fontName='Helvetica-Bold', alignment=2))
            styles.add(ParagraphStyle(name='BoxTitle', fontSize=10, fontName='Helvetica-Bold', textColor=colors.HexColor('#1e293b')))
            def footer(canvas, doc):
                canvas.saveState()
                canvas.setFont('Helvetica', 8)
                footer_text = f"SVA - Seed Vision Analyzer - Software de Visão Computacional {self.version_string}"
                canvas.line(doc.leftMargin, 0.4 * inch, doc.width + doc.leftMargin, 0.4 * inch)
                canvas.drawCentredString(landscape(letter)[0] / 2.0, 0.25 * inch, footer_text)
                canvas.restoreState()
            story = []
            logo_path = resource_path("logo2.png")
            logo = RLImage(logo_path, width=0.7*inch, height=0.7*inch) if os.path.exists(logo_path) else Spacer(0,0)
            video_source = self.analysis_data.get('video_path', 'Análise')
            datetime_str = self.analysis_data.get('datetime', '')
            seed_type = self.analysis_data.get('seed_type', 'Soja')
            speed = self.analysis_data.get('planting_speed', '3')
            seeds_per_m = self.analysis_data.get('seeds_per_meter', '14')
            try:
                ideal_spacing_cm = 100.0 / float(str(seeds_per_m).replace(',', '.')) if float(str(seeds_per_m).replace(',', '.')) > 0 else 0
            except (ValueError, TypeError):
                ideal_spacing_cm = 0
            info_list = [
                Paragraph(f"<b>Relatório de Análise - ID: {self.card_id}</b>", ParagraphStyle(name='HeaderTitle', fontSize=14, fontName='Helvetica-Bold', textColor=colors.HexColor('#1e40af'))),
                Spacer(1, 6),
                Paragraph(f"<b>Vídeo:</b> {os.path.basename(str(video_source))}", styles['Small']),
                Paragraph(f"<b>Data:</b> {datetime_str}", styles['Small']),
                Paragraph(f"<b>Parâmetros:</b> {seed_type} | {speed}km/h | {seeds_per_m}/m", styles['Small']),
                Paragraph(f"<b>Espaçamento Ideal:</b> {ideal_spacing_cm:.1f} cm", styles['Small'])
            ]
            info_table = Table([[p] for p in info_list], style=[('LEFTPADDING', (0,0), (-1,-1), 0)])
            aceitavel, falha, multipla = self.analysis_data.get('aceitavel', 0), self.analysis_data.get('falha', 0), self.analysis_data.get('multipla', 0)
            total = aceitavel + falha + multipla
            aceitavel_pct = (aceitavel / total * 100) if total > 0 else 0
            falha_pct = (falha / total * 100) if total > 0 else 0
            multipla_pct = (multipla / total * 100) if total > 0 else 0
            multipla_threshold, falha_threshold = 0.5 * ideal_spacing_cm, 1.5 * ideal_spacing_cm
            summary_data = [
                (f"<font color='#059669'><b>Aceitável</b> ({multipla_threshold:.1f} - {falha_threshold:.1f} cm)</font>", f"<font color='#059669'>{aceitavel} ({aceitavel_pct:.1f}%)</font>"),
                (f"<font color='#dc2626'><b>Falha</b> (&gt; {falha_threshold:.1f} cm)</font>", f"<font color='#dc2626'>{falha} ({falha_pct:.1f}%)</font>"),
                (f"<font color='#7c3aed'><b>Múltipla</b> (&lt; {multipla_threshold:.1f} cm)</font>", f"<font color='#7c3aed'>{multipla} ({multipla_pct:.1f}%)</font>")
            ]
            summary_table_content = Table([[Paragraph(c, styles['StatLabel']), Paragraph(v, styles['StatValue'])] for c, v in summary_data], colWidths=['70%', '30%'])
            summary_container = Table([[Paragraph("<b>Resumo da Qualidade</b>", styles['BoxTitle'])], [summary_table_content]], style=[('BOX', (0,0), (-1,-1), 1, colors.lightgrey), ('LEFTPADDING', (0,0), (-1,-1), 6), ('RIGHTPADDING', (0,0), (-1,-1), 6), ('TOPPADDING', (0,0), (-1,-1), 6), ('BOTTOMPADDING', (0,0), (-1,-1), 6)])
            top_table = Table([[logo, info_table, summary_container]], colWidths=[0.8*inch, 3.0*inch, 4.5*inch], style=[('VALIGN', (0,0), (-1,-1), 'TOP')])
            story.append(top_table)
            story.append(Spacer(1, 0.2*inch))
            left_content = []
            hist_img = self.get_histogram_for_pdf()
            box_img = self.get_boxplot_for_pdf()
            hist_container = Table([[Paragraph("<b>Histograma de Espaçamento</b>", styles['BoxTitle'])], [hist_img]], style=[('BOX', (0,0), (-1,-1), 1, colors.lightgrey), ('LEFTPADDING', (0,0), (-1,-1), 6), ('RIGHTPADDING', (0,0), (-1,-1), 6), ('TOPPADDING', (0,0), (-1,-1), 6), ('BOTTOMPADDING', (0,0), (-1,-1), 6)])
            box_container = Table([[Paragraph("<b>Boxplot de Espaçamento</b>", styles['BoxTitle'])], [box_img]], style=[('BOX', (0,0), (-1,-1), 1, colors.lightgrey), ('LEFTPADDING', (0,0), (-1,-1), 6), ('RIGHTPADDING', (0,0), (-1,-1), 6), ('TOPPADDING', (0,0), (-1,-1), 6), ('BOTTOMPADDING', (0,0), (-1,-1), 6)])
            left_content.append(hist_container)
            left_content.append(Spacer(1, 0.1*inch))
            left_content.append(box_container)
            right_content = []
            stats_table_content = self.get_stats_table_for_pdf(styles)
            stats_container = Table([[Paragraph("<b>Estatísticas Detalhadas</b>", styles['BoxTitle'])], [stats_table_content]], style=[('BOX', (0,0), (-1,-1), 1, colors.lightgrey), ('LEFTPADDING', (0,0), (-1,-1), 6), ('RIGHTPADDING', (0,0), (-1,-1), 6), ('TOPPADDING', (0,0), (-1,-1), 6), ('BOTTOMPADDING', (0,0), (-1,-1), 6)])
            right_content.append(stats_container)
            right_content.append(Spacer(1, 0.1*inch))
            discussion_content = self.get_discussion_for_pdf(styles)
            discussion_container = Table([[Paragraph("<b>Resultados e Discussão</b>", styles['BoxTitle'])], [discussion_content]], style=[('BOX', (0,0), (-1,-1), 1, colors.lightgrey), ('LEFTPADDING', (0,0), (-1,-1), 6), ('RIGHTPADDING', (0,0), (-1,-1), 6), ('TOPPADDING', (0,0), (-1,-1), 6), ('BOTTOMPADDING', (0,0), (-1,-1), 6)])
            right_content.append(discussion_container)
            right_content.append(Spacer(1, 0.1*inch))
            notes = self.analysis_data.get('notes', '').replace('\n', '<br/>')
            notes_text = Paragraph(notes if notes else "<i>Nenhuma observação inserida.</i>", styles['Small'])
            notes_container = Table([[Paragraph("<b>Observações</b>", styles['BoxTitle'])], [notes_text]], style=[('BOX', (0,0), (-1,-1), 1, colors.lightgrey), ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#fefce8')), ('LEFTPADDING', (0,0), (-1,-1), 6), ('RIGHTPADDING', (0,0), (-1,-1), 6), ('TOPPADDING', (0,0), (-1,-1), 6), ('BOTTOMPADDING', (0,0), (-1,-1), 6)])
            right_content.append(notes_container)
            main_page_table = Table([[left_content, right_content]], colWidths=[5.2 * inch, 5.2 * inch], style=[('VALIGN', (0, 0), (-1, -1), 'TOP')])
            story.append(main_page_table)
            doc = SimpleDocTemplate(filename, pagesize=landscape(letter), rightMargin=0.3*inch, leftMargin=0.3*inch, topMargin=0.3*inch, bottomMargin=0.4*inch)
            doc.build(story, onFirstPage=footer)
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Sucesso")
            msg_box.setText(f"Relatório salvo com sucesso em:\n{filename}")
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setStyleSheet(DARK_MESSAGE_BOX_STYLE) 
            msg_box.exec()
        except Exception as e:
            msg=QMessageBox.critical(self, "Erro", f"Erro ao gerar o relatório PDF:\n{str(e)}")
            msg.setStyleSheet(DARK_MESSAGE_BOX_STYLE)
            msg.exec()

    def get_pdf_story_elements(self, styles):
        story = []
        logo_path = resource_path("logo2.png")
        logo = RLImage(logo_path, width=0.7*inch, height=0.7*inch) if os.path.exists(logo_path) else Spacer(0,0)
        video_source = self.analysis_data.get('video_path', 'Análise')
        datetime_str = self.analysis_data.get('datetime', '')
        seed_type = self.analysis_data.get('seed_type', 'Soja')
        speed = self.analysis_data.get('planting_speed', '3')
        seeds_per_m = self.analysis_data.get('seeds_per_meter', '14')
        try:
            ideal_spacing_cm = 100.0 / float(str(seeds_per_m).replace(',', '.')) if float(str(seeds_per_m).replace(',', '.')) > 0 else 0
        except (ValueError, TypeError):
            ideal_spacing_cm = 0
        total_seeds = self.analysis_data.get('total_seeds', 0)
        info_list = [
            Paragraph(f"<b>Relatório de Análise - ID: {self.card_id}</b>", ParagraphStyle(name='HeaderTitle', fontSize=14, fontName='Helvetica-Bold', textColor=colors.HexColor('#1e40af'))),
            Spacer(1, 6),
            Paragraph(f"<b>Vídeo:</b> {os.path.basename(str(video_source))}", styles['Small']),
            Paragraph(f"<b>Data:</b> {datetime_str}", styles['Small']),
            Paragraph(f"<b>Parâmetros:</b> {seed_type} | {speed}km/h | {seeds_per_m}/m", styles['Small']),
            Paragraph(f"<b>Total de Sementes:</b> {total_seeds}", styles['Small']),
            Paragraph(f"<b>Espaçamento Ideal:</b> {ideal_spacing_cm:.1f} cm", styles['Small'])
        ]
        info_table = Table([[p] for p in info_list], style=[('LEFTPADDING', (0,0), (-1,-1), 0)])
        aceitavel, falha, multipla = self.analysis_data.get('aceitavel', 0), self.analysis_data.get('falha', 0), self.analysis_data.get('multipla', 0)
        total = aceitavel + falha + multipla
        aceitavel_pct = (aceitavel / total * 100) if total > 0 else 0
        falha_pct = (falha / total * 100) if total > 0 else 0
        multipla_pct = (multipla / total * 100) if total > 0 else 0
        multipla_threshold, falha_threshold = 0.5 * ideal_spacing_cm, 1.5 * ideal_spacing_cm
        summary_data = [
            (f"<font color='#059669'><b>Aceitável</b> ({multipla_threshold:.1f} - {falha_threshold:.1f} cm)</font>", f"<font color='#059669'>{aceitavel} ({aceitavel_pct:.1f}%)</font>"),
            (f"<font color='#dc2626'><b>Falha</b> (&gt; {falha_threshold:.1f} cm)</font>", f"<font color='#dc2626'>{falha} ({falha_pct:.1f}%)</font>"),
            (f"<font color='#7c3aed'><b>Múltipla</b> (&lt; {multipla_threshold:.1f} cm)</font>", f"<font color='#7c3aed'>{multipla} ({multipla_pct:.1f}%)</font>")
        ]
        summary_table_content = Table([[Paragraph(c, styles['StatLabel']), Paragraph(v, styles['StatValue'])] for c, v in summary_data], colWidths=['70%', '30%'])
        summary_container = Table([[Paragraph("<b>Resumo da Qualidade</b>", styles['BoxTitle'])], [summary_table_content]], style=[('BOX', (0,0), (-1,-1), 1, colors.lightgrey), ('LEFTPADDING', (0,0), (-1,-1), 6), ('RIGHTPADDING', (0,0), (-1,-1), 6), ('TOPPADDING', (0,0), (-1,-1), 6), ('BOTTOMPADDING', (0,0), (-1,-1), 6)])
        top_table = Table([[logo, info_table, summary_container]], colWidths=[0.8*inch, 3.0*inch, 4.5*inch], style=[('VALIGN', (0,0), (-1,-1), 'TOP')])
        story.append(top_table)
        story.append(Spacer(1, 0.2*inch))
        left_content = [self.get_histogram_for_pdf(), Spacer(1, 0.1*inch), self.get_boxplot_for_pdf()]
        right_content = [
            self.get_stats_table_for_pdf(styles), Spacer(1, 0.1*inch),
            self.get_discussion_for_pdf(styles), Spacer(1, 0.1*inch)
        ]
        main_page_table = Table([[left_content, right_content]], colWidths=[5.2 * inch, 5.2 * inch], style=[('VALIGN', (0, 0), (-1, -1), 'TOP')])
        story.append(main_page_table)
        return story

    def get_histogram_for_pdf(self):
        buffer = BytesIO()
        fig, ax = plt.subplots(figsize=(5.5, 2.8))
        fig.patch.set_facecolor('white')
        spacing_data_cm = [d['spacing_cm'] for d in self.analysis_data.get('spacing_data', [])]
        try:
            seeds_per_meter_val = float(str(self.analysis_data.get('seeds_per_meter', 0)).replace(',', '.'))
            ideal_spacing_cm = 100.0 / seeds_per_meter_val if seeds_per_meter_val > 0 else 0
        except (ValueError, TypeError): ideal_spacing_cm = 0
        if spacing_data_cm and ideal_spacing_cm > 0:
            multipla_threshold = 0.5 * ideal_spacing_cm
            falha_threshold = 1.5 * ideal_spacing_cm
            ax.axvspan(0, multipla_threshold, facecolor='#f3e8ff', alpha=0.7, zorder=0)
            ax.axvspan(multipla_threshold, falha_threshold, facecolor='#dcfce7', alpha=0.7, zorder=0)
            max_spacing = max(spacing_data_cm) if spacing_data_cm else falha_threshold
            ax.axvspan(falha_threshold, max_spacing * 1.1, facecolor='#fee2e2', alpha=0.7, zorder=0)
            n, bins, patches = ax.hist(spacing_data_cm, bins=25, facecolor='none', edgecolor='black', linewidth=0.5, alpha=0.9)
            for i in range(len(patches)):
                bin_center = (bins[i] + bins[i+1]) / 2
                if bin_center <= multipla_threshold: patches[i].set_edgecolor('#7c3aed'); patches[i].set_linewidth(1.2)
                elif bin_center >= falha_threshold: patches[i].set_edgecolor('#dc2626'); patches[i].set_linewidth(1.2)
                else: patches[i].set_edgecolor('#059669'); patches[i].set_linewidth(1.2)
        ax.set_ylabel("Frequência", fontsize=9, color="#475569")
        ax.set_xlabel("Espaçamento (cm)", fontsize=9, color="#475569")
        ax.tick_params(axis='both', which='major', labelsize=8)
        ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
        ax.grid(axis='y', linestyle='--', alpha=0.5)
        plt.tight_layout(pad=1.0)
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight', transparent=True)
        plt.close(fig)
        buffer.seek(0)
        return RLImage(buffer, width=4.8*inch, height=2.2*inch)

    def get_boxplot_for_pdf(self):
        buffer = BytesIO()
        fig, ax = plt.subplots(figsize=(5.5, 3.0))
        fig.patch.set_facecolor('white')
        spacing_data = self.analysis_data.get('spacing_data', [])
        try:
            seeds_per_meter_val = float(str(self.analysis_data.get('seeds_per_meter', 0)).replace(',', '.'))
            ideal_spacing_cm = 100.0 / seeds_per_meter_val if seeds_per_meter_val > 0 else None
        except (ValueError, TypeError): ideal_spacing_cm = None
        if spacing_data:
            data_by_class = {
                'aceitavel': [d['spacing_cm'] for d in spacing_data if d['class'] == 'aceitavel'],
                'falha': [d['spacing_cm'] for d in spacing_data if d['class'] == 'falha'],
                'multipla': [d['spacing_cm'] for d in spacing_data if d['class'] == 'multipla']
            }
            labels = ['Aceitável', 'Falha', 'Múltipla']
            data_to_plot = [data_by_class['aceitavel'], data_by_class['falha'], data_by_class['multipla']]
            border_colors = ['#059669', '#dc2626', '#7c3aed']
            bp = ax.boxplot(data_to_plot, labels=labels, patch_artist=True, vert=True, widths=0.6)
            for patch, border_color in zip(bp['boxes'], border_colors):
                patch.set_facecolor('none'); patch.set_edgecolor(border_color); patch.set_linewidth(1.5)
            for median in bp['medians']: median.set_color('black'); median.set_linewidth(1.5)
            if ideal_spacing_cm is not None and ideal_spacing_cm > 0:
                ax.axhline(y=ideal_spacing_cm, color='#16a34a', linestyle='--', linewidth=1.5, label=f'Ideal ({ideal_spacing_cm:.1f}cm)')
                ax.legend(fontsize='x-small')
        ax.set_ylabel('Espaçamento (cm)', fontsize=9, color="#475569")
        ax.tick_params(axis='both', labelsize=8)
        ax.grid(axis='y', linestyle='--', alpha=0.6)
        plt.tight_layout(pad=1.5)
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight', transparent=True)
        plt.close(fig)
        buffer.seek(0)
        return RLImage(buffer, width=4.8*inch, height=2.4*inch)

    def get_stats_table_for_pdf(self, styles):
        header = [Paragraph(h, styles['Small']) for h in ["", "<b>Aceitável</b>", "<b>Falha</b>", "<b>Múltipla</b>"]]
        table_data = [header]
        row_labels = ["Média (cm)", "Mediana (cm)", "Máximo (cm)", "Mínimo (cm)", "Desvio Padrão", "CV (%)"]
        data_by_class = {
            'aceitavel': [d['spacing_cm'] for d in self.analysis_data.get('spacing_data', []) if d['class'] == 'aceitavel'],
            'falha': [d['spacing_cm'] for d in self.analysis_data.get('spacing_data', []) if d['class'] == 'falha'],
            'multipla': [d['spacing_cm'] for d in self.analysis_data.get('spacing_data', []) if d['class'] == 'multipla']
        }
        col_map = {'aceitavel': 1, 'falha': 2, 'multipla': 3}
        stats_matrix = [['-' for _ in range(4)] for _ in range(6)]
        for i, label in enumerate(row_labels): stats_matrix[i][0] = Paragraph(f"<b>{label}</b>", styles['Small'])
        for class_name, data in data_by_class.items():
            col = col_map[class_name]
            if data:
                mean_val, median_val, max_val, min_val, std_val = np.mean(data), np.median(data), np.max(data), np.min(data), np.std(data)
                cv_val = (std_val / mean_val * 100) if mean_val > 0 else 0
                stats_values = [f"{mean_val:.2f}", f"{median_val:.2f}", f"{max_val:.2f}", f"{min_val:.2f}", f"{std_val:.2f}", f"{cv_val:.2f}"]
                for row, val_str in enumerate(stats_values): stats_matrix[row][col] = Paragraph(val_str, styles['Small'])
        table_data.extend(stats_matrix)
        table = Table(table_data, colWidths=[1.1*inch, 1.2*inch, 1.2*inch, 1.2*inch])
        table.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f1f5f9')),
            ('BACKGROUND', (0,1), (0,-1), colors.HexColor('#f8fafc')),
        ]))
        return table

    def get_discussion_for_pdf(self, styles):
        total_seeds = self.analysis_data.get('total_seeds', 1) or 1
        aceitavel_pct = (self.analysis_data.get('aceitavel', 0) / total_seeds) * 100
        falha_pct = (self.analysis_data.get('falha', 0) / total_seeds) * 100
        multipla_pct = (self.analysis_data.get('multipla', 0) / total_seeds) * 100
        analysis_html = '<b>Análise Geral:</b><br/>'
        if aceitavel_pct >= 80: analysis_html += '<font color="#059669"><b>Excelente qualidade de plantio.</b></font>'
        elif aceitavel_pct >= 60: analysis_html += '<font color="#ca8a04"><b>Qualidade satisfatória.</b></font>'
        else: analysis_html += '<font color="#dc2626"><b>Atenção necessária.</b></font>'
        recommendations = []
        if falha_pct > 20: recommendations.append("Verificar o sistema de dosagem.")
        if multipla_pct > 15: recommendations.append("Calibrar o singulador.")
        if recommendations:
            analysis_html += '<br/><font size="8" color="#475569"><b>Sugestões:</b><br/>• ' + '<br/>• '.join(recommendations) + '</font>'
        left_col = Paragraph(analysis_html, styles['Normal'])
        spacing_values = [d['spacing_cm'] for d in self.analysis_data.get('spacing_data', [])]
        cv_percentage = 0
        if spacing_values:
            mean_spacing = np.mean(spacing_values)
            std_dev = np.std(spacing_values)
            cv_percentage = (std_dev / mean_spacing * 100) if mean_spacing > 0 else 0
        params_html = '<font size="8" color="#475569"><b>Parâmetros de Referência:</b><br/>• <b>Aceitável:</b> Ideal &gt; 80%.<br/>• <b>Falhas:</b> Ideal &lt; 10-15%.<br/>• <b>Múltiplas:</b> Ideal &lt; 5-10%.</font>'
        params_html += '<br/><hr color="#e2e8f0" size="1"/>'
        params_html += f'<font size="8" color="#475569"><b>Coeficiente de Variação (CV):</b><br/>• <b>Resultado: {cv_percentage:.1f}%</b> (Ideal &lt; 30%)</font>'
        right_col = Paragraph(params_html, styles['Normal'])
        return Table([[left_col, right_col]], colWidths=['60%', '40%'], style=[('VALIGN', (0,0), (-1,-1), 'TOP'), ('BACKGROUND', (1,0), (1,0), colors.HexColor('#f8fafc'))])

    def get_chart_for_pdf(self):
        return self.get_boxplot_for_pdf()

# ... (Restante do arquivo a partir da classe CalibrationWidget) ...
# O código restante não precisa de alterações e foi omitido para economizar espaço.
# Certifique-se de que ele permaneça no seu arquivo.
class CalibrationWidget(QWidget):
    """Widget de calibração integrado na aba de calibração."""
    calibration_done = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self.first_frame = None
        self.points = [] # Adicionado para inicializar a lista de pontos
        self.setup_ui()

    def setup_ui(self):
        """Configura a interface da aba de calibração."""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # --- Painel Esquerdo (Controles) ---
        left_panel = QFrame()
        left_panel.setFixedWidth(400)
        left_panel_layout = QVBoxLayout(left_panel)
        left_panel_layout.setContentsMargins(0, 0, 5, 0)
        left_panel_layout.setSpacing(10)

        # Grupo de Controles de Calibração
        controls_group = QGroupBox("Controles de Calibração")
        controls_grid = QGridLayout(controls_group)
        
        def create_control_label(text):
            label = QLabel(text)
            label.setStyleSheet("color: black;")
            return label

        controls_grid.addWidget(create_control_label("Distância real (cm):"), 0, 0)
        self.dist_real_input = QLineEdit()
        self.dist_real_input.setText("10")
        self.dist_real_input.setPlaceholderText("Ex: 10.0")
        self.dist_real_input.setValidator(QDoubleValidator(0.0, 1000.0, 2))
        controls_grid.addWidget(self.dist_real_input, 0, 1)

        controls_grid.addWidget(create_control_label("Pixels medidos:"), 1, 0)
        self.pixels_medidos_output = QLineEdit("Automático")
        self.pixels_medidos_output.setReadOnly(True)
        controls_grid.addWidget(self.pixels_medidos_output, 1, 1)

        controls_grid.addWidget(create_control_label("Pixels/cm:"), 2, 0)
        self.pixels_cm_output = QLineEdit("Resultado")
        self.pixels_cm_output.setReadOnly(True)
        controls_grid.addWidget(self.pixels_cm_output, 2, 1)

        left_panel_layout.addWidget(controls_group)

        # Grupo de Instruções (movido para o painel esquerdo)
        instructions_group = QGroupBox("Instruções")
        instructions_group.setMaximumHeight(120) # Define uma altura máxima para a caixa
        instructions_layout = QVBoxLayout(instructions_group)
        instructions_text = QLabel(
            "<b>1.</b> Carregue um vídeo na aba 'Analisar'.<br>"
            "<b>2.</b> Clique em 2 pontos na imagem para medir.<br>"
            "<b>3.</b> Digite a distância real (cm) acima.<br>"
            "<b>4.</b> Clique em 'Calcular' e depois em 'Aplicar'."
        )
        instructions_text.setWordWrap(True)
        instructions_text.setStyleSheet("padding: 7px; color: #1e40af; line-height: 150%;")
        instructions_layout.addWidget(instructions_text)
        left_panel_layout.addWidget(instructions_group)

        # Grupo de Ações
        actions_group = QGroupBox("Ações")
        actions_layout = QHBoxLayout(actions_group)

        self.reset_button = QPushButton("🔄 Limpar Pontos")
        self.calculate_and_apply_button = QPushButton("🧮 Calcular e Aplicar")

        self.reset_button.clicked.connect(self.reset_calibration)
        self.calculate_and_apply_button.clicked.connect(self.calculate_and_apply)

        actions_layout.addWidget(self.reset_button)
        actions_layout.addStretch()
        actions_layout.addWidget(self.calculate_and_apply_button)
        actions_layout.addStretch()

        left_panel_layout.addWidget(actions_group)

        left_panel_layout.addStretch()
        main_layout.addWidget(left_panel)

        # --- Painel Direito (Vídeo) ---
        right_panel = QFrame()
        right_panel_layout = QVBoxLayout(right_panel)
        right_panel_layout.setAlignment(Qt.AlignTop) 
        right_panel_layout.setContentsMargins(10, 0, 0, 0) # Diminuído de 20 para 10
        right_panel_layout.setSpacing(10) # Espaçamento idêntico à aba Analisar

        self.video_frame_calibration = QLabel("Carregue um vídeo na aba 'Analisar' para iniciar a calibração")
        self.video_frame_calibration.setAlignment(Qt.AlignCenter)
        # Define um tamanho fixo com proporção 16:9
        self.video_frame_calibration.setFixedSize(self.parent_app.VIDEO_FRAME_WIDTH, self.parent_app.VIDEO_FRAME_HEIGHT)
        self.video_frame_calibration.setCursor(Qt.CrossCursor)
        self.video_frame_calibration.setStyleSheet('''
            QLabel {
                border: 2px dashed #94a3b8;
                background-color: #f8fafc;
                color: #64748b;
                font-size: 16px;
                border-radius: 8px;
            }
        ''')
        right_panel_layout.addWidget(self.video_frame_calibration)
        self.video_frame_calibration.mousePressEvent = self.image_click_event
        self.video_frame_calibration.setMouseTracking(True) # Habilita o rastreamento do mouse
        self.video_frame_calibration.mouseMoveEvent = self.image_move_event # Conecta o evento de movimento


        # Layout inferior para as coordenadas
        bottom_layout_calib = QHBoxLayout()
        bottom_layout_calib.setContentsMargins(0, 0, 0, 0)

        # Label para exibir as coordenadas do mouse
        self.coords_label = QLabel("Coordenadas (X, Y): --")
        self.coords_label.setAlignment(Qt.AlignCenter)
        self.coords_label.setFixedHeight(60) # Define a altura FIXA para 60 pixels
        self.coords_label.setStyleSheet('''
            QLabel {
                background-color: #f1f5f9;
                color: #475569;
                font-size: 12px;
                font-weight: bold;
                border-radius: 6px;
            }
        ''')
        bottom_layout_calib.addStretch() # Empurra para a direita
        bottom_layout_calib.addWidget(self.coords_label)
        right_panel_layout.addLayout(bottom_layout_calib)
        main_layout.addWidget(right_panel) # Adiciona o painel direito ao layout principal

        # Estilo dos botões (para consistência)
        button_style = '''
            QPushButton {
                background-color: #e2e8f0;
                color: #475569;
                border: 1px solid #94a3b8;
                padding: 8px 16px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #cbd5e1;
                border-color: #64748b;
            }
            QPushButton:pressed {
                background-color: #94a3b8;
                border-color: #475569;
            }
            QPushButton:disabled {
                background-color: #f1f5f9;
                color: #94a3b8;
                border-color: #cbd5e1;
            }
        '''
        for btn in [self.reset_button, self.calculate_and_apply_button]:
            btn.setStyleSheet(button_style)
        
        self.update_buttons_state() # Chama após a criação de todos os widgets

    def image_click_event(self, event: QMouseEvent):
        """Captura cliques na imagem para calibração."""
        if self.first_frame is None:
            QMessageBox.warning(self, "Aviso", "Por favor, carregue um vídeo na aba 'Analisar' primeiro.")
            return

        if event.button() == Qt.LeftButton:
            # --- INÍCIO DA CORREÇÃO ---
            # O problema estava aqui. A lógica anterior usava pixmap.size(), que é o tamanho da
            # imagem JÁ REDIMENSIONADA no label, causando um erro de cálculo.
            # A correção usa as dimensões do frame original (self.first_frame) para garantir
            # que a conversão de coordenadas seja precisa.

            label_size = self.video_frame_calibration.size()
            
            # Obtém as dimensões reais do frame original do vídeo
            frame_height, frame_width, _ = self.first_frame.shape
            image_size = QSize(frame_width, frame_height)

            # Calcula a escala real baseada nas dimensões originais
            scale_w = label_size.width() / image_size.width()
            scale_h = label_size.height() / image_size.height()
            scale = min(scale_w, scale_h)

            if scale <= 0: return # Evita divisão por zero se a imagem não for válida

            # Calcula o deslocamento (offset) real (as "bordas")
            offset_x = (label_size.width() - (image_size.width() * scale)) / 2
            offset_y = (label_size.height() - (image_size.height() * scale)) / 2
            
            click_x, click_y = event.position().x(), event.position().y()
            
            # Converte as coordenadas do clique para as coordenadas do frame original
            # Subtrai o offset e divide pela escala para "voltar" ao tamanho original
            frame_x = int((click_x - offset_x) / scale)
            frame_y = int((click_y - offset_y) / scale)
            
            # Garante que as coordenadas calculadas estejam dentro dos limites da imagem
            if 0 <= frame_x < frame_width and 0 <= frame_y < frame_height:
                if len(self.points) < 2:
                    self.points.append((frame_x, frame_y))
                    self.draw_points_on_frame()
                    self.update_buttons_state()
            # --- FIM DA CORREÇÃO ---

    def image_move_event(self, event: QMouseEvent):
        """Captura o movimento do mouse sobre a imagem e exibe as coordenadas."""
        x, y = event.pos().x(), event.pos().y()
        self.coords_label.setText(f"Coordenadas (X, Y): ({x}, {y})")

    def draw_points_on_frame(self, display_frame=None):
        """Desenha os pontos e a linha no frame de calibração."""
        if self.first_frame is None:
            return
        
        if display_frame is None:
            display_frame = self.first_frame.copy()
        
        for i, point_frame in enumerate(self.points):
            px, py = point_frame
            cv2.line(display_frame, (px - 10, py), (px + 10, py), (0, 0, 255), 2) # Linha horizontal da cruz
            cv2.line(display_frame, (px, py - 10), (px, py + 10), (0, 0, 255), 2) # Linha vertical da cruz
            cv2.putText(display_frame, str(i+1), (px + 15, py - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        if len(self.points) == 2:
            self.draw_dashed_line(display_frame, self.points[0], self.points[1], color=(0, 0, 255), thickness=2)

        self.display_frame_on_label(display_frame)

    def draw_dashed_line(self, img, pt1, pt2, color, thickness=1, dash_length=10):
        """Desenha uma linha tracejada entre dois pontos."""
        dist = ((pt1[0] - pt2[0])**2 + (pt1[1] - pt2[1])**2)**0.5
        dashes = int(dist / dash_length)
        for i in range(dashes):
            start = (int(pt1[0] + (pt2[0] - pt1[0]) * i / dashes), 
                     int(pt1[1] + (pt2[1] - pt1[1]) * i / dashes))
            end = (int(pt1[0] + (pt2[0] - pt1[0]) * (i + 0.5) / dashes), 
                   int(pt1[1] + (pt2[1] - pt1[1]) * (i + 0.5) / dashes))
            cv2.line(img, start, end, color, thickness)

    def map_label_to_frame_coords(self, label_pos):
        """Mapeia as coordenadas do clique no QLabel para as coordenadas do frame original."""
        if self.first_frame is None:
            return label_pos[0], label_pos[1]

        label_size = self.video_frame_calibration.size()
        pixmap = self.video_frame_calibration.pixmap()
        if pixmap is None or pixmap.isNull():
            return label_pos[0], label_pos[1]
        pixmap_size = pixmap.size()

        scale_w = label_size.width() / pixmap_size.width()
        scale_h = label_size.height() / pixmap_size.height()
        scale = min(scale_w, scale_h)

        offset_x = (label_size.width() - (pixmap_size.width() * scale)) / 2
        offset_y = (label_size.height() - (pixmap_size.height() * scale)) / 2

        frame_x = int((label_pos[0] - offset_x) / scale) if scale > 0 else 0
        frame_y = int((label_pos[1] - offset_y) / scale) if scale > 0 else 0
        return frame_x, frame_y

    def display_frame_on_label(self, frame):
        """Exibe um frame OpenCV no QLabel de calibração."""
        if frame is None:
            return
        
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        convert_to_qt_format = QImage(frame.data, w, h, bytes_per_line, QImage.Format_BGR888)
        pixmap = QPixmap.fromImage(convert_to_qt_format)
        self.video_frame_calibration.setPixmap(pixmap.scaled(self.video_frame_calibration.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def set_first_frame(self, frame):
        """Define o primeiro frame do vídeo para calibração."""
        self.first_frame = frame.copy()
        self.display_frame_on_label(self.first_frame)
        self.reset_calibration()

    def reset_calibration(self):
        """Reseta os pontos de calibração e os campos de texto."""
        self.points = []
        self.pixels_medidos_output.setText("Automático")
        self.pixels_cm_output.setText("Resultado")
        if self.first_frame is not None:
            self.draw_points_on_frame() # Redesenha a tela com os pontos limpos
        self.update_buttons_state()

    def calculate_and_apply(self):
        """Calcula o valor de pixels por centímetro."""
        if len(self.points) != 2:
            QMessageBox.warning(self, "Aviso", "Por favor, selecione exatamente dois pontos na imagem.")
            return
        
        try:
            dist_real_cm = float(self.dist_real_input.text())
            if dist_real_cm <= 0:
                raise ValueError("A distância real deve ser maior que zero.")
        except ValueError as e:
            msg=QMessageBox.critical(self, "Erro", f"Distância real inválida: {e}")
            msg.setStyleSheet(DARK_MESSAGE_BOX_STYLE)
            msg.exec()
            return
        
        p1 = np.array(self.points[0])
        p2 = np.array(self.points[1])
        pixels_dist = np.linalg.norm(p1 - p2)

        pixels_per_cm = pixels_dist / dist_real_cm if dist_real_cm > 0 else 0

        self.pixels_medidos_output.setText(f"{pixels_dist:.2f}")
        self.pixels_cm_output.setText(f"{pixels_per_cm:.2f}")
        
        # Aplica o valor e fecha a aba
        self.calibration_done.emit(pixels_per_cm)
        self.parent_app.tab_widget.setTabVisible(self.parent_app.calibration_tab_index, False)
        self.parent_app.tab_widget.setCurrentIndex(0)
        msg = QMessageBox.information(self, "Sucesso", f"Calibração de {pixels_per_cm:.2f} pixels/cm aplicada com sucesso!")
        msg.setStyleSheet(DARK_MESSAGE_BOX_STYLE)
        msg.exec()

    def update_buttons_state(self):
        """Atualiza o estado dos botões com base nos pontos selecionados."""
        dist_text = self.dist_real_input.text().replace(',', '.').strip()
        is_dist_valid = False
        try:
            if dist_text and float(dist_text) > 0:
                is_dist_valid = True
        except ValueError:
            is_dist_valid = False
            
        is_ready_to_calculate = len(self.points) == 2 and is_dist_valid
        self.calculate_and_apply_button.setEnabled(is_ready_to_calculate)
        self.reset_button.setEnabled(len(self.points) > 0 or self.pixels_cm_output.text() != "Resultado")

class MainWindow(QWidget):
    """Janela principal do aplicativo Detector de Sementes."""

    def __init__(self, initial_data=None):
        super().__init__()
        self.initial_data = initial_data 
        self.setWindowTitle("SEED VISION ANALYSER - Desenvolvido por TSM Soluções Agrícolas")
        icon_path = resource_path("icone.ico")
        self.setWindowIcon(QIcon(icon_path))

        self.VIDEO_FRAME_HEIGHT = 450 
        self.VIDEO_FRAME_WIDTH = int(self.VIDEO_FRAME_HEIGHT * (16 / 9))
        
        self.project_dir = os.path.dirname(os.path.abspath(__file__))
        self.video_path = None
        self.cap = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.current_frame = None
        self.temp_value = 100 # Valor inicial de temperatura (100%)
        self.sat_value = 100 # Valor inicial de saturação (100%)
        self.frame_count = 0
        self.total_frames = 0
        self.fps = 30
        self.playback_speed = 1.0
        self.saturation_value = 0
        self.temperature_value = 0
        self.frame_width = 0
        self.frame_height = 0
        self.playing = False
        self.pause_flag = False
        self.analysis_results = []
        self.next_analysis_id = 1
        self.auto_save_prompt_shown = False
        self.auto_save_seed_count = 251

        self.seed_type = "Soja"
        self.planting_speed = 3
        self.seeds_per_meter = 14
        self.tube_type = "Reto"
        self.pixels_per_cm = 29.80

        self.detection_method = "hsv"
        self.aceitavel_count = 0
        self.falha_count = 0
        self.multipla_count = 0
        self.total_seeds_detected = 0
        
        self.detected_seeds_history = []
        self.history_length = 30
        
        self.tracked_seeds = {}
        self.next_seed_id = 0
        self.last_crossed_seed_x = None
        self.disappeared_seeds = {}
        self.disappeared_frames_threshold = 5

        self.seed_params = {
            "Soja": {'min_area': 150, 'max_area': 3000, 'double_seed_area_threshold': 900, 'hsv_lower1': [0, 70, 50], 'hsv_upper1': [10, 255, 255], 'hsv_lower2': [160, 70, 50], 'hsv_upper2': [180, 255, 255], 'is_dual_hue': True},
            "Milho": {'min_area': 500, 'max_area': 8000, 'double_seed_area_threshold': 2000, 'hsv_lower1': [15, 40, 40], 'hsv_upper1': [40, 255, 255], 'hsv_lower2': [0,0,0], 'hsv_upper2': [0,0,0], 'is_dual_hue': False}
        }

        self.spacing_chart = pg.PlotWidget()
        self.spacing_chart.setBackground("#ffffff")
        self.spacing_chart.setTitle("Variação do Espaçamento (cm)", color="#1e293b", size="9pt")
        self.spacing_chart.setLabel('left', 'Espaçamento (cm)', color='#475569')
        self.spacing_chart.setLabel('bottom', 'Tempo (s)', color='#475569')
        self.spacing_chart.showGrid(x=True, y=True, alpha=0.3)
        self.spacing_chart.setYRange(0, 10)
        self.spacing_chart.setFixedWidth(self.VIDEO_FRAME_WIDTH)
        self.spacing_chart.setFixedHeight(150)

        self.last_plantability_results = None

        self.yolo_model = None
        self.yolo_detections = []
        self.update_thread = None # Adicionado para a thread de atualização

        self.setup_ui()
        self.apply_theme()
        self.setup_spacing_chart_plots()

        self.populate_initial_data() # Preenche os dados da janela de configuração

        if hasattr(self, 'seeds_per_m_input'):
            self.seeds_per_m_input.textChanged.connect(self.update_spacing_chart_range)
        
        self.spacing_chart_data = {'time': [], 'spacing': []}
        self.spacing_chart_points_aceitavel = {'x': [], 'y': []}
        self.spacing_chart_points_falha = {'x': [], 'y': []}
        self.spacing_chart_points_multipla = {'x': [], 'y': []}
        self.setup_spacing_chart_plots()

        # Chamada inicial para carregar o modelo YOLO (REMOVIDO PARA ACELERAR INICIALIZAÇÃO)
        # self.load_yolo_model()
    
    def populate_initial_data(self):
        """Preenche os campos da aba 'Analisar' com os dados da janela de configuração."""
        if not self.initial_data:
            return

        # Função auxiliar para processar strings como "Item A, Item B" em uma lista
        def parse_input_list(input_string):
            if not input_string:
                return []
            # Substitui ponto e vírgula por vírgula para mais flexibilidade
            items = input_string.replace(';', ',').split(',')
            # Remove espaços em branco e itens vazios da lista resultante
            return [item.strip() for item in items if item.strip()]

        # 1. Popula a lista de Tipos de Semente
        seed_types = parse_input_list(self.initial_data.get("seed_type", ""))
        if seed_types:
            self.seed_type_combo.clear()
            self.seed_type_combo.addItems(seed_types)
            self.seed_type_combo.setCurrentIndex(0) # Seleciona o primeiro item

        # 2. Popula a lista de Tipos de Tubo (usando o campo "Delineamento")
        tube_types = parse_input_list(self.initial_data.get("test_design", ""))
        if tube_types:
            self.tube_type_combo.clear()
            self.tube_type_combo.addItems(tube_types)
            self.tube_type_combo.setCurrentIndex(0)

        # 3. Popula a lista de Velocidades
        speeds = parse_input_list(self.initial_data.get("speed", ""))
        if speeds:
            self.speed_combo.clear()
            self.speed_combo.addItems(speeds)
            self.speed_combo.setCurrentIndex(0)

    def _get_tukey_summary_and_letters(self, tukey_result):
        """Processa o resultado do teste de Tukey para extrair médias e gerar letras de significância."""
        import pandas as pd
        results_df = pd.DataFrame(data=tukey_result._results_table.data[1:], columns=tukey_result._results_table.data[0])
        results_df['p-adj'] = pd.to_numeric(results_df['p-adj'])
        
        groups = np.unique(tukey_result.groups)
        group_means = {group: tukey_result.data[tukey_result.groups == group].mean() for group in groups}
        
        sorted_groups = sorted(groups, key=lambda g: group_means[g], reverse=True)
        
        letters = {group: '' for group in sorted_groups}
        if not sorted_groups:
            return {}

        # Algoritmo para atribuição de letras
        current_letter_ord = ord('a')
        
        # Agrupa os grupos que não são significativamente diferentes entre si
        sets = []
        for g1 in sorted_groups:
            current_set = {g1}
            for g2 in sorted_groups:
                if g1 == g2: continue
                
                pair_result = results_df[
                    ((results_df['group1'] == g1) & (results_df['group2'] == g2)) |
                    ((results_df['group1'] == g2) & (results_df['group2'] == g1))
                ]
                
                is_significant = pair_result.empty or pair_result.iloc[0]['p-adj'] < 0.05
                if not is_significant:
                    current_set.add(g2)
            
            is_new_set = True
            for i, s in enumerate(sets):
                if s == current_set:
                    is_new_set = False
                    break
            if is_new_set:
                sets.append(current_set)

        # Atribui letras aos conjuntos
        for group in sorted_groups:
            assigned_letter_str = ''
            for i, s in enumerate(sets):
                if group in s:
                    assigned_letter_str += chr(ord('a') + i)
            letters[group] = assigned_letter_str
            
        # Combina médias e letras em um único dicionário para o gráfico
        summary_with_letters = {
            group: (group_means[group], letters[group]) for group in groups
        }
        return summary_with_letters
    
    def apply_theme(self):
        """Aplica um tema visual moderno ao aplicativo."""
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor("#f8fafc"))
        palette.setColor(QPalette.WindowText, QColor("#1e293b"))
        palette.setColor(QPalette.Base, QColor("#ffffff"))
        palette.setColor(QPalette.AlternateBase, QColor("#f1f5f9"))
        palette.setColor(QPalette.ToolTipBase, QColor("#1e293b"))
        palette.setColor(QPalette.ToolTipText, QColor("#f8fafc"))
        palette.setColor(QPalette.Text, QColor("#1e293b"))
        palette.setColor(QPalette.Button, QColor("#e2e8f0"))
        palette.setColor(QPalette.ButtonText, QColor("#475569"))
        palette.setColor(QPalette.BrightText, QColor("#dc2626"))
        palette.setColor(QPalette.Highlight, QColor("#3b82f6"))
        palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
        self.setPalette(palette)

        self.setStyleSheet('''
            QWidget {
                font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
                font-size: 11px;
            }
            QTabWidget::pane {
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                background-color: #ffffff;
            }
            QTabWidget::tab-bar {
                left: 5px;
            }
            QTabBar::tab {
                background: #e2e8f0;
                border: 1px solid #cbd5e1;
                border-bottom-color: #cbd5e1;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                min-width: 8ex;
                padding: 8px 15px;
                margin-right: 2px;
                color: #475569;
                font-weight: bold;
            }
            QTabBar::tab:selected, QTabBar::tab:hover {
                background: #ffffff;
                border-color: #94a3b8;
                border-bottom-color: #ffffff;
                color: #1e40af;
            }
            QTabBar::tab:selected {
                border-color: #3b82f6;
                border-bottom-color: #ffffff;
            }
            QPushButton {
                background-color: #e2e8f0;
                color: #475569;
                border: 1px solid #94a3b8;
                padding: 8px 16px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #cbd5e1;
                border-color: #64748b;
            }
            QPushButton:pressed {
                background-color: #94a3b8;
                border-color: #475569;
            }
            QPushButton:disabled {
                background-color: #f1f5f9;
                color: #94a3b8;
                border-color: #cbd5e1;
            }
            QLineEdit, QComboBox {
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                padding: 5px;
                background-color: #ffffff;
                color: #1e293b;
            }
            QRadioButton {
                color: black; /* Garante que o texto seja preto */
                background: transparent;
                font-size: 10px; /* <--- NOVO: Reduz o tamanho da fonte para 10px */
            }
            QRadioButton::indicator {
                /* Desenha o círculo do botão */
                width: 14px;
                height: 14px;
                border: 2px solid #94a3b8; /* Borda cinza, como os outros controles */
                border-radius: 8px; /* Deixa redondo */
                background-color: #ffffff; /* Fundo branco */
            }
            QRadioButton::indicator:checked {
                /* Desenha o círculo interno quando marcado */
                background-color: #3b82f6; /* Cor azul de destaque */
                border: 2px solid #2563eb; /* Borda azul mais escura */
            }
            QRadioButton::indicator:hover {
                border: 2px solid #3b82f6; /* Borda azul ao passar o mouse */
            }
            QComboBox::drop-down {
                border: 0px;
            }
            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
            }
            QSlider::groove:horizontal { /* A canaleta onde o slider desliza */
                border: 1px solid #cbd5e1;
                height: 4px;
                background: #e2e8f0;
                margin: 2px 0;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #64748b;
                border: 1px solid #475569;
                width: 12px;
                height: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
            QGroupBox {
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
                background-color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 3px;
                color: #1e293b;
                font-weight: bold;
            }
            QScrollArea {
                border: none;
            }
            QScrollBar:vertical {
                border: 1px solid #e2e8f0;
                background: #f1f5f9;
                width: 10px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: #cbd5e1;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                background: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        ''')

    def setup_ui(self):
        """Configura a interface principal do aplicativo."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        #self.resize(1280, 780) # Define o tamanho inicial
        #self.setMinimumSize(1280, 780) # Garante que não possa ser menor que o tamanho inicial
        self.setFixedSize(1280, 780) # Define um tamanho fixo para a janela para evitar redimensionamento automático
        
        top_bar_layout = QHBoxLayout()
        top_bar_layout.setContentsMargins(10, 10, 10, 10)
        top_bar_layout.setSpacing(10)
        top_bar_layout.setAlignment(Qt.AlignLeft)

        app_title = QLabel(f"Software de Visão Computacional {CURRENT_VERSION}")
        app_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        app_title.setStyleSheet("color: #1e293b; padding-left: 5px;")
        top_bar_layout.addWidget(app_title)

        top_bar_layout.addStretch(1)

        self.save_project_btn = QPushButton("💾 Salvar Projeto")
        self.load_project_btn = QPushButton("📂 Carregar Projeto")
        self.update_btn = QPushButton("🔄 Atualização")
        self.help_btn = QPushButton("❓ Ajuda")

        top_button_style = '''
            QPushButton {
                background-color: #e2e8f0;
                color: #475569;
                border: 1px solid #94a3b8;
                padding: 6px 12px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #cbd5e1;
                border-color: #64748b;
            }
            QPushButton:pressed {
                background-color: #94a3b8;
                border-color: #475569;
            }
        '''
        self.save_project_btn.setStyleSheet(top_button_style)
        self.load_project_btn.setStyleSheet(top_button_style)
        self.update_btn.setStyleSheet(top_button_style)
        self.help_btn.setStyleSheet(top_button_style)

        self.save_project_btn.clicked.connect(self.save_project)
        self.load_project_btn.clicked.connect(self.load_project)
        self.update_btn.clicked.connect(self.show_update_dialog)
        self.help_btn.clicked.connect(self.show_help)

        top_bar_layout.addWidget(self.save_project_btn)
        top_bar_layout.addWidget(self.load_project_btn)
        top_bar_layout.addWidget(self.update_btn)
        top_bar_layout.addWidget(self.help_btn)

        top_bar_frame = QFrame()
        top_bar_frame.setLayout(top_bar_layout)
        top_bar_frame.setStyleSheet("background-color: #ffffff; border-bottom: 1px solid #e2e8f0;")
        main_layout.addWidget(top_bar_frame)

        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet('''
            QTabWidget::pane {
                border: none;
            }
            QTabBar::tab {
                min-width: 100px;
            }
        ''')
        main_layout.addWidget(self.tab_widget)

        self.analyze_tab = QWidget()
        self.setup_analyze_tab()
        self.tab_widget.addTab(self.analyze_tab, "🔍 Analisar")

        self.calibration_tab = CalibrationWidget(self)
        self.calibration_tab.calibration_done.connect(self.set_pixels_per_cm)
        self.calibration_tab_index = self.tab_widget.addTab(self.calibration_tab, "🎯 Calibrar Pixel/cm")
        self.tab_widget.setTabVisible(self.calibration_tab_index, False)
        self.tab_widget.currentChanged.connect(self.on_tab_changed)

       

        self.reports_tab = QWidget()
        self.setup_reports_tab()
        self.tab_widget.addTab(self.reports_tab, "📊 Relatórios")

        # --- NOVO: Aba de Estatísticas ---
        self.statistics_tab = QWidget()
        self.setup_statistics_tab()
        self.tab_widget.addTab(self.statistics_tab, "📈 Estatística")

        self.plantability_tab = QWidget()
        self.setup_plantability_tab()
        self.tab_widget.addTab(self.plantability_tab, "🌱 Plantabilidade")

    def setup_plantability_tab(self):
        """Configura a aba de Plantabilidade."""
        main_layout = QHBoxLayout(self.plantability_tab)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        left_panel = QGroupBox("Cálculo de Plantabilidade")
        left_panel.setFixedWidth(560)
        left_layout = QVBoxLayout(left_panel)
        
        form_layout = QGridLayout()

        label_plantas = QLabel("Número total de plantas:")
        label_plantas.setStyleSheet("color: #14532d; font-weight: bold;")
        form_layout.addWidget(label_plantas, 0, 0)
        self.plantas_total_input = QLineEdit()
        self.plantas_total_input.setPlaceholderText("Ex: 50000")
        form_layout.addWidget(self.plantas_total_input, 0, 1)

        label_espacamento = QLabel("Espaçamento entre fileiras (m):")
        label_espacamento.setStyleSheet("color: #14532d; font-weight: bold;")
        form_layout.addWidget(label_espacamento, 1, 0)
        self.espacamento_fileiras_input = QLineEdit()
        self.espacamento_fileiras_input.setPlaceholderText("Ex: 0.45")
        form_layout.addWidget(self.espacamento_fileiras_input, 1, 1)

        label_emergencia = QLabel("Emergência (%):")
        label_emergencia.setStyleSheet("color: #14532d; font-weight: bold;")
        form_layout.addWidget(label_emergencia, 2, 0)
        self.emergencia_input = QLineEdit()
        self.emergencia_input.setPlaceholderText("Ex: 95")
        form_layout.addWidget(self.emergencia_input, 2, 1)

        left_layout.addLayout(form_layout)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        self.calcular_plantabilidade_btn = QPushButton("Calcular")
        self.calcular_plantabilidade_btn.setStyleSheet('''
            QPushButton { background-color: #16a34a; color: white; padding: 8px; font-weight: bold; }
            QPushButton:hover { background-color: #15803d; }
        ''')
        buttons_layout.addWidget(self.calcular_plantabilidade_btn)

        self.salvar_plantabilidade_btn = QPushButton("Salvar")
        self.salvar_plantabilidade_btn.setStyleSheet('''
            QPushButton { background-color: #3b82f6; color: white; padding: 8px; font-weight: bold; }
            QPushButton:hover { background-color: #2563eb; }
        ''')
        self.salvar_plantabilidade_btn.clicked.connect(self.save_plantability_calculation)
        self.calcular_plantabilidade_btn.clicked.connect(self.calculate_plantability)
        buttons_layout.addWidget(self.salvar_plantabilidade_btn)

        left_layout.addLayout(buttons_layout)

        self.resultado_plantabilidade_text = QTextEdit("O resultado do cálculo aparecerá aqui.")
        self.resultado_plantabilidade_text.setReadOnly(True)
        self.resultado_plantabilidade_text.setStyleSheet("background-color: #ffffff; color: #1e293b;")
        left_layout.addWidget(self.resultado_plantabilidade_text)

        self.plantability_table = QTableWidget()
        self.plantability_table.setColumnCount(7)
        self.plantability_table.setHorizontalHeaderLabels([
            "População", "Espaçamento", "Emergência", "Esp. Ideal", 
            "Sementes/m", "Múltiplos (≤)", "Falhas (≥)"
        ])
        self.plantability_table.setAlternatingRowColors(True)
        self.plantability_table.setStyleSheet('''
            QTableWidget {
                background-color: #ffffff; 
                color: #166534; 
                gridline-color: transparent;
                alternate-background-color: #f0fdf4;
            }
            QHeaderView::section {
                background-color:  #515251;
                color: white;
                font-weight: bold;
                padding: 4px;
                border: none;
            }
        ''')
        self.plantability_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        left_layout.addWidget(self.plantability_table)

        right_panel = QGroupBox("Fórmulas e Conceitos")
        right_layout = QVBoxLayout(right_panel)

        explanation_text = QTextEdit()
        explanation_text.setReadOnly(True)
        explanation_text.setStyleSheet("background-color: #f8fafc; border: none;")

        html_content = """
        <div style="font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333;">
        <h3 style="color: #1e40af;">Fórmulas Básicas de Plantabilidade</h3>
        <p><strong>1. Plantas por metro linear de fileira:</strong></p>
        <div style="background-color: #eef2ff; padding: 10px; border-radius: 5px; font-family: 'Courier New', monospace;">
            plantas/m = (População (plantas/ha) &times; Espaçamento (m)) / 10.000
        </div>
        <p style="font-size: 9px; color: #64748b;"><i>* O valor 10.000 é o fator de conversão de m² por hectare.</i></p>
        <p><strong>2. Espaçamento ideal entre plantas (na fileira):</strong></p>
        <div style="background-color: #eef2ff; padding: 10px; border-radius: 5px; font-family: 'Courier New', monospace;">
            Espaçamento (cm) = 100 / (plantas/m)
        </div>
        <p><strong>3. Ajuste para Germinação/Emergência:</strong></p>
        <p>Para compensar perdas, ajusta-se a quantidade de sementes a serem semeadas.</p>
        <div style="background-color: #eef2ff; padding: 10px; border-radius: 5px; font-family: 'Courier New', monospace;">
            Sementes a semear/m = (Plantas/m desejadas) / Taxa de emergência
        </div>
        <p style="font-size: 9px; color: #64748b;"><i>* A taxa de emergência deve ser em formato decimal. Ex: para 90% de emergência, use 0.9.</i></p>
        <hr style="border: 1px solid #e2e8f0; margin: 20px 0;">
        <h3 style="color: #1e40af;">Limiares de Classificação</h3>
        <p>A literatura técnica (ABNT/Embrapa) define os intervalos com base no espaçamento de referência (<b>X_ref</b>):</p>
        <ul>
            <li><strong style="color: #7c3aed;">Duplas/Múltiplos:</strong> Espaçamento &le; 0,5 &times; X_ref</li>
            <li><strong style="color: #059669;">Aceitável/Normal:</strong> 0,5 &times; X_ref &lt; Espaçamento &lt; 1,5 &times; X_ref</li>
            <li><strong style="color: #dc2626;">Falha:</strong> Espaçamento &ge; 1,5 &times; X_ref</li>
        </ul>
        <p style="font-size: 10px; color: #475569; background-color: #f1f5f9; padding: 8px; border-radius: 4px;">
            <b>Observação:</b> O termo "dupla" refere-se a 2 plantas muito próximas, enquanto "múltipla" pode ser mais de duas.
            Ambos se enquadram na categoria de espaçamentos menores que 0,5 &times; X_ref. A análise desses percentuais
            é fundamental para avaliar a qualidade da semeadora.
        </p>
        </div>
        """
        explanation_text.setHtml(html_content)
        right_layout.addWidget(explanation_text)

        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel)

    def save_plantability_calculation(self):
        """Salva o último cálculo de plantabilidade na tabela de histórico."""
        if self.last_plantability_results is None:
            QMessageBox.warning(self, "Nenhum Cálculo", "Por favor, execute um cálculo antes de salvar.")
            return

        try:
            data = self.last_plantability_results
            row_position = 0
            self.plantability_table.insertRow(row_position)
            items = [
                f"{data['populacao_ha']:.0f}",
                f"{data['espacamento_m']:.2f} m",
                f"{data['taxa_emergencia_pct']:.0f}%",
                f"{data['espacamento_ideal_cm']:.2f} cm",
                f"{data['sementes_por_metro']:.2f}",
                f"{data['limite_multiplos']:.2f} cm",
                f"{data['limite_falhas']:.2f} cm"
            ]
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                self.plantability_table.setItem(row_position, col, item)
            self.plantability_table.resizeColumnsToContents()
            self.last_plantability_results = None
        except Exception as e:
            msg=QMessageBox.critical(self, "Erro ao Salvar", f"Ocorreu um erro ao tentar salvar os dados na tabela:\n{e}")
            msg.setStyleSheet(DARK_MESSAGE_BOX_STYLE)
            msg.exec()

    def calculate_plantability(self):
        """Calcula e exibe os resultados de plantabilidade."""
        try:
            populacao_ha_str = self.plantas_total_input.text().replace(',', '.')
            espacamento_m_str = self.espacamento_fileiras_input.text().replace(',', '.')
            taxa_emergencia_pct_str = self.emergencia_input.text().replace(',', '.')

            if not all([populacao_ha_str, espacamento_m_str, taxa_emergencia_pct_str]):
                QMessageBox.warning(self, "Campos Vazios", "Por favor, preencha todos os campos para o cálculo.")
                return

            populacao_ha = float(populacao_ha_str)
            espacamento_m = float(espacamento_m_str)
            taxa_emergencia_pct = float(taxa_emergencia_pct_str)

            if populacao_ha <= 0 or espacamento_m <= 0 or not (0 < taxa_emergencia_pct <= 100):
                raise ValueError("Os valores de entrada devem ser positivos e a emergência entre 1 e 100.")

            taxa_emergencia_dec = taxa_emergencia_pct / 100.0
            plantas_por_metro = (populacao_ha * espacamento_m) / 10000.0
            if plantas_por_metro <= 0:
                raise ValueError("O cálculo de plantas/m resultou em um valor inválido.")

            espacamento_ideal_cm = 100.0 / plantas_por_metro
            sementes_por_metro = plantas_por_metro / taxa_emergencia_dec
            x_ref = espacamento_ideal_cm
            limite_multiplos = 0.5 * x_ref
            limite_falhas = 1.5 * x_ref

            self.last_plantability_results = {
                "populacao_ha": populacao_ha,
                "espacamento_m": espacamento_m,
                "taxa_emergencia_pct": taxa_emergencia_pct,
                "espacamento_ideal_cm": espacamento_ideal_cm,
                "sementes_por_metro": sementes_por_metro,
                "limite_multiplos": limite_multiplos,
                "limite_falhas": limite_falhas,
            }

            html_output = f"""
            <div style="font-family: 'Segoe UI', Arial, sans-serif; font-size: 12px; color: #333;">
                <h4 style="color: #1e40af; margin-bottom: 5px;">Resultados do Cálculo:</h4>
                <div style="background-color: #f0f9ff; border-left: 4px solid #3b82f6; padding: 8px; margin-bottom: 10px;">
                    <strong>Espaçamento Ideal (X_ref):</strong>
                    <span style="font-size: 16px; font-weight: bold; color: #1d4ed8; float: right;">{espacamento_ideal_cm:.2f} cm</span>
                </div>
                <div style="background-color: #f0f9ff; border-left: 4px solid #3b82f6; padding: 8px; margin-bottom: 15px;">
                    <strong>Sementes a Semear por Metro:</strong>
                    <span style="font-size: 16px; font-weight: bold; color: #1d4ed8; float: right;">{sementes_por_metro:.2f} sementes/m</span>
                </div>
                <h4 style="color: #1e40af; margin-bottom: 5px;">Limiares de Classificação:</h4>
                <div style="background-color: #f3e8ff; border-left: 4px solid #7c3aed; padding: 8px; margin-bottom: 5px;">
                    <strong>Múltiplos:</strong> Espaçamentos &le; {limite_multiplos:.2f} cm
                </div>
                <div style="background-color: #dcfce7; border-left: 4px solid #16a34a; padding: 8px; margin-bottom: 5px;">
                    <strong>Aceitáveis:</strong> Espaçamentos entre {limite_multiplos:.2f} cm e {limite_falhas:.2f} cm
                </div>
                <div style="background-color: #fee2e2; border-left: 4px solid #dc2626; padding: 8px;">
                    <strong>Falhas:</strong> Espaçamentos &ge; {limite_falhas:.2f} cm
                </div>
            </div>
            """
            self.resultado_plantabilidade_text.setHtml(html_output)

        except ValueError as e:
            self.last_plantability_results = None
            msg=QMessageBox.critical(self, "Erro de Entrada", f"Por favor, insira valores numéricos válidos.\n\nDetalhe: {e}")
            msg.setStyleSheet(DARK_MESSAGE_BOX_STYLE)
            msg.exec()
        except Exception as e:
            msg=QMessageBox.critical(self, "Erro no Cálculo", f"Ocorreu um erro inesperado durante o cálculo:\n{e}")
            msg.setStyleSheet(DARK_MESSAGE_BOX_STYLE)
            msg.exec()

    def setup_analyze_tab(self):
        """Configura a aba de análise de vídeo."""
        analyze_layout = QVBoxLayout(self.analyze_tab)
        analyze_layout.setContentsMargins(15, 15, 15, 15)
        analyze_layout.setSpacing(10)

        main_h_layout = QHBoxLayout()
        
        left_panel = QFrame()
        left_panel_layout = QVBoxLayout(left_panel)
        left_panel_layout.setContentsMargins(0, 0, 5, 0)
        left_panel_layout.setSpacing(10)
        left_panel.setFixedWidth(400)

        video_controls_group = QGroupBox("Controles de Vídeo")
        video_controls_layout = QVBoxLayout(video_controls_group)

        source_selection_layout = QHBoxLayout()
        self.select_video_btn = QPushButton("📂 Selecionar Vídeo")
        self.select_video_btn.setStyleSheet('''
            QPushButton {
                background-color: #3b82f6;
                color: white;
            }
            QPushButton:hover { background-color: #2563eb; }
        ''')
        self.select_video_btn.clicked.connect(self.select_video)
        source_selection_layout.addWidget(self.select_video_btn)
        video_controls_layout.addLayout(source_selection_layout)

        self.video_path_label = QLabel("Nenhum vídeo selecionado")
        self.video_path_label.setWordWrap(True)
        self.video_path_label.setStyleSheet("color: #475569; font-size: 9px;")
        video_controls_layout.addWidget(self.video_path_label)

        playback_buttons_layout = QHBoxLayout()
        self.start_btn = QPushButton("▶️ Iniciar")
        self.pause_btn = QPushButton("⏸️ Pausar")
        self.reset_btn = QPushButton("🔄 Retornar")
        self.reset_btn.setToolTip("Zera a contagem e volta o vídeo para o início.")
        self.reset_btn.clicked.connect(self.reset_analysis)
        self.save_analysis_btn = QPushButton("💾 Salvar")
        playback_buttons_layout.addWidget(self.start_btn)
        playback_buttons_layout.addWidget(self.pause_btn)
        playback_buttons_layout.addWidget(self.reset_btn)
        playback_buttons_layout.addWidget(self.save_analysis_btn)
        video_controls_layout.addLayout(playback_buttons_layout)

        left_panel_layout.addWidget(video_controls_group)

        analysis_params_group = QGroupBox("Parâmetros de Análise")
        self.analysis_params_layout = QGridLayout(analysis_params_group)
        self.analysis_params_layout.setColumnStretch(1, 0)
        self.analysis_params_layout.setColumnStretch(2, 0)
        
        def create_styled_label(text):
            label = QLabel(text)
            # --- ALTERAÇÃO: Diminui o tamanho da fonte para 10px ---
            label.setStyleSheet("color: #1e40af; font-weight: bold; font-size: 11px;")
            return label

        self.analysis_params_layout.addWidget(create_styled_label("⚙️ Método:"), 0, 0, Qt.AlignTop)
        
        # Trocado de QGridLayout para QHBoxLayout para colocar em linha única
        method_hbox_layout = QHBoxLayout()
        method_hbox_layout.setSpacing(10) # Espaçamento menor entre os botões
        method_hbox_layout.setContentsMargins(0, 0, 0, 0)
        self.method_group = QButtonGroup(self)

        # 1. Botão YOLO (Primeiro)
        self.method_yolo_radio = QRadioButton("YOLO") # Mantido como YOLO
        self.method_yolo_radio.setToolTip("Usa apenas o modelo de Deep Learning. Requer modelo treinado.")
        self.method_yolo_radio.setChecked(True)
        self.method_group.addButton(self.method_yolo_radio, 2)
        method_hbox_layout.addWidget(self.method_yolo_radio)

        # 2. Botão HSV (Segundo)
        self.method_hsv_radio = QRadioButton("HSV (Cor)")
        self.method_hsv_radio.setToolTip("Método rápido baseado em cor e tamanho. Ideal para sementes com bom contraste.")
        self.method_group.addButton(self.method_hsv_radio, 1)
        method_hbox_layout.addWidget(self.method_hsv_radio)

        # 3. Botão Combinado (Terceiro)
        # Texto reduzido de "Combinado (YOLO + HSV)" para "Combinado"
        self.method_combined_radio = QRadioButton("YOLO + HSV") 
        self.method_combined_radio.setToolTip("Usa YOLO para detecção e HSV para refinar, identificando sementes duplas. Mais robusto.")
        self.method_group.addButton(self.method_combined_radio, 3)
        method_hbox_layout.addWidget(self.method_combined_radio)
        
        method_hbox_layout.addStretch()

        # Adiciona o layout horizontal ao layout de grade principal
        self.analysis_params_layout.addLayout(method_hbox_layout, 0, 1, 1, 2)

        '''method_grid_layout.setSpacing(5)
        self.method_group = QButtonGroup(self)

        self.method_hsv_radio = QRadioButton("HSV (Cor)")
        self.method_hsv_radio.setToolTip("Método rápido baseado em cor e tamanho. Ideal para sementes com bom contraste.")
        self.method_hsv_radio.setChecked(True)
        self.method_group.addButton(self.method_hsv_radio, 1)
        method_grid_layout.addWidget(self.method_hsv_radio, 0, 0)

        self.method_yolo_radio = QRadioButton("YOLO")
        self.method_yolo_radio.setToolTip("Usa apenas o modelo de Deep Learning. Requer modelo treinado.")
        self.method_group.addButton(self.method_yolo_radio, 2)
        method_grid_layout.addWidget(self.method_yolo_radio, 0, 1)

        self.method_combined_radio = QRadioButton("Combinado (YOLO + HSV)")
        self.method_combined_radio.setToolTip("Usa YOLO para detecção e HSV para refinar, identificando sementes duplas. Mais robusto.")
        self.method_group.addButton(self.method_combined_radio, 3)
        method_grid_layout.addWidget(self.method_combined_radio, 1, 0, 1, 2)
        self.analysis_params_layout.addLayout(method_grid_layout, 0, 1, 1, 2)'''

        self.analysis_params_layout.addWidget(create_styled_label("🌱 Semente | Deliniamento:"), 1, 0)
        self.seed_type_combo = QComboBox()
        self.seed_type_combo.setPlaceholderText("Tipo de Semente")
        self.seed_type_combo.currentTextChanged.connect(self.set_seed_type)
        self.analysis_params_layout.addWidget(self.seed_type_combo, 1, 1)

        self.tube_type_combo = QComboBox()
        self.tube_type_combo.setPlaceholderText("Deliniamento")
        self.tube_type_combo.currentTextChanged.connect(self.set_tube_type)
        self.analysis_params_layout.addWidget(self.tube_type_combo, 1, 2)

        self.analysis_params_layout.addWidget(create_styled_label("⚡ Vel. (km/h) | Nº Sementes:"), 2, 0)
        self.speed_combo = QComboBox()
        self.speed_combo.setPlaceholderText("Vel. (km/h)")
        self.speed_combo.currentTextChanged.connect(self.set_planting_speed)
        self.analysis_params_layout.addWidget(self.speed_combo, 2, 1)

        self.auto_save_count_input = QLineEdit(str(self.auto_save_seed_count))
        self.auto_save_count_input.setToolTip("Salvar automaticamente ao atingir este nº de sementes")
        self.auto_save_count_input.setValidator(QIntValidator(1, 9999))
        self.analysis_params_layout.addWidget(self.auto_save_count_input, 2, 2)

        self.analysis_params_layout.addWidget(create_styled_label("📏 Sem./m | Esp. Fileiras:"), 3, 0)
        self.seeds_per_m_input = QLineEdit()
        self.seeds_per_m_input.setPlaceholderText("ex: 10")
        self.seeds_per_m_input.textChanged.connect(self.set_seeds_per_meter)
        self.seeds_per_m_input.textChanged.connect(self.update_ideal_spacing_display)
        self.analysis_params_layout.addWidget(self.seeds_per_m_input, 3, 1)

        self.row_spacing_combo = QComboBox()
        self.row_spacing_combo.setToolTip("Espaçamento entre fileiras em metros.")
        self.row_spacing_combo.addItems(["0.40", "0.45", "0.50", "0.55", "0.60"])
        self.analysis_params_layout.addWidget(self.row_spacing_combo, 3, 2)

        self.analysis_params_layout.addWidget(create_styled_label("🎯 Pixels/cm:"), 4, 0)
        
        self.pixels_cm_display = QLineEdit()
        self.pixels_cm_display.setPlaceholderText("--")
        self.pixels_cm_display.setReadOnly(True)
        self.analysis_params_layout.addWidget(self.pixels_cm_display, 4, 1)

        calibrate_btn = QPushButton("Calibrar")
        calibrate_btn.setStyleSheet('''
            QPushButton {
                background-color: #f59e0b; /* Amarelo */
                color: black; /* CORREÇÃO: Texto preto para melhor contraste */
                font-weight: bold;
                padding: 4px 12px;
            }
            QPushButton:hover { background-color: #d97706; }
        ''')
        calibrate_btn.clicked.connect(self.show_calibration_tab)
        self.analysis_params_layout.addWidget(calibrate_btn, 4, 2)
        
        left_panel_layout.addWidget(analysis_params_group)

        counters_group = QGroupBox("Resultados da Análise")
        counters_layout = QVBoxLayout(counters_group)
        self.total_counter_widget = self.create_total_counter_widget()
        counters_layout.addWidget(self.total_counter_widget)
        self.bar_chart_widget = self.create_bar_chart_widget()
        counters_layout.addWidget(self.bar_chart_widget)

        cv_frame = QFrame()
        cv_layout = QHBoxLayout(cv_frame)
        cv_layout.setContentsMargins(8, 5, 8, 5)
        cv_frame.setStyleSheet("background-color: #f1f5f9; border-radius: 6px; border: 1px solid #e2e8f0;")

        cv_label = QLabel("📈 Coeficiente de Variação (CV):")
        cv_label.setStyleSheet("font-weight: bold; color: #475569; background: transparent; border: none;")
        cv_layout.addWidget(cv_label)
        cv_layout.addStretch()

        self.cv_value_label = QLabel("0.0%")
        self.cv_value_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #1e293b; background: transparent; border: none;")
        cv_layout.addWidget(self.cv_value_label)
        counters_layout.addWidget(cv_frame)

        left_panel_layout.addWidget(counters_group)

        left_panel_layout.addStretch(1)
        main_h_layout.addWidget(left_panel)

        right_panel_container = QWidget()
        right_panel_container_layout = QVBoxLayout(right_panel_container)
        right_panel_container_layout.setContentsMargins(0,0,0,0)
        right_panel = QFrame()
        right_panel_layout = QVBoxLayout(right_panel)
        right_panel_layout.setAlignment(Qt.AlignTop)
        right_panel_layout.setContentsMargins(10, 0, 0, 0)
        right_panel_layout.setSpacing(5)

        video_container = QWidget()
        video_container.setFixedSize(self.VIDEO_FRAME_WIDTH, self.VIDEO_FRAME_HEIGHT)
        video_container_layout = QVBoxLayout(video_container)
        video_container_layout.setContentsMargins(0, 0, 0, 0)

        self.video_label = ClickableLabel()
        self.video_label.parent_app = self
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet('''
            QLabel {
                border: 2px dashed #94a3b8;
                background-color: #f8fafc;
                border-radius: 8px;
                color: black;
                font-size: 16px;
                font-weight: bold;
            }
        ''')
        video_container_layout.addWidget(self.video_label)

        info_container = QWidget(parent=video_container)
        info_container.setStyleSheet("background-color: transparent;")
        info_layout = QHBoxLayout(info_container)
        info_layout.setContentsMargins(10, 5, 10, 5)
        info_layout.setSpacing(10)

        self.resolution_label = QLabel("Resolução: N/A")
        self.time_label = QLabel("Tempo: 00:00:000")
        self.time_label.setAlignment(Qt.AlignRight)
        
        info_label_style = "color: white; font-size: 12px; font-weight: bold; background-color: transparent;"
        info_container.setStyleSheet(info_label_style)
        info_container.setFixedWidth(self.VIDEO_FRAME_WIDTH - 10)

        right_panel_layout.addWidget(video_container)

        adjustments_layout = QHBoxLayout()
        adjustments_layout.setSpacing(15)
        # --- INÍCIO DO CÓDIGO DOS SLIDERS ---

        adjustments_layout = QHBoxLayout()
        adjustments_layout.setSpacing(15)

        # Função auxiliar interna para criar os grupos de slider (AGORA EM LINHA)
        def create_slider_group(label_text):
            # Layout principal (Horizontal)
            group_layout = QHBoxLayout()
            group_layout.setSpacing(10)
            group_layout.setContentsMargins(0, 0, 0, 0) # Remove margens

            # 1. Rótulo (Texto)
            label = QLabel(label_text)
            label.setStyleSheet("color: #1e40af; font-weight: bold; background: transparent; font-size: 11px;")
            label.setFixedWidth(90) # Largura fixa para alinhar as réguas
            group_layout.addWidget(label)

            # 2. Slider
            slider = QSlider(Qt.Horizontal)
            slider.setRange(-100, 100)
            slider.setValue(0)
            slider.setFixedWidth(120)

            # 3. Rótulo de Valor (0K ou 0%)
            value_label = QLabel("0")
            value_label.setStyleSheet("color: #1e293b; font-weight: bold; background: transparent;")
            value_label.setFixedWidth(40)

            group_layout.addWidget(slider)
            group_layout.addWidget(value_label)
            
            # Encapsula o QHBoxLayout em um QWidget para que possa ser adicionado a outro layout
            widget = QWidget()
            widget.setLayout(group_layout)
            
            return widget, slider, value_label

        # Criando o slider de Temperatura
        temp_widget, self.temperature_slider, self.temperature_value_label = create_slider_group("🌡️ Temperatura")
        self.temperature_value_label.setText("0K") # Define o sufixo "K"
        self.temperature_slider.valueChanged.connect(self.adjust_temperature)
        adjustments_layout.addWidget(temp_widget) # <-- CORREÇÃO: addWidget, pois temp_widget é um QWidget

        # Criando o slider de Saturação
        sat_widget, self.saturation_slider, self.saturation_value_label = create_slider_group("🎨 Saturação")
        self.saturation_value_label.setText("0%") # Define o sufixo "%"
        self.saturation_slider.valueChanged.connect(self.adjust_saturation)
        adjustments_layout.addWidget(sat_widget) # <-- CORREÇÃO: addWidget, pois sat_widget é um QWidget

        # --- FIM DO CÓDIGO DOS SLIDERS ---
        # Linha 3362 (Substitua este bloco de código)
        bottom_controls_layout = QHBoxLayout()
        bottom_controls_layout.setContentsMargins(0, 10, 30, 0) # CORREÇÃO: Aumenta a margem direita para 30
        bottom_controls_layout.addLayout(adjustments_layout)
        bottom_controls_layout.addStretch(1)
        
        self.speed_ruler = SpeedRulerWidget()
        self.speed_ruler.setValue(3)
        self.speed_ruler.valueChanged.connect(self.set_playback_speed)
        self.speed_ruler.setMinimumWidth(150)
        bottom_controls_layout.addWidget(self.speed_ruler)

        right_panel_layout.addLayout(bottom_controls_layout)
        right_panel_layout.addWidget(self.spacing_chart)
        right_panel_container_layout.addWidget(right_panel)
        main_h_layout.addWidget(right_panel_container)

        analyze_layout.addLayout(main_h_layout)

        self.start_btn.clicked.connect(self.start_analysis)
        self.pause_btn.clicked.connect(self.pause_analysis)

        for label in [self.resolution_label, self.time_label]:
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(15)
            shadow.setColor(QColor(0, 0, 0, 200))
            shadow.setOffset(1, 1)
            label.setGraphicsEffect(shadow)

        info_layout.addWidget(self.resolution_label)
        info_layout.addWidget(self.time_label)
        info_container.adjustSize()
        info_container.move(5, self.VIDEO_FRAME_HEIGHT - info_container.height() - 10)
        self.video_label.setText("Carregue um vídeo para iniciar a análise")

        self.save_analysis_btn.clicked.connect(self.save_and_pause_analysis)
        
    def create_total_counter_widget(self):
        """Cria o widget destacado para o contador total."""
        total_frame = QFrame()
        total_frame.setMaximumHeight(80)
        total_frame.setStyleSheet(''' 
            QFrame {
                background-color: #eef2ff;
                border: 1px solid #c7d2fe;
                border-radius: 8px;
                padding: 5px 10px;
            }
        ''')
        total_layout = QHBoxLayout(total_frame)
        total_layout.setSpacing(1)

        title_label = QLabel("🌱 Total de Sementes")
        title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        title_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title_label.setStyleSheet("color: black; border: none; background: transparent;")

        self.total_seeds_label = QLabel("0")
        self.total_seeds_label.setAlignment(Qt.AlignCenter)
        self.total_seeds_label.setMinimumWidth(70)
        self.total_seeds_label.setStyleSheet('''
            color: black; 
            background-color: #ffffff; 
            border: 1px solid #cbd5e1;
            border-radius: 6px;
            padding: 2px;
            font-family: "Segoe UI";
            font-size: 25px;
            font-weight: bold;
        ''')

        total_layout.addWidget(title_label)
        total_layout.addStretch()
        total_layout.addWidget(self.total_seeds_label)

        return total_frame

    def update_counter_widget(self, counter_type, value):
        """Atualiza o valor de um widget de contador específico."""
        self.update_bar_chart(self.aceitavel_count, self.falha_count, self.multipla_count)

    def create_bar_chart_widget(self):
        """Cria um widget para exibir o gráfico de barras lateral."""
        self.bar_chart_widget = pg.PlotWidget()
        self.bar_chart_widget.setBackground('#f8fafc')
        self.bar_chart_widget.getPlotItem().hideAxis('bottom')
        self.bar_chart_widget.getPlotItem().getAxis('left').setTextPen('#1e293b')
        self.bar_chart_widget.setMinimumHeight(120)
        self.bar_chart_widget.setMaximumHeight(150)

        categories = [(0, 'Múltipla'), (1, 'Falha'), (2, 'Aceitável')]
        ax = self.bar_chart_widget.getAxis('left')
        ax.setTicks([categories])

        # --- ALTERAÇÃO: Remove o preenchimento e usa apenas contorno colorido ---
        colors = ['#7c3aed', '#f03434', '#059669']
        light_colors_with_alpha = [(196, 181, 253, 100), (252, 165, 165, 100), (134, 239, 172, 100)]
        pens = [pg.mkPen(c, width=2) for c in colors]
        brushes = [pg.mkBrush(color) for color in light_colors_with_alpha]
        self.bar_chart_item = pg.BarGraphItem(x0=0, y=range(3), height=0.6, width=[0,0,0], pens=pens, brushes=brushes)
        self.bar_chart_widget.addItem(self.bar_chart_item)

        # --- NOVO: Linha vertical para o índice de 80% aceitável ---
        self.acceptable_line = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('#16a34a', style=Qt.DashLine, width=1.5))
        self.acceptable_line_label = pg.TextItem("80% Aceitável", color='#16a34a', anchor=(0, 1))
        self.bar_chart_widget.addItem(self.acceptable_line, ignoreBounds=True)
        self.bar_chart_widget.addItem(self.acceptable_line_label)
        self.acceptable_line.hide()
        self.acceptable_line_label.hide()

        self.text_items = []
        for i in range(3):
            # --- ALTERAÇÃO: Ajusta a âncora do texto para ficar dentro da barra ---
            text_item = pg.TextItem(anchor=(0, 0.5))
            text_item.setZValue(5) # Garante que o texto fique sobre a linha
            self.text_items.append(text_item)
            self.bar_chart_widget.addItem(text_item)

        self.update_bar_chart(0, 0, 0)
        return self.bar_chart_widget

    def update_bar_chart(self, aceitavel, falha, multipla):
        """Atualiza o gráfico de barras lateral com os novos valores."""
        if hasattr(self, 'bar_chart_item'):
            values = [multipla, falha, aceitavel]        
            total = sum(values)
            
            # --- ALTERAÇÃO: Usa setOpts para atualizar 'pens' e 'width' ---
            colors = ['#7c3aed', '#f03434', '#059669']
            light_colors_with_alpha = [(196, 181, 253, 100), (252, 165, 165, 100), (134, 239, 172, 100)]
            pens = [pg.mkPen(c, width=2) for c in colors]
            brushes = [pg.mkBrush(color) for color in light_colors_with_alpha]
            self.bar_chart_item.setOpts(width=values, pens=pens, brushes=brushes)

            for i, value in enumerate(values):
                text_color = pens[i].color()
                if total > 0:
                    percentage = (value / total) * 100
                    text = f"{value} ({percentage:.1f}%)"
                else:
                    text = "0 (0.0%)"
                self.text_items[i].setText(text, color=text_color)
                self.text_items[i].setPos(value * 0.02, i) # Posição ligeiramente dentro da barra

            # --- NOVO: Lógica para exibir a linha de 80% ---
            if total > 0 and aceitavel > 0:
                acceptable_pct = (aceitavel / total * 100) if total > 0 else 0
                acceptable_target_count = (aceitavel / (acceptable_pct / 100)) * 0.8 if acceptable_pct > 0 else 0
                self.acceptable_line.setPos(acceptable_target_count)
                self.acceptable_line_label.setPos(acceptable_target_count, 2.8) # Posição acima da barra 'Aceitável'
                self.acceptable_line.show()
                self.acceptable_line_label.show()
            else:
                self.acceptable_line.hide()
                self.acceptable_line_label.hide()

            max_val = max(values) if any(values) else 1
            self.bar_chart_widget.setXRange(0, max_val * 1.1)

    def setup_reports_tab(self):
        """Configura a aba de relatórios."""
        reports_layout = QVBoxLayout(self.reports_tab)
        reports_layout.setContentsMargins(15, 15, 15, 15)
        reports_layout.setSpacing(15)

        top_bar_layout = QHBoxLayout()

        title_label = QLabel("📊 RELATÓRIOS DE ANÁLISE")
        title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #1e40af; margin-bottom: 10px;")
        top_bar_layout.addWidget(title_label)
        top_bar_layout.addStretch()

        # --- NOVO: Botão para salvar todas as análises ---
        self.save_all_btn = QPushButton("💾 Salvar Todas as Análises")
        self.save_all_btn.setStyleSheet('''
            QPushButton {
                background-color: #16a34a; /* Verde */
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #15803d; }
        ''')
        self.save_all_btn.clicked.connect(self.save_all_analyses_to_pdf)
        top_bar_layout.addWidget(self.save_all_btn)

        self.clear_all_analyses_btn = QPushButton("🗑️ Limpar Todas as Análises")
        self.clear_all_analyses_btn.setStyleSheet('''
            QPushButton {
                background-color: #ef4444;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #dc2626; }
            QPushButton:pressed { background-color: #b91c1c; }
        ''')
        self.clear_all_analyses_btn.clicked.connect(self.clear_all_analyses)
        top_bar_layout.addWidget(self.clear_all_analyses_btn)
        reports_layout.addLayout(top_bar_layout)

        self.reports_scroll_area = QScrollArea()
        self.reports_scroll_area.setWidgetResizable(True)
        self.reports_content_widget = QWidget()
        self.reports_content_widget.setStyleSheet("background-color: #ffffff;")
        self.reports_grid_layout = QGridLayout(self.reports_content_widget)
        self.reports_scroll_area.setWidget(self.reports_content_widget)
        reports_layout.addWidget(self.reports_scroll_area)

        self.update_reports_display()

    def update_reports_display(self):
        """Atualiza a exibição dos cartões de análise na aba de relatórios."""
        for i in reversed(range(self.reports_grid_layout.count())):
            widget = self.reports_grid_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        row, col = 0, 0
        for analysis_data in self.analysis_results:
            card = AnalysisCard(analysis_data, analysis_data['id'], f"{CURRENT_VERSION}")
            card.close_requested.connect(self.remove_analysis)
            card.notes_updated.connect(self.update_analysis_notes) # Conecta o novo sinal
            self.reports_grid_layout.addWidget(card, row, col)
            col += 1
            if col >= 1: # --- ALTERAÇÃO: Mostra 1 cartão por linha ---
                col = 0
                row += 1
        self.reports_grid_layout.setRowStretch(row + 1, 1)
        self.reports_grid_layout.setColumnStretch(1, 1)

    def remove_analysis(self, card_id):
        """Remove uma análise da lista e atualiza a exibição."""
        self.analysis_results = [res for res in self.analysis_results if res['id'] != card_id]
        self.update_reports_display()

    def clear_all_analyses(self):
        """Limpa todos os resultados de análise e atualiza a exibição."""
        reply = QMessageBox.question(self, 'Confirmar Limpeza', 
                                     "Tem certeza que deseja limpar todas as análises? Esta ação é irreversível.",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.analysis_results = []
            self.next_analysis_id = 1
            self.update_reports_display()
            msg = QMessageBox.information(self, "Limpeza Concluída", "Todas as análises foram removidas.")
            msg.setStyleSheet(DARK_MESSAGE_BOX_STYLE)
            msg.exec()

    def update_analysis_notes(self, card_id, notes):
        """Atualiza as notas de uma análise específica."""
        for analysis in self.analysis_results:
            if analysis['id'] == card_id:
                analysis['notes'] = notes
                break

    def _generate_story_for_analysis(self, analysis_data, styles):
        """Helper para gerar o conteúdo de uma única análise para o PDF consolidado."""
        story = []

        # Título da Análise
        video_source = analysis_data.get('video_path', 'Análise')
        title_text = f"Relatório da Análise ID: {analysis_data.get('id', 'N/A')} - {os.path.basename(str(video_source))}"
        story.append(Paragraph(title_text, styles['h2']))
        story.append(Spacer(1, 0.2*inch))

        # Dados da análise
        aceitavel = analysis_data.get('aceitavel', 0)
        falha = analysis_data.get('falha', 0)
        multipla = analysis_data.get('multipla', 0)
        total = aceitavel + falha + multipla
        aceitavel_pct = (aceitavel / total * 100) if total > 0 else 0
        falha_pct = (falha / total * 100) if total > 0 else 0
        multipla_pct = (multipla / total * 100) if total > 0 else 0

        # Tabela de Resultados
        results_data = [
            ['Categoria', 'Qtd', '%'],
            ['Aceitável', str(aceitavel), f"{aceitavel_pct:.1f}%"],
            ['Falha', str(falha), f"{falha_pct:.1f}%"],
            ['Múltipla', str(multipla), f"{multipla_pct:.1f}%"],
            ['TOTAL', str(total), "100%"],
        ]
        results_table = Table(results_data, colWidths=[1.2*inch, 0.8*inch, 0.8*inch])
        results_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#dcfce7')),
            ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#fee2e2')),
            ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#f3e8ff')),
        ]))

        # Tabela de Informações
        info_data = [
            ['Tipo de Semente:', analysis_data.get('seed_type', 'N/A')],
            ['Velocidade:', f"{analysis_data.get('planting_speed', 'N/A')} km/h"],
            ['Sementes/m:', analysis_data.get('seeds_per_meter', 'N/A')],
            ['Duração:', analysis_data.get('duration', 'N/A')],
        ]
        info_table = Table(info_data, colWidths=[1.5*inch, 2.0*inch])
        info_table.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.grey)]))

        # Combina as duas tabelas lado a lado
        combined_table = Table([[results_table, info_table]], colWidths=[3.0*inch, 3.7*inch], style=[('VALIGN', (0,0), (-1,-1), 'TOP')])
        story.append(combined_table)
        story.append(Spacer(1, 0.2*inch))

        # Gráfico de Barras
        fig, ax = plt.subplots(figsize=(6, 2.5))
        categories = ["Aceitável", "Falha", "Múltipla"]
        values = [aceitavel, falha, multipla]
        colors_chart = ["#059669", "#dc2626", "#7c3aed"]
        ax.bar(categories, values, color=colors_chart, alpha=0.8, width=0.5)
        for i, v in enumerate(values):
            ax.text(i, v + max(values)*0.02, str(v), ha='center', fontweight='bold')
        ax.set_ylabel("Quantidade")
        ax.set_ylim(0, max(values) * 1.25 if max(values) > 0 else 1)
        
        buffer_chart = BytesIO()
        plt.savefig(buffer_chart, format="png", dpi=150, bbox_inches="tight")
        buffer_chart.seek(0)
        plt.close(fig)
        story.append(RLImage(buffer_chart, width=6.5 * inch, height=2.8 * inch))
        story.append(Spacer(1, 0.3*inch))

        return story

    def save_all_analyses_to_pdf(self):
        """Salva todas as análises visíveis em um único arquivo PDF."""
        if not self.analysis_results:
            QMessageBox.warning(self, "Nenhuma Análise", "Não há análises para salvar em um relatório consolidado.")
            return

        try:
            # --- CORREÇÃO: Redireciona o salvamento para a pasta do vídeo ---
            # Usa o caminho do vídeo da primeira análise como referência
            if self.video_path and os.path.isdir(os.path.dirname(self.video_path)):
                save_dir = os.path.dirname(self.video_path)
            else:
                # Se não, usa o diretório padrão como fallback
                save_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "SVA")
            
            os.makedirs(save_dir, exist_ok=True)
            
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Salvar Relatório Consolidado",
                os.path.join(save_dir, f"relatorio_consolidado_{datetime.now().strftime('%Y%m%d')}.pdf"),
                "PDF Files (*.pdf)"
            )

            if filename:
                doc = SimpleDocTemplate(filename, pagesize=landscape(letter),
                                        rightMargin=0.3*inch, leftMargin=0.3*inch,
                                        topMargin=0.3*inch, bottomMargin=0.4*inch)
                styles = getSampleStyleSheet()
                styles.add(ParagraphStyle(name='Small', fontSize=8, leading=10, textColor=colors.HexColor('#475569')))
                styles.add(ParagraphStyle(name='StatLabel', fontSize=9, fontName='Helvetica'))
                styles.add(ParagraphStyle(name='StatValue', fontSize=9, fontName='Helvetica-Bold', alignment=2))
                styles.add(ParagraphStyle(name='BoxTitle', fontSize=10, fontName='Helvetica-Bold', textColor=colors.HexColor('#1e293b')))
                
                story = []
                for i, analysis_data in enumerate(self.analysis_results):
                    card = AnalysisCard(analysis_data, analysis_data['id'], f"{CURRENT_VERSION}")
                    story.extend(card.get_pdf_story_elements(styles))
                    if i < len(self.analysis_results) - 1:
                        story.append(PageBreak())

                doc.build(story)
                msg=QMessageBox.information(self, "Sucesso", f"Relatório consolidado salvo com sucesso em:\n{filename}")
                msg.setStyleSheet(DARK_MESSAGE_BOX_STYLE)
                msg.exec()

        except Exception as e:
            msg=QMessageBox.critical(self, "Erro", f"Erro ao gerar o relatório PDF consolidado:\n{str(e)}")
            msg.setStyleSheet(DARK_MESSAGE_BOX_STYLE)
            msg.exec()

    def setup_statistics_tab(self):
        """Configura a aba de estatísticas com a funcionalidade ANOVA."""
        main_layout = QVBoxLayout(self.statistics_tab)
        main_layout.setContentsMargins(15, 15, 15, 10)
        
        vertical_splitter = QSplitter(Qt.Vertical)
        vertical_splitter.setStyleSheet("QSplitter::handle { background-color: transparent; }")
        vertical_splitter.setHandleWidth(1)

        table_section_widget = QWidget()
        table_section_layout = QVBoxLayout(table_section_widget)
        table_section_layout.setContentsMargins(0, 0, 0, 0)
        
        self.stats_table = QTableWidget()
        table_section_layout.addWidget(self.stats_table) 

        button_layout = QHBoxLayout()
        button_layout.addStretch() 

        self.import_csv_btn = QPushButton("📂 Importar CSV")
        self.import_csv_btn.setToolTip("Importar dados de um arquivo CSV para a tabela de estatísticas")
        self.import_csv_btn.setCursor(Qt.PointingHandCursor)
        self.import_csv_btn.clicked.connect(self.import_statistics_from_csv)
        button_layout.addWidget(self.import_csv_btn)

        self.export_csv_btn = QPushButton("💾 Salvar como CSV")
        self.export_csv_btn.setToolTip("Exportar os dados da tabela para um arquivo CSV")
        self.export_csv_btn.setCursor(Qt.PointingHandCursor)
        self.export_csv_btn.clicked.connect(self.export_statistics_to_csv)
        button_layout.addWidget(self.export_csv_btn)
        table_section_layout.addLayout(button_layout)
        
        vertical_splitter.addWidget(table_section_widget)
        
        anova_group = QGroupBox("Análise Estatística Comparativa")
        anova_group.setStyleSheet("""
            QGroupBox { background-color: white; }
            QGroupBox::title { color: #1e293b; }
        """)
        anova_layout = QVBoxLayout(anova_group)

        anova_controls_layout = QHBoxLayout()
        
        anova_label = QLabel("<b>Variável de Resposta (Y):</b>")
        anova_label.setStyleSheet("color: black;")
        anova_controls_layout.addWidget(anova_label)

        self.anova_variable_combo = QComboBox()
        self.anova_variable_combo.setStyleSheet("""
            QComboBox { color: black; }
            QComboBox QAbstractItemView {
                background-color: white;
                color: black;
            }
        """)
        self.anova_variable_combo.addItems([
            'Aceitável (%)', 'Falha (%)', 'Múltipla (%)', 'CV (%)',
            'Média (cm)', 'Mediana (cm)', 'Desv. P. (cm)'
        ])
        anova_controls_layout.addWidget(self.anova_variable_combo)
        
        anova_controls_layout.addStretch()

        self.run_anova_btn = QPushButton("📊 Gerar Análise Estatística")
        self.run_anova_btn.setStyleSheet('''
            QPushButton { background-color: #1e40af; color: white; padding: 8px; font-weight: bold; }
            QPushButton:hover { background-color: #1c3d99; }
        ''')
        self.run_anova_btn.clicked.connect(self.perform_statistical_analysis)
        anova_controls_layout.addWidget(self.run_anova_btn)

        self.save_pdf_btn = QPushButton("💾 Salvar PDF")
        self.save_pdf_btn.setStyleSheet('''
            QPushButton { background-color: #10b981; color: white; border-radius: 5px; padding: 8px 15px; font-weight: bold; }
            QPushButton:hover { background-color: #059669; }
        ''')
        self.save_pdf_btn.setEnabled(True)
        self.save_pdf_btn.clicked.connect(self.save_anova_results_to_pdf)
        anova_controls_layout.addWidget(self.save_pdf_btn)
        
        anova_layout.addLayout(anova_controls_layout)

        results_splitter = QSplitter(Qt.Horizontal)
        results_splitter.setStyleSheet("QSplitter::handle { background-color: transparent; }")
        results_splitter.setHandleWidth(1)
        
        self.anova_results_box = QTextEdit()
        self.anova_results_box.setReadOnly(True)
        self.anova_results_box.setPlaceholderText("Os resultados da análise (Descritiva e Teste de Tukey) aparecerão aqui...")
        self.anova_results_box.setStyleSheet("background-color: white; color: black; font-family: 'Courier New';")
        self.anova_results_box.setMinimumHeight(200)
        results_splitter.addWidget(self.anova_results_box)
        
        self.anova_graph_area = QWidget()
        self.anova_graph_area.setStyleSheet("background-color: #f3f4f6; border: none;")
        graph_layout = QVBoxLayout(self.anova_graph_area)
        graph_layout.setAlignment(Qt.AlignCenter)
        graph_layout.addWidget(QLabel("O Gráfico de Interação será exibido aqui após a análise."))
        
        results_splitter.addWidget(self.anova_graph_area)
        
        anova_layout.addWidget(results_splitter)

        vertical_splitter.addWidget(anova_group)
        main_layout.addWidget(vertical_splitter)
        
        vertical_splitter.setStretchFactor(0, 4)
        vertical_splitter.setStretchFactor(1, 6)

        self.stats_table.setAlternatingRowColors(True)
        self.stats_table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        self.stats_table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                color: black;
                /* --- ALTERAÇÃO: Cor da grade alterada para cinza claro --- */
                gridline-color: #e5e7eb; 
                border: 1px solid #d1d5db; 
                alternate-background-color: #f9fafb; 
                selection-background-color: #dbeafe; 
                selection-color: black; 
            }
            QTableWidget::item {
                color: black;
                padding: 4px;
                border: none;
            }
            QHeaderView::section {
                background-color: #f3f4f6;
                color: black;
                font-weight: bold;
                padding: 5px;
                border: none;
                border-bottom: 2px solid #d1d5db;
            }
            QPushButton {
                background-color: transparent;
                border: none;
                padding: 4px;
            }
            QPushButton:hover {
                background-color: #fee2e2;
                border-radius: 4px;
            }
        """)
        self.update_statistics_table()

    def update_statistics_table(self):
        """Atualiza a tabela na aba de estatísticas com os dados das análises."""
        if not hasattr(self, 'stats_table'):
            return

        self.stats_table.setRowCount(0)
        
        headers = [
            "Repetição", "Deliniamento", "Tipo de\nSemente", "Vel. Esteira\n(km/h)", "Sem./m", "Esp. Fileira\n(m)",
            "Total\nSem.", "Aceitável\n(%)", "Falha\n(%)", "Múltipla\n(%)", "CV (%)",
            "Média\n(cm)", "Mediana\n(cm)", "1Q(cm)", "3Q (cm)", "Desv. P\n(cm)", "Soma\nEsp. (m)", "Área (m2)",
            "Ação"
        ]
        self.stats_table.setColumnCount(len(headers))
        self.stats_table.setHorizontalHeaderLabels(headers)

        for analysis in self.analysis_results:
            row_position = self.stats_table.rowCount()
            self.stats_table.insertRow(row_position)

            # --- INÍCIO DA CORREÇÃO ---
            # Define as variáveis de estatística
            cv_percentage, mean_spacing, median_spacing, q1, q3, std_dev, sum_spacing_m, area_m2 = (0, 0, 0, 0, 0, 0, 0, 0)

            # Verifica se a análise foi importada de um CSV
            if analysis.get('is_imported'):
                # Se foi importada, pega os valores de estatística que já vieram prontos
                stats = analysis.get('imported_stats', {})
                cv_percentage = stats.get('cv_pct', 0)
                mean_spacing = stats.get('mean_cm', 0)
                median_spacing = stats.get('median_cm', 0)
                q1 = stats.get('q1_cm', 0)
                q3 = stats.get('q3_cm', 0)
                std_dev = stats.get('std_dev_cm', 0)
                sum_spacing_m = stats.get('sum_spacing_m', 0)
                
                # Calcula a área com os dados importados
                row_spacing_m = float(str(analysis.get('row_spacing', '0')).replace(',', '.'))
                area_m2 = row_spacing_m * sum_spacing_m if row_spacing_m > 0 else 0
            else:
                # Se a análise foi feita no programa, calcula as estatísticas na hora
                all_spacing_data = analysis.get('spacing_data', [])
                acceptable_spacing_values = [d['spacing_cm'] for d in all_spacing_data if d.get('class') == 'aceitavel']
                
                if acceptable_spacing_values:
                    mean_spacing = np.mean(acceptable_spacing_values)
                    std_dev = np.std(acceptable_spacing_values)
                    cv_percentage = (std_dev / mean_spacing * 100) if mean_spacing > 0 else 0
                    median_spacing = np.median(acceptable_spacing_values)
                    q1 = np.percentile(acceptable_spacing_values, 25)
                    q3 = np.percentile(acceptable_spacing_values, 75)
                
                all_spacing_values_cm = [d['spacing_cm'] for d in all_spacing_data]
                if all_spacing_values_cm:
                    sum_spacing_m = sum(all_spacing_values_cm) / 100.0
                    row_spacing_m = float(str(analysis.get('row_spacing', '0')).replace(',', '.'))
                    area_m2 = row_spacing_m * sum_spacing_m if row_spacing_m > 0 else 0
            # --- FIM DA CORREÇÃO ---

            total = analysis.get('total_seeds', 0)
            aceitavel = analysis.get('aceitavel', 0)
            falha = analysis.get('falha', 0)
            multipla = analysis.get('multipla', 0)
            aceitavel_pct = (aceitavel / total * 100) if total > 0 else 0
            falha_pct = (falha / total * 100) if total > 0 else 0
            multipla_pct = (multipla / total * 100) if total > 0 else 0

            data_to_add = [
                str(analysis.get('repetition_count', 1)),
                str(analysis.get('tube_type', '')),
                analysis.get('seed_type', ''),
                str(analysis.get('planting_speed', '')),
                str(analysis.get('seeds_per_meter', '')),
                str(analysis.get('row_spacing', '')),
                str(total),
                f"{aceitavel_pct:.1f}",
                f"{falha_pct:.1f}",
                f"{multipla_pct:.1f}",
                f"{cv_percentage:.1f}",
                f"{mean_spacing:.2f}",
                f"{median_spacing:.2f}",
                f"{q1:.2f}",
                f"{q3:.2f}",
                f"{std_dev:.2f}",
                f"{sum_spacing_m:.2f}",
                f"{area_m2:.4f}"
            ]

            for col, data in enumerate(data_to_add):
                self.stats_table.setItem(row_position, col, QTableWidgetItem(data))
            
            if analysis.get('repetition_count', 1) > 1:
                for col in range(len(headers)):
                    item = self.stats_table.item(row_position, col)
                    if item: item.setBackground(QColor("#fee2e2"))

            delete_btn = QPushButton()
            delete_btn.setIcon(self.style().standardIcon(QStyle.SP_TrashIcon))
            delete_btn.setToolTip("Excluir esta análise")
            delete_btn.setCursor(Qt.PointingHandCursor)
            delete_btn.clicked.connect(lambda checked=False, analysis_id=analysis.get('id'): self.delete_analysis_from_table(analysis_id))
            self.stats_table.setCellWidget(row_position, len(headers) - 1, delete_btn)

        self.stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.stats_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.stats_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.stats_table.horizontalHeader().setSectionResizeMode(len(headers) - 1, QHeaderView.ResizeToContents)

    def import_statistics_from_csv(self):
        """Abre um diálogo para importar dados de um arquivo CSV e adicioná-los às análises."""
        project_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "SVA")
        path, _ = QFileDialog.getOpenFileName(self, "Importar Arquivo CSV", project_dir, "CSV Files (*.csv)")

        if not path:
            return

        try:
            import pandas as pd
            # Utiliza a biblioteca pandas para ler o CSV de forma robusta
            df = pd.read_csv(path, sep=';', decimal=',')

            imported_analyses = []
            for index, row in df.iterrows():
                try:
                    total_seeds = float(row.get("Total Sem.", 0))
                    aceitavel_pct = float(row.get("Aceitável (%)", 0))
                    falha_pct = float(row.get("Falha (%)", 0))
                    multipla_pct = float(row.get("Múltipla (%)", 0))

                    # --- INÍCIO DA CORREÇÃO ---
                    # Agora, lemos e armazenamos as estatísticas que já vêm prontas do CSV
                    analysis_data = {
                        'id': self.next_analysis_id,
                        'datetime': datetime.now().strftime("%d/%m/%Y %H:%M"),
                        'video_path': f"Importado de {os.path.basename(path)}",
                        'repetition_count': int(row.get("Repetição", 1)),
                        'tube_type': row.get("Deliniamento", "N/A"),
                        'seed_type': row.get("Tipo de Semente", "N/A"),
                        'planting_speed': float(row.get("Vel. Esteira (km/h)", 0)),
                        'seeds_per_meter': float(row.get("Sem./m", 0)),
                        'row_spacing': float(row.get("Esp. Fileira (m)", 0)),
                        'total_seeds': total_seeds,
                        'aceitavel': round(total_seeds * (aceitavel_pct / 100.0)),
                        'falha': round(total_seeds * (falha_pct / 100.0)),
                        'multipla': round(total_seeds * (multipla_pct / 100.0)),
                        'spacing_data': [], # Deixamos vazio pois usaremos os dados prontos
                        'notes': 'Dados importados de CSV.',
                        
                        # Adiciona um marcador e um dicionário com as estatísticas prontas
                        'is_imported': True,
                        'imported_stats': {
                            'cv_pct': float(row.get("CV (%)", 0)),
                            'mean_cm': float(row.get("Média (cm)", 0)),
                            'median_cm': float(row.get("Mediana (cm)", 0)),
                            'q1_cm': float(row.get("1Q(cm)", 0)),
                            'q3_cm': float(row.get("3Q (cm)", 0)),
                            'std_dev_cm': float(row.get("Desv. P. (cm)", 0)),
                            'sum_spacing_m': float(row.get("Soma Esp. (m)", 0))
                        }
                    }
                    # --- FIM DA CORREÇÃO ---
                    
                    imported_analyses.append(analysis_data)
                    self.next_analysis_id += 1
                except (ValueError, TypeError, KeyError) as e:
                    print(f"Aviso: Pulando linha inválida no CSV. Erro: {e}\nDados da linha: {row}")
                    continue

            if not imported_analyses:
                QMessageBox.warning(self, "Importação Vazia", "Nenhum registro válido foi encontrado ou lido do arquivo CSV.")
                return

            self.analysis_results.extend(imported_analyses)
            self.update_statistics_table()
            self.update_reports_display()
            self.anova_results_box.clear()
            
            if hasattr(self, 'anova_graph_area') and self.anova_graph_area.layout():
                while self.anova_graph_area.layout().count():
                    child = self.anova_graph_area.layout().takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()
            
            msg = QMessageBox.information(self, "Sucesso", f"{len(imported_analyses)} registros importados com sucesso do arquivo CSV.")
            msg.setStyleSheet(DARK_MESSAGE_BOX_STYLE)
            msg.exec()

        except Exception as e:
            msg = QMessageBox.critical(self, "Erro de Importação", f"Ocorreu um erro grave ao ler o arquivo CSV:\n{str(e)}\n\nVerifique se o arquivo está no formato correto (separado por ';').")
            msg.setStyleSheet(DARK_MESSAGE_BOX_STYLE)
            msg.exec()
    def delete_analysis_from_table(self, analysis_id_to_delete):
        """Remove uma análise da lista de resultados e atualiza as visualizações."""
        self.analysis_results = [res for res in self.analysis_results if res.get('id') != analysis_id_to_delete]
        self.update_statistics_table() # Atualiza a tabela de estatísticas
        self.update_reports_display()  # Mantém a aba de relatórios sincronizada
    
    def perform_statistical_analysis(self):
        """
        Extrai dados da tabela, calcula estatísticas descritivas e executa
        um teste de Tukey para comparações múltiplas.
        """
        if self.stats_table.rowCount() < 2:
            QMessageBox.warning(self, "Dados Insuficientes", 
                                "É necessário ter pelo menos 2 linhas de dados para realizar uma análise estatística.")
            return

        try:
            # --- NOVO: IMPORTAÇÕES LOCAIS PARA ACELERAR A INICIALIZAÇÃO ---
            import pandas as pd
            from statsmodels.stats.multicomp import pairwise_tukeyhsd
            headers_raw = [self.stats_table.horizontalHeaderItem(i).text() for i in range(self.stats_table.columnCount() - 1)]
            headers = [self._normalize_header_for_pandas(h) for h in headers_raw]
            
            # --- INÍCIO DA CORREÇÃO (WORKAROUND) ---
            # Procura dinamicamente pelos nomes normalizados das colunas necessárias
            # para evitar o erro de chave (KeyError).
            try:
                tubo_col_normalized = headers[headers_raw.index("Deliniamento")]
                velocidade_col_normalized = headers[headers_raw.index("Vel. Esteira\n(km/h)")]
            except ValueError:
                msg=QMessageBox.critical(self, "Erro de Cabeçalho", "Não foi possível encontrar as colunas 'Deliniamento' ou 'Vel. Esteira (km/h)' na tabela. A análise não pode continuar.")
                msg.setStyleSheet(DARK_MESSAGE_BOX_STYLE)
                msg.exec()
            return
            # --- FIM DA CORREÇÃO ---

            data = []
            for row in range(self.stats_table.rowCount()):
                row_data = [self.stats_table.item(row, col).text().replace(',', '.')
                            for col in range(self.stats_table.columnCount() - 1)]
                data.append(row_data)

            df = pd.DataFrame(data, columns=headers)
            
            numeric_cols = ['aceitavel_pct', 'falha_pct', 'multipla_pct', 'cv_pct', 'media_cm', 'mediana_cm', 
                            'q1_cm', 'q3_cm', 'desv_p_cm']
            # Adiciona a coluna de velocidade dinamicamente à lista de colunas numéricas
            if velocidade_col_normalized not in numeric_cols:
                numeric_cols.append(velocidade_col_normalized)

            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            df.dropna(inplace=True)

            response_variable_map = {
                'Aceitável (%)': 'aceitavel_pct', 'Falha (%)': 'falha_pct', 'Múltipla (%)': 'multipla_pct',
                'CV (%)': 'cv_pct', 'Média (cm)': 'media_cm', 'Mediana (cm)': 'mediana_cm', 'Desv. P. (cm)': 'desv_p_cm'
            }
            selected_variable = self.anova_variable_combo.currentText()
            response_var = response_variable_map[selected_variable]

            if response_var not in df.columns:
                raise KeyError(f"A variável de resposta '{response_var}' não foi encontrada.")

            results_string = f"{'='*80}\n ANÁLISE ESTATÍSTICA DESCRITIVA E COMPARATIVA\n{'='*80}\n\n"
            results_string += f"Variável de Resposta: {selected_variable}\n"
            results_string += f"Número de Observações Válidas: {len(df)}\n\n"

            # Usa os nomes de coluna encontrados dinamicamente
            results_string += f"--- 1. ESTATÍSTICAS DESCRITIVAS ---\n\n"
            desc_stats = df.groupby([tubo_col_normalized, velocidade_col_normalized])[response_var].describe()
            results_string += desc_stats.to_string()
            results_string += f"\n\n"

            results_string += f"--- 2. TESTE DE COMPARAÇÃO MÚLTIPLA (TUKEY HSD) ---\n\n"
            results_string += "A coluna 'reject=True' indica que a diferença entre os grupos é estatisticamente significativa (p < 0.05).\n\n"
            
            df[tubo_col_normalized] = df[tubo_col_normalized].astype('category')
            df[velocidade_col_normalized] = df[velocidade_col_normalized].astype('category')
            df['grupo_combinado'] = df[tubo_col_normalized].astype(str) + " @ " + df[velocidade_col_normalized].astype(str) + " km/h"

            tukey_letters_summary = {}

            if df['grupo_combinado'].nunique() < 2:
                results_string += "AVISO: Não há grupos suficientes para realizar o teste de Tukey.\n"
            else:
                tukey_result = pairwise_tukeyhsd(endog=df[response_var], groups=df['grupo_combinado'], alpha=0.05)
                results_string += str(tukey_result)
                results_string += "\n\n"
                
                tukey_letters_summary = self._get_tukey_summary_and_letters(tukey_result)

                significant_pairs = []
                tukey_df = pd.DataFrame(data=tukey_result._results_table.data[1:], columns=tukey_result._results_table.data[0])
                for _, row in tukey_df.iterrows():
                    if row['reject']:
                        conclusion = f"'{row['group1']}' e '{row['group2']}' são estatisticamente diferentes."
                        significant_pairs.append(f"• {conclusion} (p-valor: {row['p-adj']:.4f})")

                if significant_pairs:
                    results_string += "--- 3. CONCLUSÕES PRINCIPAIS (TUKEY HSD) ---\n\n"
                    results_string += "\n".join(significant_pairs)
                else:
                    results_string += "--- 3. CONCLUSÕES PRINCIPAIS (TUKEY HSD) ---\n\n"
                    results_string += "Não foram encontradas diferenças estatisticamente significativas entre os grupos."

            results_string += f"\n\n{'='*80}\n FIM DA ANÁLISE\n{'='*80}\n"
            self.anova_results_box.setText(results_string)
            self.save_pdf_btn.setEnabled(True)

            self.generate_interaction_plot(df, response_var, selected_variable, tukey_letters_summary)

        except Exception as e:
            error_message = f"Ocorreu um erro ao gerar a análise estatística:\n\n{str(e)}\n\n"
            error_message += "Possíveis causas:\n"
            error_message += "- Colunas com nomes inesperados ou dados não numéricos.\n"
            error_message += "- Variação insuficiente nos dados para comparação."
            self.anova_results_box.setText(error_message)
            msg=QMessageBox.critical(self, "Erro na Análise", error_message)
            msg.setStyleSheet(DARK_MESSAGE_BOX_STYLE)
            msg.exec()

    def save_anova_results_to_pdf(self):
        """Salva os resultados da ANOVA e o gráfico em um arquivo PDF formatado."""
        
        # 1. Obter o caminho para salvar o arquivo
        default_filename = f"Analise_Estatistica_ANOVA_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        file_path, _ = QFileDialog.getSaveFileName(self, "Salvar Análise Estatística em PDF", default_filename, "PDF Files (*.pdf)")
        
        if not file_path:
            return # Usuário cancelou
            
        # 2. Configuração do PDF
        doc = SimpleDocTemplate(file_path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Estilo para o título
        title_style = ParagraphStyle('TitleStyle', parent=styles['Title'], fontSize=18, spaceAfter=20, alignment=1)
        
        # Estilo para o corpo do texto (pré-formatado)
        code_style = ParagraphStyle('CodeStyle', parent=styles['Code'], fontSize=8, spaceBefore=10, spaceAfter=10)
        
        # 3. Adicionar Título
        story.append(Paragraph("Relatório de Análise Estatística (ANOVA e Tukey HSD)", title_style))
        story.append(Spacer(1, 0.5 * inch))
        
        # 4. Adicionar Resultados de Texto (ANOVA e Tukey)
        results_text = self.anova_results_box.toPlainText()
        
        # O texto da caixa de resultados é pré-formatado, usamos <pre> para manter a formatação
        story.append(Paragraph("<b>Resultados da Análise (ANOVA e Tukey HSD):</b>", styles['Heading2']))
        
        # Quebrar o texto em parágrafos para quebrar linha corretamente no PDF
        for line in results_text.split('\n'):
            # Substituir espaços por &nbsp; para preservar o alinhamento de colunas da tabela
            formatted_line = line.replace(' ', '&nbsp;')
            story.append(Paragraph(formatted_line, code_style))
            
        story.append(Spacer(1, 0.5 * inch))
        
        # 5. Adicionar Gráfico
        if hasattr(self, 'anova_graph_label') and self.anova_graph_label.pixmap():
            story.append(Paragraph("<b>Gráfico de Interação:</b>", styles['Heading2']))
            story.append(Spacer(1, 0.2 * inch))
            
            # Converte o QPixmap do gráfico para um objeto de imagem do ReportLab
            pixmap = self.anova_graph_label.pixmap()
            
            # Salva a imagem em um buffer de memória
            buffer = QBuffer()
            buffer.open(QBuffer.ReadWrite)
            pixmap.save(buffer, "PNG") # Salva os dados do pixmap no buffer
            
            # --- CORREÇÃO: Converte o QBuffer para um BytesIO que o ReportLab entende ---
            # Lê todos os dados do QBuffer e os coloca em um BytesIO.
            image_stream = BytesIO(buffer.data())
            rl_image = RLImage(image_stream)
            
            # Ajusta o tamanho da imagem para caber na página (exemplo: 500 pontos de largura)
            img_width = 500 # Largura em pontos (aprox. 7 polegadas)
            img_height = rl_image.drawHeight * img_width / rl_image.drawWidth
            rl_image.drawWidth = img_width
            rl_image.drawHeight = img_height
            
            story.append(rl_image)
            story.append(Spacer(1, 0.5 * inch))

        # 6. Construir o PDF
        try:
            doc.build(story)
            msg = QMessageBox.information(self, "Sucesso", f"O relatório PDF foi salvo com sucesso em:\n{file_path}")
        except Exception as e:
            msg = QMessageBox.critical(self, "Erro ao Salvar PDF", f"Ocorreu um erro ao gerar o PDF: {e}")
            msg.setStyleSheet(DARK_MESSAGE_BOX_STYLE)
            msg.exec()
            
    
    def generate_interaction_plot(self, df, response_var, response_var_display_name, tukey_summary):
        """Gera um gráfico de interação com anotações de média e letras de significância."""
        try:
            import pandas as pd 
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
            # Usa o estilo padrão do Matplotlib para garantir que não haja conflitos
            plt.style.use('default')

            df['deliniamento'] = df['deliniamento'].astype('category')
            grouped = df.groupby(['deliniamento', 'velocidade_esteira_kmh'])[response_var].agg(['mean', 'sem']).reset_index()

            fig, ax = plt.subplots(figsize=(6, 4))
            
            # Adiciona a grade (grid) manualmente
            ax.grid(True, which='major', axis='y', linestyle='--', color='#cccccc', zorder=0)
            ax.set_axisbelow(True)

            tube_types = grouped['deliniamento'].unique()
            colors = plt.colormaps.get_cmap('viridis').resampled(len(tube_types))
            
            for i, tube_type in enumerate(tube_types):
                subset = grouped[grouped['deliniamento'] == tube_type]
                
                ax.plot(subset['velocidade_esteira_kmh'], subset['mean'], 
                        marker='o', linestyle='-', label=tube_type, color=colors(i), zorder=3)
                
                ax.errorbar(subset['velocidade_esteira_kmh'], subset['mean'], 
                            yerr=subset['sem'], fmt='none', capsize=5, color=colors(i), zorder=3)
                
                for _, row in subset.iterrows():
                    x_pos = row['velocidade_esteira_kmh']
                    y_pos = row['mean']
                    
                    group_name = f"{row['deliniamento']} @ {row['velocidade_esteira_kmh']} km/h"
                    
                    if group_name in tukey_summary:
                        mean_val, letter = tukey_summary[group_name]
                        annotation_text = f"{mean_val:.1f} {letter}"
                        
                        # Esta é a parte que desenha o texto e garante que a cor seja PRETA
                        ax.text(x_pos, y_pos + (ax.get_ylim()[1] * 0.02), annotation_text, 
                                fontsize=8, 
                                color='black',
                                ha='center',
                                va='bottom',
                                bbox=dict(boxstyle='round,pad=0.2', fc='yellow', alpha=0.8),
                                zorder=5)

            ax.set_title(f'Interação para {response_var_display_name}', fontsize=12, color='black')
            ax.set_xlabel('Velocidade da Esteira (km/h)', fontsize=10, color='black')
            ax.set_ylabel(response_var_display_name, fontsize=10, color='black')
            ax.tick_params(axis='x', colors='black')
            ax.tick_params(axis='y', colors='black')
            ax.set_xticks(sorted(grouped['velocidade_esteira_kmh'].unique()))
            ax.legend(title="Deliniamento", fontsize='small')
            
            ax.set_ylim(top=ax.get_ylim()[1] * 1.15)
            
            plt.tight_layout(pad=1.5)
            
            buf = BytesIO()
            plt.savefig(buf, format='png')
            plt.close(fig)
            buf.seek(0)
            
            pixmap = QPixmap.fromImage(QImage.fromData(buf.getvalue(), 'PNG'))
            self.anova_graph_label = QLabel()
            self.anova_graph_label.setPixmap(pixmap)
            self.anova_graph_label.setAlignment(Qt.AlignCenter)

            if hasattr(self, 'anova_graph_area') and self.anova_graph_area.layout():
                while self.anova_graph_area.layout().count():
                    child = self.anova_graph_area.layout().takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()
                self.anova_graph_area.layout().addWidget(self.anova_graph_label)
        
        except Exception as e:
            msg=QMessageBox.critical(self, "Erro na Geração do Gráfico", f"Não foi possível gerar o Gráfico de Interação:\n{str(e)}")
            msg.setStyleSheet(DARK_MESSAGE_BOX_STYLE)
            msg.exec()
            plt.close('all')
    def _normalize_header_for_pandas(self, header_text):
        """Normaliza o texto do cabeçalho para ser um identificador válido no Pandas."""
        try:
            import unicodedata
            # Normaliza para remover acentos, converte para minúsculas
            text = unicodedata.normalize('NFKD', header_text).encode('ascii', 'ignore').decode('utf-8').lower()
        except ImportError:
            text = header_text.lower()

        # Substituições específicas para padronizar os nomes
        text = text.replace('\n', '_').replace(' ', '_') # Remove quebras de linha e espaços
        text = text.replace('(%)', '_pct').replace('(cm)', '_cm').replace('(km/h)', '_kmh')
        text = text.replace('sem./m', 'sem_m').replace('desv._p', 'desv_p').replace('1q', 'q1').replace('3q', 'q3')
        text = text.replace('vel._esteira', 'velocidade_esteira') # Trata a abreviação
        text = ''.join(c for c in text if c.isalnum() or c == '_') # Remove caracteres inválidos
        text = '_'.join(filter(None, text.split('_'))) # Remove múltiplos underscores
        return text

    def export_statistics_to_csv(self):
        """Exporta os dados da tabela de estatísticas para um arquivo CSV."""
        if self.stats_table.rowCount() == 0:
            QMessageBox.warning(self, "Nenhum Dado", "Não há dados na tabela para exportar.")
            return

        project_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "SVA")
        os.makedirs(project_dir, exist_ok=True)
        default_filename = os.path.join(project_dir, f"estatisticas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        
        path, _ = QFileDialog.getSaveFileName(self, "Salvar Arquivo CSV", default_filename, "CSV Files (*.csv)")

        if path:
            try:
                with open(path, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile, delimiter=';') # Usa ponto e vírgula como delimitador
                    
                    # --- CORREÇÃO: Formata os cabeçalhos para o CSV ---
                    headers = [
                        self.stats_table.horizontalHeaderItem(i).text().replace('\n', ' ')
                        for i in range(self.stats_table.columnCount() - 1) # Ignora a coluna "Ação"
                    ]
                    writer.writerow(headers)

                    # --- CORREÇÃO: Formata os dados numéricos com vírgula decimal ---
                    for row in range(self.stats_table.rowCount()):
                        row_data = []
                        for col in range(self.stats_table.columnCount() - 1): # -1 para ignorar a coluna "Ação"
                            item = self.stats_table.item(row, col)
                            text = item.text() if item else ''
                            # Substitui ponto por vírgula para colunas numéricas
                            header_text = headers[col]
                            if header_text.endswith('(%)') or header_text.endswith('(cm)') or header_text.endswith('(km/h)'):
                                text = text.replace('.', ',')
                            row_data.append(text)
                        writer.writerow(row_data)
                
                msg=QMessageBox.information(self, "Sucesso", f"Dados exportados com sucesso para:\n{path}")
                msg.setStyleSheet(DARK_MESSAGE_BOX_STYLE)
                msg.exec()

            except Exception as e:
                msg=QMessageBox.critical(self, "Erro de Exportação", f"Ocorreu um erro ao salvar o arquivo CSV:\n{str(e)}")
                msg.setStyleSheet(DARK_MESSAGE_BOX_STYLE)
                msg.exec()

    def add_analysis_to_statistics_table(self, analysis_data):
        """Adiciona uma nova análise à tabela de estatísticas."""
        self.update_statistics_table() # Simplesmente recria a tabela inteira

    def append_to_summary_csv(self, analysis_data):
        """Adiciona uma linha de resumo de uma análise a um arquivo CSV."""
        try:
            summary_file_path = os.path.join(self.project_dir, "summary_analysis.csv")
            fieldnames = [
                'id', 'datetime', 'video_path', 'seed_type', 'planting_speed', 
                'seeds_per_meter', 'total_seeds', 'aceitavel', 'falha', 'multipla'
            ]
            write_header = not os.path.exists(summary_file_path)

            with open(summary_file_path, mode='a', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                if write_header:
                    writer.writeheader()
                
                row_data = {key: analysis_data.get(key, '') for key in fieldnames}
                writer.writerow(row_data)

        except Exception as e:
            print(f"Erro ao salvar o resumo em CSV: {e}")
            
    # =========================================================================

    def select_video(self):
        """Abre um diálogo para o usuário selecionar um arquivo de vídeo."""
        # CORREÇÃO: Usa o BASE_DIR
        file_path, _ = QFileDialog.getOpenFileName(self, "Selecionar Vídeo", BASE_DIR, "Arquivos de Vídeo (*.mp4 *.avi *.mov)")
        if file_path:
            self.load_video(file_path)
            self.reset_analysis()
            self.tab_widget.setCurrentIndex(0)

    def load_video(self, source):
        """Carrega o vídeo ou a câmera selecionada e inicializa o OpenCV."""
        if self.cap:
            self.cap.release()
        
        self.video_path = source
        self.video_path_label.setText(os.path.basename(str(self.video_path)))
        self.cap = cv2.VideoCapture(self.video_path)

        if not self.cap.isOpened():
            msg=QMessageBox.critical(self, "Erro", f"Não foi possível abrir a fonte de vídeo: {source}")
            msg.setStyleSheet(DARK_MESSAGE_BOX_STYLE)
            msg.exec()
            self.video_path = None
            self.video_path_label.setText("Nenhum vídeo selecionado")
            return
        
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        if self.fps == 0: self.fps = 30
        self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

        self.resolution_label.setText(f"Resolução: {self.frame_width}x{self.frame_height}")
        self.time_label.setText("Tempo: 00:00:00")
        
        self.detection_line_x = int(self.frame_width * 0.75)

        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ret, frame = self.cap.read()
        if ret:
            self.calibration_tab.set_first_frame(frame)         
        
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        self.update_frame()
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.save_analysis_btn.setEnabled(False)

    def update_frame(self):
        """Lê e exibe o próximo frame do vídeo."""
        if self.playing and not self.pause_flag and self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                self.current_frame = frame
                self.frame_count = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))          
                adjusted_frame = self.apply_visual_adjustments(frame)
                processed_frame = self.detect_seeds_in_frame(adjusted_frame)
                self.display_frame(processed_frame)
                self.update_time_label()
            else:
                self.stop_analysis()

    def apply_visual_adjustments(self, frame):
        """Aplica ajustes de saturação e temperatura ao frame."""
        if self.saturation_value == 0 and self.temperature_value == 0:
            return frame

        # 1. Ajuste de Saturação (HSV)
        frame_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        # O slider vai de -100 a 100. O fator deve ser de 0 a 2.
        sat_factor = (self.saturation_value + 100) / 100.0
        s_channel = frame_hsv[:, :, 1].astype(np.float32) * sat_factor
        frame_hsv[:, :, 1] = np.clip(s_channel, 0, 255).astype(np.uint8)
        frame_adjusted = cv2.cvtColor(frame_hsv, cv2.COLOR_HSV2BGR)

        # 2. Ajuste de Temperatura (Simulação com Balanço de Cores RGB)
        # O slider vai de -100 (frio) a 100 (quente).
        temp_factor = self.temperature_value / 100.0
        
        # Fator de ajuste: 1.0 + (temp_factor) * 0.5
        # Se temp_factor = 1.0 (100%), fator = 1.5 (mais vermelho)
        # Se temp_factor = -1.0 (-100%), fator = 0.5 (menos vermelho)
        r_factor = 1.0 + (temp_factor) * 0.5
        b_factor = 1.0 - (temp_factor) * 0.5
        
        r_channel = frame_adjusted[:, :, 2].astype(np.float32) * r_factor
        b_channel = frame_adjusted[:, :, 0].astype(np.float32) * b_factor
        
        frame_adjusted[:, :, 2] = np.clip(r_channel, 0, 255).astype(np.uint8)
        frame_adjusted[:, :, 0] = np.clip(b_channel, 0, 255).astype(np.uint8)
        
        return frame_adjusted

        if self.saturation_value != 0:
            hsv = cv2.cvtColor(adjusted_frame, cv2.COLOR_BGR2HSV)
            h, s, v = cv2.split(hsv)
            s = s.astype(np.float32)
            s = np.clip(s * (1 + self.saturation_value / 120.0), 0, 255)
            s = s.astype(np.uint8)
            final_hsv = cv2.merge((h, s, v))
            adjusted_frame = cv2.cvtColor(final_hsv, cv2.COLOR_HSV2BGR)

        if self.temperature_value != 0:
            value = self.temperature_value / 100.0
            if value > 0:
                gamma_r, gamma_b = 1.0 - value * 0.4, 1.0 + value * 0.4
            else:
                gamma_r, gamma_b = 1.0 - value * 0.4, 1.0 + value * 0.4

            lut_r = np.array([((i / 255.0) ** (1/gamma_r)) * 255 for i in np.arange(0, 256)]).astype("uint8")
            lut_b = np.array([((i / 255.0) ** (1/gamma_b)) * 255 for i in np.arange(0, 256)]).astype("uint8")

            b, g, r = cv2.split(adjusted_frame)
            r = cv2.LUT(r, lut_r)
            b = cv2.LUT(b, lut_b)
            adjusted_frame = cv2.merge((b, g, r))

        return adjusted_frame

    def display_frame(self, frame):
        """Exibe um frame OpenCV no QLabel principal."""
        if frame is None: return

        h, w, ch = frame.shape
        self.video_label.setText("") # Limpa o texto "Carregue um vídeo..."
        bytes_per_line = ch * w
        convert_to_qt_format = QImage(frame.data, w, h, bytes_per_line, QImage.Format_BGR888)
        pixmap = QPixmap.fromImage(convert_to_qt_format)
        self.video_label.setPixmap(pixmap.scaled(self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def start_analysis(self):
        """Inicia a análise do vídeo."""
        if self.seed_type_combo.currentIndex() == -1:
            QMessageBox.warning(self, "Parâmetro Faltando", "Por favor, selecione o 'Tipo de Semente'.")
            return
        if self.speed_combo.currentIndex() == -1:
            QMessageBox.warning(self, "Parâmetro Faltando", "Por favor, selecione a 'Velocidade (km/h)'.")
            return
        if not self.seeds_per_m_input.text().strip():
            QMessageBox.warning(self, "Parâmetro Faltando", "Por favor, preencha o campo 'Sementes/m'.")
            return
        if not self.pixels_cm_display.text().strip():
            QMessageBox.warning(self, "Parâmetro Faltando", "O valor de 'Pixels/cm' não foi definido. Por favor, use a aba de Calibração.")
            return

        if self.cap and self.cap.isOpened():
            if self.pause_flag:
                self.pause_flag = False
                self._start_playing_internal()
                return

            self.reset_analysis()
            self._start_playing_internal()

    def pause_analysis(self):
        """Pausa a análise do vídeo."""
        self.pause_flag = True
        self.timer.stop()
        self.start_btn.setText("▶️ Continuar")
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.save_analysis_btn.setEnabled(True)

    # Linha 3496 (Substitua a função completa)

    def save_and_pause_analysis(self, is_auto_save=False):
        """Salva a análise atual e pausa o vídeo, lendo os dados atuais da interface."""
        if not self.cap or not self.cap.isOpened() or (not self.playing and not self.pause_flag):
            return
        
        # Pausa o vídeo imediatamente, mas não reseta os contadores ainda.
        self._stop_playing_internal()

        if self.total_seeds_detected > 0:
            final_frame_base64 = None
            if self.current_frame is not None:
                _, buffer = cv2.imencode('.png', self.current_frame)
                final_frame_base64 = base64.b64encode(buffer).decode('utf-8')

            # --- Captura os valores atuais diretamente da interface ---
            current_seed_type = self.seed_type_combo.currentText()
            current_tube_type = self.tube_type_combo.currentText() # Este é o Delineamento
            current_speed = self.speed_combo.currentText()
            current_seeds_per_meter = self.seeds_per_m_input.text()
            current_row_spacing = self.row_spacing_combo.currentText()

            # Lógica de repetição usando os valores atuais
            repetition_count = 1
            for res in self.analysis_results:
                if (res.get('seed_type') == current_seed_type and
                    res.get('tube_type') == current_tube_type and
                    str(res.get('planting_speed')) == current_speed):
                    repetition_count += 1
            
            # ... (Restante do bloco de análise de dados, Linhas 3543 a 3574, permanece o mesmo) ...
            analysis_data = {**self.initial_data} 
            analysis_data.update({
                'id': self.next_analysis_id,
                'datetime': datetime.now().strftime("%d/%m/%Y %H:%M"),
                'video_path': self.video_path,
                'seed_type': current_seed_type,
                'planting_speed': current_speed,
                'tube_type': current_tube_type,
                'repetition_count': repetition_count,
                'row_spacing': current_row_spacing,
                'seeds_per_meter': current_seeds_per_meter,
                'pixels_per_cm': self.pixels_per_cm,
                'aceitavel': self.aceitavel_count,
                'falha': self.falha_count,
                'multipla': self.multipla_count,
                'total_seeds': self.total_seeds_detected,
                'spacing_data': self.spacing_data,
                'duration': str(timedelta(seconds=int(self.frame_count / self.fps))),
                'final_frame_base64': final_frame_base64,
                'notes': ''
            })
            self.analysis_results.append(analysis_data)
            self.next_analysis_id += 1
            self.update_reports_display()
            self.append_to_summary_csv(analysis_data)
            self.update_statistics_table()

            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setText("Análise salva com sucesso!")
            msg_box.setInformativeText("O novo relatório está disponível na aba 'Relatórios'.")
            msg_box.setWindowTitle("Análise Salva")
            
            go_to_report_btn = msg_box.addButton("Ir para Relatórios", QMessageBox.ActionRole)
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.exec()
            if msg_box.clickedButton() == go_to_report_btn:
                self.tab_widget.setCurrentIndex(3)
        
        
        # --- Lógica de Continuação/Pausa ---
        if is_auto_save:
            # Se for salvamento automático, reseta contadores e continua pausado
            self.reset_counters_for_continuation()
            self.pause_flag = True
        
        # Define o estado da interface
        self.start_btn.setText("▶️ Continuar")
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.save_analysis_btn.setEnabled(False)

    def stop_analysis(self):
        """Para a análise do vídeo, salva os resultados e reseta para um novo início."""
        if not self.cap or not self.cap.isOpened() or (not self.playing and not self.pause_flag): return

        self._stop_playing_internal()
        
        if self.total_seeds_detected > 0:
            final_frame_base64 = None
            if self.current_frame is not None:
                _, buffer = cv2.imencode('.png', self.current_frame)
                final_frame_base64 = base64.b64encode(buffer).decode('utf-8')

            # --- CORREÇÃO: Captura os valores atuais diretamente da interface ---
            current_seed_type = self.seed_type_combo.currentText()
            current_tube_type = self.tube_type_combo.currentText() # Este é o Delineamento
            current_speed = self.speed_combo.currentText()
            current_seeds_per_meter = self.seeds_per_m_input.text()
            current_row_spacing = self.row_spacing_combo.currentText()

            # Lógica de repetição usando os valores atuais
            repetition_count = 1
            for res in self.analysis_results:
                if (res.get('seed_type') == current_seed_type and
                    res.get('tube_type') == current_tube_type and
                    str(res.get('planting_speed')) == current_speed):
                    repetition_count += 1

            analysis_data = {**self.initial_data}
            analysis_data.update({
                'id': self.next_analysis_id,
                'datetime': datetime.now().strftime("%d/%m/%Y %H:%M"),
                'video_path': self.video_path,
                'seed_type': current_seed_type,
                'planting_speed': current_speed,
                'tube_type': current_tube_type,
                'repetition_count': repetition_count,
                'row_spacing': current_row_spacing,
                'seeds_per_meter': current_seeds_per_meter,
                'pixels_per_cm': self.pixels_per_cm,
                'aceitavel': self.aceitavel_count,
                'falha': self.falha_count,
                'multipla': self.multipla_count,
                'total_seeds': self.total_seeds_detected,
                'spacing_data': self.spacing_data,
                'duration': str(timedelta(seconds=int(self.frame_count / self.fps))),
                'final_frame_base64': final_frame_base64
            })
            self.analysis_results.append(analysis_data)
            self.next_analysis_id += 1
            self.append_to_summary_csv(analysis_data)
            self.update_statistics_table()
            self.update_reports_display()
            msg=QMessageBox.information(self, "Análise Concluída", "A análise do vídeo foi concluída e os resultados foram salvos nos relatórios.")
            msg.setStyleSheet(DARK_MESSAGE_BOX_STYLE)
            msg.exec()

        self.start_btn.setText("▶️ Iniciar")
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.save_analysis_btn.setEnabled(False)
        self.pause_flag = False

    def _stop_playing_internal(self):
        if self.timer.isActive():
            self.timer.stop()
        self.playing = False

    def _start_playing_internal(self):
        self.playing = True
        self.timer.start(int(1000 / (self.fps * self.playback_speed)))
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.save_analysis_btn.setEnabled(True)

    def check_seed_count_for_auto_save(self):
        """Verifica se o número de sementes atingiu o alvo para o salvamento automático."""
        try:
            target_count = int(self.auto_save_count_input.text())
        except (ValueError, TypeError):
            return # Ignora se o valor for inválido

        if self.total_seeds_detected >= target_count and not self.auto_save_prompt_shown:
            self.auto_save_prompt_shown = True  # Garante que o aviso seja mostrado apenas uma vez
            self.pause_analysis()  # Pausa a análise para o usuário decidir

            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Question)
            msg_box.setWindowTitle("Contagem Atingida")
            msg_box.setText(f"A contagem de {target_count} sementes foi atingida.")
            msg_box.setInformativeText("Deseja salvar a análise agora?")
            
            save_button = msg_box.addButton("Salvar Análise", QMessageBox.AcceptRole)
            cancel_button = msg_box.addButton("Cancelar", QMessageBox.RejectRole)
            msg_box.exec()

            if msg_box.clickedButton() == save_button:
                # Salva e reseta os contadores para continuar a análise a partir daqui
                # A função save_and_pause_analysis irá internamente chamar reset_counters_for_continuation
                self.save_and_pause_analysis(is_auto_save=True)


    def detect_seeds_in_frame(self, frame):
        """Lógica de detecção de sementes, com otimização de ROI para o YOLO."""
        # --- NOVO: IMPORTAÇÃO LOCAL PARA ACELERAR A INICIALIZAÇÃO ---
        from ultralytics import YOLO
        processed_frame = frame.copy()
        frame_height, frame_width, _ = frame.shape
        
        yolo_detections = []
        color_detections = []

        # Define o método de detecção com base na seleção do RadioButton
        if self.method_hsv_radio.isChecked(): self.detection_method = "hsv"
        elif self.method_yolo_radio.isChecked(): self.detection_method = "yolo"
        elif self.method_combined_radio.isChecked(): self.detection_method = "combined"

        # Verifica se precisa carregar o modelo YOLO
        needs_yolo = self.detection_method in ["yolo", "combined"]

        # Lógica para carregar o modelo YOLO apenas quando necessário
        if needs_yolo and self.yolo_model is None:
            try:
                from ultralytics import YOLO
                model_path = os.path.join(self.project_dir, "SVA", "best.pt")
                if not os.path.exists(model_path):
                    msg=QMessageBox.critical(self, "Erro de Modelo", f"Modelo YOLO não encontrado em:\n{model_path}\n\nExecute um treinamento primeiro ou coloque o arquivo 'best.pt' no local correto.")
                    msg.setStyleSheet(DARK_MESSAGE_BOX_STYLE)
                    msg.exec()
                    self.method_hsv_radio.setChecked(True) # Volta para o método HSV como padrão
                    needs_yolo = False
                else:
                    self.yolo_model = YOLO(model_path)
                    print("Modelo YOLO carregado com sucesso.")
            except Exception as e:
                msg=QMessageBox.critical(self, "Erro ao Carregar YOLO", f"Não foi possível carregar o modelo YOLO.\nErro: {e}")
                msg.setStyleSheet(DARK_MESSAGE_BOX_STYLE)
                msg.exec()
                self.method_hsv_radio.setChecked(True)
                needs_yolo = False

        # --- OTIMIZAÇÃO: Define a Região de Interesse (ROI) para o YOLO ---
        y_start = int(frame_height * 0.30)
        y_end = int(frame_height * 0.70)
        
        # --- MÉTODO YOLO (AGORA OTIMIZADO) ---
        if needs_yolo and self.yolo_model:
            # 1. Recorta o frame para a ROI
            roi_frame = frame[y_start:y_end, :]
            
            # 2. Envia APENAS O FRAME RECORTADO para o YOLO
            results = self.yolo_model.predict(source=roi_frame, show=False, conf=0.4, verbose=False)
            
            for r in results:
                for box in r.boxes:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    # --- ALTERAÇÃO: Captura a classe da detecção YOLO ---
                    cls = int(box.cls[0])
                    # Assumimos que classe 0 = semente simples, classe 1 = semente dupla
                    is_double_seed = (cls == 1)
                    # ---------------------------------------------------------
                    
                    # 3. --- IMPORTANTE: Corrige as coordenadas Y ---
                    # Adiciona o deslocamento (offset) y_start de volta às coordenadas
                    # para que a posição seja correta no frame original completo.
                    y1_orig = y1 + y_start
                    y2_orig = y2 + y_start
                    # --- FIM DA ALTERAÇÃO ---
                    
                    x, y, w, h = int(x1), int(y1_orig), int(x2 - x1), int(y2_orig - y1_orig)
                    cx, cy = int(x + w / 2), int(y + h / 2)
                    # --- ALTERAÇÃO: Usa a classe para definir 'is_double' ---
                    yolo_detections.append({'center': (cx, cy), 'bbox': (x, y, w, h), 'is_double': is_double_seed})
                    # --- FIM DA ALTERAÇÃO ---

        # --- MÉTODO COR/TAMANHO (Executado se for HSV ou Combinado) ---
        if self.detection_method in ["hsv", "combined"]:
            roi_points = np.array([
                (0, y_start),
                (frame_width, y_start),
                (frame_width, y_end),
                (0, y_end)
            ], np.int32)
            cv2.polylines(processed_frame, [roi_points], isClosed=True, color=(255, 120, 0), thickness=2)
            color_detections = self.detect_seeds_by_color(frame, roi_points)
        
        # --- FUSÃO DOS MÉTODOS E RASTREAMENTO ---
        if self.detection_method == "hsv":
            current_frame_detections = color_detections
        elif self.detection_method == "yolo":
            current_frame_detections = yolo_detections
        elif self.detection_method == "combined":
            current_frame_detections = self.fuse_detections(yolo_detections, color_detections)
        else:
            current_frame_detections = color_detections

        # --- LÓGICA DE RASTREAMENTO E CONTAGEM (permanece a mesma) ---
        ideal_spacing_cm = 100.0 / self.seeds_per_meter if self.seeds_per_meter > 0 else 0
        ideal_spacing_pixels = ideal_spacing_cm * self.pixels_per_cm
        falha_threshold_pixels = 1.5 * ideal_spacing_pixels
        dupla_threshold_pixels = 0.5 * ideal_spacing_pixels
        min_spacing_px = 3.0

        # --- LÓGICA DE RASTREAMENTO E CONTAGEM APRIMORADA ---
        
        # 1. Atualiza sementes que desapareceram
        disappeared_ids = []
        for seed_id, data in self.disappeared_seeds.items():
            data['frames_disappeared'] += 1
            if data['frames_disappeared'] > self.disappeared_frames_threshold:
                disappeared_ids.append(seed_id)
        
        for seed_id in disappeared_ids:
            del self.disappeared_seeds[seed_id]

        # 2. Tenta encontrar correspondência para as detecções atuais
        new_tracked_seeds = {}
        unmatched_detections = []

        for det in current_frame_detections:
            cx, cy = det['center']
            matched_id = -1
            min_dist = float('inf')
            
            # Combina sementes ativas e desaparecidas para a busca
            search_pool = {**self.tracked_seeds, **self.disappeared_seeds}

            for seed_id, seed_data in search_pool.items():
                dist = np.hypot(cx - seed_data['center'][0], cy - seed_data['center'][1])
                if dist < 50 and dist < min_dist:
                    min_dist = dist
                    matched_id = seed_id
            
            if matched_id != -1: # Se encontrou um match
                # Recupera os dados da semente, seja ela ativa ou desaparecida
                prev_seed = search_pool[matched_id]
                old_cx = prev_seed['center'][0]
                counted = prev_seed.get('counted', False)

                # Atualiza os dados da semente
                updated_data = {**det, 'counted': counted, 'just_counted': False, 'id': matched_id}
                updated_data['is_double'] = det.get('is_double', False) or prev_seed.get('is_double', False)

                # Lógica de contagem ao cruzar a linha
                if not counted and cx > self.detection_line_x and old_cx <= self.detection_line_x:
                    self.total_seeds_detected += 2 if updated_data.get('is_double', False) else 1
                    updated_data['counted'] = True
                    updated_data['just_counted'] = True
                
                new_tracked_seeds[matched_id] = updated_data
                
                # Se a semente estava na lista de desaparecidas, remove-a de lá
                if matched_id in self.disappeared_seeds:
                    del self.disappeared_seeds[matched_id]
            else:
                unmatched_detections.append(det)

        # 3. Adiciona novas sementes que não tiveram correspondência
        for det in unmatched_detections:
            cx, cy = det['center']
            counted = False
            if cx > self.detection_line_x:
                self.total_seeds_detected += 2 if det.get('is_double', False) else 1
                counted = True
                det['just_counted'] = True
            
            new_tracked_seeds[self.next_seed_id] = {**det, 'counted': counted, 'just_counted': det.get('just_counted', False)}
            self.next_seed_id += 1

        # 4. Move sementes que não foram vistas neste frame para a lista de desaparecidas
        for seed_id in self.tracked_seeds:
            if seed_id not in new_tracked_seeds:
                self.disappeared_seeds[seed_id] = self.tracked_seeds[seed_id]
                self.disappeared_seeds[seed_id]['frames_disappeared'] = 1

        # 5. Atualiza o dicionário de sementes ativas
        self.tracked_seeds = new_tracked_seeds

        # --- LÓGICA DE CLASSIFICAÇÃO DE ESPAÇAMENTO (permanece a mesma) ---
        centers = [(sid, data['center'][0]) for sid, data in self.tracked_seeds.items()]
        centers.sort(key=lambda t: t[1])
        for sid, cx in centers:
            data = self.tracked_seeds[sid]
            if data.get('just_counted', False):
                cx_val = data['center'][0]
                prev_x = None
                for _, other_x in centers:
                    if other_x < cx_val:
                        prev_x = other_x
                if prev_x is None and self.last_crossed_seed_x is not None:
                    prev_x = self.last_crossed_seed_x

                if prev_x is not None:
                    if data.get('is_double', False):
                        self.multipla_count += 1
                        spacing_cm = (cx_val - prev_x) / self.pixels_per_cm
                        self.spacing_data.append({'time': self.frame_count / self.fps, 'spacing_cm': spacing_cm, 'class': 'multipla'})
                    else:
                        spacing_pixels = cx_val - prev_x
                        if spacing_pixels > min_spacing_px:
                            spacing_cm = spacing_pixels / self.pixels_per_cm
                            current_time_sec = self.frame_count / self.fps
                            point_class = ''
                            if spacing_pixels < dupla_threshold_pixels:
                                self.multipla_count += 1
                                point_class = 'multipla'
                            elif spacing_pixels > falha_threshold_pixels:
                                self.falha_count += 1
                                point_class = 'falha'
                            else:
                                self.aceitavel_count += 1
                                point_class = 'aceitavel'
                            
                            point_data = {'time': current_time_sec, 'spacing_cm': spacing_cm, 'class': point_class}
                            self.spacing_data.append(point_data)
                            self.update_spacing_chart(point_data)
                            self.update_cv_display() # Atualiza o CV

                elif not data.get('is_double', False):
                    self.aceitavel_count += 1
                self.last_crossed_seed_x = cx_val
                self.tracked_seeds[sid]['just_counted'] = False

        for seed_id, seed_data in self.tracked_seeds.items():
            x, y, w, h = seed_data['bbox']
            color = (255, 0, 255) if seed_data.get('is_double', False) else (0, 255, 0)
            cv2.rectangle(processed_frame, (x, y), (x + w, y + h), color, 2)
            cv2.putText(processed_frame, f"{self.seed_type}-{seed_id + 1}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        visible_seeds_centers = [d['center'] for d in self.tracked_seeds.values()]
        if len(visible_seeds_centers) >= 2:
            visible_seeds_centers.sort(key=lambda p: p[0])
            for i in range(len(visible_seeds_centers) - 1):
                p1 = visible_seeds_centers[i]
                p2 = visible_seeds_centers[i+1]
                dist_x = abs(p1[0] - p2[0])
                if dist_x <= dupla_threshold_pixels:
                    line_color, label = (255, 0, 255), "MULTIPLO"
                elif dist_x >= falha_threshold_pixels:
                    line_color, label = (0, 0, 255), "FALHA"
                else:
                    line_color, label = (0, 255, 0), "ACEITAVEL"
                mid_x = int((p1[0] + p2[0]) / 2)
                mid_y = int((p1[1] + p2[1]) / 2)
                cv2.line(processed_frame, p1, p2, line_color, 2)
                cv2.putText(processed_frame, f'{label}', (mid_x - 30, mid_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, line_color, 1, cv2.LINE_AA)

        self.update_counter_widget("Aceitável", self.aceitavel_count)
        self.update_counter_widget("Falha", self.falha_count)
        self.update_counter_widget("Múltipla", self.multipla_count)

        if hasattr(self, 'total_seeds_label'):
            self.total_seeds_label.setText(str(self.total_seeds_detected))

        # --- NOVO: Verifica se a contagem para salvamento automático foi atingida ---
        self.check_seed_count_for_auto_save()

        cv2.line(processed_frame, (self.detection_line_x, 0), 
                 (self.detection_line_x, frame_height), (0, 0, 255), 2)
        
        return processed_frame
        
    def fuse_detections(self, yolo_detections, color_detections):
        
        '''Combina de forma inteligente as detecções do YOLO e do método de Cor/Tamanho.
        A lógica é:
        1. Confia nas caixas delimitadoras (bbox) do YOLO como base.
        2. Usa a análise de Cor/Tamanho para "enriquecer" as detecções do YOLO,
           especificamente para identificar se uma detecção é dupla (is_double).
        3.'''

        if not yolo_detections:
            return color_detections

        fused_detections = list(yolo_detections)
        color_detections_to_add = []
        
        fusion_threshold = 40  

        for color_det in color_detections:
            closest_yolo_det = None
            min_dist = float('inf')

            for yolo_det in fused_detections:
                dist = np.hypot(
                    color_det['center'][0] - yolo_det['center'][0],
                    color_det['center'][1] - yolo_det['center'][1]
                )
                if dist < min_dist:
                    min_dist = dist
                    closest_yolo_det = yolo_det

            if closest_yolo_det and min_dist < fusion_threshold:
                if color_det.get('is_double', False):
                    closest_yolo_det['is_double'] = True
            else:
                color_detections_to_add.append(color_det)

        fused_detections.extend(color_detections_to_add)
                
        return fused_detections

    def detect_seeds_by_color(self, frame, roi_points):
        """Detecta sementes usando o método de Cor/Tamanho com lógica aprimorada para múltiplas."""
        detections = []
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        roi_mask = np.zeros(frame.shape[:2], dtype=np.uint8)
        cv2.fillPoly(roi_mask, [roi_points], 255)

        params = self.seed_params["Soja"]

        lower1 = np.array(params['hsv_lower1'])
        upper1 = np.array(params['hsv_upper1'])
        mask = cv2.inRange(hsv, lower1, upper1)

        if params.get('is_dual_hue', False):
            lower2 = np.array(params['hsv_lower2'])
            upper2 = np.array(params['hsv_upper2'])
            mask2 = cv2.inRange(hsv, lower2, upper2)
            mask = cv2.bitwise_or(mask, mask2)

        mask = cv2.bitwise_and(mask, mask, mask=roi_mask)

        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        min_seed_area = params['min_area']
        max_seed_area = params['max_area']
        double_seed_area_threshold = params['double_seed_area_threshold']

        for cnt in contours:
            area = cv2.contourArea(cnt)

            # 1. Ignora qualquer contorno que seja pequeno demais
            if area < min_seed_area:
                continue

            # --- MELHORIA: Análise de Forma (Solidez) para Sementes Duplas ---
            # 2. Verifica se a área é grande o suficiente para ser considerada múltipla
            is_large_enough_for_double = area > double_seed_area_threshold

            # 3. Calcula a solidez (quão "sólido" é o contorno)
            # Uma semente única tem solidez perto de 1.0. Duas sementes juntas têm um valor menor.
            hull = cv2.convexHull(cnt)
            hull_area = cv2.contourArea(hull)
            solidity = float(area) / hull_area if hull_area > 0 else 0

            # Uma detecção é considerada dupla se for grande E tiver uma forma irregular (baixa solidez)
            is_double = is_large_enough_for_double and solidity < 0.94

            # 4. Se NÃO for dupla, verificamos se ela não é grande demais para ser uma semente única
            if not is_double and area > max_seed_area:
                continue
            
            # Se o código chegou até aqui, é uma detecção válida (única ou múltipla)
            x, y, w, h = cv2.boundingRect(cnt)
            detections.append({'center': (int(x + w / 2), int(y + h / 2)), 'bbox': (x, y, w, h), 'is_double': is_double})
            
        return detections
    
    def update_spacing_chart(self, point_data):
        """Adiciona um novo ponto ao gráfico de espaçamento em tempo real."""
        time = point_data['time']
        spacing = point_data['spacing_cm']
        point_class = point_data['class']

        self.spacing_chart_data['time'].append(time)
        self.spacing_chart_data['spacing'].append(spacing)
        self.spacing_chart_line.setData(self.spacing_chart_data['time'], self.spacing_chart_data['spacing'])

        if point_class == 'aceitavel':
            self.spacing_chart_points_aceitavel['x'].append(time)
            self.spacing_chart_points_aceitavel['y'].append(spacing)
            self.spacing_chart_aceitavel_scatter.setData(self.spacing_chart_points_aceitavel['x'], self.spacing_chart_points_aceitavel['y'])
        elif point_class == 'falha':
            self.spacing_chart_points_falha['x'].append(time)
            self.spacing_chart_points_falha['y'].append(spacing)
            self.spacing_chart_falha_scatter.setData(self.spacing_chart_points_falha['x'], self.spacing_chart_points_falha['y'])
        elif point_class == 'multipla':
            self.spacing_chart_points_multipla['x'].append(time)
            self.spacing_chart_points_multipla['y'].append(spacing)
            self.spacing_chart_multipla_scatter.setData(self.spacing_chart_points_multipla['x'], self.spacing_chart_points_multipla['y'])

    def update_spacing_chart_range(self, text):
        """Atualiza a faixa do eixo Y do gráfico com base no espaçamento ideal."""
        try:
            ideal_spacing_cm = 100.0 / float(text.replace(',', '.'))
            self.spacing_chart.setYRange(0, ideal_spacing_cm * 3)
        except (ValueError, ZeroDivisionError):
            self.spacing_chart.setYRange(0, 50)

    def set_seed_type(self, text):
        self.seed_type = text

    def set_planting_speed(self, text):
        try: self.planting_speed = int(text)
        except ValueError: self.planting_speed = 3

    def set_seeds_per_meter(self, text):
        try:
            self.seeds_per_meter = float(text.replace(',', '.'))
        except (ValueError, TypeError):
            self.seeds_per_meter = 0.0

    def set_tube_type(self, text):
        """Define o Deliniamento selecionado."""
        self.tube_type = text

    def set_pixels_per_cm(self, value):
        self.pixels_per_cm = value 
        self.pixels_cm_display.setText(f"{self.pixels_per_cm:.2f}")

    def update_time_label(self):
        if self.cap and self.fps > 0:
            total_seconds = self.frame_count / self.fps
            minutes = int(total_seconds // 60)
            seconds = int(total_seconds % 60)
            milliseconds = int((total_seconds * 1000) % 1000)
            self.time_label.setText(f"Tempo: {minutes:02d}:{seconds:02d}:{milliseconds:03d}")

    def setup_spacing_chart_plots(self):
        """Configura os itens de plotagem para o gráfico de espaçamento."""
        self.acceptable_spacing_region = pg.LinearRegionItem(orientation=pg.LinearRegionItem.Horizontal, brush=pg.mkBrush(22, 163, 74, 40), pen=pg.mkPen(None))
        self.acceptable_spacing_region.setMovable(False)
        self.spacing_chart.addItem(self.acceptable_spacing_region)
        self.acceptable_spacing_region.hide()

        self.spacing_chart_line = self.spacing_chart.plot(pen=pg.mkPen(color='#94a3b8', width=1))
        self.spacing_chart_aceitavel_scatter = self.spacing_chart.plot(pen=None, symbol='o', symbolBrush='#059669', symbolSize=6)
        self.spacing_chart_falha_scatter = self.spacing_chart.plot(pen=None, symbol='o', symbolBrush='#dc2626', symbolSize=6)
        self.spacing_chart_multipla_scatter = self.spacing_chart.plot(pen=None, symbol='o', symbolBrush='#7c3aed', symbolSize=6)
        
        self.ideal_spacing_line = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('#16a34a', style=Qt.DashLine, width=2))
        self.spacing_chart.addItem(self.ideal_spacing_line)
        self.ideal_spacing_line.hide()

        self.ideal_spacing_legend = pg.TextItem(anchor=(0, 1))
        self.ideal_spacing_legend.setPos(0, 0)
        self.spacing_chart.addItem(self.ideal_spacing_legend)
        self.ideal_spacing_legend.hide()

    def update_ideal_spacing_display(self, text):
        """Atualiza o display de espaçamento ideal e a linha no gráfico em tempo real."""
        try:
            seeds_per_m = float(text.replace(',', '.'))
            if seeds_per_m > 0:
                ideal_spacing_cm = 100.0 / seeds_per_m
                if hasattr(self, 'ideal_spacing_line'):
                    self.ideal_spacing_line.setPos(ideal_spacing_cm)
                    self.ideal_spacing_line.show()
                    legend_html = f'<div style="background-color:rgba(241, 245, 249, 0.8); color:#16a34a; padding:3px 3px; border-radius:3px;"><b>Esp. Ideal: {ideal_spacing_cm:.1f} cm</b></div>'
                    self.ideal_spacing_legend.setPos(0, ideal_spacing_cm)
                    self.ideal_spacing_legend.setHtml(legend_html)
                    self.ideal_spacing_legend.show()

                    if hasattr(self, 'acceptable_spacing_region'):
                        lower_bound = 0.5 * ideal_spacing_cm
                        upper_bound = 1.5 * ideal_spacing_cm
                        self.acceptable_spacing_region.setRegion([lower_bound, upper_bound])
                        self.acceptable_spacing_region.show()
            else:
                if hasattr(self, 'ideal_spacing_line'): self.ideal_spacing_line.hide()
                if hasattr(self, 'ideal_spacing_legend'): self.ideal_spacing_legend.hide()
                if hasattr(self, 'acceptable_spacing_region'): self.acceptable_spacing_region.hide()

        except (ValueError, ZeroDivisionError):
            if hasattr(self, 'ideal_spacing_line'): self.ideal_spacing_line.hide()
            if hasattr(self, 'ideal_spacing_legend'): self.ideal_spacing_legend.hide()
            if hasattr(self, 'acceptable_spacing_region'): self.acceptable_spacing_region.hide()    
    def update_temperature_value(self, value):
        self.temperature_value = value
        self.temp_label.setText(f"{value}%")       
        """Atualiza o valor da temperatura e o label."""
        self.temp_value = value
        self.temp_label.setText(f"{value}%")

    def update_saturation_value(self, value):
        self.saturation_value = value
        self.sat_label.setText(f"{value}%")    
        """Atualiza o valor da saturação e o label."""
        self.sat_value = value
        self.sat_label.setText(f"{value}%")

    def set_playback_speed(self, index):
        if 0 <= index < len(self.speed_ruler.speeds):
            self.playback_speed = self.speed_ruler.speeds[index]
        else:
            self.playback_speed = 1.0 # Fallback para velocidade normal
        if self.timer.isActive():
            self.timer.setInterval(int(1000 / (self.fps * self.playback_speed)))
            if self.fps > 0 and self.playback_speed > 0:
                self.timer.setInterval(int(1000 / (self.fps * self.playback_speed)))

    def adjust_saturation(self, value):
        self.saturation_value = value
        self.saturation_value_label.setText(f"{value}%")
        if not self.playing and self.current_frame is not None:
            adjusted_frame = self.apply_visual_adjustments(self.current_frame)
            processed_frame = self.detect_seeds_in_frame(adjusted_frame)
            self.display_frame(processed_frame)

    def adjust_temperature(self, value):
        self.temperature_value = value
        self.temperature_value_label.setText(f"{value}K")
        if not self.playing and self.current_frame is not None:
            adjusted_frame = self.apply_visual_adjustments(self.current_frame)
            processed_frame = self.detect_seeds_in_frame(adjusted_frame)
            self.display_frame(processed_frame)

    def apply_visual_adjustments(self, frame):
        """Aplica ajustes de saturação e temperatura ao frame."""
        if self.saturation_value == 0 and self.temperature_value == 0:
            return frame

        # 1. Ajuste de Saturação (HSV)
        frame_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        # O slider vai de -100 a 100. O fator deve ser de 0 a 2.
        sat_factor = (self.saturation_value + 100) / 100.0
        s_channel = frame_hsv[:, :, 1].astype(np.float32) * sat_factor
        frame_hsv[:, :, 1] = np.clip(s_channel, 0, 255).astype(np.uint8)
        frame_adjusted = cv2.cvtColor(frame_hsv, cv2.COLOR_HSV2BGR)

        # 2. Ajuste de Temperatura (Simulação com Balanço de Cores RGB)
        # O slider vai de -100 (frio) a 100 (quente).
        temp_factor = self.temperature_value / 100.0
        
        # Fator de ajuste: 1.0 + (temp_factor) * 0.5
        # Se temp_factor = 1.0 (100%), fator = 1.5 (mais vermelho)
        # Se temp_factor = -1.0 (-100%), fator = 0.5 (menos vermelho)
        r_factor = 1.0 + (temp_factor) * 0.5
        b_factor = 1.0 - (temp_factor) * 0.5
        
        r_channel = frame_adjusted[:, :, 2].astype(np.float32) * r_factor
        b_channel = frame_adjusted[:, :, 0].astype(np.float32) * b_factor
        
        frame_adjusted[:, :, 2] = np.clip(r_channel, 0, 255).astype(np.uint8)
        frame_adjusted[:, :, 0] = np.clip(b_channel, 0, 255).astype(np.uint8)
        
        return frame_adjusted

        if self.saturation_value != 0:
            hsv = cv2.cvtColor(adjusted_frame, cv2.COLOR_BGR2HSV)
            h, s, v = cv2.split(hsv)
            s = s.astype(np.float32)
            
            # Ajuste de Saturação: Multiplica o canal S
            # O valor do slider é de -100 a 100.
            # O fator de multiplicação será de 0.0 a 2.0 (1.0 + value/100)
            factor = 1.0 + (self.saturation_value / 100.0)
            s = s * factor
            s = np.clip(s, 0, 255).astype(np.uint8)
            
            adjusted_frame = cv2.cvtColor(cv2.merge([h, s, v]), cv2.COLOR_HSV2BGR)

        if self.temperature_value != 0:
            # Ajuste de Temperatura: Simplesmente adiciona/subtrai dos canais R e B
            # O valor do slider é de -100 a 100.
            # O valor de ajuste será de -50 a 50
            temp_adj = int(self.temperature_value * 0.5)

            # Para temperatura (mais quente): Aumenta R, Diminui B
            # Para temperatura (mais frio): Diminui R, Aumenta B
            
            # Divide o frame em canais B, G, R
            b, g, r = cv2.split(adjusted_frame)
            
            # Ajusta R e B
            r = r.astype(np.int16) + temp_adj
            b = b.astype(np.int16) - temp_adj
            
            # Garante que os valores permaneçam no intervalo [0, 255]
            r = np.clip(r, 0, 255).astype(np.uint8)
            b = np.clip(b, 0, 255).astype(np.uint8)
            
            # Mescla os canais de volta
            adjusted_frame = cv2.merge([b, g, r])

        return adjusted_frame

    def adjust_temperature_cv(self, frame, value):
        """Aplica ajuste de temperatura (color balance) usando OpenCV."""
        # O valor do slider é de -100 a 100.
        # Mapeia para um valor de ajuste de temperatura, por exemplo, -50 a 50
        temp_adj = int(value * 0.5)

        # Se o ajuste for zero, retorna o frame original
        if temp_adj == 0:
            return frame

        # Divide o frame em canais B, G, R
        b, g, r = cv2.split(frame)
        
        # Ajusta R e B
        # Para temperatura (mais quente): Aumenta R, Diminui B
        # Para temperatura (mais frio): Diminui R, Aumenta B
        
        r = r.astype(np.int16) + temp_adj
        b = b.astype(np.int16) - temp_adj
        
        # Garante que os valores permaneçam no intervalo [0, 255]
        r = np.clip(r, 0, 255).astype(np.uint8)
        b = np.clip(b, 0, 255).astype(np.uint8)
        
        # Mescla os canais de volta
        return cv2.merge([b, g, r])

    def update_cv_display(self):
        """Calcula e atualiza o Coeficiente de Variação em tempo real."""
        spacing_values = [d['spacing_cm'] for d in self.spacing_data]
        if len(spacing_values) > 1:
            mean_spacing = np.mean(spacing_values)
            std_dev = np.std(spacing_values)
            cv_percentage = (std_dev / mean_spacing * 100) if mean_spacing > 0 else 0
            self.cv_value_label.setText(f"{cv_percentage:.1f}%")
        else:
            self.cv_value_label.setText("0.0%")


    def video_label_clicked(self, event: QMouseEvent):
        pass

    def on_tab_changed(self, index):
        if index == 1 and self.cap and self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.cap.read()
            if ret:
                self.calibration_tab.set_first_frame(frame)
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.frame_count)
        elif index == 3: # Índice 3 é a aba Relatórios
            self.update_reports_display()
    
    def show_calibration_tab(self):
        """Mostra a aba de calibração e muda para ela."""
        if hasattr(self, 'calibration_tab_index'):
            self.tab_widget.setTabVisible(self.calibration_tab_index, True)
            self.tab_widget.setCurrentIndex(self.calibration_tab_index)

    def populate_camera_list(self):
        """Detecta e lista as câmeras disponíveis."""
        self.camera_combo.clear()
        available_cameras = []
        for i in range(5):
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if cap.isOpened():
                available_cameras.append(f"Câmera {i}")
                cap.release()
        if available_cameras:
            self.camera_combo.addItems(available_cameras)
        else:
            self.camera_combo.addItem("Nenhuma câmera encontrada")
            self.camera_combo.setEnabled(False)
            self.start_camera_btn.setEnabled(False)

    def start_camera_feed(self):
        """Inicia a transmissão da câmera selecionada."""
        camera_index = self.camera_combo.currentIndex()
        if camera_index >= 0:
            self.load_video(camera_index)
            self.reset_analysis()

    # Linha 5532 (Substitua a função completa)
    # Linha 5532 (Substitua a função completa)
    # Linha 5532 (Substitua a função completa)
    def save_project(self):
        """Salva o estado completo do projeto (Setup, Calibração, Análise e Resultados) em um arquivo JSON."""
        
        os.makedirs(PROJECTS_DIR, exist_ok=True)
        default_filename = f"{self.initial_data.get('test_name', 'projeto_sem_nome')}.json"
        filename, _ = QFileDialog.getSaveFileName(self, "Salvar Projeto", os.path.join(PROJECTS_DIR, default_filename), "JSON Files (*.json)")
        
        if filename:
            # --- CORREÇÃO: Salva no formato "plano" (igual ao Teste2.json) ---
            project_data = {}
            
            # Adiciona os dados do 'initial_data' diretamente
            project_data.update(self.initial_data)
            
            # Adiciona os outros dados
            project_data['pixels_per_cm'] = self.pixels_per_cm
            project_data['video_path'] = self.video_path
            project_data['seeds_per_meter'] = self.seeds_per_m_input.text()
            project_data['row_spacing'] = self.row_spacing_combo.currentText()
            project_data['auto_save_seed_count'] = self.auto_save_seed_count
            project_data['detection_method'] = self.detection_method
            project_data['saturation_value'] = self.saturation_value
            project_data['temperature_value'] = self.temperature_value
            project_data['analysis_results'] = self.analysis_results
            project_data['next_analysis_id'] = self.next_analysis_id
            
            try:
                with open(filename, 'w') as f:
                    json.dump(project_data, f, indent=4)
                
                # --- CORREÇÃO (AttributeError) ---
                msg = QMessageBox(self)
                msg.setWindowTitle("Sucesso")
                msg.setText("Projeto salvo com sucesso!")
                msg.setIcon(QMessageBox.Information)
                msg.setStandardButtons(QMessageBox.Ok)
                msg.setStyleSheet(DARK_MESSAGE_BOX_STYLE)
                msg.exec()
                
            except Exception as e:
                # --- CORREÇÃO (AttributeError) ---
                msg = QMessageBox(self)
                msg.setWindowTitle("Erro")
                msg.setText(f"Erro ao salvar o projeto: {e}")
                msg.setIcon(QMessageBox.Critical)
                msg.setStandardButtons(QMessageBox.Ok)
                msg.setStyleSheet(DARK_MESSAGE_BOX_STYLE)
                msg.exec()

    # Linha 5575 (Substitua a função completa)
   # Linha 5575 (Substitua a função completa)
    def load_project(self):
        """Carrega um projeto salvo (.json) e restaura o estado da aplicação."""
        
        filename, _ = QFileDialog.getOpenFileName(self, "Carregar Projeto", PROJECTS_DIR, "JSON Files (*.json)")
        if filename:
            try:
                with open(filename, 'r') as f:
                    project_data = json.load(f)
                
                # --- CORREÇÃO: Lê o formato "plano" ---
                
                # 1. Dados Iniciais (Setup) - Carrega da raiz
                self.initial_data = {
                    "user_email": project_data.get('user_email', ''),
                    "test_name": project_data.get('test_name', ''),
                    "seed_type": project_data.get('seed_type', ''),
                    "test_design": project_data.get('test_design', ''),
                    "speed": project_data.get('speed', '3'),
                    "seeds_per_m": project_data.get('seeds_per_m', ''),
                    "row_spacing": project_data.get('row_spacing', '45')
                }
                
                # 2. Dados da Calibração
                self.pixels_per_cm = project_data.get('pixels_per_cm', 29.80)
                
                # 3. Dados da Análise (Configurações)
                self.video_path = project_data.get('video_path')
                self.auto_save_seed_count = project_data.get('auto_save_seed_count', 251)
                self.detection_method = project_data.get('detection_method', 'hsv')
                self.saturation_value = project_data.get('saturation_value', 0)
                self.temperature_value = project_data.get('temperature_value', 0)
                
                # 4. Resultados (Relatórios e Estatísticas)
                self.analysis_results = project_data.get('analysis_results', [])
                self.next_analysis_id = project_data.get('next_analysis_id', max([res.get('id', 0) for res in self.analysis_results] or [0]) + 1)

                # --- Atualiza a UI com os dados carregados ---
                self.video_path_label.setText(os.path.basename(self.video_path) if self.video_path else "Nenhum vídeo selecionado")
                
                self.populate_initial_data() # Preenche os combos e inputs com self.initial_data
                
                # Define os valores dos inputs da aba Analisar
                self.seeds_per_m_input.setText(str(project_data.get('seeds_per_meter', self.initial_data.get('seeds_per_m', ''))))
                self.auto_save_count_input.setText(str(self.auto_save_seed_count))
                self.pixels_cm_display.setText(f"{self.pixels_per_cm:.2f}")
                self.row_spacing_combo.setCurrentText(project_data.get('row_spacing', self.initial_data.get('row_spacing', '45')))
                
                # (O restante do código para definir sliders, método de detecção, etc., permanece o mesmo)
                # ...
                
                self.update_ideal_spacing_display(self.seeds_per_m_input.text())
                self.reset_analysis()
                self.update_reports_display()
                self.update_statistics_table() # Preenche a tabela de estatísticas

                # --- CORREÇÃO (AttributeError) ---
                msg = QMessageBox(self)
                msg.setWindowTitle("Sucesso")
                msg.setText("Projeto carregado com sucesso!")
                msg.setIcon(QMessageBox.Information)
                msg.setStandardButtons(QMessageBox.Ok)
                msg.setStyleSheet(DARK_MESSAGE_BOX_STYLE)
                msg.exec()
                    
            except Exception as e:
                # --- CORREÇÃO (AttributeError) ---
                msg = QMessageBox(self)
                msg.setWindowTitle("Erro")
                msg.setText(f"Erro ao carregar o projeto: {e}")
                msg.setIcon(QMessageBox.Critical)
                msg.setStandardButtons(QMessageBox.Ok)
                msg.setStyleSheet(DARK_MESSAGE_BOX_STYLE)
                msg.exec()

    def show_help(self):
        help_dialog = HelpWindow(self)
        help_dialog.exec()

    def show_update_dialog(self):
        """Exibe a janela de diálogo de atualização."""
        dialog = UpdateDialog(self,current_version=CURRENT_VERSION)
        dialog.exec()

    def update_finished_handler(self, success, message):
        """Trata o resultado da thread de atualização do modelo."""
        if success:
            msg=QMessageBox.information(self, "Atualização Concluída", message)
            msg.setStyleSheet(DARK_MESSAGE_BOX_STYLE)
            msg.exec()
            # Recarrega o modelo YOLO se o download foi bem-sucedido
            self.load_yolo_model()
        else:
            msg=QMessageBox.warning(self, "Atualização Falhou", message)
            msg.setStyleSheet(DARK_MESSAGE_BOX_STYLE)
            msg.exec()

    def load_yolo_model(self):
        """Função auxiliar para carregar o modelo YOLO, que deve ser chamada após o download."""
        model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "SVA", TARGET_FILENAME)
        if os.path.exists(model_path):
            try:
                from ultralytics import YOLO
                # A linha 43 já importa 'YOLO'
                self.yolo_model = YOLO(model_path)
                print(f"Modelo YOLO carregado com sucesso de: {model_path}")
            except Exception as e:
                print(f"Erro ao carregar o modelo YOLO: {e}")
                self.yolo_model = None
        else:
            print(f"Aviso: Arquivo {TARGET_FILENAME} não encontrado no diretório do programa. Usando modelo padrão ou None.")
            # Tenta carregar o modelo padrão (se houver) ou deixa como None
            self.yolo_model = None

    def show_help(self):
        help_dialog = HelpWindow(self)
        help_dialog.exec()

    def reset_analysis(self):
        self.aceitavel_count = 0
        self.falha_count = 0
        self.multipla_count = 0
        self.total_seeds_detected = 0
        self.spacing_data = []
        self.detected_seeds_history = []
        self.auto_save_prompt_shown = False # Reseta a flag do aviso
        self.update_bar_chart(0, 0, 0)
        self.frame_count = 0
        self.update_cv_display() # Reseta o display do CV
        self.tracked_seeds = {}
        self.next_seed_id = 0
        self.disappeared_seeds = {} # Limpa as sementes desaparecidas
        self.last_crossed_seed_x = None
        self.update_time_label()
        
        if self.cap:
            self.reset_model_state()
            self.spacing_chart_data = {'time': [], 'spacing': []}
            self.spacing_chart_points_aceitavel = {'x': [], 'y': []}
            self.spacing_chart_points_falha = {'x': [], 'y': []}
            self.spacing_chart_points_multipla = {'x': [], 'y': []}
            self.spacing_chart_line.clear()
            self.spacing_chart_aceitavel_scatter.clear()
            self.spacing_chart_falha_scatter.clear()
            self.spacing_chart_multipla_scatter.clear()
            
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            
            ret, frame = self.cap.read()
            if ret:
                self.display_frame(frame)

    def reset_counters_for_continuation(self):
        """
        Reinicia a contagem das sementes e dados da análise,
        mas preserva o ponto atual do vídeo. 
        Também descarta quaisquer sementes que já tenham cruzado
        a linha vermelha de contagem (para evitar recontagem).
        """
        # === Reset dos contadores principais ===
        self.aceitavel_count = 0
        self.falha_count = 0
        self.multipla_count = 0
        self.total_seeds_detected = 0
        self.spacing_data = []
        self.auto_save_prompt_shown = False
        self.partial_seed_count_start = 0
        self.last_crossed_seed_x = None

        # === Reset de estruturas de rastreamento ===
        self.tracked_seeds = {}
        self.next_seed_id = 0
        self.disappeared_seeds = {}

        # --- NOVO: remove sementes após a linha vermelha ---
        try:
            if hasattr(self, "count_line_x") and self.count_line_x is not None:
                # Mantém apenas as sementes que ainda não cruzaram a linha
                self.detected_seeds_history = [
                    s for s in getattr(self, "detected_seeds_history", [])
                    if s.get("x", 0) < self.count_line_x
                ]
            else:
                # Se não houver linha definida, limpa tudo
                self.detected_seeds_history = []
        except Exception:
            self.detected_seeds_history = []

        # === Reset de gráficos e displays ===
        self.update_bar_chart(0, 0, 0)
        self.update_cv_display()
        self.spacing_chart_data = {'time': [], 'spacing': []}

        # Limpa gráficos individuais
        for plot in [
            self.spacing_chart_line,
            self.spacing_chart_aceitavel_scatter,
            self.spacing_chart_falha_scatter,
            self.spacing_chart_multipla_scatter
        ]:
            try:
                plot.clear()
            except Exception:
                pass

        print("[INFO] Contadores reiniciados e sementes após a linha vermelha desconsideradas.")

    def reset_model_state(self):
        """Reseta o estado do modelo de detecção para forçar o recarregamento."""
        self.yolo_model = None

if __name__ == '__main__':
    try:
        import ctypes
        myappid = 'talisson.seedcounter.v1'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except (ImportError, AttributeError):
        pass

    app = QApplication(sys.argv)    
    app.setWindowIcon(QIcon(resource_path("icone.ico")))

    # --- LÓGICA DE INICIALIZAÇÃO ---
    # 1. Mostra a tela de splash imediatamente
    splash = SplashScreen()
    screen_geometry = app.primaryScreen().geometry()
    splash.move((screen_geometry.width() - splash.width()) // 2, (screen_geometry.height() - splash.height()) // 2)
    splash.show()
    app.processEvents() # Garante que a splash screen seja desenhada
    QTimer.singleShot(50, lambda: None) # Pequeno delay para o Windows processar o ícone

    # 2. Mostra a nova janela de configuração
    setup_dialog = SetupDialog()
    
    # 3. O programa só continua se o usuário clicar em "Iniciar"
    if setup_dialog.exec() == QDialog.Accepted:
        initial_data = setup_dialog.get_data()

        # 4. Cria a janela principal, passando os dados da configuração
        main_window = MainWindow(initial_data=initial_data)
        
        # Centraliza a janela principal e a exibe
        top_left_x = (screen_geometry.width() - main_window.width()) // 2
        main_window.move(top_left_x, 0)
        
        # 5. Fecha a splash e mostra a janela principal
        splash.close()
        main_window.show()
        sys.exit(app.exec())
    else:
        # Se o usuário fechar a janela de configuração, o programa encerra
        splash.close() # Garante que a splash feche antes de sair
        sys.exit(0)

    def save_project(self, auto_save=False):
        """Salva o estado atual do projeto (dados de setup, calibração e resultados de análise)."""
        project_data = {
            "is_loaded_project": True, # Indica que é um arquivo de projeto
            "user_email": self.setup_data.get("user_email"),
            "test_name": self.setup_data.get("test_name"),
            "seed_type": self.setup_data.get("seed_type"),
            "test_design": self.setup_data.get("test_design"),
            "speed": self.setup_data.get("speed"),
            "pixel_cm_ratio": self.pixel_cm_ratio,
            "analysis_results": self.analysis_results,
            "analysis_counter": self.analysis_counter
        }

        default_filename = f"{self.setup_data.get('test_name', 'Novo_Projeto')}.scproj"
        
        if auto_save:
            # Tenta salvar no diretório de trabalho, sem perguntar
            save_dir = os.path.join(os.path.expanduser("~"), "SVA_Projects")
            os.makedirs(save_dir, exist_ok=True)
            file_path = os.path.join(save_dir, default_filename)
        else:
            file_path, _ = QFileDialog.getSaveFileName(self, "Salvar Projeto", default_filename, "SVA Project (*.scproj)")
        
        if file_path:
            try:
                with open(file_path, 'wb') as f:
                    pickle.dump(project_data, f)
                
                if not auto_save:
                    msg=QMessageBox.information(self, "Sucesso", f"Projeto salvo com sucesso em:\n{file_path}")
                    msg.setStyleSheet(DARK_MESSAGE_BOX_STYLE)
                    msg.exec()
            except Exception as e:
                msg=QMessageBox.critical(self, "Erro ao Salvar Projeto", f"Não foi possível salvar o projeto:\n{e}")
                msg.setStyleSheet(DARK_MESSAGE_BOX_STYLE)
                msg.exec()

    def load_project_data(self, project_data):
        """Carrega os dados de um projeto salvo na MainWindow."""
        self.setup_data = {
            "user_email": project_data.get("user_email", ""),
            "test_name": project_data.get("test_name", "Projeto Carregado"),
            "seed_type": project_data.get("seed_type", ""),
            "test_design": project_data.get("test_design", ""),
            "speed": project_data.get("speed", ""),
            "tube_type": "N/A", 
            "seeds_per_m": "0",
            "row_spacing": "0"
        }
        self.pixel_cm_ratio = project_data.get("pixel_cm_ratio", 0.0)
        self.analysis_results = project_data.get("analysis_results", [])
        self.analysis_counter = project_data.get("analysis_counter", 0)

        self.setWindowTitle(f"SVA - {self.setup_data.get('test_name', 'Projeto Carregado')}")
        self.update_analysis_tab()
        self.update_analysis_summary()
        # É necessário garantir que o widget de calibração exista antes de chamar set_pixel_cm_ratio
        if hasattr(self, 'calibration_tab'):
            self.calibration_tab.set_pixel_cm_ratio(self.pixel_cm_ratio)
        
        msg=QMessageBox.information(self, "Projeto Carregado", f"Projeto '{self.setup_data['test_name']}' carregado com sucesso. Calibração e resultados restaurados.")
        msg.setStyleSheet(DARK_MESSAGE_BOX_STYLE)
        msg.exec()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    # Simulação da versão atual
    dialog = UpdateDialog(current_version=CURRENT_VERSION)
    dialog.exec()
    sys.exit(app.exec())
