"""
test_performance.py
===================
Benchmarks the RPi5 system across resolutions and MediaPipe model complexities.
Records per-second FPS and CPU temperature, then generates:
  - Bar charts: Average FPS and Temperature per configuration
  - Line plots:  Temperature vs Time for each MP model (with cooler-on marker)
  - CSV:         Raw data saved to performance_results.csv

Install dependency before running (inside your venv):
    pip install matplotlib

Usage
-----
  # Without Flask (run alone):
      python test_performance.py

  # With Flask running in the background:
      Open a second terminal → source pose-rec/bin/activate → python app.py
      Then run this script. It will prompt you before each Flask condition.

Configuration
-------------
  TEST_DURATION_S    : seconds per configuration (5s warmup + 30s measured)
  RESOLUTIONS        : list of (width, height) tuples to test
  MODEL_COMPLEXITIES : 0 = Lightweight, 2 = Heavy
  COOLER_THRESHOLD_C : temperature at which the RPi5 fan activates (~60°C)
"""

import subprocess
import time
import csv

import cv2
import mediapipe as mp
import numpy as np
import matplotlib.pyplot as plt
from picamera2 import Picamera2

mp_draw = mp.solutions.drawing_utils

# ─────────────────────────────────────────────
#  CONFIGURATION  ← edit these if needed
# ─────────────────────────────────────────────
TEST_DURATION_S     = 35          # total seconds per config (first 5 discarded)
WARMUP_S            = 5           # warmup seconds to discard
RESOLUTIONS         = [(640, 480), (1280, 720), (1680, 1050)]
MODEL_COMPLEXITIES  = [0, 2]      # 0 = lightweight, 2 = heavy
COOLER_THRESHOLD_C  = 50.0        # °C – RPi5 active cooler turn-on point (empirically verified)
RESULTS_CSV         = "performance_results.csv"
RAW_CSV             = "performance_raw.csv"

MODEL_LABELS = {0: "Lightweight", 2: "Heavy"}


# ─────────────────────────────────────────────
#  TEMPERATURE HELPER
# ─────────────────────────────────────────────
def read_temp() -> float:
    """Read CPU temperature via vcgencmd. Returns float in °C."""
    try:
        result = subprocess.run(
            ["vcgencmd", "measure_temp"],
            capture_output=True, text=True, timeout=2
        )
        # Output format: temp=52.3'C
        temp_str = result.stdout.strip().replace("temp=", "").replace("'C", "")
        return float(temp_str)
    except Exception:
        return -1.0


# ─────────────────────────────────────────────
#  SINGLE BENCHMARK RUN
# ─────────────────────────────────────────────
def run_benchmark(resolution: tuple, model_complexity: int, label: str) -> dict:
    """
    Run camera + MediaPipe loop for TEST_DURATION_S seconds.
    Returns a dict with avg_fps, avg_temp, and per-second time-series lists.
    """
    width, height = resolution
    mp_pose = mp.solutions.pose

    picam2 = Picamera2()
    cam_config = picam2.create_preview_configuration(
        main={"format": "RGB888", "size": (width, height)}
    )
    picam2.configure(cam_config)
    picam2.start()
    time.sleep(1)  # let camera settle

    fps_series  = []
    temp_series = []
    time_series = []

    print(f"  [{label}] Starting {TEST_DURATION_S}s run "
          f"({WARMUP_S}s warmup discarded)...")

    try:
        with mp_pose.Pose(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
            model_complexity=model_complexity
        ) as pose:

            run_start        = time.time()
            bucket_start     = time.time()
            frames_in_bucket = 0
            elapsed_buckets  = 0
            display_fps      = 0.0        # updated each second for the overlay
            landmark_vis_thresh = 0.7     # matches main_v2.py

            while True:
                elapsed = time.time() - run_start
                if elapsed >= TEST_DURATION_S:
                    break

                # capture and process one frame
                frame = picam2.capture_array()
                frame.flags.writeable = False
                results = pose.process(frame)
                frame.flags.writeable = True

                # ── Replicate main_v2.py display conditions ──────────────────
                # 1. Draw skeleton before flipping (same order as main_v2.py)
                if results.pose_landmarks:
                    landmarks = results.pose_landmarks.landmark
                    avg_vis = sum(lm.visibility for lm in landmarks) / len(landmarks)
                    if avg_vis > landmark_vis_thresh:
                        mp_draw.draw_landmarks(
                            frame,
                            results.pose_landmarks,
                            mp.solutions.pose.POSE_CONNECTIONS
                        )

                # 2. Flip for mirror view (same as main_v2.py)
                frame = cv2.flip(frame, 1)

                # 3. UI overlay (after flip, same as main_v2.py)
                if results.pose_landmarks:
                    # info box background
                    cv2.rectangle(frame, (0, 0), (220, 80), (245, 117, 16), -1)
                    cv2.putText(frame, "BENCHMARK MODE", (8, 25),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                    cv2.putText(frame, label, (8, 55),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                    # FPS counter (top right, same position as main_v2.py)
                    cv2.putText(frame, f"FPS: {int(display_fps)}",
                                (width - 90, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    # in-frame / step-back prompt
                    if avg_vis > landmark_vis_thresh:
                        cv2.putText(frame, "IN FRAME", (10, 75),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    else:
                        cv2.putText(frame, "STEP BACK AND CENTER YOURSELF",
                                    (40, 240),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

                cv2.imshow("Benchmark Preview", frame)
                if cv2.waitKey(1) & 0xFF == 27:   # ESC to skip current config
                    break
                # ─────────────────────────────────────────────────────────────

                frames_in_bucket += 1

                # record one-second buckets
                if time.time() - bucket_start >= 1.0:
                    bucket_fps  = frames_in_bucket / (time.time() - bucket_start)
                    bucket_temp = read_temp()
                    display_fps = bucket_fps          # update overlay value
                    elapsed_buckets += 1

                    if elapsed_buckets > WARMUP_S:   # discard warmup period
                        t = elapsed_buckets - WARMUP_S
                        fps_series.append(bucket_fps)
                        temp_series.append(bucket_temp)
                        time_series.append(t)

                    frames_in_bucket = 0
                    bucket_start = time.time()

    except KeyboardInterrupt:
        print(f"\n  [{label}] Interrupted by user — partial data kept.")

    finally:
        # stop() pauses the stream but leaves the device acquired.
        # close() fully releases the hardware so the next run can open it.
        picam2.stop()
        picam2.close()
        cv2.destroyAllWindows()
        time.sleep(2)  # short pause to let the driver fully reset

    avg_fps  = float(np.mean(fps_series))  if fps_series  else 0.0
    avg_temp = float(np.mean(temp_series)) if temp_series else 0.0

    print(f"  [{label}] Done — Avg FPS: {avg_fps:.1f}  Avg Temp: {avg_temp:.1f}°C")

    return {
        "label":      label,
        "resolution": f"{width}x{height}",
        "model":      MODEL_LABELS[model_complexity],
        "complexity": model_complexity,
        "avg_fps":    avg_fps,
        "avg_temp":   avg_temp,
        "fps_series": fps_series,
        "temp_series":temp_series,
        "time_series":time_series,
    }


# ─────────────────────────────────────────────
#  MAIN TEST LOOP
# ─────────────────────────────────────────────
def main():
    all_results = []
    raw_rows    = []

    flask_states = [False, True]

    for complexity in MODEL_COMPLEXITIES:
        model_name = MODEL_LABELS[complexity]
        for flask_running in flask_states:
            flask_label = "Flask ON" if flask_running else "Flask OFF"

            print("\n" + "="*60)
            print(f"  Model: {model_name}   |   {flask_label}")
            print("="*60)

            if flask_running:
                input("  >>> Start 'python app.py' in your other terminal, "
                      "then press ENTER to continue...")
            else:
                input("  >>> Ensure Flask is NOT running, "
                      "then press ENTER to continue...")

            for res in RESOLUTIONS:
                label = f"{model_name} | {res[0]}x{res[1]} | {flask_label}"
                result = run_benchmark(res, complexity, label)
                result["flask"] = flask_running
                all_results.append(result)

                for i, t in enumerate(result["time_series"]):
                    raw_rows.append({
                        "model":      model_name,
                        "resolution": result["resolution"],
                        "flask":      flask_label,
                        "elapsed_s":  t,
                        "fps":        round(result["fps_series"][i], 2),
                        "temp_c":     result["temp_series"][i],
                    })

    # save CSVs
    with open(RESULTS_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "model", "resolution", "flask", "avg_fps", "avg_temp"
        ])
        writer.writeheader()
        for r in all_results:
            writer.writerow({
                "model":      r["model"],
                "resolution": r["resolution"],
                "flask":      "yes" if r["flask"] else "no",
                "avg_fps":    round(r["avg_fps"], 2),
                "avg_temp":   round(r["avg_temp"], 2),
            })

    with open(RAW_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "model", "resolution", "flask", "elapsed_s", "fps", "temp_c"
        ])
        writer.writeheader()
        writer.writerows(raw_rows)

    print(f"\nResults saved → {RESULTS_CSV}  and  {RAW_CSV}")

    plot_bar_charts(all_results)
    plot_temp_vs_time(all_results)
    print("Plots saved.")


# ─────────────────────────────────────────────
#  PLOT 1 – BAR CHARTS (FPS + Temperature)
# ─────────────────────────────────────────────
def plot_bar_charts(results: list):
    for complexity in MODEL_COMPLEXITIES:
        model_name = MODEL_LABELS[complexity]
        subset = [r for r in results if r["complexity"] == complexity]

        labels    = [f"{r['resolution']}\n{'Flask ON' if r['flask'] else 'Flask OFF'}"
                     for r in subset]
        fps_vals  = [r["avg_fps"]  for r in subset]
        temp_vals = [r["avg_temp"] for r in subset]

        x     = np.arange(len(labels))
        width = 0.5

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        fig.suptitle(f"Performance Benchmarks — {model_name} MediaPipe Model",
                     fontsize=14, fontweight="bold")

        # FPS bar
        bars1 = ax1.bar(x, fps_vals, width, color="#4C9BE8", edgecolor="black")
        ax1.axhline(y=15, color="red", linestyle="--", linewidth=1.5,
                    label="15 FPS target")
        ax1.set_title("Average FPS")
        ax1.set_ylabel("Frames per Second")
        ax1.set_xticks(x)
        ax1.set_xticklabels(labels, fontsize=9)
        ax1.legend()
        ax1.set_ylim(0, max(fps_vals) * 1.25 if fps_vals else 30)
        for bar, val in zip(bars1, fps_vals):
            ax1.text(bar.get_x() + bar.get_width() / 2,
                     bar.get_height() + 0.3,
                     f"{val:.1f}", ha="center", va="bottom", fontsize=9)

        # Temperature bar
        bars2 = ax2.bar(x, temp_vals, width, color="#E87C4C", edgecolor="black")
        ax2.axhline(y=COOLER_THRESHOLD_C, color="blue", linestyle="--",
                    linewidth=1.5,
                    label=f"Cooler threshold ({COOLER_THRESHOLD_C:.0f}°C)")
        ax2.set_title("Average CPU Temperature")
        ax2.set_ylabel("Temperature (°C)")
        ax2.set_xticks(x)
        ax2.set_xticklabels(labels, fontsize=9)
        ax2.legend()
        ax2.set_ylim(0, max(temp_vals) * 1.2 if temp_vals else 80)
        for bar, val in zip(bars2, temp_vals):
            ax2.text(bar.get_x() + bar.get_width() / 2,
                     bar.get_height() + 0.3,
                     f"{val:.1f}°C", ha="center", va="bottom", fontsize=9)

        plt.tight_layout()
        fname = f"bar_chart_{model_name.lower()}.png"
        plt.savefig(fname, dpi=150)
        plt.close()
        print(f"  Saved: {fname}")


# ─────────────────────────────────────────────
#  PLOT 2 – TEMPERATURE vs TIME LINE PLOTS
# ─────────────────────────────────────────────
def plot_temp_vs_time(results: list):
    colors = {
        "640x480":   "#E84C4C",
        "1280x720":  "#4C9BE8",
        "1680x1050": "#4CE87C",
    }

    for complexity in MODEL_COMPLEXITIES:
        model_name = MODEL_LABELS[complexity]

        # Flask OFF runs show the sustained warm-up curve most clearly
        subset = [r for r in results
                  if r["complexity"] == complexity and not r["flask"]]

        if not subset:
            continue

        fig, axes = plt.subplots(1, len(subset), figsize=(6 * len(subset), 5),
                                 sharey=True)
        if len(subset) == 1:
            axes = [axes]  # keep iterable if only one resolution was tested

        fig.suptitle(
            f"CPU Temperature vs Time — {model_name} MediaPipe Model (Flask OFF)",
            fontsize=13, fontweight="bold"
        )

        for ax, result in zip(axes, subset):
            res   = result["resolution"]
            times = result["time_series"]
            temps = result["temp_series"]
            color = colors.get(res, "grey")

            ax.plot(times, temps, color=color, linewidth=2, label=res)
            ax.axhline(y=COOLER_THRESHOLD_C, color="red", linestyle="--",
                       linewidth=1.2, label=f"Cooler ON ({COOLER_THRESHOLD_C:.0f}°C)")

            # annotate first time temperature crosses cooler threshold
            cooler_triggered = False
            for t, temp in zip(times, temps):
                if temp >= COOLER_THRESHOLD_C and not cooler_triggered:
                    ax.axvline(x=t, color="red", linestyle="-", linewidth=1.5)
                    ax.annotate(
                        f"Cooler\nON\n~{t}s",
                        xy=(t, temp),
                        xytext=(t + 1, temp - 4),
                        fontsize=7,
                        color="red",
                        arrowprops=dict(arrowstyle="->", color="red")
                    )
                    cooler_triggered = True

            ax.set_title(f"{res}", fontsize=11)
            ax.set_xlabel("Time (s)")
            if ax is axes[0]:
                ax.set_ylabel("Temperature (°C)")
            ax.set_ylim(30, 90)
            ax.legend(fontsize=8)
            ax.grid(True, alpha=0.3)

        plt.tight_layout()
        fname = f"temp_vs_time_{model_name.lower()}.png"
        plt.savefig(fname, dpi=150)
        plt.close()
        print(f"  Saved: {fname}")


# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("\n  RPi5 Performance Benchmark")
    print("  ===========================")
    print(f"  Duration per config : {TEST_DURATION_S}s "
          f"({WARMUP_S}s warmup + {TEST_DURATION_S - WARMUP_S}s measured)")
    print(f"  Resolutions         : {RESOLUTIONS}")
    print(f"  Models              : {[MODEL_LABELS[c] for c in MODEL_COMPLEXITIES]}")
    print(f"  Flask conditions    : ON and OFF")
    print(f"  Cooler marker at    : {COOLER_THRESHOLD_C}°C")
    print()
    print("  Before running: pip install matplotlib")
    print()
    main()
