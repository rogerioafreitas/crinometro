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
from scipy.signal import hilbert, find_peaks, butter, sosfiltfilt, peak_widths, spectrogram

class CricketAnalyzer:
    @staticmethod
    def _safe_mode(values):
        if not values: return 0
        try: return statistics.mode(values)
        except statistics.StatisticsError:
            modes = statistics.multimode(values)
            return min(modes) if modes else 0

    @staticmethod
    def analyze(file_path, params, pulse_learner=None):
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

        # ----------------------------------------------------------------------
        # Estágio 2.5: Identificação da Frequência Dominante Focal por Densidade
        # de Chilreios e Filtro de Tolerância Espectral (±300 Hz)
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

        # Filtragem por desvio de frequência: elimina pulsos com diferença > 300 Hz
        freq_tol = float(params.get("freq_tolerance_hz", 300.0))
        valid_peaks_stage3 = []
        freq_outliers = []
        if len(valid_peaks_stage2) > 0:
            for p in valid_peaks_stage2:
                t_p = p / float(rate)
                f_p = float(np.interp(t_p, t_spec, dom_freqs))
                if abs(f_p - carrier_freq) <= freq_tol:
                    valid_peaks_stage3.append(p)
                else:
                    freq_outliers.append(p)

        # Se o filtro reteve picos consistentes, descarta os pulsos fora de ±300 Hz
        if len(valid_peaks_stage3) >= 2:
            candidate_peaks = np.asarray(valid_peaks_stage3, dtype=int)
            distant_peaks = list(freq_outliers)
        elif len(valid_peaks_stage3) == 1:
            candidate_peaks = np.asarray(valid_peaks_stage3, dtype=int)
            distant_peaks = list(freq_outliers)
        else:
            candidate_peaks = np.asarray(valid_peaks_stage2, dtype=int)
            distant_peaks = []

        # Classificação contextual e segregação focal/distante
        if pulse_learner is not None and len(candidate_peaks) > 0:
            gap_min_s = float(params.get("gap_min", 25.0)) / 1000.0 * 0.85
            gap_max_s = float(params.get("gap_max", 35.0)) / 1000.0 * 1.15
            focal_sens = float(params.get("focal_sensitivity", 0.60))
            candidate_peaks, ml_distant_peaks = pulse_learner.filter_peaks(
                candidate_peaks, rate, env1_smooth, raw_signal=data_b1,
                gap_min_s=gap_min_s, gap_max_s=gap_max_s, focal_sensitivity=focal_sens
            )
            distant_peaks = list(sorted(set(distant_peaks) | set(ml_distant_peaks)))

        # Agrupamento com coerência de trilha acústica em tempo linear O(N)
        peaks = np.asarray(sorted(candidate_peaks), dtype=int)
        chirps, chirp_peaks_list, media, moda = CricketAnalyzer.regroup_chirps(
            peaks, params, rate, env1_smooth, raw_signal=data_b1
        )

        return (rate, data.astype(np.float32), data_b1.astype(np.float32), env1_smooth, peaks, chirps, chirp_peaks_list,
                media, moda, f_spec, t_spec, Sxx_db, dom_freqs, audio_duration_sec, distant_peaks, carrier_freq)

    @staticmethod
    def regroup_chirps(peaks, params, rate, env, raw_signal=None):
        """Reagrupa picos em chilreios com filtro de coerência de trilha em tempo linear O(N).

        Preserva a contagem fisiológica do grilo focal, expurgando intrusos rítmicos ou
        pulsos com amplitudes/centroides discrepantes sem penalizar chilreios legítimos.
        """
        if len(peaks) < 2:
            return [], [], 0.0, 0
        peaks = np.asarray(sorted(peaks), dtype=int)
        pulse_times_s = peaks / float(rate)
        # Tolerância fisiológica rigorosa no intervalo inter-pulso (gap)
        gap_min_s = float(params.get("gap_min", 25.0)) / 1000.0 * 0.85
        gap_max_s = float(params.get("gap_max", 35.0)) / 1000.0 * 1.15

        # 1. Agrupamento preliminar por intervalos temporais (O(N))
        chirp_peaks_list = []
        current_chirp = [peaks[0]]
        for i in range(1, len(pulse_times_s)):
            gap_s = pulse_times_s[i] - pulse_times_s[i - 1]
            if gap_min_s <= gap_s <= gap_max_s:
                current_chirp.append(peaks[i])
            else:
                if len(current_chirp) >= 2:
                    chirp_peaks_list.append(current_chirp)
                current_chirp = [peaks[i]]
        if len(current_chirp) >= 2:
            chirp_peaks_list.append(current_chirp)

        # 2. Refinamento e Track Coherence em tempo linear O(N)
        refined_chirps = []
        min_p = int(params.get("min_p", 2))

        for chirp in chirp_peaks_list:
            if len(chirp) < min_p:
                continue
            valid_idx = [p for p in chirp if 0 <= p < len(env)]
            if len(valid_idx) < min_p:
                continue

            amps = env[valid_idx]
            ref_amp = float(np.median(amps))

            # Coerência de amplitude fisiológica: descarta ecos e picos de fundo espúrios
            allowed_var = float(params.get("amp_var", 0.40)) * 1.25
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
                    # Colisão temporal: dois pulsos sobrepostos (grilo distante intrudindo)
                    # Mantém o pulso com maior amplitude
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
        # A fisiologia neuromuscular do grilo focal impõe um período refratário mínimo entre chilreios consecutivos:
        # O intervalo entre o término do último pulso de um chilreio e o início do próximo chilreio (ΔT_ICI)
        # pode se alongar caso o grilo silencie ou pause, mas nunca pode ser drasticamente menor do que a cadência típica.
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
                # Limiar fisiológico refratário: 70% do intervalo mediano entre chilreios
                ici_min_refractory_s = 0.70 * ici_median_s

                gated_chirps = [refined_chirps[0]]
                for i in range(1, len(refined_chirps)):
                    cand = refined_chirps[i]
                    last_valid = gated_chirps[-1]
                    t_last_end = last_valid[-1] / float(rate)
                    t_cand_start = cand[0] / float(rate)
                    dt_from_last = t_cand_start - t_last_end

                    if dt_from_last < ici_min_refractory_s:
                        # Conflito de período refratário fisiológico: o candidato surgiu prematuramente
                        # durante a janela de silêncio obrigatória do grilo focal.
                        cand_amps = env[cand] if len(cand) > 0 and 0 <= cand[0] < len(env) else [0.0]
                        last_amps = env[last_valid] if len(last_valid) > 0 and 0 <= last_valid[0] < len(env) else [0.0]
                        cand_mean_amp = float(np.mean(cand_amps))
                        last_mean_amp = float(np.mean(last_amps))

                        # Se o candidato for expressivamente mais forte e consistente, substitui o anterior;
                        # caso contrário, descarta o candidato como ruído espúrio ou grilo secundário de fundo.
                        if cand_mean_amp > 1.35 * last_mean_amp and len(cand) >= len(last_valid):
                            gated_chirps[-1] = cand
                        else:
                            # Descarta o candidato prematuro
                            continue
                    else:
                        gated_chirps.append(cand)
                refined_chirps = gated_chirps

        chirps = [len(cp) for cp in refined_chirps]
        media = float(statistics.mean(chirps)) if len(chirps) > 0 else 0.0
        moda = CricketAnalyzer._safe_mode(chirps) if len(chirps) > 0 else 0
        return chirps, refined_chirps, media, moda

