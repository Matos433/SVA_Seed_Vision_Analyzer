from tkinter import messagebox
import requests
import os
import sys
import threading
import subprocess
import pathlib
import shutil
from datetime import datetime
import time

from updates import _create_and_execute_update_script

# Constantes para controle de janelas do Windows
SW_HIDE = 0
SW_SHOWNORMAL = 1
SW_SHOWMINIMIZED = 2
SW_SHOWMAXIMIZED = 3



def is_version_greater(latest_version, current_version):
    """
    Compara duas versões e retorna True se a versão mais recente for superior à atual.

    Args:
        latest_version (str): Versão mais recente (ex: "0.3.9", "1.0.0")
        current_version (str): Versão atual (ex: "0.3.2", "0.9.1")

    Returns:
        bool: True se latest_version > current_version, False caso contrário
    """

    def parse_version(version_str):
        """
        Converte string de versão em lista de inteiros para comparação.
        Exemplo: "0.3.9" -> [0, 3, 9]
        """
        try:
            # Remove caracteres não numéricos e pontos extras
            clean_version = version_str.strip()
            # Divide por pontos e converte para inteiros
            parts = []
            for part in clean_version.split("."):
                # Extrai apenas números da parte
                numeric_part = "".join(filter(str.isdigit, part))
                if numeric_part:
                    parts.append(int(numeric_part))
                else:
                    parts.append(0)
            return parts
        except Exception as e:
            logger.warning(f"Erro ao fazer parse da versão '{version_str}': {e}")
            return [0]

    try:
        latest_parts = parse_version(latest_version)
        current_parts = parse_version(current_version)

        # Normaliza o tamanho das listas (preenche com zeros se necessário)
        max_len = max(len(latest_parts), len(current_parts))
        latest_parts.extend([0] * (max_len - len(latest_parts)))
        current_parts.extend([0] * (max_len - len(current_parts)))

        # Compara parte por parte
        for latest_part, current_part in zip(latest_parts, current_parts):
            if latest_part > current_part:
                return True
            elif latest_part < current_part:
                return False

        # Se chegou até aqui, as versões são iguais
        return False

    except Exception as e:
        logger.error(f"Erro na comparação de versões: {e}")
        # Em caso de erro, usa comparação simples de string como fallback
        return latest_version != current_version


def check_for_updates(url, hw=False, config=None, is_check_startup=False):

    try:
        user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        )
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": user_agent,
        }
        if hw:
            vers = config.HW_info.get("Version", "N/A")
            current_version = (
                vers.lower()
                .replace("release", "")
                .replace("v", "")
                .replace("rc", "")
                .replace("alpha", "")
                .replace("beta", "")
                .replace("-", "")
                .replace(" ", "")
            )
            if (
                current_version == "N/A"
                or current_version == ""
                or current_version is None
            ):
                messagebox.showwarning("Erro", "Versão atual não obtida.")
                return
        else:
            current_version = (
                VERSION_GBOX.lower()
                .replace("release", "")
                .replace("v", "")
                .replace("rc", "")
                .replace("alpha", "")
                .replace("beta", "")
                .replace("-", "")
                .replace(" ", "")
            )
        latest_version = get_latest_version(headers, url)

        if latest_version is None:
            logger.error("Não foi possível obter a versão mais atualizada.")
            return

        elif is_version_greater(latest_version, current_version):
            if is_check_startup:
                # Verificar se o usuário desabilitou as notificações automáticas
                if (
                    not hw
                    and hasattr(config, "auto_check_updates")
                    and not config.auto_check_updates
                ):
                    return  # Não mostrar se estiver desabilitado
                elif (
                    hw
                    and hasattr(config, "auto_check_hw_updates")
                    and not config.auto_check_hw_updates
                ):
                    return  # Não mostrar se estiver desabilitado

                # Usar messagebox com checkbox para verificação inicial
                if not hw:
                    title = "Atualização Disponível"
                    message = (
                        f"Nova versão disponível: {latest_version}\n"
                        f"Versão atual: {current_version}\n\n"
                        f"Deseja atualizar agora?"
                    )
                    checkbox_text = (
                        "Não quero mais receber notificações de atualizações,\n"
                        "estou satisfeito com a versão atual, velha e defasada."
                    )
                    res, dont_show_again = messagebox_with_checkbox(
                        config.root_interface,
                        title,
                        message,
                        checkbox_text,
                        config,
                    )
                else:
                    title = "Atualização de firmware Disponível"
                    message = (
                        f"Nova versão de firmware disponível: {latest_version}\n"
                        f"Versão atual: {current_version}\n\n"
                        f"Deseja atualizar agora?"
                    )
                    checkbox_text = (
                        "Não quero mais receber notificações de atualizações,\n"
                        "estou satisfeito com a versão atual, velha e defasada."
                    )
                    res, dont_show_again = messagebox_with_checkbox(
                        config.root_interface,
                        title,
                        message,
                        checkbox_text,
                        config,
                    )

                # Salvar preferência se checkbox foi marcado
                if dont_show_again:
                    if not hw:
                        config.auto_check_updates = False
                        # atualizar no menu também
                        if hasattr(config, "checkbox_auto_updates"):
                            config.checkbox_auto_updates.set(False)
                    elif hw:
                        config.auto_check_hw_updates = False
                        if hasattr(config, "checkbox_auto_hw_updates"):
                            config.checkbox_auto_hw_updates.set(False)
                    # Salvar esta configuração no arquivo de config se necessário
                    config.save_configs()

                if res != "yes":
                    return
            else:
                res = messagebox.askquestion(
                    message=(
                        f"Atualização disponível,  nova versão: {latest_version}, "
                        f"versão atual: {current_version} deseja atualizar?"
                    ),
                    title="Atualização",
                )
            if res == "no":
                return
            elif res == "yes":
                result_download = download_latest_version(
                    headers, url, hw, config=config
                )
                if result_download:
                    logger.info("Atualização concluída.")
                    if not hw:
                        new_filename = list(result_download.keys())[0]
                        if getattr(sys, "frozen", False):
                            res = messagebox.askquestion(
                                message=(
                                    "Atualização concluída. É necessário reiniciar para as atualizações "
                                    "surtirem efeito, reiniciar?"
                                ),
                                title="Atualização",
                            )
                            if res == "yes":
                                # Criar script de atualização e executar
                                folder = config.pasta_do_projeto_temporaria
                                _create_and_execute_update_script(new_filename, pasta_projeto=folder)
                                os._exit(0)
                        else:
                            res = messagebox.askquestion(
                                "Modo [Dev]",
                                'Atualização concluída. Ao clicar em "Sim" o script será fechado '
                                "e irá abrir o executável.",
                            )
                            if res == "yes":
                                # Configuração para evitar janelas de terminal no Windows
                                startupinfo = None
                                creation_flags = 0
                                if os.name == 'nt':  # Windows
                                    startupinfo = subprocess.STARTUPINFO()
                                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                                    startupinfo.wShowWindow = subprocess.SW_HIDE
                                    creation_flags = subprocess.CREATE_NO_WINDOW
                                
                                subprocess.Popen([new_filename], startupinfo=startupinfo, creationflags=creation_flags)
                                os._exit(0)
                    else:
                        files = list(result_download.keys())
                        port_COM = config.SERIAL_PORT
                        res = messagebox.askquestion(
                            "Update ESP32",
                            f"Download concluido, deseja atualizar o ESP32?\n"
                            f"Ao prosseguir será  tentado gravar o firmware na porta serial {port_COM}.\n\n"
                            f"Certifique-se de que o dispositivo está conectado e a porta serial está correta.",
                        )
                        if res == "yes":
                            update_esp32(files=files, config=config)

        else:
            if not is_check_startup:
                messagebox.showinfo(
                    "Versão atualizada", "Você já está com a versão mais atualizada."
                )

        if (
            current_version.lower() != "n/a"
            and current_version != None
            and is_version_greater(VERSION_MIN_FW, current_version)
            and hw
        ):
            messagebox.showwarning(
                "Firmware desatualizado",
                f"A sua versão do firmware é {current_version}, "
                f"mas a versão mínima necessária é {VERSION_MIN_FW}. "
                f"É possivel que haja problemas de compatibilidade.",
            )
    except Exception as erro:
        logger.error(f"Erro: {erro}")


def get_latest_version(headers, url):

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        latest_release = response.json()
        # Extract and normalize version number from release name
        return (
            latest_release["name"]
            .lower()
            .replace("release", "")
            .replace("v", "")
            .replace("-rc", "")
            .replace("alpha", "")
            .replace("beta", "")
            .replace("-", "")
            .replace(" ", "")
        )

    except requests.exceptions.RequestException as e:
        logger.error(f"Falha RequestException: {e}")

        return None
    except Exception as erro:
        messagebox.showwarning(f"Erro", "Erro: {erro}")
        logger.error(f"Erro: {erro}")
        return None


def download_latest_version(headers, URL, hw, config):
    """
    Downloads the latest version with a progress window.

    Args:
        headers (dict): HTTP headers for authentication

    Returns:
        str: Path to downloaded file or None if failed
    """

    progress_window = None
    from Functions.Folders import _get_local_filename
    from Functions.CustomsWindows import _create_progress_window

    try:
        # Get latest release info
        latest_release = _get_latest_release_info(headers, URL)
        if not latest_release:
            return None

        # Find executable asset
        assets = []
        if hw:
            assets = _find_bin_executable_assets(latest_release["assets"])
        else:
            asset = _find_executable_asset(latest_release["assets"])
            assets.append(asset)
        if assets is None or len(assets) == 0:
            messagebox.showerror(
                "Erro", "Arquivo executável não encontrado no release."
            )
            return None

            # Check if file already exists

        for asset in assets:
            result_download = {}
            asset_name = asset["name"]
            local_filename = _get_local_filename(
                latest_release["name"], hw, asset_name, config
            )
            print(f"Local filename: {local_filename}")
            if pathlib.Path(local_filename).is_file() and not hw:
                messagebox.showinfo(
                    "Versão atualizada",
                    "Houve um equívoco, você já está com a versão mais atualizada.",
                )
                return None

            # Create progress window
            progress_window = _create_progress_window(
                asset["name"], asset["size"], config
            )

            # Download file with progress tracking
            success = _download_file_with_progress(
                asset, local_filename, progress_window, headers
            )

            # Pós-validação: garantir que o arquivo baixado tenha um nome único
            if success and os.path.exists(local_filename):
                # Se o nome local gerado for "Gbox.exe" (sem versão), renomear para evitar conflitos
                if os.path.basename(local_filename).lower() == "gbox.exe":
                    import time

                    timestamp = int(time.time())
                    new_safe_name = os.path.join(
                        os.path.dirname(local_filename),
                        f"Gbox_downloaded_{timestamp}.exe",
                    )
                    try:
                        shutil.move(local_filename, new_safe_name)
                        local_filename = new_safe_name
                        logger.info(
                            f"Arquivo renomeado para nome único: {os.path.basename(new_safe_name)}"
                        )
                    except Exception as e:
                        logger.warning(f"Falha ao renomear arquivo: {e}")

                # Verificar integridade básica do arquivo baixado
                file_size = os.path.getsize(local_filename)
                if file_size != asset["size"]:
                    logger.warning(
                        f"Tamanho do arquivo diferente. Esperado: {asset['size']}, Atual: {file_size}"
                    )

            result_download[local_filename] = success
            progress_window.destroy()

        if all(result_download.values()):
            return result_download
        else:
            return None

    except Exception as e:
        messagebox.showerror("Erro", f"Erro durante o download: {e}")
        logger.error(f"Falha no download: {e}")
        return None


def _get_latest_release_info(headers, URL):
    """Get latest release information from GitHub API."""
    try:
        with requests.Session() as session:
            session.headers.update(headers)
            response = session.get(URL)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao obter informações do release: {e}")
        return None


def thread_check_hw_updates(config):
    version_get = get_current_version_HW(config)
    if version_get != None and version_get != "" and version_get != "N/A":
        check_for_updates(
            LATEST_RELEASE_URL_HW, hw=True, config=config, is_check_startup=True
        )
    else:
        logger.warning(
            "Versão do hardware não encontrada ou inválida. Verifique a conexão com o dispositivo."
        )
        logger.warning(version_get)


def get_current_version_HW(config):
    """
    Obtém a versão atual do hardware conectado via serial.
    Atualiza config.HW_info com as informações recebidas.
    Retorna a versão do hardware ou None se não conseguir obter.
    """
    from Functions.serial_comunication import _send_message_serial

    def update_ui_thread_safe():
        """Atualiza a UI de forma thread-safe"""
        try:
            text_info_label = ""
            for key, value in config.HW_info.items():
                text_info_label += f"{key.capitalize()}: {value}\n"

            # ✅ Agendar atualização da UI na thread principal
            config.root_interface.after(
                0, lambda: config.info_label_hw_gbox.config(text=text_info_label)
            )
        except Exception as e:
            logger.error(f"Falha ao atualizar UI: {e}")

    if config.serial is None or not config.serial.is_open:
        messagebox.showerror(
            "Erro", "Nenhum dispositivo conectado para verificar versão HW."
        )
        return None

    # Comandos esperados e chaves correspondentes
    commands = [
        ("VERSION", "Version"),
        ("BOARD", "Board"),
        ("FLASH_SIZE", "Flash_Size"),
        ("RAM", "RAM"),
        ("CPU", "CPU"),
    ]

    # Limpa HW_info antes de atualizar
    for _, key in commands:
        config.HW_info[key] = ""

    # Tenta obter cada informação separadamente
    for cmd, key in commands:
        try:
            config.serial.reset_input_buffer()
            _send_message_serial(cmd, config)

            # ✅ SOLUÇÃO: Usar lock para thread-safety
            with config.serial_lock:
                # Aguarda resposta por até 1 segundo
                start_time = time.time()
                while time.time() - start_time < 1:
                    if config.serial.in_waiting > 0:
                        answer = (
                            config.serial.readline().decode(errors="ignore").strip()
                        )
                        if f"{cmd}=" in answer:
                            config.HW_info[key] = answer.split("=", 1)[1]
                            break
                        else:
                            config.HW_info[key] = "N/A"
                    time.sleep(0.01)  # ✅ Pequena pausa para não sobrecarregar
        except Exception as e:
            config.HW_info[key] = f"Erro: {e}"

    # ✅ Atualizar UI de forma thread-safe
    update_ui_thread_safe()

    return config.HW_info.get("Version", None)


def call_check_updates(url, hw, config):
    if hw and config.connection_type != "serial":
        messagebox.showerror(
            "Erro", "Para atualizar o hardware, conexão deve ser serial."
        )
        return
    thread_update = threading.Thread(target=check_for_updates(url, hw, config))
    thread_update.start()


def _find_bin_executable_assets(assets):
    """Find the .bin executable asset in the release assets."""
    list_assets = []
    for asset in assets:
        if asset["name"].endswith(".bin"):
            list_assets.append(asset)
    if len(list_assets) == 3:
        return list_assets
    else:
        messagebox.showerror("Erro", "Arquivos .bin não encontrados no release.")
        return None


def _find_executable_asset(assets):
    """Find the executable asset in the release assets."""
    for asset in assets:
        if "Gbox" in asset["name"] and asset["name"].endswith(".exe"):
            return asset
    return None


def _download_file_with_progress(asset, local_filename, progress_window, auth_headers):
    """Download file with progress tracking using threading."""
    from Functions.CustomsWindows import _update_progress

    download_headers = {
        "Accept": "application/octet-stream",
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Connection": "keep-alive",
    }

    # Variáveis compartilhadas entre threads
    download_result = {"success": False, "error": None}

    def download_thread():
        try:
            # ADICIONAR: Configurações de sessão para melhor performance
            session = requests.Session()
            session.headers.update(download_headers)

            # ADICIONAR: Timeouts adequados
            response = session.get(
                asset["url"],
                headers=download_headers,
                stream=True,
                timeout=(10, 30),  # (connect_timeout, read_timeout)
            )

            if response.status_code != 200:
                download_result["error"] = f"Erro no download: {response.status_code}"
                return

            total_size = asset["size"]
            downloaded_size = 0

            with open(local_filename, "wb") as f:
                last_percent = 0
                for chunk in response.iter_content(chunk_size=131072):
                    # Check if user cancelled
                    if progress_window.cancel_var.get():
                        logger.info("\nDownload cancelado pelo usuário")
                        if os.path.exists(local_filename):
                            # Agendar remoção do arquivo após um breve delay para evitar conflitos
                            def delayed_removal():
                                time.sleep(0.5)  # Aguarda 500ms
                                try:
                                    if os.path.exists(local_filename):
                                        os.remove(local_filename)
                                        logger.info(
                                            f"Arquivo {local_filename} removido após cancelamento"
                                        )
                                except Exception as remove_error:
                                    logger.error(
                                        f"Falha ao remover arquivo {local_filename}: {remove_error}"
                                    )

                            # Executar remoção em thread separada
                            threading.Thread(
                                target=delayed_removal, daemon=True
                            ).start()
                        download_result["error"] = "Download cancelado"
                        return

                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)

                        # Update progress on main thread
                        percent = (downloaded_size / total_size) * 100
                        if percent - last_percent >= 1:
                            last_percent = percent
                            progress_window.root_interface.after(
                                0,
                                lambda p=percent, d=downloaded_size, t=total_size: _update_progress(
                                    progress_window, p, d, t
                                ),
                            )

            download_result["success"] = True

        except Exception as e:
            download_result["error"] = f"Erro durante o download: {e}"
            logger.error(f"Falha no download: {e}")

        # Close progress window on main thread
        progress_window.root_interface.after(0, progress_window.destroy)

    # Start download in separate thread
    thread = threading.Thread(target=download_thread, daemon=True)
    thread.start()

    # Wait for download to complete or be cancelled
    while thread.is_alive():
        progress_window.update()
        if progress_window.cancel_var.get():
            # Give thread time to cleanup
            thread.join(timeout=1.0)
            break
        progress_window.after(100)  # Check every 100ms

    # Return result
    if download_result["error"]:
        if "cancelado" not in download_result["error"]:
            messagebox.showerror("Erro", download_result["error"])
        return False

    return download_result["success"]