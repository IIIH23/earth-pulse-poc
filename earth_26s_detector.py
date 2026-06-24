#!/usr/bin/env python3
"""
Detect the narrow ~26-second microseism line for Earth Pulse.

This is different from earth_period.py, which finds the dominant primary
microseism peak. The 26-second pulse near 0.0385 Hz is faint and can be buried
under the stronger ocean-storm microseism, so this script measures a narrow
spectral line against adjacent background bands.

Usage:
    pip install -r requirements.txt
    python earth_26s_detector.py
    python earth_26s_detector.py --hours 24 --verbose
    python earth_26s_detector.py --plot

Notes:
    - Use longer windows, usually 12-24 hours, for clearer detections.
    - A quiet window may produce no detection; that is expected.
    - This is single-station spectral detection, not source triangulation.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

try:
    from obspy import UTCDateTime
    from obspy.clients.fdsn import Client
    from scipy.signal import welch
except ImportError:
    print(
        "ERROR: missing dependencies.\n"
        "Install with:  pip install -r requirements.txt",
        file=sys.stderr,
    )
    sys.exit(1)


# -----------------------------------------------------------------------------
# Detection configuration
# -----------------------------------------------------------------------------
CHANNEL = "LHZ"
DEFAULT_HOURS = 6.0
DEFAULT_DETECT_SNR = 3.0

# 26 s = 0.03846 Hz. Keep the target tight and compare it to adjacent background
# that remains below the main primary microseism rise around 0.05 Hz.
TARGET_LOW_HZ = 0.036
TARGET_HIGH_HZ = 0.041
TARGET_CENTER_HZ = 1.0 / 26.0
BACKGROUND_BANDS_HZ = ((0.028, 0.0345), (0.0425, 0.049))

# Weighted toward the South Atlantic / Gulf of Guinea source region, with quiet
# and global reference stations.
STATIONS = [
    ("II", "SHEL", "00", CHANNEL),  # St. Helena, South Atlantic
    ("II", "ASCN", "00", CHANNEL),  # Ascension Island, South Atlantic
    ("II", "BFO", "00", CHANNEL),   # Black Forest, Germany
    ("II", "MBAR", "00", CHANNEL),  # Mbarara, Uganda
    ("IU", "TSUM", "00", CHANNEL),  # Tsumeb, Namibia
    ("IU", "ANMO", "00", CHANNEL),  # Albuquerque, USA
]

LOCATION_FALLBACKS = ("00", "10", "")


# -----------------------------------------------------------------------------
# Data structures
# -----------------------------------------------------------------------------
@dataclass
class StationDetection:
    code: str
    period_s: float | None
    frequency_hz: float | None
    snr: float | None
    detected: bool
    error: str | None = None


@dataclass
class Microseism26sResult:
    detected_any: bool
    consensus_period_s: float | None
    consensus_frequency_hz: float | None
    confidence_label: str
    stations_detected: int
    stations_attempted: int
    per_station: list[StationDetection]
    timestamp_utc: datetime


# -----------------------------------------------------------------------------
# Core algorithm
# -----------------------------------------------------------------------------
def analyze_station(
    client: Client,
    net: str,
    sta: str,
    loc: str,
    chan: str,
    start: UTCDateTime,
    end: UTCDateTime,
    detect_snr: float,
    verbose: bool = False,
) -> StationDetection:
    """Fetch one station's LHZ data and detect the 26 s spectral line."""
    code = f"{net}.{sta}"
    try:
        location_candidates = [loc]
        for fallback in LOCATION_FALLBACKS:
            if fallback not in location_candidates:
                location_candidates.append(fallback)

        st = None
        used_location = None
        errors = []
        for location in location_candidates:
            try:
                label = location or "--"
                if verbose:
                    print(
                        f"  [{code}] fetching {label}.{chan} "
                        f"{start.isoformat()} -> {end.isoformat()}"
                    )
                candidate = client.get_waveforms(
                    network=net,
                    station=sta,
                    location=location,
                    channel=chan,
                    starttime=start,
                    endtime=end,
                )
                if len(candidate) == 0:
                    errors.append(f"{label}: no data returned")
                    continue
                st = candidate
                used_location = label
                break
            except Exception as exc:
                errors.append(f"{location or '--'}: {str(exc).splitlines()[0]}")

        if st is None:
            return StationDetection(
                code,
                None,
                None,
                None,
                False,
                "; ".join(errors)[:200] if errors else "no data returned",
            )

        st.merge(method=1, fill_value=0)
        tr = st[0]
        tr.detrend("demean")
        tr.detrend("linear")

        data = tr.data.astype(np.float64)
        sample_rate = float(tr.stats.sampling_rate)
        sample_count = len(data)
        if sample_count < 4096:
            return StationDetection(
                code,
                None,
                None,
                None,
                False,
                f"too few samples ({sample_count})",
            )

        # Long segments give enough frequency resolution to isolate the narrow
        # line while still averaging enough windows to reduce random noise.
        nperseg = int(min(8192, max(2048, sample_count // 4)))
        freqs, psd = welch(
            data,
            fs=sample_rate,
            nperseg=nperseg,
            noverlap=nperseg // 2,
            detrend="linear",
        )

        target_mask = (freqs >= TARGET_LOW_HZ) & (freqs <= TARGET_HIGH_HZ)
        background_mask = np.zeros_like(freqs, dtype=bool)
        for low_hz, high_hz in BACKGROUND_BANDS_HZ:
            background_mask |= (freqs >= low_hz) & (freqs <= high_hz)

        if target_mask.sum() < 2 or background_mask.sum() < 4:
            return StationDetection(
                code,
                None,
                None,
                None,
                False,
                "insufficient spectral resolution",
            )

        target_freqs = freqs[target_mask]
        target_psd = psd[target_mask]
        peak_idx = int(np.argmax(target_psd))
        peak_freq = float(target_freqs[peak_idx])
        peak_power = float(target_psd[peak_idx])
        background_floor = float(np.median(psd[background_mask]))
        snr = peak_power / background_floor if background_floor > 0 else 0.0
        period = 1.0 / peak_freq if peak_freq > 0 else None
        detected = period is not None and snr >= detect_snr

        if verbose:
            status = "DETECTED" if detected else "below threshold"
            print(
                f"  [{code}] {status} ({used_location}.{chan}): period={period:.2f}s "
                f"freq={peak_freq:.4f}Hz SNR={snr:.1f}"
            )

        return StationDetection(code, period, peak_freq, snr, detected)

    except Exception as exc:
        return StationDetection(code, None, None, None, False, str(exc)[:200])


def consensus_period(
    detections: list[StationDetection],
) -> tuple[float | None, str]:
    """Aggregate detected stations into one consensus period and label."""
    detected = [
        detection
        for detection in detections
        if detection.detected and detection.period_s is not None
    ]
    if not detected:
        return None, "not detected (try --hours 24 or another day)"

    periods = np.array([detection.period_s for detection in detected])
    median_period = float(np.median(periods))
    spread = float(np.max(periods) - np.min(periods))

    if len(detected) >= 2 and spread <= 1.5:
        label = "high (multiple stations, tight agreement)"
    elif len(detected) >= 2:
        label = "medium (multiple stations, some spread)"
    else:
        label = "low (single station; confirm with a longer window)"

    return median_period, label


def detect_26s_microseism(
    hours: float = DEFAULT_HOURS,
    detect_snr: float = DEFAULT_DETECT_SNR,
    verbose: bool = False,
) -> Microseism26sResult:
    """Fetch recent waveforms and detect the ~26-second microseism line."""
    client = Client("EARTHSCOPE")
    end = UTCDateTime() - 300  # LHZ data can lag by a few minutes.
    start = end - hours * 3600

    print("Searching for the ~26 s microseism line")
    print(f"Window: {hours:g} hour(s) ending {end.datetime.replace(tzinfo=timezone.utc).isoformat()}")
    print(f"Channel: {CHANNEL}")
    print(f"Target band: {TARGET_LOW_HZ:.3f}-{TARGET_HIGH_HZ:.3f} Hz")
    print(f"SNR threshold: {detect_snr:g}")
    print(f"Stations: {', '.join(station for _, station, _, _ in STATIONS)}")
    print()

    detections = [
        analyze_station(client, net, sta, loc, chan, start, end, detect_snr, verbose)
        for net, sta, loc, chan in STATIONS
    ]
    period, confidence_label = consensus_period(detections)
    detected_count = sum(1 for detection in detections if detection.detected)

    return Microseism26sResult(
        detected_any=detected_count > 0,
        consensus_period_s=period,
        consensus_frequency_hz=(1.0 / period) if period else None,
        confidence_label=confidence_label,
        stations_detected=detected_count,
        stations_attempted=len(STATIONS),
        per_station=detections,
        timestamp_utc=datetime.now(timezone.utc),
    )


# -----------------------------------------------------------------------------
# Plotting
# -----------------------------------------------------------------------------
def save_psd_plot(
    client: Client,
    hours: float,
    out_path: Path,
) -> None:
    """Save a PSD plot for the first station that returns usable data."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("(matplotlib is not installed - skipping plot)")
        return

    end = UTCDateTime() - 300
    start = end - hours * 3600
    trace = None
    station_code = None

    for net, sta, loc, chan in STATIONS:
        locations = [loc]
        for fallback in LOCATION_FALLBACKS:
            if fallback not in locations:
                locations.append(fallback)
        for location in locations:
            try:
                st = client.get_waveforms(net, sta, location, chan, start, end)
                if len(st) == 0:
                    continue
                st.merge(method=1, fill_value=0)
                trace = st[0]
                station_code = f"{net}.{sta}.{location or '--'}"
                break
            except Exception:
                continue
        if trace is not None:
            break

    if trace is None or station_code is None:
        print("(no data available for plot)")
        return

    trace.detrend("demean")
    trace.detrend("linear")
    data = trace.data.astype(np.float64)
    sample_rate = float(trace.stats.sampling_rate)
    nperseg = int(min(8192, max(2048, len(data) // 4)))
    freqs, psd = welch(data, fs=sample_rate, nperseg=nperseg, noverlap=nperseg // 2)

    band = (freqs >= 0.02) & (freqs <= 0.06)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.semilogy(freqs[band], psd[band], color="#6FA8DC", linewidth=1)
    ax.axvspan(
        TARGET_LOW_HZ,
        TARGET_HIGH_HZ,
        alpha=0.2,
        color="#7FE5C8",
        label="26 s target band",
    )
    ax.axvline(
        TARGET_CENTER_HZ,
        color="#E8C87F",
        linestyle="--",
        linewidth=1,
        label="26 s center",
    )
    ax.set_title(f"{station_code} PSD")
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Power spectral density")
    ax.legend()
    ax.grid(alpha=0.3, which="both")
    fig.tight_layout()
    fig.savefig(out_path, dpi=110)
    plt.close(fig)
    print(f"Saved PSD plot -> {out_path}")


# -----------------------------------------------------------------------------
# Reporting and CLI
# -----------------------------------------------------------------------------
def print_report(result: Microseism26sResult, verbose: bool) -> None:
    print("=" * 60)
    print("  Earth Pulse - 26-second microseism detection")
    print(f"  {result.timestamp_utc.isoformat(timespec='seconds')}")
    print("=" * 60)

    if not result.detected_any:
        print("  RESULT: 26 s line not detected in this window.")
        print("  Quiet windows are normal; try --hours 24 or another day.")
    else:
        print("  RESULT: 26 s line detected")
        print(f"  Consensus period: {result.consensus_period_s:.2f} s")
        print(f"  Frequency:        {result.consensus_frequency_hz:.4f} Hz")
        print(f"  Confidence:       {result.confidence_label}")
        print(
            f"  Detected on:      {result.stations_detected}/"
            f"{result.stations_attempted} stations"
        )
        half_period = result.consensus_period_s / 2
        print()
        print(f"  Breathing rhythm: {half_period:.1f}s inhale / {half_period:.1f}s exhale")
        print("  Baseline rhythm:  13.0s inhale / 13.0s exhale")

    print()
    if verbose or not result.detected_any:
        print("Per-station detail:")
        for detection in result.per_station:
            if detection.error:
                print(f"  ERR {detection.code:10s} {detection.error}")
            elif detection.detected:
                print(
                    f"  OK  {detection.code:10s} {detection.period_s:5.2f}s "
                    f"SNR={detection.snr:4.1f} DETECTED"
                )
            else:
                period = f"{detection.period_s:5.2f}s" if detection.period_s else "n/a"
                snr = f"{detection.snr:.1f}" if detection.snr is not None else "n/a"
                print(f"  --  {detection.code:10s} {period:>7s} SNR={snr:>4s}")
        print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--hours", type=float, default=DEFAULT_HOURS,
                        help="Hours of LHZ data to fetch (default: 6.0)")
    parser.add_argument("--snr", type=float, default=DEFAULT_DETECT_SNR,
                        help="SNR threshold for detection (default: 3.0)")
    parser.add_argument("--plot", action="store_true",
                        help="Save a PSD diagnostic plot")
    parser.add_argument("--plot-path", type=Path, default=Path("earth_26s_psd.png"),
                        help="Output path for --plot (default: earth_26s_psd.png)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show per-station diagnostics")
    args = parser.parse_args()

    if args.hours <= 0:
        print("ERROR: --hours must be positive", file=sys.stderr)
        return 2
    if args.snr <= 0:
        print("ERROR: --snr must be positive", file=sys.stderr)
        return 2

    try:
        result = detect_26s_microseism(
            hours=args.hours,
            detect_snr=args.snr,
            verbose=args.verbose,
        )
    except Exception as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        return 2

    print_report(result, verbose=args.verbose)

    if args.plot:
        try:
            save_psd_plot(Client("EARTHSCOPE"), args.hours, args.plot_path)
        except Exception as exc:
            print(f"(plot failed: {exc})")

    return 0 if result.detected_any else 1


if __name__ == "__main__":
    sys.exit(main())
