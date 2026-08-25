#!/usr/bin/env python3
"""
Synthetic chamber fit demo — P2 L2.2 without lab hardware.

Generates incubation matrix T={20,32,38,44}C × RH={60,80}% × Tier
with known alpha=0.048 beta=0.008, adds 5% noise, then refits
alpha/beta via non-linear least squares. Reports R²/RMSE vs true.

Shows the refit pipeline is ready for real plate counts; no hardware needed.
Citation: [@labuza1993kinetics; @taoukis1997tti]
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import curve_fit


def phi_env(T, H, alpha, beta, T0=20, H0=60):
    return np.exp(alpha * np.maximum(0, T - T0) + beta * np.maximum(0, H - H0))


def main() -> None:
    rng = np.random.default_rng(42)
    alpha_true, beta_true = 0.048, 0.008
    Ts = np.array([20, 32, 38, 44] * 10)  # 4 temps ×10 repeats
    Hs = np.array([60, 80] * 20)
    # True Phi
    phi_true = phi_env(Ts, Hs, alpha_true, beta_true)
    # Add 5% noise
    phi_obs = phi_true * (1 + rng.normal(0, 0.05, size=len(phi_true)))
    phi_obs = np.clip(phi_obs, 1, 5)

    def model(X, alpha, beta):
        T, H = X
        return np.exp(alpha * np.maximum(0, T - 20) + beta * np.maximum(0, H - 60))

    popt, pcov = curve_fit(model, (Ts, Hs), phi_obs, p0=[0.04, 0.01], bounds=(0, [0.1, 0.05]))
    alpha_fit, beta_fit = popt
    phi_pred = model((Ts, Hs), alpha_fit, beta_fit)
    ss_res = np.sum((phi_obs - phi_pred) ** 2)
    ss_tot = np.sum((phi_obs - np.mean(phi_obs)) ** 2)
    r2 = 1 - ss_res / ss_tot
    rmse = np.sqrt(np.mean((phi_obs - phi_pred) ** 2))

    print(f"true  alpha={alpha_true:.4f} beta={beta_true:.4f}")
    print(f"fit   alpha={alpha_fit:.4f} beta={beta_fit:.4f}")
    print(f"R²={r2:.3f} RMSE={rmse:.3f} (target R²>0.95, RMSE<0.1 for field refit)")
    print("pass" if r2 > 0.95 and rmse < 0.1 else "fail — need more repeats/noise control")


if __name__ == "__main__":
    main()
