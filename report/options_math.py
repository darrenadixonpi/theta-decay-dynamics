"""
Core options math for Theta Decay Dynamics Report.
Black-Scholes and Merton jump-diffusion pricing, theta computation, and Monte Carlo.
"""
import numpy as np
from scipy.stats import norm
from math import log, sqrt, exp, factorial

def bs_d1(S, K, r, sigma, T):
    if T <= 0 or sigma <= 0: return 0.0
    return (log(S/K) + (r + 0.5*sigma**2)*T) / (sigma*sqrt(T))

def bs_d2(S, K, r, sigma, T):
    return bs_d1(S, K, r, sigma, T) - sigma*sqrt(T)

def bs_call_price(S, K, r, sigma, T):
    if T <= 1e-10: return max(S - K, 0.0)
    d1 = bs_d1(S, K, r, sigma, T)
    d2 = bs_d2(S, K, r, sigma, T)
    return S*norm.cdf(d1) - K*exp(-r*T)*norm.cdf(d2)

def bs_put_price(S, K, r, sigma, T):
    if T <= 1e-10: return max(K - S, 0.0)
    d1 = bs_d1(S, K, r, sigma, T)
    d2 = bs_d2(S, K, r, sigma, T)
    return K*exp(-r*T)*norm.cdf(-d2) - S*norm.cdf(-d1)

def bs_theta_put(S, K, r, sigma, T):
    if T <= 1e-10: return 0.0
    d1 = bs_d1(S, K, r, sigma, T)
    d2 = bs_d2(S, K, r, sigma, T)
    return -S * norm.pdf(d1) * sigma / (2*sqrt(T)) + r * K * exp(-r*T) * norm.cdf(-d2)

def bs_theta_call(S, K, r, sigma, T):
    if T <= 1e-10: return 0.0
    d1 = bs_d1(S, K, r, sigma, T)
    d2 = bs_d2(S, K, r, sigma, T)
    return -S * norm.pdf(d1) * sigma / (2*sqrt(T)) - r * K * exp(-r*T) * norm.cdf(d2)

def short_put_theta(S, K, r, sigma, T):
    return -bs_theta_put(S, K, r, sigma, T) / 365.0

def short_call_theta(S, K, r, sigma, T):
    return -bs_theta_call(S, K, r, sigma, T) / 365.0

def theta_peak_dte(S, K, sigma):
    log_m = abs(log(S/K))
    if log_m < 0.001: return 0
    return (log_m**2) / (sigma**2) * 365

def bs_gamma(S, K, r, sigma, T):
    if T <= 1e-10: return 0.0
    d1 = bs_d1(S, K, r, sigma, T)
    return norm.pdf(d1) / (S * sigma * sqrt(T))

def bs_vega(S, K, r, sigma, T):
    if T <= 1e-10: return 0.0
    d1 = bs_d1(S, K, r, sigma, T)
    return S * norm.pdf(d1) * sqrt(T)

def bs_vomma(S, K, r, sigma, T):
    """d²V/dσ² — convexity of option value in implied vol."""
    if T <= 1e-10 or sigma <= 0: return 0.0
    d1 = bs_d1(S, K, r, sigma, T)
    d2 = bs_d2(S, K, r, sigma, T)
    vega = bs_vega(S, K, r, sigma, T)
    return vega * d1 * d2 / sigma

def bs_vanna(S, K, r, sigma, T):
    """d²V/dS dσ — cross sensitivity of delta to vol (and vega to spot)."""
    if T <= 1e-10 or sigma <= 0: return 0.0
    d1 = bs_d1(S, K, r, sigma, T)
    d2 = bs_d2(S, K, r, sigma, T)
    return -norm.pdf(d1) * d2 / sigma

def bs_charm_put(S, K, r, sigma, T):
    """dΔ/dt for puts — delta decay (per year)."""
    if T <= 1e-10 or sigma <= 0: return 0.0
    d1 = bs_d1(S, K, r, sigma, T)
    d2 = bs_d2(S, K, r, sigma, T)
    return -norm.pdf(d1) * (2 * r * T - d2 * sigma * sqrt(T)) / (2 * T * sigma * sqrt(T)) + r * exp(-r * T) * norm.cdf(-d2)

def bs_charm_call(S, K, r, sigma, T):
    if T <= 1e-10 or sigma <= 0: return 0.0
    d1 = bs_d1(S, K, r, sigma, T)
    d2 = bs_d2(S, K, r, sigma, T)
    return -norm.pdf(d1) * (2 * r * T - d2 * sigma * sqrt(T)) / (2 * T * sigma * sqrt(T)) - r * exp(-r * T) * norm.cdf(d2)

def bs_speed(S, K, r, sigma, T):
    """dΓ/dS — rate of change of gamma with spot."""
    if T <= 1e-10 or sigma <= 0: return 0.0
    d1 = bs_d1(S, K, r, sigma, T)
    gamma = bs_gamma(S, K, r, sigma, T)
    return -gamma / S * (1.0 + d1 / (sigma * sqrt(T)))

def bs_delta_put(S, K, r, sigma, T):
    if T <= 1e-10: return -1.0 if S < K else 0.0
    return norm.cdf(bs_d1(S, K, r, sigma, T)) - 1.0

def merton_price(S, K, r, sigma_d, T, lam, mu_j, sigma_j, n_terms=20, option_type='put'):
    lam_prime = lam * exp(mu_j + 0.5*sigma_j**2)
    price = 0.0
    for n in range(n_terms):
        sigma_n = sqrt(sigma_d**2 + n*sigma_j**2/T) if T > 0 else sigma_d
        r_n = r - lam*(exp(mu_j + 0.5*sigma_j**2) - 1) + n*(mu_j + 0.5*sigma_j**2)/T if T > 0 else r
        w = exp(-lam_prime*T) * (lam_prime*T)**n / factorial(n)
        price += w * (bs_put_price(S, K, r_n, sigma_n, T) if option_type == 'put'
                      else bs_call_price(S, K, r_n, sigma_n, T))
    return price

def short_put_theta_merton(S, K, r, sigma_d, T, lam, mu_j, sigma_j):
    if T <= 1e-5: return 0.0
    dT = 1e-5
    V1 = merton_price(S, K, r, sigma_d, T, lam, mu_j, sigma_j)
    V2 = merton_price(S, K, r, sigma_d, T - dT, lam, mu_j, sigma_j)
    return -((V2 - V1) / dT) / 365.0

def compute_transaction_costs(premium, spread_pct, contracts=1, commission=0.65):
    return premium * spread_pct * contracts * 100 * 2 + commission * contracts * 2
