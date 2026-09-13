"""
Crinômetro - Módulo de Machine Learning e Active Learning (PulseLearner).
"""
import os
import sys
import json
import time
import pickle
import base64
import warnings
import random
import re
import copy
import numpy as np
import scipy.integrate
from scipy.signal import hilbert, peak_widths, find_peaks

try:
    from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
    from sklearn.mixture import GaussianMixture
except Exception:
    HistGradientBoostingClassifier = None
    RandomForestClassifier = None
    GaussianMixture = None

from utils.constants import APP_VERSION, CONFIG_FILE, DEFAULT_ALGO_PARAMS
from utils.helpers import parse_version_tuple, is_version_newer

class PulseLearner:
    """Faz a ponte entre a correção manual do usuário e a classificação de pulsos.

    A ideia é simples: a interface produz um conjunto de amostras positivas e negativas,
    e o classificador aprende a separar batimentos válidos de ruído. O estado treinado é
    serializado em base64 dentro do arquivo de configuração JSON já existente e em arquivo .pkl.
    """

    def __init__(self, config_path=CONFIG_FILE):
        self.config_path = config_path
        config_dir = os.path.dirname(os.path.abspath(config_path))
        self.persistence_path = os.path.join(config_dir, "modelo_treinado.pkl")
        self.model = None
        self.feature_names = [
            "peak_amp_rel",           # 1. Amplitude do pico relativa à mediana local
            "peak_width_s",           # 2. Largura temporal a 50% (FWHM)
            "peak_width_75_s",        # 3. Largura temporal a 75%
            "local_snr_db",           # 4. SNR local em dB
            "energy_rel",             # 5. Energia local normalizada por pico²
            "std_amp_rel",            # 6. Desvio padrão local relativo
            "prominence_ratio",       # 7. Razão de proeminência sobre vales circundantes
            "peak_sharpness_rel",     # 8. Curvatura no ápice normalizada
            "crest_factor",           # 9. Fator de crista (Peak / RMS local)
            "skewness_local",         # 10. Assimetria do flanco de subida vs decaimento
            "local_density_rel",      # 11. Densidade de energia em 10 ms
            "autocorr_1ms",           # 12. Autocorrelação do envelope em lag de ~1 ms
            "band_energy_ratio",      # 13. Proporção de energia na janela curta vs longa
            "rise_slope_rel",         # 14. Inclinação de subida normalizada
            "spectral_centroid",      # 15. Centroide espectral em Hz (atenuação atmosférica)
            "spectral_rolloff_85",    # 16. Spectral roll-off 85% em Hz
            "attack_time_10_90_ms",   # 17. Tempo de subida 10%-90% do envelope (ms)
            "local_hnr_db",           # 18. Harmonic-to-Noise Ratio local em dB
            "multiscale_energy_ratio",# 19. Razão de energia multi-escala (15 ms / 80 ms)
            "prior_p_focal",          # 20. Prior físico de focalidade via GMM bimodal
        ]
        self.training_features = np.empty((0, len(self.feature_names)), dtype=float)
        self.training_labels = np.empty((0,), dtype=int)
        self.pruning_rules = []
        self.load_from_config()
        self.load_persisted_training()

    def is_trained(self):
        return self.model is not None

    def _build_model(self, n_samples=None):
        if n_samples is None:
            n_samples = len(self.training_labels) if hasattr(self, "training_labels") else 0
        if HistGradientBoostingClassifier is not None:
            if n_samples > 0 and n_samples < 30:
                # Regularização robusta para poucas amostras de correção ativa
                return HistGradientBoostingClassifier(
                    max_iter=50,
                    max_depth=3,
                    min_samples_leaf=2,
                    learning_rate=0.08,
                    l2_regularization=2.0,
                    random_state=42,
                    class_weight="balanced",
                )
            return HistGradientBoostingClassifier(
                max_iter=80,
                max_depth=4,
                min_samples_leaf=5,
                learning_rate=0.08,
                l2_regularization=1.0,
                random_state=42,
                class_weight="balanced",
            )
        elif RandomForestClassifier is not None:
            return RandomForestClassifier(
                n_estimators=80,
                max_depth=5,
                min_samples_split=6,
                min_samples_leaf=3,
                max_features="sqrt",
                class_weight="balanced",
                random_state=42,
                n_jobs=-1,
            )
        else:
            raise RuntimeError("scikit-learn não está instalado; use pip install scikit-learn para habilitar o aprendizado ativo.")

    @staticmethod
    def extract_features_for_peak(peak_idx, rate, env_signal, raw_signal=None, prior_p_focal=1.0):
        peak_idx = int(np.asarray(peak_idx).item())
        n_features = 20
        if peak_idx < 0 or peak_idx >= len(env_signal):
            return np.zeros(n_features, dtype=float)

        rate = float(rate)
        half_window = max(4, int(rate * 0.030))  # Janela local de 30 ms
        start = max(0, peak_idx - half_window)
        end = min(len(env_signal), peak_idx + half_window + 1)
        segment = env_signal[start:end]

        if segment.size == 0:
            return np.zeros(n_features, dtype=float)

        peak_amp = max(1e-9, float(env_signal[peak_idx]))
        median_amp = float(np.median(segment))
        std_amp = float(np.std(segment))
        local_rms = float(np.sqrt(np.mean(segment ** 2))) if segment.size else 1e-6

        # 1. Amplitude relativa à mediana local
        peak_amp_rel = float(peak_amp / (median_amp + 1e-6))

        # 2 & 3. Largura temporal a 50% e 75%
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            w50, _, _, _ = peak_widths(env_signal, [peak_idx], rel_height=0.5)
            w75, _, _, _ = peak_widths(env_signal, [peak_idx], rel_height=0.75)
        peak_width_s = float(w50[0] / rate) if w50.size else 0.0
        peak_width_75_s = float(w75[0] / rate) if w75.size else 0.0

        # 4. SNR local em dB
        local_noise = max(std_amp, 1e-6)
        local_snr_db = float(20.0 * np.log10((peak_amp + 1e-6) / (local_noise + 1e-6)))

        # 5. Energia local normalizada (independente de ganho global)
        energy_rel = float(np.sum(segment ** 2) / (segment.size * (peak_amp ** 2) + 1e-9))

        # 6. Desvio padrão relativo
        std_amp_rel = float(std_amp / (peak_amp + 1e-6))

        # 7. Razão de proeminência sobre vales circundantes
        left_valley = float(np.min(env_signal[start:peak_idx])) if peak_idx > start else peak_amp
        right_valley = float(np.min(env_signal[peak_idx + 1:end])) if end > peak_idx + 1 else peak_amp
        base_valley = max(left_valley, right_valley)
        prominence_ratio = float((peak_amp - base_valley) / (peak_amp + 1e-6))

        # 8. Curvatura no ápice normalizada (2ª derivada)
        left_val = float(env_signal[peak_idx - 1]) if peak_idx > 0 else peak_amp
        right_val = float(env_signal[peak_idx + 1]) if peak_idx < len(env_signal) - 1 else peak_amp
        peak_sharpness_rel = float((2.0 * peak_amp - left_val - right_val) / (peak_amp + 1e-6))

        # 9. Fator de crista
        crest_factor = float(peak_amp / (local_rms + 1e-6))

        # 10. Assimetria local
        left_subseg = env_signal[start:peak_idx]
        right_subseg = env_signal[peak_idx + 1:end]
        mean_left = float(np.mean(left_subseg)) if left_subseg.size else peak_amp
        mean_right = float(np.mean(right_subseg)) if right_subseg.size else peak_amp
        skewness_local = float((mean_left - mean_right) / (peak_amp + 1e-6))

        # 11. Densidade de energia na vizinhança curta (10 ms)
        short_half = max(2, int(rate * 0.010))
        short_start = max(0, peak_idx - short_half)
        short_end = min(len(env_signal), peak_idx + short_half + 1)
        short_seg = env_signal[short_start:short_end]
        local_density_rel = float(np.mean(short_seg) / (peak_amp + 1e-6))

        # 12. Autocorrelação do envelope em lag de ~1 ms
        lag_1ms = max(1, int(rate * 0.001))
        if len(segment) > lag_1ms + 2:
            seg_norm = segment - np.mean(segment)
            denom = np.sum(seg_norm ** 2)
            autocorr_1ms = float(np.sum(seg_norm[:-lag_1ms] * seg_norm[lag_1ms:]) / denom) if denom > 1e-9 else 0.0
        else:
            autocorr_1ms = 0.0

        # 13. Razão de energia na janela curta vs janela longa
        band_energy_ratio = float((np.sum(short_seg ** 2) + 1e-9) / (np.sum(segment ** 2) + 1e-9))

        # 14. Inclinação de subida normalizada
        dt_rise = max(1, peak_idx - start)
        rise_slope_rel = float((peak_amp - left_valley) / (dt_rise / rate * peak_amp + 1e-6))

        # --- NOVOS DESCRITORES FÍSICOS DE ATENUAÇÃO E DISTÂNCIA (15 a 20) ---
        spectral_centroid = 4500.0
        spectral_rolloff_85 = 5500.0
        local_hnr_db = 15.0

        if raw_signal is not None and len(raw_signal) > 0:
            w_spec = max(8, int(rate * 0.035))  # Janela Hann de 35 ms
            s_spec = max(0, peak_idx - w_spec)
            e_spec = min(len(raw_signal), peak_idx + w_spec + 1)
            raw_seg = raw_signal[s_spec:e_spec]
            if len(raw_seg) >= 8:
                h_win = np.hanning(len(raw_seg))
                fft_mag = np.abs(np.fft.rfft(raw_seg * h_win))
                freqs = np.fft.rfftfreq(len(raw_seg), 1.0 / rate)
                sum_mag = np.sum(fft_mag)
                if sum_mag > 1e-9:
                    # 15. Centroide espectral
                    spectral_centroid = float(np.sum(freqs * fft_mag) / sum_mag)
                    # 16. Spectral Roll-off 85%
                    cum_energy = np.cumsum(fft_mag ** 2)
                    thresh_85 = 0.85 * cum_energy[-1]
                    idx_85 = np.searchsorted(cum_energy, thresh_85)
                    idx_85 = min(idx_85, len(freqs) - 1)
                    spectral_rolloff_85 = float(freqs[idx_85])
                    # 18. Local HNR em dB (portadora +-150 Hz vs ruído fora)
                    peak_freq = freqs[np.argmax(fft_mag)]
                    carrier_mask = (freqs >= peak_freq - 150.0) & (freqs <= peak_freq + 150.0)
                    e_carrier = np.sum(fft_mag[carrier_mask] ** 2)
                    e_noise = np.sum(fft_mag[~carrier_mask] ** 2)
                    local_hnr_db = float(10.0 * np.log10((e_carrier + 1e-9) / (e_noise + 1e-9)))

        # 17. Attack Time 10% a 90% (tempo de subida em ms com interpolação linear contínua)
        amp_10 = 0.10 * peak_amp
        amp_90 = 0.90 * peak_amp
        attack_time_10_90_ms = 2.0
        if peak_idx > start:
            rise_seg = env_signal[start:peak_idx + 1]
            idx_10 = np.where(rise_seg <= amp_10)[0]
            idx_90 = np.where(rise_seg >= amp_90)[0]
            i10 = idx_10[-1] if len(idx_10) > 0 else 0
            i90 = idx_90[0] if len(idx_90) > 0 else len(rise_seg) - 1
            # Interpolação linear precisa sub-amostra
            t10 = float(i10)
            if i10 < len(rise_seg) - 1:
                dy10 = float(rise_seg[i10 + 1] - rise_seg[i10])
                if abs(dy10) > 1e-9:
                    t10 += float(np.clip((amp_10 - rise_seg[i10]) / dy10, 0.0, 1.0))
            t90 = float(i90)
            if i90 > 0:
                dy90 = float(rise_seg[i90] - rise_seg[i90 - 1])
                if abs(dy90) > 1e-9:
                    t90 = float(i90 - 1) + float(np.clip((amp_90 - rise_seg[i90 - 1]) / dy90, 0.0, 1.0))
            if t90 > t10:
                attack_time_10_90_ms = float((t90 - t10) / rate * 1000.0)
            else:
                attack_time_10_90_ms = 0.5

        # 19. Multi-scale energy ratio (15 ms focal vs 80 ms contextual)
        w_ctx = max(8, int(rate * 0.040))
        s_ctx = max(0, peak_idx - w_ctx)
        e_ctx = min(len(env_signal), peak_idx + w_ctx + 1)
        e_short = np.sum(env_signal[short_start:short_end] ** 2) + 1e-9
        e_long = np.sum(env_signal[s_ctx:e_ctx] ** 2) + 1e-9
        multiscale_energy_ratio = float(e_short / e_long)

        # 20. Prior P(focal)
        prior_p_focal_val = float(np.clip(prior_p_focal, 0.0, 1.0))

        feat = np.asarray([
            peak_amp_rel,
            peak_width_s,
            peak_width_75_s,
            local_snr_db,
            energy_rel,
            std_amp_rel,
            prominence_ratio,
            peak_sharpness_rel,
            crest_factor,
            skewness_local,
            local_density_rel,
            autocorr_1ms,
            band_energy_ratio,
            rise_slope_rel,
            spectral_centroid,
            spectral_rolloff_85,
            attack_time_10_90_ms,
            local_hnr_db,
            multiscale_energy_ratio,
            prior_p_focal_val,
        ], dtype=float)
        return np.nan_to_num(feat, nan=0.0, posinf=10000.0, neginf=-10000.0)

    @staticmethod
    def compute_unsupervised_focal_priors(peaks, rate, env_signal, raw_signal=None):
        """Etapa 2: Estima o prior contínuo P(focal) através de clusterização bimodal GMM.

        Incorpora a salvaguarda para amostras escassas: se N < 10, retorna P(focal) = 1.0.
        """
        peaks = np.asarray(peaks, dtype=int)
        n = len(peaks)
        if n == 0:
            return np.empty((0,), dtype=float)
        # Salvaguarda 1: N < 10 amostras
        if n < 10 or GaussianMixture is None:
            return np.ones(n, dtype=float)

        rate = float(rate)
        F_rows = []
        w_spec = max(8, int(rate * 0.035))

        for p in peaks:
            p_int = int(p)
            amp = float(env_signal[p_int]) if 0 <= p_int < len(env_signal) else 1e-6
            log_amp = float(np.log(max(1e-6, amp)))

            centroid = 4500.0
            if raw_signal is not None and len(raw_signal) > 0:
                s = max(0, p_int - w_spec)
                e = min(len(raw_signal), p_int + w_spec + 1)
                seg = raw_signal[s:e]
                if len(seg) >= 8:
                    fft_mag = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
                    freqs = np.fft.rfftfreq(len(seg), 1.0 / rate)
                    s_mag = np.sum(fft_mag)
                    if s_mag > 1e-9:
                        centroid = float(np.sum(freqs * fft_mag) / s_mag)

            F_rows.append([log_amp, centroid])

        F = np.asarray(F_rows, dtype=float)
        means = np.mean(F, axis=0)
        stds = np.std(F, axis=0)
        stds[stds < 1e-6] = 1.0
        F_norm = (F - means) / stds

        try:
            gmm = GaussianMixture(n_components=2, covariance_type='diag', random_state=42, max_iter=100)
            gmm.fit(F_norm)
            # Componente focal tem maior amplitude e maior centroide espectral
            c_focal = int(np.argmax(gmm.means_[:, 0] + 0.5 * gmm.means_[:, 1]))
            probs = gmm.predict_proba(F_norm)[:, c_focal]
            return np.clip(probs, 0.0, 1.0)
        except Exception:
            return np.ones(n, dtype=float)

    @staticmethod
    def build_training_matrix(peaks_detected, peaks_user_verified, rate, env_signal,
                              raw_signal=None, require_both_classes=True):
        detected = {int(p) for p in np.asarray(peaks_detected, dtype=int)}
        verified = {int(p) for p in np.asarray(peaks_user_verified, dtype=int)}

        if not detected and not verified:
            raise ValueError("Não há picos suficientes para treinar o modelo.")

        all_peaks = sorted(detected | verified)
        priors_map = {}
        if all_peaks:
            priors = PulseLearner.compute_unsupervised_focal_priors(all_peaks, rate, env_signal, raw_signal)
            priors_map = dict(zip(all_peaks, priors))

        X_rows = []
        y_rows = []

        # 1. Picos verificados (Positivos - estridulações reais)
        for peak_idx in sorted(verified):
            if 0 <= peak_idx < len(env_signal):
                p_prior = priors_map.get(peak_idx, 1.0)
                X_rows.append(PulseLearner.extract_features_for_peak(
                    peak_idx, rate, env_signal, raw_signal=raw_signal, prior_p_focal=p_prior
                ))
                y_rows.append(1)

        # 2. Falsos positivos / grilos distantes removidos pelo usuário (Negativos explícitos)
        explicit_negatives = detected - verified
        for peak_idx in sorted(explicit_negatives):
            if 0 <= peak_idx < len(env_signal):
                p_prior = priors_map.get(peak_idx, 0.0)
                X_rows.append(PulseLearner.extract_features_for_peak(
                    peak_idx, rate, env_signal, raw_signal=raw_signal, prior_p_focal=p_prior
                ))
                y_rows.append(0)

        # 3. Mineração Automática de Negativos (Negative Mining de Grilos Distantes e Ruído)
        num_pos = len([y for y in y_rows if y == 1])
        num_neg = len([y for y in y_rows if y == 0])
        target_min_neg = max(15, int(num_pos * 0.40))

        if num_neg < target_min_neg and len(env_signal) > 1000:
            sorted_v = sorted(verified)
            v_array = np.asarray(sorted_v) if sorted_v else np.empty(0, dtype=int)
            exclusion_samples = int(rate * 0.040)  # 40 ms de distância de pulsos validados

            # A) Hard Negatives: outros picos detectados no envelope que não pertencem ao grilo focal
            raw_ambient_pks, _ = find_peaks(env_signal, height=0.03, distance=int(rate * 0.020))
            hard_negatives = []
            for hpk in raw_ambient_pks:
                if v_array.size == 0 or np.min(np.abs(v_array - hpk)) > exclusion_samples:
                    hard_negatives.append(hpk)

            # B) Amostras de ruído nas pausas inter-chilreios
            candidate_silence = []
            for i in range(len(sorted_v) - 1):
                p_cur = sorted_v[i]
                p_next = sorted_v[i + 1]
                if (p_next - p_cur) > 2 * exclusion_samples:
                    mid_s = p_cur + exclusion_samples
                    mid_e = p_next - exclusion_samples
                    chunk = env_signal[mid_s:mid_e]
                    if chunk.size > 0:
                        candidate_silence.append(mid_s + int(np.argmax(chunk)))

            if sorted_v and sorted_v[0] > 2 * exclusion_samples:
                lead_chunk = env_signal[exclusion_samples : sorted_v[0] - exclusion_samples]
                if lead_chunk.size > 0:
                    candidate_silence.append(exclusion_samples + int(np.argmax(lead_chunk)))

            if sorted_v and (len(env_signal) - sorted_v[-1]) > 2 * exclusion_samples:
                trail_chunk = env_signal[sorted_v[-1] + exclusion_samples : len(env_signal) - exclusion_samples]
                if trail_chunk.size > 0:
                    candidate_silence.append(sorted_v[-1] + exclusion_samples + int(np.argmax(trail_chunk)))

            all_mined_negatives = list(set(hard_negatives + candidate_silence))
            needed_neg = target_min_neg - num_neg
            if len(all_mined_negatives) > needed_neg:
                rng = np.random.RandomState(42)
                selected_negatives = rng.choice(all_mined_negatives, size=needed_neg, replace=False)
            else:
                selected_negatives = all_mined_negatives

            for neg_idx in selected_negatives:
                if 0 <= neg_idx < len(env_signal):
                    X_rows.append(PulseLearner.extract_features_for_peak(
                        neg_idx, rate, env_signal, raw_signal=raw_signal, prior_p_focal=0.0
                    ))
                    y_rows.append(0)

        X = np.asarray(X_rows, dtype=float)
        y = np.asarray(y_rows, dtype=int)
        if X.shape[0] == 0:
            raise ValueError("Não há amostras de treinamento.")
        if require_both_classes and np.unique(y).size < 2:
            raise ValueError("O conjunto de correções precisa incluir pelo menos uma classe positiva e uma negativa para treinar.")
        return X, y

    def fit(self, X, y):
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=int)
        if X.size == 0 or y.size == 0:
            raise ValueError("Sem dados de treinamento disponíveis.")
        self.model = self._build_model(n_samples=len(y))
        self.model.fit(X, y)
        self.training_features = X.copy()
        self.training_labels = y.copy()
        self.save_persisted_training()
        return self.model

    def update_from_corrections(self, peaks_detected, peaks_user_verified, rate, env_signal, raw_signal=None):
        X_new, y_new = self.build_training_matrix(
            peaks_detected, peaks_user_verified, rate, env_signal,
            raw_signal=raw_signal, require_both_classes=False,
        )
        if self.training_features.size:
            if self.training_features.shape[1] != X_new.shape[1]:
                # Salvaguarda 3: alinhamento dinâmico de dimensões
                if self.training_features.shape[1] < X_new.shape[1]:
                    pad = np.zeros((len(self.training_features), X_new.shape[1] - self.training_features.shape[1]), dtype=float)
                    self.training_features = np.hstack((self.training_features, pad))
                else:
                    self.training_features = self.training_features[:, :X_new.shape[1]]
            X = np.vstack((self.training_features, X_new))
            y = np.concatenate((self.training_labels, y_new))
        else:
            X, y = X_new, y_new
        samples = np.unique(np.column_stack((X, y)), axis=0)
        self.training_features = samples[:, :-1]
        self.training_labels = samples[:, -1].astype(int)

        _MAX_SAMPLES = 5000
        if len(self.training_features) > _MAX_SAMPLES:
            self.training_features = self.training_features[-_MAX_SAMPLES:]
            self.training_labels = self.training_labels[-_MAX_SAMPLES:]

        if np.unique(self.training_labels).size < 2:
            self.save_persisted_training()
            return False

        # Indução de regras de poda contrastivas (Hard Negative Rule Induction)
        explicit_negatives = sorted(set(peaks_detected) - set(peaks_user_verified))
        valid_pulses = sorted(set(peaks_user_verified))
        if explicit_negatives and valid_pulses:
            induced = self.induce_pruning_rules(
                valid_pulses, explicit_negatives, rate, env_signal, raw_signal=raw_signal
            )
            if induced:
                print(f"[Active Learning] {len(induced)} regra(s) rígida(s) de poda induzida(s):")
                for r in induced:
                    print(f"  • {r['label']} {r['op']} {r['threshold']:.2f}")

        self.model = self._build_model(n_samples=len(self.training_labels))
        self.model.fit(self.training_features, self.training_labels)
        self.save_persisted_training()
        return True

    def induce_pruning_rules(self, valid_peaks, false_positive_peaks, rate, env_signal, raw_signal=None):
        """Induz regras rígidas de poda contrastiva (Hard Negative Rule Induction).
        
        Identifica candidatos removidos pelo pesquisador como falsos positivos (N_falso)
        e compara com a vizinhança de pulsos confirmados (P_valido) no mesmo áudio.
        Se uma métrica morfológica ou espectral isolar perfeitamente os falsos positivos,
        induz e armazena uma regra de poda com margem de segurança de 30% do gap.
        """
        valid_peaks = [int(p) for p in valid_peaks if 0 <= int(p) < len(env_signal)]
        fp_peaks = [int(p) for p in false_positive_peaks if 0 <= int(p) < len(env_signal)]
        if not valid_peaks or not fp_peaks:
            return []

        # Extrai os descritores dos dois conjuntos
        X_val = [self.extract_features_for_peak(p, rate, env_signal, raw_signal) for p in valid_peaks]
        X_fp = [self.extract_features_for_peak(p, rate, env_signal, raw_signal) for p in fp_peaks]
        X_val = np.asarray(X_val, dtype=float)
        X_fp = np.asarray(X_fp, dtype=float)

        target_metrics = [
            ("spectral_centroid", "Centroide Espectral (Hz)"),
            ("crest_factor", "Fator de Crista"),
            ("peak_width_s", "Duração FWHM (s)"),
            ("attack_time_10_90_ms", "Tempo de Ataque 10-90% (ms)"),
            ("spectral_rolloff_85", "Roll-off 85% (Hz)"),
            ("local_hnr_db", "HNR Local (dB)"),
        ]

        new_rules = []
        for feat_name, feat_label in target_metrics:
            if feat_name not in self.feature_names:
                continue
            idx = self.feature_names.index(feat_name)
            v_val = X_val[:, idx]
            v_fp = X_fp[:, idx]

            min_val, max_val = float(np.min(v_val)), float(np.max(v_val))
            min_fp, max_fp = float(np.min(v_fp)), float(np.max(v_fp))

            # Caso 1: Todos os válidos têm valor estritamente SUPERIOR aos falsos positivos
            if min_val > max_fp:
                gap = min_val - max_fp
                if gap > 0:
                    # Margem de segurança de 30% acima do maior falso positivo
                    threshold = max_fp + 0.30 * gap
                    rule = {
                        "feature": feat_name,
                        "label": feat_label,
                        "op": "<",
                        "threshold": float(threshold),
                        "safe_margin": float(0.30 * gap),
                        "gap": float(gap),
                        "min_valid": min_val,
                        "max_fp": max_fp,
                    }
                    new_rules.append(rule)

            # Caso 2: Todos os válidos têm valor estritamente INFERIOR aos falsos positivos
            elif max_val < min_fp:
                gap = min_fp - max_val
                if gap > 0:
                    # Margem de segurança de 30% abaixo do menor falso positivo
                    threshold = min_fp - 0.30 * gap
                    rule = {
                        "feature": feat_name,
                        "label": feat_label,
                        "op": ">",
                        "threshold": float(threshold),
                        "safe_margin": float(0.30 * gap),
                        "gap": float(gap),
                        "max_valid": max_val,
                        "min_fp": min_fp,
                    }
                    new_rules.append(rule)

        # Atualiza o repositório de regras de poda
        for nr in new_rules:
            self.pruning_rules = [
                r for r in self.pruning_rules
                if not (r["feature"] == nr["feature"] and r["op"] == nr["op"])
            ]
            self.pruning_rules.append(nr)

        if new_rules:
            self.save_to_config()
            self.save_persisted_training()
        return new_rules

    def check_pruning_rules(self, feat_vector):
        """Verifica se um vetor de características viola alguma regra de poda induzida."""
        if not getattr(self, "pruning_rules", None):
            return False, None
        for rule in self.pruning_rules:
            fname = rule.get("feature")
            if fname not in self.feature_names:
                continue
            fidx = self.feature_names.index(fname)
            val = float(feat_vector[fidx])
            op = rule.get("op")
            thresh = float(rule.get("threshold", 0.0))
            if op == "<" and val < thresh:
                return True, rule
            elif op == ">" and val > thresh:
                return True, rule
        return False, None

    def predict(self, X):
        if self.model is None:
            return np.asarray([], dtype=int)
        X = np.asarray(X, dtype=float)
        if X.size == 0:
            return np.asarray([], dtype=int)
        if X.ndim == 1:
            X = X.reshape(1, -1)

        n_expected = getattr(self.model, "n_features_in_", None)
        if n_expected is not None and n_expected > 0:
            if X.shape[1] > n_expected:
                X_used = X[:, :n_expected]
            elif X.shape[1] < n_expected:
                pad = np.zeros((X.shape[0], n_expected - X.shape[1]), dtype=float)
                X_used = np.hstack((X, pad))
            else:
                X_used = X
        else:
            X_used = X

        try:
            return self.model.predict(X_used).astype(int)
        except Exception as exc:
            print(f"Aviso na classificação com modelo treinado ({exc}); aceitando todos os picos como válidos.")
            return np.ones(X.shape[0], dtype=int)

    def filter_peaks(self, peaks, rate, env_signal, raw_signal=None,
                     gap_min_s=0.020, gap_max_s=0.040, focal_sensitivity=0.60):
        """Filtro bioacústico de segregação de grilos focais vs distantes e ruído.

        Retorna (kept_peaks, distant_peaks).
        """
        peaks = np.asarray(sorted(peaks), dtype=int)
        if peaks.size == 0:
            return peaks, np.asarray([], dtype=int)

        amps = env_signal[peaks]
        # Piso de amplitude focal: evita que grilos de fundo (< -10 dB do grilo focal) entrem
        a_focal = float(np.percentile(amps, 85)) if len(amps) >= 5 else float(np.max(amps))
        focal_floor = max(0.06, a_focal * (0.22 + 0.10 * focal_sensitivity))

        # Etapa 2: Priors não-supervisionados de focalidade (GMM Bimodal)
        priors = PulseLearner.compute_unsupervised_focal_priors(peaks, rate, env_signal, raw_signal)

        # Etapa 2.1: Filtro Rápido Pré-Inferência via Regras Rígidas de Poda (Hard Negative Gate)
        pruned_indices = set()
        if getattr(self, "pruning_rules", None):
            for i, p in enumerate(peaks):
                f_vec = PulseLearner.extract_features_for_peak(
                    int(p), rate, env_signal, raw_signal=raw_signal, prior_p_focal=priors[i]
                )
                violated, rule = self.check_pruning_rules(f_vec)
                if violated:
                    pruned_indices.add(i)

        # Se não há modelo supervisionado treinado, o GMM atua como classificador bimodal calibrado
        if self.model is None:
            gmm_thresh = 0.50 + 0.30 * focal_sensitivity
            # Picos aceitos: alta probabilidade no GMM e amplitude acima do piso focal
            kept_mask = (priors >= gmm_thresh) & (amps >= focal_floor)

            # Resgate contextual restritivo: apenas para vizinho imediato de pulso já confirmado
            for i in range(len(peaks)):
                if not kept_mask[i] and priors[i] >= 0.40 and amps[i] >= focal_floor * 0.80:
                    t_cur = peaks[i] / float(rate)
                    has_left = (i > 0 and kept_mask[i - 1] and
                                (gap_min_s <= t_cur - peaks[i - 1] / float(rate) <= gap_max_s) and
                                amps[i] >= 0.50 * amps[i - 1])
                    has_right = (i < len(peaks) - 1 and kept_mask[i + 1] and
                                 (gap_min_s <= peaks[i + 1] / float(rate) - t_cur <= gap_max_s) and
                                 amps[i] >= 0.50 * amps[i + 1])
                    if has_left or has_right:
                        kept_mask[i] = True

            if pruned_indices:
                for idx in pruned_indices:
                    kept_mask[idx] = False

            if not np.any(kept_mask) and len(priors) > 0:
                kept_mask = (priors >= np.percentile(priors, 75))
                if pruned_indices:
                    for idx in pruned_indices:
                        kept_mask[idx] = False
            return peaks[kept_mask], peaks[~kept_mask]

        # Com modelo supervisionado treinado (HistGradientBoosting / RandomForest)
        features = np.asarray([
            PulseLearner.extract_features_for_peak(
                int(p), rate, env_signal, raw_signal=raw_signal, prior_p_focal=priors[i]
            )
            for i, p in enumerate(peaks)
        ], dtype=float)

        n_expected = getattr(self.model, "n_features_in_", None)
        if n_expected is not None and n_expected > 0:
            if features.shape[1] > n_expected:
                X_used = features[:, :n_expected]
            elif features.shape[1] < n_expected:
                pad = np.zeros((features.shape[0], n_expected - features.shape[1]), dtype=float)
                X_used = np.hstack((features, pad))
            else:
                X_used = features
        else:
            X_used = features

        try:
            if hasattr(self.model, "predict_proba"):
                probs = self.model.predict_proba(X_used)
                classes = list(self.model.classes_)
                class1_idx = classes.index(1) if 1 in classes else -1
                pos_probs = probs[:, class1_idx] if class1_idx >= 0 else np.ones(len(peaks))
            else:
                pos_probs = self.model.predict(X_used).astype(float)
        except Exception as exc:
            print(f"Aviso no predict_proba ({exc}); aceitando todos os picos como válidos.")
            return peaks, np.asarray([], dtype=int)

        # Combinação linear: 65% confiança supervisionada + 35% prior físico GMM
        combined_score = 0.65 * pos_probs + 0.35 * priors

        # Limiares restritivos modulados pelo controle de sensibilidade focal
        HIGH_CONF_THRESH = 0.58 + 0.25 * focal_sensitivity
        LOW_CONF_THRESH = 0.42 + 0.20 * focal_sensitivity

        n = len(peaks)
        kept_mask = np.zeros(n, dtype=bool)
        pulse_times = peaks / float(rate)

        # 1. Pulsos de alta confiança e que respeitam o piso focal: aprovados diretamente
        kept_mask[(combined_score >= HIGH_CONF_THRESH) & (amps >= focal_floor)] = True

        # 2. Contextual Gating restritivo: pulsos intermediários aceitos apenas se forem vizinhos
        # de um pulso JÁ CONFIRMADO e com amplitude coerente (evita que ruídos se aprovem mutuamente)
        for i in range(n):
            if not kept_mask[i] and combined_score[i] >= LOW_CONF_THRESH and amps[i] >= focal_floor * 0.75:
                t_cur = pulse_times[i]
                has_prev_match = (i > 0 and kept_mask[i - 1] and
                                  gap_min_s <= (t_cur - pulse_times[i - 1]) <= gap_max_s and
                                  amps[i] >= 0.50 * amps[i - 1])
                has_next_match = (i < n - 1 and kept_mask[i + 1] and
                                  gap_min_s <= (pulse_times[i + 1] - t_cur) <= gap_max_s and
                                  amps[i] >= 0.50 * amps[i + 1])
                if has_prev_match or has_next_match:
                    kept_mask[i] = True

        # Aplicação mandatória de regras rígidas de poda pré-inferência
        if pruned_indices:
            for idx in pruned_indices:
                kept_mask[idx] = False

        return peaks[kept_mask], peaks[~kept_mask]

    def serialize(self):
        if self.model is None:
            return None
        payload = pickle.dumps(self.model)
        return {
            "model_type": type(self.model).__name__,
            "feature_names": self.feature_names,
            "model_pickle_b64": base64.b64encode(payload).decode("ascii"),
        }

    def save_to_config(self):
        if self.model is None:
            return False
        try:
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
            except FileNotFoundError:
                config = {}
            if not isinstance(config, dict):
                config = {}
            config["pulse_learner"] = self.serialize()
            config["pruning_rules"] = getattr(self, "pruning_rules", [])
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            return True
        except (OSError, TypeError, ValueError) as exc:
            print(f"Erro ao persistir modelo de aprendizado: {exc}")
            return False

    def save_persisted_training(self):
        payload = {
            "model": self.model,
            "training_features": self.training_features,
            "training_labels": self.training_labels,
            "feature_names": self.feature_names,
            "pruning_rules": getattr(self, "pruning_rules", []),
            "version": APP_VERSION,
        }
        temp_path = self.persistence_path + ".tmp"
        try:
            with open(temp_path, "wb") as f:
                pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)
            os.replace(temp_path, self.persistence_path)
            return True
        except (OSError, pickle.PickleError) as exc:
            print(f"Erro ao persistir treinamento: {exc}")
            return False

    def load_persisted_training(self):
        if not os.path.exists(self.persistence_path):
            return False
        try:
            with open(self.persistence_path, "rb") as f:
                payload = pickle.load(f)
            if not isinstance(payload, dict):
                return False
            features = np.asarray(payload.get("training_features", []), dtype=float)
            labels = np.asarray(payload.get("training_labels", []), dtype=int)
            if features.ndim == 2 and len(labels) == len(features):
                if features.shape[1] < len(self.feature_names):
                    pad = np.zeros((len(features), len(self.feature_names) - features.shape[1]), dtype=float)
                    self.training_features = np.hstack((features, pad))
                elif features.shape[1] == len(self.feature_names):
                    self.training_features = features
                else:
                    self.training_features = features[:, :len(self.feature_names)]
                self.training_labels = labels

            # Salvaguarda contra modelos degenerados (sem exemplos negativos de ruído/distantes)
            if self.training_labels.size > 0:
                n_neg = int(np.sum(self.training_labels == 0))
                n_pos = int(np.sum(self.training_labels == 1))
                if n_neg < 10 or (n_pos / max(1, n_neg)) > 6.0:
                    print("Aviso: Base de treinamento legada com desbalanceamento extremo detectada. Reiniciando modelo para modo restritivo de alta precisão.")
                    self.model = None
                    self.training_features = np.empty((0, len(self.feature_names)))
                    self.training_labels = np.empty(0, dtype=int)
                    return False

            self.pruning_rules = payload.get("pruning_rules", getattr(self, "pruning_rules", []))
            model = payload.get("model")
            if model is not None and hasattr(model, "predict"):
                self.model = model
            return self.model is not None or self.training_features.size > 0
        except Exception as exc:
            print(f"Aviso: não foi possível restaurar o treinamento: {exc}")
            return False

    def load_from_config(self):
        if not os.path.exists(self.config_path):
            return False
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            if not isinstance(config, dict):
                return False
            self.pruning_rules = config.get("pruning_rules", getattr(self, "pruning_rules", []))
            payload = config.get("pulse_learner")
            if not isinstance(payload, dict) or not payload.get("model_pickle_b64"):
                return False
            model_bytes = base64.b64decode(payload["model_pickle_b64"])
            self.model = pickle.loads(model_bytes)
            return True
        except Exception as exc:
            print(f"Aviso: não foi possível restaurar o modelo treinado: {exc}")
            self.model = None
            return False

    def export_model_file(self, filepath):
        """Exporta o modelo treinado completo, conjunto de dados e metadados para um arquivo independente."""
        if self.model is None and self.training_features.size == 0:
            raise ValueError("Não há modelo ou dados de treinamento disponíveis para exportar.")
        payload = {
            "model": self.model,
            "training_features": self.training_features,
            "training_labels": self.training_labels,
            "feature_names": self.feature_names,
            "version": APP_VERSION,
            "timestamp": time.time(),
        }
        with open(filepath, "wb") as f:
            pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)
        return True

    def import_model_file(self, filepath):
        """Carrega e valida um modelo de treinamento exportado anteriormente, com verificação de versão."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Arquivo não encontrado: {filepath}")
        with open(filepath, "rb") as f:
            payload = pickle.load(f)
        if not isinstance(payload, dict):
            raise ValueError("Formato de arquivo de treinamento inválido.")

        # Verificação de versão do arquivo .pkl em relação à versão do app
        file_version = str(payload.get("version", "1.0.0"))
        if is_version_newer(file_version, APP_VERSION):
            raise ValueError(
                f"O arquivo de treinamento foi gerado por uma versão mais recente do Crinômetro (v{file_version}).\n\n"
                f"Sua versão atual é v{APP_VERSION}.\n\n"
                f"Por favor, atualize seu aplicativo em:\n"
                f"https://github.com/rogerioafreitas/crinometro"
            )

        features = np.asarray(payload.get("training_features", []), dtype=float)
        labels = np.asarray(payload.get("training_labels", []), dtype=int)
        model = payload.get("model")

        # Adaptação para modelos antigos com 7 ou outros números de features
        if features.size > 0 and labels.size > 0:
            if features.ndim == 2:
                if features.shape[1] < len(self.feature_names):
                    pad = np.zeros((len(features), len(self.feature_names) - features.shape[1]), dtype=float)
                    self.training_features = np.hstack((features, pad))
                else:
                    self.training_features = features[:, :len(self.feature_names)]
            else:
                self.training_features = features
            self.training_labels = labels

        if model is not None and hasattr(model, "predict"):
            self.model = model
        elif self.training_features.size > 0 and self.training_labels.size > 0 and np.unique(self.training_labels).size >= 2:
            self.model = self._build_model()
            self.model.fit(self.training_features, self.training_labels)
        else:
            raise ValueError("O arquivo não contém um classificador válido ou dados suficientes para treino.")

        self.save_persisted_training()
        self.save_to_config()
        return True

    def reset(self):
        """Zera completamente o modelo, dados de treino e arquivos persistidos."""
        self.model = None
        self.training_features = np.empty((0, len(self.feature_names)), dtype=float)
        self.training_labels = np.empty((0,), dtype=int)
        self.pruning_rules = []
        if os.path.exists(self.persistence_path):
            try:
                os.remove(self.persistence_path)
            except OSError:
                pass
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                if isinstance(config, dict):
                    config["pulse_learner"] = None
                    config["pruning_rules"] = []
                    with open(self.config_path, "w", encoding="utf-8") as f:
                        json.dump(config, f, indent=4, ensure_ascii=False)
        except Exception:
            pass


