#!/usr/bin/env python3
"""
earth_period.py — Earth Pulse: proof-of-concept Earth rhythm extractor.

Pulls 1 hour of seismic data from several IRIS FDSN stations, bandpass-filters
to the primary microseism band, and extracts the dominant period of Earth's
natural oscillation.

Usage:
    pip install obspy matplotlib numpy
    python earth_period.py                  # default: last hour, 5 stations
    python earth_period.py --hours 6        # longer window = more stable
    python earth_period.py --plot           # save spectrum & waveform plots
    python earth_period.py --verbose        # show per-station details

Expected output:
    Earth period:   25.34 seconds
    Confidence:     0.87 (high)
    Stations used:  3/5

This is a research script, not production code. The production version will
live on a server with proper error handling, retries, and persistence.

References:
    Primary microseism: 10–20 s period (0.05–0.10 Hz)
    Secondary microseism: 5–10 s period (0.10–0.20 Hz) — IGNORED here
    IRIS FDSN web service: https://service.iris.edu/fdsnws/
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

try:
    from obspy import UTCDateTime
    from obspy.clients.fdsn import Client
    from obspy.signal.filter import bandpass
except ImportError:
    print(
        "ERROR: obspy is not installed.\n"
        "Install with:  pip install obspy matplotlib numpy",
        file=sys.stderr,
    )
    sys.exit(1)


# -----------------------------------------------------------------------------
# Configuration — global, broadband, well-maintained stations.
# Each is (network, station, location, channel).
# BHZ = broadband, vertical component, ~20-40 Hz sampling.
# Spread across continents so we are robust to regional outages.
# -----------------------------------------------------------------------------
STATIONS = [
    ("IU", "ANMO", "00", "BHZ"),   # Albuquerque, NM, USA
    ("IU", "COLA", "00", "BHZ"),   # College Outpost, Alaska
    ("II", "BFO",  "00", "BHZ"),   # Black Forest, Germany
    ("IU", "MAJO", "00", "BHZ"),   # Matsushiro, Japan
    ("IU", "CASY", "00", "BHZ"),   # Casey, Antarctica
]

# Primary microseism band only. We exclude secondary (5-10s) because it's noisier
# and breathing at 5s exhale is uncomfortably fast.
BAND_LOW_HZ = 0.04   # 25 s period
BAND_HIGH_HZ = 0.10  # 10 s period

# Confidence thresholds for cross-station agreement (in seconds).
GOOD_AGREEMENT_S = 1.5   # all stations within ±1.5 s → high confidence
OK_AGREEMENT_S = 3.0     # within ±3 s → medium confidence


# -----------------------------------------------------------------------------
# Data structures
# -----------------------------------------------------------------------------
@dataclass
class StationResult:
    code: str
    period_s: float | None
    frequency_hz: float | None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.period_s is not None


@dataclass
class EarthRhythm:
    period_s: float
    frequency_hz: float
    confidence: float
    confidence_label: str
    stations_used: int
    stations_attempted: int
    per_station: list[StationResult]
    timestamp_utc: datetime


# -----------------------------------------------------------------------------
# Core algorithm
# -----------------------------------------------------------------------------
def fetch_and_analyze(
    client: Client,
    net: str,
    sta: str,
    loc: str,
    chan: str,
    start: UTCDateTime,
    end: UTCDateTime,
    verbose: bool = False,
) -> StationResult:
    """Fetch waveform from one station, return its dominant period.

    Returns a StationResult with either period_s set OR error set.
    """
    code = f"{net}.{sta}"
    try:
        if verbose:
            print(f"  [{code}] fetching {start.isoformat()} -> {end.isoformat()}")
        st = client.get_waveforms(
            network=net,
            station=sta,
            location=loc,
            channel=chan,
            starttime=start,
            endtime=end,
        )
        if len(st) == 0:
            return StationResult(code, None, None, error="no data returned")

        tr = st[0]
        # Remove mean, detrend, then bandpass. obspy convenience methods.
        tr.detrend("demean")
        tr.detrend("linear")
        tr.filter(
            "bandpass",
            freqmin=BAND_LOW_HZ,
            freqmax=BAND_HIGH_HZ,
            corners=4,
            zerophase=True,
        )

        # FFT to find dominant frequency in the band.
        data = tr.data.astype(np.float64)
        n = len(data)
        if n < 1024:
            return StationResult(code, None, None, error=f"too few samples ({n})")

        fs = tr.stats.sampling_rate  # Hz
        freqs = np.fft.rfftfreq(n, d=1.0 / fs)
        spectrum = np.abs(np.fft.rfft(data))

        # Mask to our band only — we don't care about peaks outside it.
        mask = (freqs >= BAND_LOW_HZ) & (freqs <= BAND_HIGH_HZ)
        band_freqs = freqs[mask]
        band_spec = spectrum[mask]

        if len(band_spec) == 0:
            return StationResult(code, None, None, error="empty band after masking")

        peak_idx = int(np.argmax(band_spec))
        peak_freq = float(band_freqs[peak_idx])
        if peak_freq <= 0:
            return StationResult(code, None, None, error="zero peak frequency")

        period = 1.0 / peak_freq

        if verbose:
            print(f"  [{code}] dominant period = {period:.2f} s "
                  f"(freq {peak_freq:.4f} Hz)")

        return StationResult(code, period, peak_freq)

    except Exception as e:
        # Catch broadly — IRIS occasionally returns weird errors per station.
        # We tolerate per-station failure as long as enough others succeed.
        return StationResult(code, None, None, error=str(e)[:200])


def consensus_period(results: list[StationResult]) -> tuple[float, float, str]:
    """Aggregate per-station periods into one consensus value + confidence.

    Strategy:
      - Take the median (robust to outliers).
      - Confidence = how tightly stations agree.
    """
    periods = np.array([r.period_s for r in results if r.ok])
    if len(periods) == 0:
        return float("nan"), 0.0, "none"
    if len(periods) == 1:
        return float(periods[0]), 0.3, "low (single station)"

    median = float(np.median(periods))
    # Median absolute deviation, robust spread measure.
    spread = float(np.median(np.abs(periods - median)))

    if spread <= GOOD_AGREEMENT_S and len(periods) >= 3:
        confidence = min(1.0, 0.6 + 0.4 * (1 - spread / GOOD_AGREEMENT_S))
        label = "high"
    elif spread <= OK_AGREEMENT_S:
        confidence = max(0.4, 0.6 - 0.2 * (spread - GOOD_AGREEMENT_S))
        label = "medium"
    else:
        confidence = 0.3
        label = "low (stations disagree)"

    return median, confidence, label


def compute_earth_rhythm(
    hours: float = 1.0,
    verbose: bool = False,
) -> EarthRhythm:
    """Main entry point. Returns EarthRhythm computed from configured stations."""
    client = Client("IRIS")
    end = UTCDateTime() - 60  # 1-minute buffer; very recent data may not be available
    start = end - hours * 3600

    print(f"Fetching {hours:g} hour(s) of data ending at "
          f"{end.datetime.replace(tzinfo=timezone.utc).isoformat()}")
    print(f"Using stations: {', '.join(s[1] for s in STATIONS)}")
    print()

    results: list[StationResult] = []
    for (net, sta, loc, chan) in STATIONS:
        r = fetch_and_analyze(client, net, sta, loc, chan, start, end, verbose)
        results.append(r)

    period, confidence, label = consensus_period(results)
    used = sum(1 for r in results if r.ok)

    return EarthRhythm(
        period_s=period,
        frequency_hz=(1.0 / period) if period and not np.isnan(period) else float("nan"),
        confidence=confidence,
        confidence_label=label,
        stations_used=used,
        stations_attempted=len(STATIONS),
        per_station=results,
        timestamp_utc=datetime.now(timezone.utc),
    )


# -----------------------------------------------------------------------------
# Plotting (optional, for visual sanity check)
# -----------------------------------------------------------------------------
def save_diagnostic_plot(
    client: Client,
    hours: float,
    out_path: Path,
) -> None:
    """Save a 2-panel plot: waveform (filtered) + spectrum for one station.
    Helps you visually confirm there's a real signal, not just noise.
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("(matplotlib not installed - skipping plot)")
        return

    net, sta, loc, chan = STATIONS[0]
    end = UTCDateTime() - 60
    start = end - hours * 3600

    st = client.get_waveforms(net, sta, loc, chan, start, end)
    if len(st) == 0:
        print("(no data for plot)")
        return

    tr = st[0]
    tr.detrend("demean")
    tr.detrend("linear")
    tr.filter("bandpass", freqmin=BAND_LOW_HZ, freqmax=BAND_HIGH_HZ,
              corners=4, zerophase=True)

    data = tr.data.astype(np.float64)
    fs = tr.stats.sampling_rate
    t = np.arange(len(data)) / fs

    freqs = np.fft.rfftfreq(len(data), d=1.0 / fs)
    spectrum = np.abs(np.fft.rfft(data))
    mask = (freqs >= 0.02) & (freqs <= 0.20)  # wider for visualization

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6))

    ax1.plot(t, data, linewidth=0.5, color="#7FE5C8")
    ax1.set_title(f"{sta} - bandpass filtered ({BAND_LOW_HZ}-{BAND_HIGH_HZ} Hz)")
    ax1.set_xlabel("seconds")
    ax1.set_ylabel("amplitude")
    ax1.grid(alpha=0.3)

    ax2.plot(freqs[mask], spectrum[mask], color="#6FA8DC")
    ax2.axvspan(BAND_LOW_HZ, BAND_HIGH_HZ, alpha=0.15, color="green",
                label="primary microseism band")
    ax2.set_title("Spectrum (FFT magnitude)")
    ax2.set_xlabel("Hz")
    ax2.set_ylabel("|FFT|")
    ax2.legend()
    ax2.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(out_path, dpi=110)
    plt.close()
    print(f"Saved diagnostic plot → {out_path}")


# -----------------------------------------------------------------------------
# Pretty printing
# -----------------------------------------------------------------------------
def print_report(rhythm: EarthRhythm, verbose: bool) -> None:
    print("=" * 56)
    print(f"  Earth Pulse - calibration report")
    print(f"  {rhythm.timestamp_utc.isoformat(timespec='seconds')}")
    print("=" * 56)
    if np.isnan(rhythm.period_s):
        print("FAILED: no usable data from any station.")
    else:
        print(f"  Earth period:    {rhythm.period_s:.2f} seconds")
        print(f"  Frequency:       {rhythm.frequency_hz:.4f} Hz")
        print(f"  Confidence:      {rhythm.confidence:.2f} "
              f"({rhythm.confidence_label})")
        print(f"  Stations used:   {rhythm.stations_used}/"
              f"{rhythm.stations_attempted}")
        # Breathing recommendation
        half = rhythm.period_s / 2
        print()
        print(f"  -> Recommended breathing: "
              f"{half:.1f}s inhale / {half:.1f}s exhale")
        # Compare to 13/13 baseline
        delta = rhythm.period_s - 26.0
        print(f"  -> Deviation from 13/13 baseline (26 s): {delta:+.2f} s")
    print()

    if verbose or rhythm.confidence < 0.6:
        print("Per-station detail:")
        for r in rhythm.per_station:
            if r.ok:
                print(f"  OK  {r.code:10s} period = {r.period_s:5.2f} s")
            else:
                print(f"  ERR {r.code:10s} {r.error}")
        print()


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--hours", type=float, default=1.0,
                        help="Hours of data to fetch (default: 1.0)")
    parser.add_argument("--plot", action="store_true",
                        help="Save diagnostic waveform + spectrum plot")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show per-station diagnostics")
    args = parser.parse_args()

    try:
        rhythm = compute_earth_rhythm(hours=args.hours, verbose=args.verbose)
    except Exception as e:
        print(f"FATAL: {e}", file=sys.stderr)
        return 2

    print_report(rhythm, verbose=args.verbose)

    if args.plot:
        try:
            save_diagnostic_plot(Client("IRIS"), args.hours,
                                 Path("earth_period_plot.png"))
        except Exception as e:
            print(f"(plot failed: {e})")

    return 0 if not np.isnan(rhythm.period_s) else 1


if __name__ == "__main__":
    sys.exit(main())
