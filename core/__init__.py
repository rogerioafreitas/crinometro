"""
Pacote Core do Crinômetro (DSP, Aprendizado Ativo e Motores de Renderização).
"""
from core.analyzer import CricketAnalyzer
from core.learner import PulseLearner
from core.engines import HighPerfLineEngine, HighPerfSpectrogramEngine
from core.worker import GenericWorker
