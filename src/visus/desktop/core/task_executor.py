"""
Bot Vision Suite - Task Executor

Este módulo gerencia a execução de tarefas de automação, incluindo
detecção de texto/imagem, cliques, digitação e navegação com backtracking.
"""

import time
import threading
import logging
import os
from typing import List, Dict, Any, Optional, Tuple, Union
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image

from ..utils.config import BotVisionConfig
from ..utils.text_filters import limpar_texto, matches_filter
from ..exceptions import TaskExecutionError, ImageNotFoundError, TextNotFoundError
from .ocr_engine import OCREngine
from .overlay import show_overlay
from .relative_image import RelativeImageDetector
from .keyboard_commands import KeyboardCommander
from .virtual_mouse import VirtualMouse
from .wait_manager import WaitManager

logger = logging.getLogger(__name__)


class TaskResult:
    """Classe para armazenar resultado de execução de uma task."""
    
    def __init__(self, task_index: int, success: bool, task_name: str, 
                 location: Optional[Tuple] = None, error: Optional[str] = None):
        self.task_index = task_index
        self.success = success
        self.task_name = task_name
        self.location = location
        self.error = error
        self.attempts = 0


class TaskExecutor:
    """
    Executor de tarefas de automação com suporte a OCR, detecção de imagem
    e execução robusta com backtracking.
    """
    
    def __init__(self, config: Optional[BotVisionConfig] = None):
        """
        Inicializa o executor de tarefas.

        Args:
            config (BotVisionConfig, optional): Configuração da biblioteca
        """
        self.config = config or BotVisionConfig()
        self.ocr_engine = OCREngine(self.config)
        self.relative_detector = RelativeImageDetector()
        self.keyboard_commander = KeyboardCommander()
        self.virtual_mouse = VirtualMouse(self.config)
        self.wait_manager = WaitManager(self.config)

        # Configurações padrão
        self.default_confidence = 0.9
        self.default_margin = 50
        self.max_attempts = 4

        # Estado interno
        self.task_failures = {}
        self.current_task_index = 0
        self.last_extracted_text = None  # Armazena último texto extraído

        self._setup_pyautogui()
    
    def _setup_pyautogui(self) -> None:
        """Configura PyAutoGUI com as configurações apropriadas."""
        try:
            import pyautogui
            # Configurações de segurança e performance
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.1
        except ImportError:
            raise TaskExecutionError("PyAutoGUI não está instalado")
    
    def execute_tasks(self, tasks: List[Dict[str, Any]]) -> List[TaskResult]:
        """
        Executa uma lista de tarefas sequencialmente.
        Implementa backtrack corretamente: volta para a tarefa anterior e depois retorna para a que falhou.
        
        Args:
            tasks (list): Lista de dicionários com configurações das tarefas
            
        Returns:
            list: Lista de TaskResult com resultados de cada tarefa
            
        Raises:
            TaskExecutionError: Se houver erro crítico na execução
        """
        if not tasks:
            logger.warning("Lista de tarefas está vazia")
            return []
        
        logger.info(f"Iniciando execução de {len(tasks)} tarefas")
        
        results = []
        i = 0
        backtrack_stack = []  # Pilha para rastrear backtracks
        
        while i < len(tasks):
            task = tasks[i]
            task_result = self._execute_single_task(task, i, len(tasks))
            
            # Adiciona resultado apenas se não for uma reexecução
            if len(results) <= i:
                results.append(task_result)
            else:
                results[i] = task_result  # Atualiza resultado existente
            
            if task_result.success:
                logger.info(f"✓ Tarefa {i+1}/{len(tasks)}: '{task_result.task_name}' concluída com sucesso")
                
                # Verifica se há backtracks pendentes na pilha
                if backtrack_stack:
                    # Remove o item da pilha e volta para a tarefa original que falhou
                    original_failed_task = backtrack_stack.pop()
                    logger.info(f"🔄 Retornando para a tarefa {original_failed_task+1} que originalmente falhou após backtrack")
                    i = original_failed_task
                    # Reseta as tentativas de falha para a tarefa original
                    if i in self.task_failures:
                        self.task_failures[i] = 0
                else:
                    # Comportamento normal: avança para a próxima tarefa
                    i += 1
                
                # Se não foi um skip, executa a ação
                if task_result.location != "skip":
                    self._perform_action(task, task_result.location)
            else:
                # Tarefa falhou, verifica backtracking
                backtrack = task.get('backtrack', False)
                
                if backtrack and i > 0:
                    # Gerencia backtracking
                    self.task_failures.setdefault(i, 0)
                    self.task_failures[i] += 1
                    
                    if self.task_failures[i] <= 2:  # Limita tentativas de backtrack
                        # Adiciona a tarefa atual na pilha de backtrack (para retornar depois)
                        if i not in backtrack_stack:  # Evita duplicatas
                            backtrack_stack.append(i)
                            logger.info(f"📌 Tarefa {i+1} adicionada à pilha de backtrack para reexecução posterior")
                        
                        prev_task_name = tasks[i-1].get('text', tasks[i-1].get('image', f"Tarefa {i}"))
                        logger.info(f"✗ Tarefa {i+1}/{len(tasks)}: '{task_result.task_name}' falhou. "
                                  f"BACKTRACKING para tarefa {i}/{len(tasks)}: '{prev_task_name}'")
                        i -= 1  # Volta para tarefa anterior
                    else:
                        logger.info(f"✗ Tarefa {i+1}/{len(tasks)}: '{task_result.task_name}' falhou "
                                  f"após múltiplas tentativas de backtracking. Avançando.")
                        # Remove da pilha se estiver lá
                        if i in backtrack_stack:
                            backtrack_stack.remove(i)
                        i += 1
                else:
                    # Sem backtrack ou primeira tarefa
                    if backtrack:
                        logger.info(f"✗ Tarefa {i+1}/{len(tasks)}: '{task_result.task_name}' falhou "
                                  f"mas é a primeira tarefa. Avançando.")
                    else:
                        logger.info(f"✗ Tarefa {i+1}/{len(tasks)}: '{task_result.task_name}' falhou "
                                  f"e tem 'backtrack': False. Avançando.")
                    i += 1
        
        successful_tasks = sum(1 for r in results if r.success)
        logger.info(f"Execução concluída: {successful_tasks}/{len(results)} tarefas bem-sucedidas")
        
        return results
    
    def _execute_single_task(self, task: Dict[str, Any], task_index: int, total_tasks: int) -> TaskResult:
        """
        Executa uma única tarefa.
        
        Args:
            task (dict): Configuração da tarefa
            task_index (int): Índice da tarefa
            total_tasks (int): Total de tarefas
            
        Returns:
            TaskResult: Resultado da execução
        """
        self.current_task_index = task_index
        
        # Extrai informações da tarefa
        region = task.get('region')
        delay = task.get('delay', 0)
        early_confidence_threshold = task.get('early_confidence', 75.0)
        
        # Nome da tarefa para logs
        if task.get('type') == 'relative_image':
            anchor_name = os.path.basename(task.get('anchor_image', 'unknown'))
            target_name = os.path.basename(task.get('target_image', 'unknown'))
            task_name = f"Relative: {target_name} near {anchor_name}"
        else:
            task_name = task.get('text', task.get('image', f"Tarefa {task_index+1}"))
        
        logger.info(f"Iniciando tarefa {task_index+1}/{total_tasks}: {task_name}")
        
        location = None
        attempts = 0
        last_error = None
        
        # Tenta executar a tarefa com múltiplas tentativas
        while attempts < self.max_attempts and location is None:
            try:
                if 'text' in task:
                    # Verifica se tem parâmetros de wait
                    if task.get('wait_until_found') or task.get('wait_until_disappears'):
                        location = self._find_text_with_wait(task, attempts)
                    else:
                        location = self._find_text_location(task, attempts)
                elif 'image' in task:
                    # Verifica se tem parâmetros de wait
                    if task.get('wait_until_found') or task.get('wait_until_disappears'):
                        location = self._find_image_with_wait(task, attempts)
                    else:
                        location = self._find_image_location(task, attempts)
                elif task.get('type') == 'relative_image':
                    location = self._find_relative_image_location(task, attempts)
                elif task.get('type') == 'click':
                    location = self._find_coordinate_location(task, attempts)
                elif task.get('type') == 'type_text':
                    location = self._execute_type_text(task, attempts)
                elif task.get('type') == 'keyboard_command':
                    location = self._execute_keyboard_command(task, attempts)
                elif task.get('type') == 'extract_text':
                    location = self._execute_extract_text(task, attempts)
                else:
                    last_error = "Task sem chave 'text', 'image' ou tipo válido definido"
                    logger.warning(last_error)
                    break
                    
            except Exception as e:
                last_error = str(e)
                logger.error(f"Erro na tarefa {task_index+1}, tentativa {attempts+1}: {e}")
            
            # Se não encontrou, aguarda antes da próxima tentativa
            if not location:
                time.sleep(max(0.5, attempts * 0.5))
            
            attempts += 1
        
        # Cria resultado
        if location:
            result = TaskResult(task_index, True, task_name, location)
        else:
            result = TaskResult(task_index, False, task_name, error=last_error)
        
        result.attempts = attempts
        return result
    
    def _find_text_location(self, task: Dict[str, Any], attempt: int) -> Optional[Union[str, Tuple]]:
        """
        Encontra localização de texto usando OCR.
        
        Args:
            task (dict): Configuração da tarefa
            attempt (int): Número da tentativa atual
            
        Returns:
            tuple or str: Coordenadas da localização ou "skip"
        """
        target_text = task.get('text')
        filter_type = task.get('char_type', 'both').lower()
        region = task.get('region')
        early_confidence_threshold = task.get('early_confidence', 75.0)
        
        # Valida região
        if not region:
            raise TextNotFoundError("Nenhuma região definida para OCR")
        
        logger.debug(f"Buscando texto '{target_text}' na região {region} "
                   f"com filtro '{filter_type}' (tentativa {attempt+1} de {self.max_attempts})")
        
        # Captura screenshot da região
        region_img = self._capture_region(region)
        
        logger.info(f"Área capturada para OCR: {region[2]}x{region[3]} pixels")
        
        # Usa OCR engine para encontrar texto
        found_boxes, confidence_scores, early_match = self.ocr_engine.find_text(
            region_img, target_text, filter_type, early_confidence_threshold
        )
        
        if found_boxes:
            # Verifica se todas as confianças estão abaixo do limiar
            if all(score < early_confidence_threshold for score in confidence_scores):
                logger.info(f"Todas as confianças para '{target_text}' estão abaixo de "
                           f"{early_confidence_threshold}%. Presumindo que já foi clicado.")
                return "skip"
            
            # Seleciona melhor resultado
            if early_match:
                selected_box_relative = found_boxes[0]
                logger.info(f"Usando detecção antecipada com confiança: {confidence_scores[0]:.2f}%")
            elif task.get('best_confidence', True):
                best_index = confidence_scores.index(max(confidence_scores))
                selected_box_relative = found_boxes[best_index]
                logger.info(f"Selecionada detecção com maior confiança: {max(confidence_scores):.2f}%")
            else:
                # Comportamento legacy com occurrence
                occurrence = task.get('occurrence', 1)
                if len(found_boxes) >= occurrence:
                    selected_box_relative = found_boxes[occurrence - 1]
                else:
                    selected_box_relative = found_boxes[-1]
            
            # Converte coordenadas relativas para absolutas
            selected_box = (
                region[0] + selected_box_relative[0],
                region[1] + selected_box_relative[1],
                selected_box_relative[2],
                selected_box_relative[3]
            )
            
            logger.info(f"Texto '{target_text}' encontrado na posição {selected_box_relative} "
                       f"dentro da região {region}")
            return selected_box
        else:
            logger.warning(f"Texto '{target_text}' não encontrado na região {region}")
            return None
    
    def _find_image_location(self, task: Dict[str, Any], attempt: int) -> Optional[Tuple]:
        """
        Encontra localização de imagem.
        
        Args:
            task (dict): Configuração da tarefa
            attempt (int): Número da tentativa atual
            
        Returns:
            tuple: Coordenadas da localização ou None
        """
        image_path = task.get('image')
        confidence = task.get('confidence', self.default_confidence)
        region = task.get('region')
        specific = task.get('specific', True)
        
        if specific and region:
            logger.debug(f"Buscando {image_path} na região {region} "
                       f"com confiança {confidence} (tentativa {attempt+1} de {self.max_attempts})")
            location = self._locate_image_with_retry(image_path, region=region, confidence=confidence)
        else:
            logger.debug(f"Buscando {image_path} em toda a tela "
                       f"com confiança {confidence} (tentativa {attempt+1} de {self.max_attempts})")
            location = self._locate_image_with_retry(image_path, confidence=confidence)

        return location

    def _find_image_with_wait(self, task: Dict[str, Any], attempt: int) -> Optional[Tuple]:
        """
        Encontra imagem com parâmetros de espera inteligente.

        Args:
            task (dict): Configuração da tarefa
            attempt (int): Número da tentativa atual

        Returns:
            tuple: Coordenadas da localização ou None
        """
        wait_until_found = task.get('wait_until_found', False)
        wait_until_disappears = task.get('wait_until_disappears', False)
        wait_timeout = task.get('wait_timeout') or self.config.get('wait_timeout', 30)

        image_path = task.get('image')

        # Cria função de busca para o wait manager
        def search_image():
            return self._find_image_location(task, attempt)

        # ETAPA 1: Se wait_until_found=True, aguarda aparecer primeiro
        if wait_until_found:
            logger.info(f"Aguardando imagem '{image_path}' aparecer (timeout: {wait_timeout}s)")
            result = self.wait_manager.wait_until_found(
                search_image,
                timeout=wait_timeout,
                description=f"imagem '{image_path}'"
            )
            if not result:
                return None  # Timeout na espera para aparecer
        else:
            # Se não tem wait_until_found, busca normalmente
            result = search_image()
            if not result:
                return None  # Não encontrou a imagem

        # ETAPA 2: Se encontrou (ou já estava visível) e tem wait_until_disappears
        if wait_until_disappears:
            # Se é apenas find_image (sem clique), aguarda desaparecer imediatamente
            if task.get('type') != 'click_image' and not task.get('mouse_button'):
                logger.info(f"Aguardando imagem '{image_path}' desaparecer (timeout: {wait_timeout}s)")
                disappeared = self.wait_manager.wait_until_disappears(
                    search_image,
                    timeout=wait_timeout,
                    description=f"imagem '{image_path}'"
                )
                return result if disappeared else None
            else:
                # Para click_image, marca que deve aguardar desaparecer APÓS o clique
                task['_wait_after_click'] = True
                task['_wait_timeout'] = wait_timeout
                task['_image_path'] = image_path

        return result

    def _find_text_with_wait(self, task: Dict[str, Any], attempt: int) -> Optional[Union[str, Tuple]]:
        """
        Encontra texto com parâmetros de espera inteligente.

        Args:
            task (dict): Configuração da tarefa
            attempt (int): Número da tentativa atual

        Returns:
            tuple or str: Coordenadas da localização, "skip" ou None
        """
        wait_until_found = task.get('wait_until_found', False)
        wait_until_disappears = task.get('wait_until_disappears', False)
        wait_timeout = task.get('wait_timeout') or self.config.get('wait_timeout', 30)

        target_text = task.get('text')

        # Cria função de busca para o wait manager
        def search_text():
            return self._find_text_location(task, attempt)

        # ETAPA 1: Se wait_until_found=True, aguarda aparecer primeiro
        if wait_until_found:
            logger.info(f"Aguardando texto '{target_text}' aparecer (timeout: {wait_timeout}s)")
            result = self.wait_manager.wait_until_found(
                search_text,
                timeout=wait_timeout,
                description=f"texto '{target_text}'"
            )
            if not result:
                return None  # Timeout na espera para aparecer
        else:
            # Se não tem wait_until_found, busca normalmente
            result = search_text()
            if not result:
                return None  # Não encontrou o texto

        # ETAPA 2: Se encontrou (ou já estava visível) e tem wait_until_disappears,
        # guarda a posição para clicar e programa a espera para depois do clique
        if wait_until_disappears:
            # Marca que deve aguardar desaparecer APÓS o clique
            task['_wait_after_click'] = True
            task['_wait_timeout'] = wait_timeout
            task['_target_text'] = target_text

        return result
    
    def _capture_region(self, region: Tuple[int, int, int, int]) -> Image.Image:
        """
        Captura screenshot de uma região.
        
        Args:
            region (tuple): (x, y, width, height)
            
        Returns:
            PIL.Image: Imagem capturada
            
        Raises:
            TaskExecutionError: Se falhar na captura
        """
        try:
            import pyautogui
            region_img = pyautogui.screenshot(region=region)
            
            if not region_img or region_img.width <= 1 or region_img.height <= 1:
                raise TaskExecutionError(f"Falha ao capturar região {region}")
            
            return region_img
            
        except Exception as e:
            raise TaskExecutionError(f"Erro na captura de tela: {e}")
    
    def _locate_image_with_retry(self, image_path: str, region: Optional[Tuple] = None,
                                confidence: float = 0.9, max_attempts: int = 3,
                                scales: Optional[List[float]] = None) -> Optional[Tuple]:
        """
        Localiza imagem com múltiplas tentativas e escalas.
        
        Args:
            image_path (str): Caminho para imagem
            region (tuple, optional): Região onde buscar
            confidence (float): Nível de confiança
            max_attempts (int): Máximo de tentativas
            scales (list, optional): Escalas a testar
            
        Returns:
            tuple: Coordenadas da imagem ou None
        """
        if scales is None:
            scales = [1.0, 0.95, 1.05, 0.71, 1.41]  # Escala original, ±5%, e variações mais amplas
        
        try:
            import pyautogui

            for attempt in range(max_attempts):
                # Testa todas as escalas em paralelo
                location = self._parallel_scale_search(image_path, scales, region, confidence)
                if location:
                    return location

                # Se não encontrou, reduz confiança e tenta novamente com todas as escalas
                adjusted_confidence = max(0.7, confidence - 0.05 * (attempt + 1))
                logger.debug(f"Ajustando confiança para {adjusted_confidence} na tentativa {attempt+1}")

                location = self._parallel_scale_search(image_path, scales, region, adjusted_confidence)
                if location:
                    return location

                # Pequena pausa apenas entre tentativas principais (não entre escalas)
                if attempt < max_attempts - 1:
                    time.sleep(0.2)

            return None
            
        except Exception as e:
            logger.error(f"Erro na localização de imagem: {e}")
            return None

    def _parallel_scale_search(self, image_path: str, scales: List[float],
                              region: Optional[Tuple], confidence: float) -> Optional[Tuple]:
        """
        Testa todas as escalas simultaneamente usando threads paralelas.

        Args:
            image_path (str): Caminho da imagem
            scales (list): Lista de escalas para testar
            region (tuple, optional): Região de busca
            confidence (float): Confiança mínima

        Returns:
            tuple: Coordenadas da primeira imagem encontrada ou None
        """
        def search_single_scale(scale: float) -> Optional[Tuple]:
            """Busca imagem em uma escala específica."""
            try:
                if scale == 1.0:
                    # Usa imagem original
                    import pyautogui
                    if region:
                        return pyautogui.locateOnScreen(image_path, region=region, confidence=confidence)
                    else:
                        return pyautogui.locateOnScreen(image_path, confidence=confidence)
                else:
                    # Usa imagem redimensionada
                    return self._try_scaled_image(image_path, scale, region, confidence)
            except Exception as e:
                logger.debug(f"Erro ao buscar imagem com escala {scale}: {e}")
                return None

        # Executa busca em paralelo para todas as escalas
        with ThreadPoolExecutor(max_workers=len(scales)) as executor:
            # Submete todas as tarefas
            future_to_scale = {executor.submit(search_single_scale, scale): scale for scale in scales}

            # Processa resultados conforme completam
            for future in as_completed(future_to_scale):
                scale = future_to_scale[future]
                try:
                    result = future.result()
                    if result:
                        logger.debug(f"Imagem encontrada com escala {scale}: {result}")
                        return result
                except Exception as e:
                    logger.debug(f"Erro na thread da escala {scale}: {e}")
                    continue

        return None

    def _try_scaled_image(self, image_path: str, scale: float, region: Optional[Tuple],
                         confidence: float) -> Optional[Tuple]:
        """
        Tenta localizar imagem com escala específica.
        
        Args:
            image_path (str): Caminho da imagem
            scale (float): Escala a aplicar
            region (tuple, optional): Região de busca
            confidence (float): Confiança
            
        Returns:
            tuple: Localização ou None
        """
        try:
            import pyautogui
            from PIL import Image
            
            # Carrega e redimensiona imagem
            ref_img = Image.open(image_path)
            new_width = int(ref_img.width * scale)
            new_height = int(ref_img.height * scale)
            scaled_img = ref_img.resize((new_width, new_height))
            
            # Salva temporariamente
            temp_path = f"temp_scaled_{scale}_{os.getpid()}.png"
            scaled_img.save(temp_path)
            
            try:
                if region:
                    location = pyautogui.locateOnScreen(temp_path, region=region, confidence=confidence)
                else:
                    location = pyautogui.locateOnScreen(temp_path, confidence=confidence)
                
                return location
                
            finally:
                # Remove arquivo temporário
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    
        except Exception as e:
            logger.debug(f"Erro ao testar imagem escalada: {e}")
            return None
    
    def _perform_action(self, task: Dict[str, Any], location: Tuple) -> None:
        """
        Executa a ação (clique, digitação) na localização encontrada.
        
        Args:
            task (dict): Configuração da tarefa
            location (tuple): Coordenadas onde executar ação
        """
        delay = task.get('delay', 0)
        show_overlay_enabled = task.get('show_overlay')
        
        # Se não especificado na task, usa configuração global
        if show_overlay_enabled is None:
            show_overlay_enabled = self.config.get('show_overlay', True)
        
        # Mostra overlay visual apenas se habilitado
        if show_overlay_enabled:
            # Obter configurações de overlay da configuração
            overlay_duration = self.config.get('overlay_duration', 1000)
            overlay_color = self.config.get('overlay_color', 'red')
            overlay_width = self.config.get('overlay_width', 4)
            
            overlay_thread = threading.Thread(
                target=show_overlay, 
                args=(location,),
                kwargs={
                    'duration': overlay_duration,
                    'color': overlay_color,
                    'width': overlay_width
                }
            )
            overlay_thread.start()
            
            # Pequeno delay para exibir overlay
            time.sleep(0.2)
        else:
            overlay_thread = None
        
        # Executa clique
        self._perform_click(task, location)
        
        # Processa comandos de texto (apenas se não foi executado antes)
        if 'sendtext' in task and task['sendtext'] and not task.get('_sendtext_executed', False):
            self._process_sendtext(task['sendtext'])
            task['_sendtext_executed'] = True  # Marca como executado para evitar duplicação
        
        # Aguarda overlay finalizar se foi criado
        if overlay_thread:
            overlay_thread.join()

        # ETAPA 3: Se deve aguardar desaparecer APÓS o clique
        wait_until_disappears = task.get('wait_until_disappears', False)
        if wait_until_disappears or task.get('_wait_after_click', False):
            wait_timeout = task.get('wait_timeout') or task.get('_wait_timeout', 30)
            image_path = task.get('image') or task.get('_image_path')
            target_text = task.get('text') or task.get('_target_text')

            if image_path:
                logger.info(f"Iniciando verificação de desaparecimento da imagem '{image_path}' (timeout: {wait_timeout}s)")
                # Cria função de busca para verificar se desapareceu
                def search_image_after_click():
                    try:
                        # Usa uma cópia da task para evitar efeitos colaterais
                        search_task = task.copy()
                        # Remove parâmetros de wait para busca direta
                        search_task.pop('wait_until_found', None)
                        search_task.pop('wait_until_disappears', None)
                        search_task.pop('_wait_after_click', None)

                        # Debug: mostra parâmetros de busca
                        region_info = f"região {search_task.get('region')}" if search_task.get('region') else "tela inteira"
                        confidence = search_task.get('confidence', 0.9)
                        specific = search_task.get('specific', True)
                        logger.debug(f"Verificando desaparecimento: {region_info}, confiança={confidence}, specific={specific}")

                        result = self._find_image_location(search_task, 0)

                        # Debug: resultado da busca
                        if result:
                            logger.debug(f"Imagem ainda encontrada em: {result}")
                        else:
                            logger.debug(f"Imagem não encontrada (desapareceu)")

                        return result
                    except Exception as e:
                        logger.debug(f"Erro ao buscar imagem para verificar desaparecimento: {e}")
                        return None

                disappeared = self.wait_manager.wait_until_disappears(
                    search_image_after_click,
                    timeout=wait_timeout,
                    description=f"imagem '{image_path}'"
                )

                if disappeared:
                    logger.info(f"Imagem '{image_path}' desapareceu com sucesso - continuando RPA")
                else:
                    logger.warning(f"Imagem '{image_path}' ainda visível após timeout - continuando RPA mesmo assim")
            elif target_text:
                logger.info(f"Iniciando verificação de desaparecimento do texto '{target_text}' (timeout: {wait_timeout}s)")
                # Cria função de busca para verificar se desapareceu
                def search_text_after_click():
                    try:
                        # Usa uma cópia da task para evitar efeitos colaterais
                        search_task = task.copy()
                        # Remove parâmetros de wait para busca direta
                        search_task.pop('wait_until_found', None)
                        search_task.pop('wait_until_disappears', None)
                        search_task.pop('_wait_after_click', None)
                        result = self._find_text_location(search_task, 0)
                        return result
                    except Exception as e:
                        logger.debug(f"Erro ao buscar texto para verificar desaparecimento: {e}")
                        return None

                disappeared = self.wait_manager.wait_until_disappears(
                    search_text_after_click,
                    timeout=wait_timeout,
                    description=f"texto '{target_text}'"
                )

                if disappeared:
                    logger.info(f"Texto '{target_text}' desapareceu com sucesso - continuando RPA")
                else:
                    logger.warning(f"Texto '{target_text}' ainda visível após timeout - continuando RPA mesmo assim")

            # Remove flags temporários
            task.pop('_wait_after_click', None)
            task.pop('_wait_timeout', None)
            task.pop('_image_path', None)
            task.pop('_target_text', None)

        time.sleep(delay)
    
    def _perform_click(self, task: Dict[str, Any], location: Tuple) -> None:
        """
        Executa clique na localização ou apenas move o mouse.
        Suporta mouse virtual configurável.

        Args:
            task (dict): Configuração da tarefa
            location (tuple): Coordenadas do clique/movimento
        """
        try:
            import pyautogui

            # Calcula ponto central
            click_point = pyautogui.center(location)

            # Determina tipo de mouse button
            mouse_button = task.get('mouse_button', self.config.get('default_mouse_button', 'left')).lower()

            # Normaliza mouse_button para virtual mouse
            if mouse_button == 'double left':
                mouse_button = 'double'

            # Usa virtual mouse ou físico baseado na configuração
            # Para virtual mouse, passa a informação da localização para garantir centro exato
            success = self.virtual_mouse.click(
                x=click_point.x,
                y=click_point.y,
                button=mouse_button,
                location_info=location  # Passa informação completa da região encontrada
            )

            if success:
                if mouse_button == 'move_to':
                    logger.info(f"Mouse movido para a posição ({click_point.x}, {click_point.y}) (apenas movimento)")
                elif mouse_button == 'right':
                    logger.info(f"Clique direito realizado na posição ({click_point.x}, {click_point.y})")
                elif mouse_button in ['double', 'double left']:
                    logger.info(f"Clique duplo realizado na posição ({click_point.x}, {click_point.y})")
                else:
                    logger.info(f"Clique esquerdo realizado na posição ({click_point.x}, {click_point.y})")
            else:
                raise TaskExecutionError("Falha ao executar ação do mouse")

        except Exception as e:
            logger.error(f"Erro ao executar ação do mouse: {e}")
            raise TaskExecutionError(f"Falha na ação do mouse: {e}")
    
    def _process_sendtext(self, text_command: str) -> None:
        """
        Processa comandos de texto especiais e digita texto.
        
        Args:
            text_command (str): Comando de texto com possíveis comandos especiais
        """
        try:
            import pyautogui
            import pyperclip
            
            logger.info(f"Processando sendtext: '{text_command}'")
            
            text_to_write = text_command
            
            # Processa comandos especiais
            while True:
                original_text = text_to_write
                lower_text = text_to_write.lower()
                
                if lower_text.startswith('{ctrl}a'):
                    logger.info("Executando: CTRL+A")
                    pyautogui.hotkey('ctrl', 'a')
                    text_to_write = text_to_write[len('{ctrl}a'):]
                    time.sleep(0.1)
                elif lower_text.startswith('{del}'):
                    logger.info("Executando: DELETE")
                    pyautogui.press('delete')
                    text_to_write = text_to_write[len('{del}'):]
                    time.sleep(0.1)
                elif lower_text.startswith('{tab}'):
                    logger.info("Executando: TAB")
                    pyautogui.press('tab')
                    text_to_write = text_to_write[len('{tab}'):]
                    time.sleep(0.1)
                elif lower_text.startswith('{enter}'):
                    logger.info("Executando: ENTER")
                    pyautogui.press('enter')
                    text_to_write = text_to_write[len('{enter}'):]
                    time.sleep(0.1)
                else:
                    break  # Sem mais comandos especiais
                
                # Proteção contra loop infinito
                if text_to_write == original_text:
                    break
            
            # Digita texto restante usando clipboard para melhor compatibilidade
            if text_to_write:
                logger.info(f"Colando texto: '{text_to_write}'")
                pyperclip.copy(text_to_write)
                pyautogui.hotkey('ctrl', 'v')
                time.sleep(0.5)
                
        except Exception as e:
            logger.error(f"Erro ao processar sendtext: {e}")
            raise TaskExecutionError(f"Falha no sendtext: {e}")
    
    def _find_relative_image_location(self, task: Dict[str, Any], attempt: int) -> Optional[Tuple]:
        """
        Encontra localização de imagem relativa (âncora + target).
        
        Args:
            task (dict): Configuração da tarefa
            attempt (int): Número da tentativa atual
            
        Returns:
            tuple: Coordenadas da localização ou None
        """
        anchor_image = task.get('anchor_image')
        target_image = task.get('target_image')
        confidence = task.get('confidence', self.default_confidence)
        max_distance = task.get('max_distance', 200)
        target_region = task.get('target_region') if task.get('specific', False) else None
        
        if not anchor_image or not target_image:
            raise TaskExecutionError("Imagem relativa requer 'anchor_image' e 'target_image'")
        
        region_info = f", região_target={target_region}" if target_region else ", tela_inteira"
        logger.info(f"Buscando imagem relativa: âncora='{anchor_image}', target='{target_image}', "
                   f"confiança={confidence}, distância_max={max_distance}px{region_info} "
                   f"(tentativa {attempt+1} de {self.max_attempts})")
        
        try:
            location = self.relative_detector.locate_relative_image(
                anchor_image, target_image, confidence, max_distance, target_region
            )
            return location
        except Exception as e:
            logger.error(f"Erro na detecção de imagem relativa: {e}")
            return None
    
    def _find_coordinate_location(self, task: Dict[str, Any], attempt: int) -> Optional[Tuple]:
        """
        Encontra localização baseada em coordenadas específicas.
        
        Args:
            task (dict): Configuração da tarefa
            attempt (int): Número da tentativa atual
            
        Returns:
            tuple: Coordenadas da localização ou None
        """
        x = task.get('x')
        y = task.get('y')
        
        if x is None or y is None:
            raise TaskExecutionError("Clique direto requer coordenadas 'x' e 'y'")
        
        logger.info(f"Executando clique em coordenadas ({x}, {y}) "
                   f"(tentativa {attempt+1} de {self.max_attempts})")
        
        # Cria uma região pequena na posição especificada
        return (x, y, 1, 1)
    
    def _execute_type_text(self, task: Dict[str, Any], attempt: int) -> str:
        """
        Executa digitação de texto.
        
        Args:
            task (dict): Configuração da tarefa
            attempt (int): Número da tentativa atual
            
        Returns:
            str: "skip" para indicar que não precisa de clique
        """
        text = task.get('text', '')
        interval = task.get('interval', 0.05)
        
        logger.info(f"Digitando texto: '{text}' (tentativa {attempt+1} de {self.max_attempts})")
        
        try:
            self.keyboard_commander.type_text(text, interval)
            return "skip"  # Marca para pular o clique
        except Exception as e:
            logger.error(f"Erro ao digitar texto: {e}")
            return None
    
    def _execute_keyboard_command(self, task: Dict[str, Any], attempt: int) -> str:
        """
        Executa comando de teclado.
        
        Args:
            task (dict): Configuração da tarefa
            attempt (int): Número da tentativa atual
            
        Returns:
            str: "skip" para indicar que não precisa de clique
        """
        command = task.get('command', '')
        
        logger.info(f"Executando comando de teclado: '{command}' "
                   f"(tentativa {attempt+1} de {self.max_attempts})")
        
        try:
            success = self.keyboard_commander.execute_command(command)
            if success:
                return "skip"  # Marca para pular o clique
            else:
                return None
        except Exception as e:
            logger.error(f"Erro ao executar comando de teclado: {e}")
            return None

    def _execute_extract_text(self, task: Dict[str, Any], attempt: int) -> str:
        """
        Executa extração de texto de uma região específica.
        
        Args:
            task (dict): Configuração da tarefa com campos:
                - region (tuple, optional): Região para extrair texto
                - filter_type (str): Tipo de filtro ("numbers", "letters", "both")
                - confidence_threshold (float): Limiar de confiança mínimo
                - return_full_data (bool): Se deve retornar dados completos
                - backtrack (bool): Se deve tentar múltiplas vezes
            attempt (int): Número da tentativa atual
            
        Returns:
            str: "skip" para indicar que não precisa de clique
        """
        region = task.get('region')
        filter_type = task.get('filter_type', 'both')
        confidence_threshold = task.get('confidence_threshold', 50.0)
        return_full_data = task.get('return_full_data', False)
        backtrack = task.get('backtrack', False)
        
        logger.info(f"Extraindo texto da região {region} com filtro '{filter_type}' "
                   f"(tentativa {attempt+1} de {self.max_attempts})")
        
        try:
            if region is None:
                # Se não especificou região, captura tela inteira
                import pyautogui
                screen = pyautogui.screenshot()
                region = (0, 0, screen.width, screen.height)
                region_img = screen
            else:
                region_img = self._capture_region(region)
            
            # Usa o método extract_all_text do OCR engine
            ocr_results = self.ocr_engine.extract_all_text(region_img, filter_type)
            
            # Filtra por confiança - ajusta limiar baseado na tentativa
            adjusted_threshold = confidence_threshold - (attempt * 10.0)  # Reduz 10% a cada tentativa
            adjusted_threshold = max(30.0, adjusted_threshold)  # Mínimo de 30%
            
            filtered_results = [
                result for result in ocr_results 
                if result.confidence >= adjusted_threshold
            ]
            
            if return_full_data:
                # Prepara dados completos com coordenadas absolutas
                full_data = []
                for result in filtered_results:
                    absolute_box = (
                        region[0] + result.box[0],
                        region[1] + result.box[1],
                        result.box[2],
                        result.box[3]
                    ) if region != (0, 0, region_img.width, region_img.height) else result.box
                    
                    full_data.append({
                        'text': result.text,
                        'confidence': result.confidence,
                        'box': result.box,  # Coordenadas relativas à região
                        'absolute_box': absolute_box  # Coordenadas absolutas na tela
                    })
                
                # Armazena resultado para recuperação posterior
                self.last_extracted_text = full_data
                logger.info(f"Texto extraído com dados completos: {len(full_data)} elementos encontrados")
            else:
                # Extrai apenas os textos
                texts = [result.text for result in filtered_results]
                self.last_extracted_text = texts
                logger.info(f"Texto extraído: {len(texts)} elementos encontrados - {texts}")
            
            return "skip"  # Marca para pular o clique
            
        except Exception as e:
            logger.error(f"Erro ao extrair texto: {e}")
            return None


# Funções de conveniência
def execute_tasks(tasks, config: Optional[BotVisionConfig] = None) -> List[TaskResult]:
    """
    Função de conveniência para executar tarefas.
    Suporta tanto lista simples quanto lista de listas (múltiplos conjuntos de tarefas).
    
    Args:
        tasks: Lista de tarefas ou lista de listas de tarefas
        config (BotVisionConfig, optional): Configuração
        
    Returns:
        list: Lista de resultados (pode ser lista de listas se entrada for lista de listas)
    """
    # Verifica se é uma lista de listas (múltiplos conjuntos de tarefas)
    if isinstance(tasks, list) and tasks:
        if isinstance(tasks[0], list):
            logger.info(f"Detectados múltiplos conjuntos de tarefas ({len(tasks)} conjuntos). Executando sequencialmente.")
            all_results = []
            
            for i, task_list in enumerate(tasks):
                if isinstance(task_list, list):
                    logger.info(f"--- Iniciando conjunto de tarefas {i+1}/{len(tasks)} ({len(task_list)} tarefas) ---")
                    executor = TaskExecutor(config)
                    results = executor.execute_tasks(task_list)
                    all_results.append(results)
                    logger.info(f"--- Finalizado conjunto de tarefas {i+1}/{len(tasks)} ---")
                else:
                    logger.warning(f"Item {i} na lista principal não é uma lista de tarefas. Pulando.")
                    all_results.append([])
            
            return all_results
        else:
            # Lista simples de tarefas
            logger.info("Detectada lista simples de tarefas. Executando.")
            executor = TaskExecutor(config)
            return executor.execute_tasks(tasks)
    elif isinstance(tasks, list) and not tasks:
        logger.info("A lista de tarefas está vazia. Nada para executar.")
        return []
    else:
        logger.error(f"As tarefas importadas não são uma lista. Tipo: {type(tasks)}. Não é possível executar.")
        return []


def click_images(tasks, default_confidence: float = 0.9, 
                default_margin: int = 50):
    """
    Função para compatibilidade total com código legado.
    Suporta tanto lista simples quanto lista de listas (múltiplos conjuntos de tarefas).
    
    Args:
        tasks: Lista de tarefas ou lista de listas de tarefas
        default_confidence (float): Confiança padrão
        default_margin (int): Margem padrão
        
    Returns:
        list: Lista de resultados (pode ser lista de listas se entrada for lista de listas)
    """
    config = BotVisionConfig()
    config.set('default_confidence', default_confidence)
    config.set('default_margin', default_margin)
    
    return execute_tasks(tasks, config)
