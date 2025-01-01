"""
This Python file implements the Black-76 option pricing model.

Features:
1. Pricing European call and put options using the Black-76 model.
2. Numerically solving for the implied forward price given market data using numerical methods (e.g., fsolve).
3. Calculating option Greeks (Delta, Gamma, Vega, Theta, and Rho) for both call and put options.
4. Leveraging concurrent methods (e.g., ProcessPoolExecutor) to enable parallel computations for large datasets, significantly improving efficiency in batch processing.

The Black-76 model is widely used for pricing options on futures or forward contracts. It assumes the underlying asset follows a lognormal distribution and provides a robust framework for financial derivatives analysis.

2. `black_76_option`:
3. `objective`:
4. `solve_forward_price`: Uses numerical optimization to derive the implied forward price from market data.
5. `black_76_greeks`: Calculates option Greeks (Delta, Gamma, Vega, Theta, Rho) for a given option type and parameters.
"""

import pandas as pd
import numpy as np
from scipy.stats import norm
from scipy.optimize import fsolve
from concurrent.futures import ProcessPoolExecutor


# Computes the `d1` and `d2` parameters used in Black-76 pricing formulas.
def calculate_d1_d2(F, K, T, sigma):
    d1 = (np.log(F / K) + 0.5 * sigma**2 * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    return d1, d2

# Computes the price of call or put options based on input parameters
# (forward price, strike price, volatility, risk-free rate, and time to maturity).
def black_76_option(F, K, r, T, sigma, option_type="Call"):
    d1, d2 = calculate_d1_d2(F, K, T, sigma)
    if option_type == "Call":
        return np.exp(-r * T) * (F * norm.cdf(d1) - K * norm.cdf(d2))
    elif option_type == "Put":
        return np.exp(-r * T) * (K * norm.cdf(-d2) - F * norm.cdf(-d1))
    else:
        raise ValueError("Invalid option type. Use 'call' or 'put'.")

# Defines the objective function for numerically solving for the forward price.
def objective(F, market_price, K, r, T, sigma, option_type):
    return black_76_option(F, K, r, T, sigma, option_type) - market_price

# Uses numerical optimization to derive the implied forward price from market data.
def solve_forward_price(row):
    """
    Solve for the forward price for a given row in the DataFrame.
    """
    market_price = row["premium"]
    K = row["strike"]
    r = row["risk_free_rate"]
    T = row["time_to_maturity"]
    sigma = row["iv"]
    option_type = row["type"]

    # Initial guess
    F_initial_guess = K
    # Solve for forward price
    F_solution = fsolve(objective, F_initial_guess, args=(market_price, K, r, T, sigma, option_type))[0]
    return F_solution

# Parallel computation of forward prices
def parallel_forward_prices(df):
    with ProcessPoolExecutor() as executor:
        # Map each row to the solve_forward_price function
        forward_prices = list(executor.map(solve_forward_price, [row for _, row in df.iterrows()]))
    # Add the results back to the DataFrame
    df["forward_price"] = forward_prices
    return df


if __name__ == "__main__":
    # Load the DataFrame from the local pickle file
    df = pd.read_pickle("block_trade.pkl").iloc[:1000, :]

    # Compute forward prices in parallel
    forward_price = parallel_forward_prices(df)
    df["forward_price"] = parallel_forward_prices(df)

    # Save the updated DataFrame back to a pickle file
    df.to_pickle("block_trade_with_forward_prices.pkl")

    # Display the updated DataFrame
    print("Forward prices computed and saved successfully.")
    print(df)