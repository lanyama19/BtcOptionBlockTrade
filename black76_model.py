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

if __name__ == "__main__":
    # Load the DataFrame from the local pickle file
    df = pd.read_pickle("block_trade.pkl")

    # Compute forward prices in parallel
    forward_price_df = parallel_forward_prices(df)

    # Save the updated DataFrame back to a pickle file
    forward_price_df.to_pickle("block_trade_with_forward_prices.pkl")

    # Display the updated DataFrame
    print("Forward prices computed and saved successfully.")
    print(forward_price_df.head())

