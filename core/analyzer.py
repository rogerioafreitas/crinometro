"""
Crinômetro - Motor Bioacústico DSP (Processamento de Sinal e Agrupamento Rítmico).
"""
import os
import re
import time
import warnings
import numpy as np
import statistics
from scipy.io import wavfile
from scipy.io.wavfile import WavFileWarning
from scipy.signal import hilbert, find_peaks, butter, sosfiltfilt, peak_widths, spectrogram, welch

class CricketAnalyzer:
    @staticmethod
    def _safe_mode(values):
        if not values: return 0
        try: return statistics.mode(values)
        except statistics.StatisticsError:
            modes = statistics.multimode(values)
            return min(modes) if modes else 0

    @staticmethod
    def compute_psd(data, sr):
        """Calcula o Espectro de Potência Médio (PSD) usando o método de Welch com janela Hann."""
        # Tamanho da janela e overlap ideais para resolução de frequência
        nperseg = min(len(data), int(sr * 0.05)) # Janela de 50ms para boa resolução espectral
        f, Pxx = welch(data, sr, window='hann', nperseg=nperseg, scaling='density')
        # Conversão para dB (escala logarítmica de potência)
        # Proteção contra log(0)
        with np.errstate(divide='ignore', invalid='ignore'):
            Pxx_db = 10 * np.log10(np.clip(Pxx, 1e-12, None))
            
        # Remove a lixeira DC (f=0) para evitar o artefato vertical no início do gráfico
        return f[1:], Pxx_db[1:]

    @staticmethod
    def analyze(file_path, params, pulse_learner=None, cached_spec=None):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", WavFileWarning)
            rate, data = wavfile.read(file_path)
        if len(data.shape) > 1:
            data = data[:, 0]

        data = data.astype(np.float64)
        if len(data) == 0:
            raise ValueError("O arquivo de áudio está vazio.")

        # Remove offset DC e ruídos de baixa frequência / vento (< 50 Hz)
        data = data - np.mean(data)
        nyq = 0.5 * rate
        if rate > 120.0 and nyq > 50.0:
            sos_dc = butter(2, 50.0 / nyq, btype='high', output='sos')
            data = sosfiltfilt(sos_dc, data)

        max_abs = np.max(np.abs(data))
        if max_abs == 0:
            raise ValueError("O arquivo de áudio está mudo.")

        audio_duration_sec = len(data) / rate

        # Filtragem passa-faixa Butterworth IIR em unidades físicas (isolamento da banda estridulatória)
        b1_min = max(20.0, float(params.get("b1_min", 3200)))
        b1_max = min(nyq - 20.0, float(params.get("b1_max", 6000)))
        sos_b1 = butter(4, [b1_min / nyq, b1_max / nyq], btype='band', output='sos')
        data_b1 = sosfiltfilt(sos_b1, data)
        env1 = np.abs(hilbert(data_b1))

        # Normalização robusta baseada na energia da banda estridulatória (imune a estalos e ruído grave)
        scale_p99 = float(np.percentile(env1, 99.85)) if len(env1) > 1000 else float(np.max(env1))
        if scale_p99 <= 0 or not np.isfinite(scale_p99):
            scale_p99 = float(np.max(env1))
        if scale_p99 <= 0 or not np.isfinite(scale_p99):
            scale_p99 = 1.0

        env1 = env1 / scale_p99
        data_b1 = data_b1 / scale_p99

        # Sinal original normalizado de forma segura para exibição visual
        raw_scale = float(np.percentile(np.abs(data), 99.9)) if len(data) > 1000 else float(max_abs)
        raw_scale = max(raw_scale, 1e-9)
        data = np.clip(data / raw_scale, -1.0, 1.0)

        # Suavização por janela de Hann normalizada (elimina ringing e ondulações espúrias dos lóbulos laterais)
        smooth_window = max(9, int(rate * params.get("smooth_window_ms", 15.0) / 1000.0))
        if smooth_window % 2 == 0:
            smooth_window += 1
        hann_win = np.hanning(smooth_window)
        kernel = hann_win / np.sum(hann_win)
        env1_smooth = np.convolve(env1, kernel, mode='same').astype(np.float32)

        if cached_spec is not None and all(k in cached_spec for k in ("f_spec", "t_spec", "Sxx_db", "dom_freqs")):
            f_spec = cached_spec["f_spec"]
            t_spec = cached_spec["t_spec"]
            Sxx_db = cached_spec["Sxx_db"]
            dom_freqs = cached_spec["dom_freqs"]
        else:
            # Espectrograma de banda larga para exibição visual (cobre todos os sons até 10+ kHz / Nyquist)
            f_spec, t_spec, Sxx = spectrogram(data, rate, nperseg=1024, noverlap=768)
            Sxx_db = (10 * np.log10(Sxx + 1e-10)).astype(np.float32)
            f_spec = f_spec.astype(np.float32)
            t_spec = t_spec.astype(np.float32)

            freq_mask = (f_spec >= b1_min) & (f_spec <= b1_max)
            if np.any(freq_mask):
                Sxx_band = Sxx[freq_mask, :]
                band_indices = np.where(freq_mask)[0]
                dom_in_band = np.argmax(Sxx_band, axis=0)
                dom_freq_idx = band_indices[dom_in_band]
            else:
                dom_freq_idx = np.argmax(Sxx, axis=0)

            dom_freqs = f_spec[dom_freq_idx].astype(np.float64)
            # Refinamento parabólico sub-bin contínuo da frequência dominante (vetorizado)
            df = float(f_spec[1] - f_spec[0]) if len(f_spec) > 1 else 1.0
            valid_k = (dom_freq_idx > 0) & (dom_freq_idx < Sxx.shape[0] - 1)
            valid_cols = np.where(valid_k)[0]
            if len(valid_cols) > 0:
                k = dom_freq_idx[valid_cols]
                alpha = Sxx_db[k - 1, valid_cols]
                beta = Sxx_db[k, valid_cols]
                gamma = Sxx_db[k + 1, valid_cols]
                denom = alpha - 2.0 * beta + gamma
                non_zero = np.abs(denom) > 1e-6
                p = np.zeros_like(denom, dtype=np.float32)
                p[non_zero] = 0.5 * (alpha[non_zero] - gamma[non_zero]) / denom[non_zero]
                p_valid = non_zero & (p >= -1.0) & (p <= 1.0)
                dom_freqs[valid_cols[p_valid]] = f_spec[k[p_valid]] + p[p_valid] * df
            dom_freqs = dom_freqs.astype(np.float32)
        dist_samples = max(1, int(rate * (params.get("gap_min", 25.0) / 1000.0 * 0.75)))

        # Limiar adaptativo restritivo de alta especificidade (prioriza precisão e elimina falsos positivos)
        noise_floor_param = float(params.get("noise_floor", 1.00))
        noise_25 = float(np.percentile(env1_smooth, 25))
        search_thresh = max(float(params.get("amp_min", 0.08)) * noise_floor_param, noise_25 * 2.5)
        search_thresh = max(0.06, search_thresh)

        prominence_val = max(0.015, float(params.get("prominence", 0.02)))
        width_min = max(0.0, float(params.get("width_min_ms", 0.0)) * rate / 1000.0)
        width_max_ms = float(params.get("width_max_ms", 0.0))
        width_max = None if width_max_ms <= 0 else width_max_ms * rate / 1000.0

        dist_samples = max(1, int(rate * (float(params.get("gap_min", 25.0)) / 1000.0 * 0.88)))

        raw_peaks, _ = find_peaks(env1_smooth, height=(search_thresh, params.get("amp_max", 2.0)),
                                  distance=dist_samples, prominence=prominence_val,
                                  width=(width_min, width_max))

        # Estágio 1: Triagem e validação morfológica dos pulsos candidatos
        # Como data_b1 já é filtrado com Butterworth passa-faixa em [b1_min, b1_max],
        # a envoltória env1_smooth reflete diretamente a banda estridulatória.
        # Falsos positivos de frequência e cantos distantes são isolados no Estágio 2.5.
        peaks_filtered = np.asarray(raw_peaks, dtype=int)
        valid_peaks_stage2 = []
        peak_dur_dict = {}
        discarded_peaks_reasons = {}

        if len(peaks_filtered) > 0:
            widths_samples, _, _, _ = peak_widths(env1_smooth, peaks_filtered, rel_height=0.7)
            pulse_durations_s = widths_samples / rate
            peak_dur_dict = dict(zip(peaks_filtered, pulse_durations_s))

            dur_tol = 0.45
            dur_min_lim = (params["dur_min"] / 1000.0) * (1 - dur_tol)
            dur_max_lim = (params["dur_max"] / 1000.0) * (1 + dur_tol)
            for p in peaks_filtered:
                dur = peak_dur_dict[p]
                if dur_min_lim <= dur <= dur_max_lim:
                    valid_peaks_stage2.append(p)
                else:
                    discarded_peaks_reasons[int(p)] = (
                        f"Duração fora da faixa ({dur*1000.0:.1f} ms; faixa permitida: {dur_min_lim*1000.0:.1f}–{dur_max_lim*1000.0:.1f} ms)"
                    )

        # ----------------------------------------------------------------------
        # Estágio 2.5: Identificação da Frequência Dominante Focal por Densidade
        # de Chilreios e Filtro de Tolerância Espectral (±300 Hz padrão)
        # ----------------------------------------------------------------------
        carrier_freq = 5000.0
        if len(valid_peaks_stage2) >= 2:
            prelim_chirps, prelim_chirp_peaks_list, _, _ = CricketAnalyzer.regroup_chirps(
                valid_peaks_stage2, params, rate, env1_smooth, raw_signal=data_b1
            )
            chirp_freqs = []
            chirp_weights = []
            for cp in prelim_chirp_peaks_list:
                if len(cp) >= int(params.get("min_p", 2)):
                    times_cp = np.asarray(cp, dtype=float) / rate
                    freqs_cp = np.interp(times_cp, t_spec, dom_freqs)
                    chirp_freqs.append(float(np.median(freqs_cp)))
                    chirp_weights.append(len(cp))

            if chirp_freqs:
                # Localiza a frequência com maior densidade de chilreios
                f_min_search = float(params.get("b1_min", 3200))
                f_max_search = float(params.get("b1_max", 6000))
                bin_width = 50.0  # resolução espectral de 50 Hz
                bins = np.arange(f_min_search, f_max_search + bin_width, bin_width)
                counts, edges = np.histogram(chirp_freqs, bins=bins, weights=chirp_weights)
                if np.sum(counts) > 0:
                    best_bin = int(np.argmax(counts))
                    bin_lo = edges[best_bin] - 75.0
                    bin_hi = edges[best_bin + 1] + 75.0
                    modal_freqs = [f for f in chirp_freqs if bin_lo <= f <= bin_hi]
                    carrier_freq = float(np.median(modal_freqs)) if modal_freqs else float((edges[best_bin] + edges[best_bin + 1]) / 2.0)
                else:
                    carrier_freq = float(np.median(chirp_freqs))
            elif len(valid_peaks_stage2) > 0:
                times_pks = np.asarray(valid_peaks_stage2, dtype=float) / rate
                carrier_freq = float(np.median(np.interp(times_pks, t_spec, dom_freqs)))
        elif len(valid_peaks_stage2) > 0:
            times_pks = np.asarray(valid_peaks_stage2, dtype=float) / rate
            carrier_freq = float(np.median(np.interp(times_pks, t_spec, dom_freqs)))
        elif len(dom_freqs) > 0:
            carrier_freq = float(np.median(dom_freqs))

        # Filtragem por desvio de frequência em relação à portadora
        freq_tol = float(params.get("freq_tolerance_hz", 700.0))
        valid_peaks_stage3 = []
        freq_outliers = []
        if len(valid_peaks_stage2) > 0:
            for p in valid_peaks_stage2:
                t_p = p / float(rate)
                f_p = float(np.interp(t_p, t_spec, dom_freqs))
                diff = f_p - carrier_freq
                if abs(diff) <= freq_tol:
                    valid_peaks_stage3.append(p)
                else:
                    freq_outliers.append(p)
                    discarded_peaks_reasons[int(p)] = (
                        f"Frequência fora da tolerância da portadora "
                        f"({f_p:.0f} Hz; desvio de {diff:+.0f} Hz da portadora {carrier_freq:.0f} Hz; limite ±{freq_tol:.0f} Hz)"
                    )

        # Se o filtro reteve picos consistentes, descarta os pulsos fora da tolerância
        if len(valid_peaks_stage3) >= 1:
            candidate_peaks = np.asarray(valid_peaks_stage3, dtype=int)
            distant_peaks = list(freq_outliers)
        else:
            candidate_peaks = np.asarray(valid_peaks_stage2, dtype=int)
            distant_peaks = []

        # Classificação contextual e segregação focal/distante (ML)
        if pulse_learner is not None and len(candidate_peaks) > 0:
            gap_min_s = float(params.get("gap_min", 25.0)) / 1000.0 * 0.85
            gap_max_s = float(params.get("gap_max", 35.0)) / 1000.0 * 1.15
            focal_sens = float(params.get("focal_sensitivity", 0.60))
            candidate_peaks, ml_distant_peaks = pulse_learner.filter_peaks(
                candidate_peaks, rate, env1_smooth, raw_signal=data_b1,
                gap_min_s=gap_min_s, gap_max_s=gap_max_s, focal_sensitivity=focal_sens
            )
            for p in ml_distant_peaks:
                discarded_peaks_reasons[int(p)] = "Classificado pelo modelo ML como ruído / canto distante"
            distant_peaks = list(sorted(set(distant_peaks) | set(ml_distant_peaks)))

        # Agrupamento com coerência de trilha acústica em tempo linear O(N)
        peaks = np.asarray(sorted(candidate_peaks), dtype=int)
        chirps, chirp_peaks_list, media, moda = CricketAnalyzer.regroup_chirps(
            peaks, params, rate, env1_smooth, raw_signal=data_b1
        )

        # Identifica pulsos candidatos que não foram retidos em nenhum chilreio
        valid_in_chirps = set()
        for cp in chirp_peaks_list:
            valid_in_chirps.update(cp)

        min_p = int(params.get("min_p", 2))
        for p in candidate_peaks:
            p_int = int(p)
            if p_int not in valid_in_chirps and p_int not in discarded_peaks_reasons:
                discarded_peaks_reasons[p_int] = f"Pulso isolado / sequência incompleta (< {min_p} pulsos por chilreio)"

        all_distant = sorted(list(set(distant_peaks) | set(discarded_peaks_reasons.keys())))

        # Task 2.2: Calcula o PSD (Power Spectral Density) do áudio bruto (data) para ver o espectro real
        f_psd, Pxx_db = CricketAnalyzer.compute_psd(data, rate)

        return (rate, data.astype(np.float32), data_b1.astype(np.float32), env1_smooth, peaks, chirps, chirp_peaks_list,
                media, moda, f_spec, t_spec, Sxx_db, dom_freqs, audio_duration_sec, all_distant, carrier_freq,
                discarded_peaks_reasons, valid_peaks_stage2, peak_dur_dict, f_psd.astype(np.float32), Pxx_db.astype(np.float32))

    @staticmethod
    def reevaluate_carrier_tolerance(
        valid_peaks_stage2, carrier_freq, new_tol_hz,
        rate, t_spec, dom_freqs, env, params, data_b1=None,
        pulse_learner=None, base_discarded_reasons=None
    ):
        """Re-avalia rapidamente em tempo real a tolerância espectral da portadora.

        Executa em menos de 30 ms sem recalcular transformadas pesadas.
        Retorna: (peaks, chirps, chirp_peaks_list, media, moda, all_distant, discarded_reasons)
        """
        valid_peaks_stage2 = np.asarray(valid_peaks_stage2, dtype=int)
        freq_tol = float(new_tol_hz)
        discarded_reasons = {}

        # 1. Preserva motivos prévios não espectrais (ex: duração fora da faixa ou ML)
        if base_discarded_reasons:
            for pk, reason in base_discarded_reasons.items():
                if "Frequência fora da tolerância" not in reason and "Pulso isolado" not in reason:
                    discarded_reasons[int(pk)] = reason

        # 2. Triagem rápida por desvio da frequência portadora
        if len(valid_peaks_stage2) > 0 and len(dom_freqs) > 0 and len(t_spec) > 0:
            times_pks = valid_peaks_stage2 / float(rate)
            f_pks = np.interp(times_pks, t_spec, dom_freqs)
            diffs = f_pks - carrier_freq
            mask = np.abs(diffs) <= freq_tol

            valid_peaks_stage3 = valid_peaks_stage2[mask]
            outliers = valid_peaks_stage2[~mask]
            outliers_f = f_pks[~mask]
            outliers_diff = diffs[~mask]

            for p, f_val, d_val in zip(outliers, outliers_f, outliers_diff):
                discarded_reasons[int(p)] = (
                    f"Frequência fora da tolerância da portadora "
                    f"({f_val:.0f} Hz; desvio de {d_val:+.0f} Hz da portadora {carrier_freq:.0f} Hz; limite ±{freq_tol:.0f} Hz)"
                )
        else:
            valid_peaks_stage3 = valid_peaks_stage2

        if len(valid_peaks_stage3) >= 1:
            candidate_peaks = np.asarray(valid_peaks_stage3, dtype=int)
        else:
            candidate_peaks = np.asarray(valid_peaks_stage2, dtype=int)

        # 3. Classificação ML (Removido daqui pois já foi processado na análise principal e não depende da tolerância)
        # O array candidate_peaks já reflete o estágio 2 (pós-ML)
        pass

        # 4. Agrupamento em chilreios
        peaks = np.asarray(sorted(candidate_peaks), dtype=int)
        chirps, chirp_peaks_list, media, moda = CricketAnalyzer.regroup_chirps(
            peaks, params, rate, env, raw_signal=data_b1
        )

        valid_in_chirps = set()
        for cp in chirp_peaks_list:
            valid_in_chirps.update(cp)

        min_p = int(params.get("min_p", 2))
        for p in candidate_peaks:
            p_int = int(p)
            if p_int not in valid_in_chirps and p_int not in discarded_reasons:
                discarded_reasons[p_int] = f"Pulso isolado / sequência incompleta (< {min_p} pulsos por chilreio)"

        all_distant = sorted(list(discarded_reasons.keys()))
        return (peaks, chirps, chirp_peaks_list, media, moda, all_distant, discarded_reasons)

    @staticmethod
    def regroup_chirps(peaks, params, rate, env, raw_signal=None):
        """Reagrupa picos em chilreios com filtro de coerência de trilha em tempo linear O(N).

        Preserva a contagem fisiológica do grilo focal, expurgando intrusos rítmicos ou
        pulsos com amplitudes/centroides discrepantes sem penalizar chilreios legítimos.
        Picos forçados (user_added_peaks) são sempre preservados se respeitarem o intervalo temporal.
        """
        if len(peaks) < 2:
            return [], [], 0.0, 0
        peaks = np.asarray(sorted(peaks), dtype=int)
        pulse_times_s = peaks / float(rate)
        # Tolerância fisiológica rigorosa no intervalo inter-pulso (gap)
        gap_min_s = float(params.get("gap_min", 25.0)) / 1000.0 * 0.85
        gap_max_s = float(params.get("gap_max", 35.0)) / 1000.0 * 1.15
        min_p = int(params.get("min_p", 2))

        # 1. Agrupamento preliminar por intervalos temporais (O(N))
        chirp_peaks_list = []
        current_chirp = [peaks[0]]
        
        def _keep_chirp(c):
            return len(c) >= min_p

        for i in range(1, len(pulse_times_s)):
            gap_s = pulse_times_s[i] - pulse_times_s[i - 1]
            if gap_min_s <= gap_s <= gap_max_s:
                current_chirp.append(peaks[i])
            else:
                if _keep_chirp(current_chirp):
                    chirp_peaks_list.append(current_chirp)
                current_chirp = [peaks[i]]
        if _keep_chirp(current_chirp):
            chirp_peaks_list.append(current_chirp)

        # 2. Refinamento e Track Coherence em tempo linear O(N)
        refined_chirps = []

        for chirp in chirp_peaks_list:
            
            if len(chirp) < min_p:
                continue
            valid_idx = [p for p in chirp if 0 <= p < len(env)]
            if len(valid_idx) < min_p:
                continue

            amps = env[valid_idx]
            ref_amp = float(np.median(amps))

            # Coerência de amplitude fisiológica: permite modulação suave (crescendo/decrescendo natural)
            allowed_var = float(params.get("amp_var", 0.40)) * 1.65
            coherent_pulses = []
            for p in valid_idx:
                dev = abs(env[p] - ref_amp) / (ref_amp + 1e-6)
                if dev <= allowed_var:
                    coherent_pulses.append(p)

            if len(coherent_pulses) < min_p:
                continue

            # Verificação de colisão/intrusão entre pulsos muito próximos (O(K))
            c_times = np.asarray(coherent_pulses) / float(rate)
            clean_track = [coherent_pulses[0]]
            for k in range(1, len(coherent_pulses)):
                dt = c_times[k] - (clean_track[-1] / float(rate))
                if dt < gap_min_s * 0.80:
                    # Colisão temporal
                    if env[coherent_pulses[k]] > env[clean_track[-1]]:
                        clean_track[-1] = coherent_pulses[k]
                else:
                    clean_track.append(coherent_pulses[k])

            # Re-segmentação linear em blocos rítmicos válidos (O(K))
            if len(clean_track) >= min_p:
                sub_chirps = []
                sub = [clean_track[0]]
                for k in range(1, len(clean_track)):
                    dt = (clean_track[k] - clean_track[k - 1]) / float(rate)
                    if gap_min_s <= dt <= gap_max_s:
                        sub.append(clean_track[k])
                    else:
                        if len(sub) >= min_p:
                            sub_chirps.append(sub)
                        sub = [clean_track[k]]
                
                if len(sub) >= min_p:
                    sub_chirps.append(sub)

                for sc in sub_chirps:
                    refined_chirps.append(sc)

        # 3. Filtro Rítmico Fisiológico Inter-Chilreio (Inter-Chirp Interval - ICI Gate)
        # O intervalo entre chilreios pode variar naturalmente; o período refratário visa
        # podar apenas colisões de grilos intrusos sobrepostos (dt < 150 ms), sem descartar
        # chilreios legítimos de grilos que cantam com cadência rápida.
        if len(refined_chirps) >= 3:
            refined_chirps.sort(key=lambda cp: cp[0])
            ici_intervals_s = []
            for i in range(len(refined_chirps) - 1):
                t_end_cur = refined_chirps[i][-1] / float(rate)
                t_start_next = refined_chirps[i + 1][0] / float(rate)
                dt_ici = t_start_next - t_end_cur
                if dt_ici > gap_max_s:
                    ici_intervals_s.append(dt_ici)

            if len(ici_intervals_s) >= 2:
                ici_median_s = float(np.median(ici_intervals_s))
                ici_param_s = float(params.get("ici_min", 200.0)) / 1000.0 * 0.70
                # Limiar fisiológico refratário adaptativo: entre 120 ms e 180 ms
                ici_min_refractory_s = max(0.120, min(0.180, 0.45 * ici_median_s, ici_param_s))

                gated_chirps = [refined_chirps[0]]
                for i in range(1, len(refined_chirps)):
                    cand = refined_chirps[i]
                    last_valid = gated_chirps[-1]
                    t_last_end = last_valid[-1] / float(rate)
                    t_cand_start = cand[0] / float(rate)
                    dt_from_last = t_cand_start - t_last_end

                    if dt_from_last < ici_min_refractory_s:
                        # Colisão estrita intra-refratária (< 150 ms):
                        cand_amps = env[cand] if len(cand) > 0 and 0 <= cand[0] < len(env) else [0.0]
                        last_amps = env[last_valid] if len(last_valid) > 0 and 0 <= last_valid[0] < len(env) else [0.0]
                        cand_mean_amp = float(np.mean(cand_amps))
                        last_mean_amp = float(np.mean(last_amps))

                        # Candidato com múltiplos pulsos (> 3) e amplitude consistente não é descartado
                        if len(cand) >= 3 and cand_mean_amp >= 0.70 * last_mean_amp:
                            gated_chirps.append(cand)
                        elif cand_mean_amp > 1.20 * last_mean_amp and len(cand) >= len(last_valid):
                            gated_chirps[-1] = cand
                        else:
                            continue
                    else:
                        gated_chirps.append(cand)
                refined_chirps = gated_chirps

        # Assegura de forma infalível que NENHUM chilreio sem a quantidade mínima de pulsos passe.
        final_chirps = []
        for cp in refined_chirps:
            if len(cp) >= min_p:
                final_chirps.append(cp)
        refined_chirps = final_chirps

        chirps = [len(cp) for cp in refined_chirps]
        media = float(statistics.mean(chirps)) if len(chirps) > 0 else 0.0
        moda = CricketAnalyzer._safe_mode(chirps) if len(chirps) > 0 else 0
        return chirps, refined_chirps, media, moda

