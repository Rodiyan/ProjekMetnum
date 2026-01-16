from flask import Flask, render_template, request, jsonify
import sympy as sp
import numpy as np
import matplotlib.pyplot as plt
import io
import base64
import re

app = Flask(__name__)

# ===============================
# VALIDASI DAN NORMALISASI FUNGSI
# ===============================
def normalize_function(func_str: str) -> str:
    """Normalisasi string fungsi menjadi format yang valid (untuk akar real)."""
    if not func_str or func_str.strip() == "":
        raise ValueError("Fungsi tidak boleh kosong")

    func = func_str.strip()
    func = re.sub(r"\s+", "", func)  # hapus spasi

    # Jika ada "=", ambil sisi kiri (mis: "x^2-4=0" -> "x^2-4")
    if "=" in func:
        func = func.split("=")[0].strip()

    # Ganti ^ dengan **
    func = func.replace("^", "**")

    # Jika hanya 'x' atau hanya angka atau tidak ada x, jadikan bentuk punya x agar tidak error di pemrosesan
    if func.lower() == "x":
        func = "x - 2"
    elif func.replace(".", "", 1).isdigit() and func.count(".") <= 1:
        # konstanta -> anggap x - konstanta
        func = f"x - {func}"
    elif "x" not in func and "X" not in func:
        func = f"x - ({func})"

    # Validasi karakter: ini simpel (bukan parser keamanan penuh),
    # tapi cukup untuk tugas fungsi matematika umum
    allowed_pattern = re.compile(r"^[0-9xX\.\+\-\*\/\(\)\[\]\{\}a-zA-Z_]+$")
    if not allowed_pattern.match(func):
        raise ValueError(
            "Karakter tidak valid dalam fungsi. Gunakan hanya: angka, x, +, -, *, /, **, (), sin, cos, tan, exp, log, sqrt"
        )

    return func

# ===============================
# UTILITAS: PARSING FUNGSI
# ===============================
def parse_function(func_str: str):
    """
    Return:
      f  : callable numpy
      df : callable numpy (turunan)
      func_sym : sympy expr
    """
    try:
        func_str = normalize_function(func_str)

        x = sp.symbols("x")

        # batasi sympify namespace agar tidak aneh-aneh
        allowed_locals = {
            "x": x,
            "sin": sp.sin,
            "cos": sp.cos,
            "tan": sp.tan,
            "exp": sp.exp,
            "log": sp.log,
            "sqrt": sp.sqrt,
            "pi": sp.pi,
            "E": sp.E,
        }

        func_sym = sp.sympify(func_str, locals=allowed_locals)
        df_sym = sp.diff(func_sym, x)

        f = sp.lambdify(x, func_sym, "numpy")
        df = sp.lambdify(x, df_sym, "numpy")

        # uji evaluasi sekali agar cepat ketahuan error
        _ = f(0.0)
        _ = df(0.0)

        return f, df, func_sym

    except Exception as e:
        raise ValueError(
            f"Fungsi tidak valid: '{func_str}'. Error: {str(e)}. "
            f"Contoh yang benar: x**2 - 4, sin(x) - 0.5, exp(x) - 2"
        )

# ===============================
# METODE BISECTION
# ===============================
def bisection_method(f, a, b, tol, max_iter):
    data = []
    steps = []

    a = float(a)
    b = float(b)

    try:
        fa = f(a)
        fb = f(b)
    except Exception as e:
        raise ValueError(f"Tidak dapat mengevaluasi fungsi di a/b. Error: {str(e)}")

    if not np.isfinite(fa) or not np.isfinite(fb):
        raise ValueError("Fungsi menghasilkan NaN/Inf. Coba interval lain.")

    # syarat utama bisection: tanda beda
    if fa * fb > 0:
        # beri beberapa saran interval sederhana
        suggestions = []
        test_intervals = [
            (-10, 10), (-5, 5), (-2, 2), (0, 2), (1, 3), (-3, -1)
        ]
        for ta, tb in test_intervals:
            try:
                fta, ftb = f(ta), f(tb)
                if np.isfinite(fta) and np.isfinite(ftb) and fta * ftb <= 0:
                    suggestions.append((ta, tb))
            except:
                pass

        if suggestions:
            sug_txt = "Coba interval berikut (tanda berbeda):\n"
            for i, (sa, sb) in enumerate(suggestions[:3], start=1):
                sug_txt += f"{i}. a={sa}, b={sb}\n"
            raise ValueError(f"f(a) dan f(b) memiliki tanda sama.\n\n{sug_txt}")
        raise ValueError("f(a) dan f(b) memiliki tanda sama. Coba interval lain.")

    steps.append({
        "step": 0,
        "title": "Inisialisasi",
        "description": f"Interval awal: [a, b] = [{a:.6f}, {b:.6f}]",
        "details": [
            f"f(a) = {fa:.6f}",
            f"f(b) = {fb:.6f}",
            f"f(a)×f(b) = {(fa*fb):.6f} < 0 ✓",
            "Akar berada di antara a dan b (tanda berbeda)."
        ],
        "status": "init"
    })

    c_old = None
    converged = False
    last_c = None

    for i in range(1, max_iter + 1):
        c = (a + b) / 2.0
        last_c = c

        try:
            fc = f(c)
        except:
            raise ValueError("Tidak dapat mengevaluasi fungsi di titik tengah c.")

        if not np.isfinite(fc):
            raise ValueError("f(c) menghasilkan NaN/Inf. Coba interval lain.")

        error = abs(c - c_old) if c_old is not None else abs(b - a)

        # simpan table
        data.append({
            "iterasi": i,
            "a": float(a),
            "b": float(b),
            "c": float(c),
            "f_c": float(fc),
            "error": float(error)
        })

        # step-by-step
        if fa * fc < 0:
            action = "f(a)×f(c) < 0 → akar di kiri → b = c"
            next_interval = f"[{a:.6f}, {c:.6f}]"
        else:
            action = "f(a)×f(c) > 0 → akar di kanan → a = c"
            next_interval = f"[{c:.6f}, {b:.6f}]"

        steps.append({
            "step": i,
            "title": f"Iterasi {i}",
            "description": f"c = {c:.6f}, f(c) = {fc:.6f}",
            "details": [
                f"c = (a+b)/2 = ({a:.6f}+{b:.6f})/2 = {c:.6f}",
                f"f(c) = {fc:.6f}",
                f"f(a)×f(c) = {fa:.6f}×{fc:.6f} = {(fa*fc):.6f}",
                action,
                f"Interval baru: {next_interval}",
                f"Error: {error:.10f}"
            ],
            "status": "calculating"
        })

        # kriteria konvergensi: error kecil ATAU |f(c)| kecil (opsional)
        if error <= tol or abs(fc) <= tol:
            converged = True
            steps.append({
                "step": i + 1,
                "title": "Konvergen! ✓",
                "description": f"Akar ditemukan: x ≈ {c:.6f}",
                "details": [
                    f"Error = {error:.10f}, toleransi = {tol}",
                    f"f(x) = {fc:.10f} ≈ 0"
                ],
                "status": "success"
            })
            break

        # update interval
        if fa * fc < 0:
            b = c
            fb = fc
        else:
            a = c
            fa = fc

        c_old = c

    if not converged:
        # NOTIF gagal
        fc_last = f(last_c) if last_c is not None else np.nan
        steps.append({
            "step": max_iter + 1,
            "title": "Tidak konvergen ✗",
            "description": f"Bisection tidak mencapai toleransi dalam {max_iter} iterasi.",
            "details": [
                f"Perkiraan terakhir: c ≈ {last_c:.6f}" if last_c is not None else "Tidak ada nilai c terakhir.",
                f"f(c) = {float(fc_last):.10f}" if np.isfinite(fc_last) else "f(c) tidak finite.",
                "Coba naikkan max_iter atau ubah interval awal."
            ],
            "status": "failed"
        })
        raise ValueError(
            f"Bisection tidak konvergen sampai {max_iter} iterasi. "
            f"c≈{last_c:.6f}, f(c)={float(fc_last):.6f}."
        )

    return data, last_c, steps

# ===============================
# METODE NEWTON-RAPHSON 
# ===============================
def newton_raphson_method(f, df, x0, tol, max_iter):
    data = []
    steps = []

    x_old = float(x0)

    # evaluasi awal
    fx0 = f(x_old)
    dfx0 = df(x_old)

    if not np.isfinite(fx0) or not np.isfinite(dfx0):
        raise ValueError("Nilai awal menghasilkan NaN/Inf. Coba x0 lain.")

    steps.append({
        "step": 0,
        "title": "Inisialisasi",
        "description": f"Tebakan awal: x₀ = {x_old:.6f}",
        "details": [
            f"f(x₀) = {fx0:.6f}",
            f"f'(x₀) = {dfx0:.6f}",
            "Rumus: x_{n+1} = x_n - f(x_n) / f'(x_n)"
        ],
        "status": "init"
    })

    converged = False
    last_x = x_old

    for i in range(1, max_iter + 1):
        fx = f(x_old)
        dfx = df(x_old)

        if not np.isfinite(fx) or not np.isfinite(dfx):
            raise ValueError("Hasil evaluasi NaN/Inf. Coba tebakan awal lain.")

        # hindari pembagian dengan turunan ~ 0
        if abs(dfx) < 1e-12:
            suggestions = [x_old + 0.5, x_old - 0.5, 1.0, -1.0, 2.0, -2.0]
            sug_txt = "Coba tebakan awal:\n" + "\n".join([f"• {s:.2f}" for s in suggestions[:3]])
            raise ValueError(f"Akar real tidak ditemukan. Fungsi (ini) tidak memiliki solusi di bilangan real.")

        x_new = x_old - fx / dfx

        if not np.isfinite(x_new):
            raise ValueError("Iterasi menghasilkan NaN/Inf (divergen). Coba x0 lain.")

        error = abs(x_new - x_old)
        fx_new = f(x_new)

        if not np.isfinite(fx_new):
            raise ValueError("f(x) menjadi NaN/Inf saat iterasi (divergen).")

        # Kriteria konvergensi (lebih aman): |Δx| kecil DAN |f(x)| kecil
        if (error <= tol) and (abs(fx_new) <= tol):
            converged = True

        steps.append({
            "step": i,
            "title": f"Iterasi {i}",
            "description": f"x = {x_new:.6f}, f(x) = {fx_new:.6f}",
            "details": [
                f"f(x_{i-1}) = f({x_old:.6f}) = {fx:.6f}",
                f"f'(x_{i-1}) = {dfx:.6f}",
                f"Δx = f(x)/f'(x) = {fx:.6f}/{dfx:.6f} = {(fx/dfx):.6f}",
                f"x_{i} = x_{i-1} - Δx = {x_old:.6f} - {(fx/dfx):.6f} = {x_new:.6f}",
                f"|Δx| = {error:.10f}",
                f"|f(x_i)| = {abs(fx_new):.10f}"
            ],
            "status": "converged" if converged else "calculating",
            "x_old": float(x_old),
            "x_new": float(x_new),
            "fx": float(fx),
            "dfx": float(dfx),
            "error": float(error)
        })

        data.append({
            "iterasi": i,
            "x": float(x_old),
            "f_x": float(fx),
            "df_x": float(dfx),
            "error": float(error)
        })

        last_x = x_new

        if converged:
            steps.append({
                "step": i + 1,
                "title": "Konvergen! ✓",
                "description": f"Akar ditemukan: x ≈ {x_new:.6f}",
                "details": [
                    f"|Δx| = {error:.10f} ≤ {tol}",
                    f"|f(x)| = {abs(fx_new):.10f} ≤ {tol}",
                    f"Solusi: x = {x_new:.6f}"
                ],
                "status": "success"
            })
            break

        x_old = x_new

    if not converged:
        fx_last = f(last_x)
        steps.append({
            "step": max_iter + 1,
            "title": "Tidak konvergen ✗",
            "description": f"Newton-Raphson tidak menemukan akar dalam {max_iter} iterasi.",
            "details": [
                f"Nilai terakhir: x ≈ {last_x:.6f}",
                f"f(x) = {float(fx_last):.10f}",
                "Kemungkinan: tebakan awal buruk, metode divergen, atau fungsi tidak punya akar real (contoh: x^2 + 2)."
            ],
            "status": "failed"
        })
        raise ValueError(
            f"Newton-Raphson tidak konvergen sampai {max_iter} iterasi. "
            f"x≈{last_x:.6f}, f(x)={float(fx_last):.6f}."
        )

    return data, last_x, steps

# ===============================
# GRAFIK FUNGSI
# ===============================
def generate_plot(f, root, a=None, b=None):
    # range plot
    if a is not None and b is not None:
        x_min = min(a, b, root) - 1
        x_max = max(a, b, root) + 1
    else:
        x_min = root - 3
        x_max = root + 3

    x_vals = np.linspace(x_min, x_max, 400)

    y_vals = []
    for x in x_vals:
        try:
            y = f(x)
            y_vals.append(y if np.isfinite(y) else np.nan)
        except:
            y_vals.append(np.nan)

    plt.figure(figsize=(10, 6))
    plt.axhline(y=0, linestyle="--", alpha=0.5)
    plt.axvline(x=0, linestyle="--", alpha=0.5)

    mask = ~np.isnan(y_vals)
    if np.any(mask):
        plt.plot(x_vals[mask], np.array(y_vals)[mask], linewidth=2, label="f(x)")

    # plot titik root (kalau finite)
    try:
        f_root = f(root)
        if np.isfinite(f_root):
            plt.plot(root, f_root, "ro", markersize=8, label=f"Root ≈ {root:.4f}")
    except:
        pass

    plt.xlabel("x")
    plt.ylabel("f(x)")
    plt.title("Grafik Fungsi")
    plt.grid(True, alpha=0.3)
    plt.legend()

    img = io.BytesIO()
    plt.savefig(img, format="png", dpi=100, bbox_inches="tight")
    plt.close()
    img.seek(0)

    return base64.b64encode(img.getvalue()).decode()

# ===============================
# ROUTE UTAMA
# ===============================
@app.route("/")
def index():
    return render_template("index.html")

# ===============================
# ROUTE HITUNG
# ===============================
@app.route("/calculate", methods=["POST"])
def calculate():
    try:
        data = request.json or {}

        required_fields = ["function", "method", "tolerance", "max_iter"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Field '{field}' harus diisi"}), 400

        func_str = data["function"]
        method = data["method"]
        tol = float(data["tolerance"])
        max_iter = int(data["max_iter"])

        if tol <= 0:
            return jsonify({"error": "Toleransi harus > 0"}), 400
        if max_iter <= 0:
            return jsonify({"error": "Maksimum iterasi harus > 0"}), 400

        # parse fungsi
        try:
            f, df, sym_func = parse_function(func_str)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

        # jalankan metode
        if method == "bisection":
            if "a" not in data or "b" not in data:
                return jsonify({"error": "Untuk metode bisection, a dan b harus diisi"}), 400
            a = float(data["a"])
            b = float(data["b"])
            if a >= b:
                return jsonify({"error": "a harus < b"}), 400

            try:
                iterations, root, steps = bisection_method(f, a, b, tol, max_iter)
                plot = generate_plot(f, root, a, b)
            except ValueError as e:
                return jsonify({"error": str(e), "steps": []}), 400

        elif method == "newton":
            if "x0" not in data:
                return jsonify({"error": "Untuk metode Newton, x0 harus diisi"}), 400
            x0 = float(data["x0"])

            try:
                iterations, root, steps = newton_raphson_method(f, df, x0, tol, max_iter)
                plot = generate_plot(f, root)
            except ValueError as e:
                return jsonify({"error": str(e), "steps": []}), 400

        else:
            return jsonify({"error": "Metode tidak valid"}), 400

        result = {
            "root": float(root),
            "f_root": float(f(root)),
            "iterations": iterations,
            "steps": steps,
            "plot": plot
        }

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": f"Kesalahan server: {str(e)}"}), 500

# ===============================
# MAIN
# ===============================
if __name__ == "__main__":
    app.run(debug=True, port=5000)
