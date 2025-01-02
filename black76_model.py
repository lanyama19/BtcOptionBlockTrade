import pandas as pd
import numpy as np
from scipy.stats import norm
from scipy.optimize import fsolve
from concurrent.futures import ProcessPoolExecutor
import os


# Computes the `d1` and `d2` parameters used in Black-76 pricing formulas.
def calculate_d1_d2(F, K, T, sigma):
    d1 = (np.log(F / K) + 0.5 * sigma**2 * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    return d1, d2


# Computes the price of call or put options based on input parameters.
def black_76_option(F, K, r, T, sigma, option_type="Call"):
    d1, d2 = calculate_d1_d2(F, K, T, sigma)
    if option_type == "Call":
        return np.exp(-r * T) * (F * norm.cdf(d1) - K * norm.cdf(d2))
    elif option_type == "Put":
        return np.exp(-r * T) * (K * norm.cdf(-d2) - F * norm.cdf(-d1))
    else:
        raise ValueError("Invalid option type. Use 'Call' or 'Put'.")


# Defines the objective function for numerically solving for the forward price.
def objective(F, market_price, K, r, T, sigma, option_type):
    return black_76_option(F, K, r, T, sigma, option_type) - market_price


# Uses numerical optimization to derive the implied forward price from market data.
def solve_forward_price(row_dict):
    """
    Solve for the forward price for a given dictionary row.
    """
    try:
        market_price = row_dict["premium"]
        K = row_dict["strike"]
        r = row_dict["risk_free_rate"]
        T = row_dict["time_to_maturity"]
        sigma = row_dict["iv"]
        option_type = row_dict["type"]

        # Initial guess
        F_initial_guess = K

        # Solve for forward price
        F_solution = fsolve(objective, F_initial_guess, args=(market_price, K, r, T, sigma, option_type))[0]
        return {"unique_id": row_dict["unique_id"], "forward_price": F_solution}
    except Exception as e:
        print(f"Error solving forward price for row: {row_dict}, Error: {e}")
        return {"unique_id": row_dict["unique_id"], "forward_price": None}


# Parallel computation of forward prices.
def parallel_forward_prices(df):
    # Add a unique identifier for each row as a sequential number
    df = df.reset_index(drop=True)  # Reset index to ensure consistency
    df["unique_id"] = df.index.astype(int)  # Add unique_id based on index

    # Convert DataFrame to list of dictionaries
    data_dicts = df.to_dict(orient="records")

    with ProcessPoolExecutor() as executor:
        results = list(executor.map(solve_forward_price, data_dicts))

    # Convert results back to DataFrame
    results_df = pd.DataFrame(results)

    # Merge results with the original DataFrame on unique_id
    df = df.merge(results_df, on="unique_id", how="left")
    return df


# Computes the Greek letters: Delta, Gamma, Vega, Theta.
def calculate_greeks(F, K, r, T, sigma, contract_size, action, option_type="Call"):
    d1, d2 = calculate_d1_d2(F, K, T, sigma)

    # Delta
    if option_type == "Call":
        delta = np.exp(-r * T) * norm.cdf(d1)
    elif option_type == "Put":
        delta = np.exp(-r * T) * (norm.cdf(d1) - 1)
    else:
        raise ValueError("Invalid option type. Use 'Call' or 'Put'.")

    # Gamma
    gamma = (np.exp(-r * T) * norm.pdf(d1)) / (F * sigma * np.sqrt(T))

    # Vega
    vega = F * np.exp(-r * T) * norm.pdf(d1) * np.sqrt(T)

    # Yearly Theta
    if option_type == "Call":
        yearly_theta = (-F * norm.pdf(d1) * sigma * np.exp(-r * T) / (2 * np.sqrt(T))
                        - r * F * norm.cdf(d1) * np.exp(-r * T))
    elif option_type == "Put":
        yearly_theta = (-F * norm.pdf(d1) * sigma * np.exp(-r * T) / (2 * np.sqrt(T))
                        + r * F * norm.cdf(-d1) * np.exp(-r * T))

    # Convert to daily Theta
    daily_theta = yearly_theta / 365

    # Adjust Greeks by contract size and action (Bought = +1, Sold = -1)
    action_multiplier = 1 if action == "Bought" else -1
    delta *= contract_size * action_multiplier
    gamma *= contract_size * action_multiplier
    vega *= contract_size * action_multiplier
    daily_theta *= contract_size * action_multiplier

    return {"Delta": delta, "Gamma": gamma, "Vega": vega, "Theta": daily_theta}


# Function to process a single row
def process_row(row_dict):
    try:
        F = row_dict["forward_price"]
        K = row_dict["strike"]
        r = row_dict["risk_free_rate"]
        T = row_dict["time_to_maturity"]
        sigma = row_dict["iv"]
        contract_size = row_dict["contract_size"]
        action = row_dict["action"]
        option_type = row_dict["type"]

        # Calculate Greeks
        greeks = calculate_greeks(F, K, r, T, sigma, contract_size, action, option_type)
        greeks["unique_id"] = row_dict["unique_id"]
        return greeks
    except Exception as e:
        print(f"Error processing row: {row_dict}, Error: {e}")
        return {"unique_id": row_dict["unique_id"], "Delta": None, "Gamma": None, "Vega": None, "Theta": None}

# Parallel computation of Greeks
def parallel_calculate_greeks(df):
    # Ensure unique identifiers for each row
    df = df.reset_index(drop=True)
    df["unique_id"] = df.index

    # Convert DataFrame to list of dictionaries
    data_dicts = df.to_dict(orient="records")

    with ProcessPoolExecutor() as executor:
        results = list(executor.map(process_row, data_dicts))

    # Convert results back to DataFrame
    results_df = pd.DataFrame(results)

    # Merge results with the original DataFrame on unique_id
    df = df.merge(results_df, on="unique_id", how="left")
    return df


if __name__ == "__main__":
    '''
    # Load the DataFrame from the local pickle file
    df = pd.read_pickle("block_trade.pkl")

    # Compute forward prices in parallel
    forward_price_df = parallel_forward_prices(df)

    # Save the updated DataFrame back to a pickle file
    forward_price_df.to_pickle("block_trade_with_forward_prices.pkl")

    # Display the updated DataFrame
    print("Forward prices computed and saved successfully.")
    print(forward_price_df.head())
    '''
    # Load the DataFrame from the local pickle file
    input_path = os.path.join("data", "block_trade_with_forward_prices.pkl")
    output_path = os.path.join("data", "block_trade_with_greeks.pkl")

    df = pd.read_pickle(input_path)

    # Compute Greeks in parallel
    greeks_df = parallel_calculate_greeks(df)

    # Save the updated DataFrame back to a pickle file
    greeks_df.to_pickle(output_path)

    # Display the updated DataFrame
    print("Greeks computed and saved successfully.")
    print(greeks_df.head())